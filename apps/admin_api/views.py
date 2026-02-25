"""
Admin API Views — authenticated endpoints consumed by the Tag Along admin dashboard.

All endpoints require authentication (IsAuthenticated).
All responses follow the standard envelope: { "success": true, "data": { ... } }
"""
from datetime import timedelta, date

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.groups.models import Group, GroupMember
from apps.trips.models import Trip
from apps.expenses.models import Expense

User = get_user_model()


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)

    # Totals
    total_users = User.objects.count()
    total_groups = Group.objects.count()
    total_trips = Trip.objects.count()
    total_expenses = Expense.objects.aggregate(s=Sum('amount'))['s'] or 0

    # Growth (compare last 30 days vs previous 30 days)
    users_this = User.objects.filter(created_at__gte=thirty_days_ago).count()
    users_prev = User.objects.filter(created_at__gte=sixty_days_ago, created_at__lt=thirty_days_ago).count()
    groups_this = Group.objects.filter(created_at__gte=thirty_days_ago).count()
    groups_prev = Group.objects.filter(created_at__gte=sixty_days_ago, created_at__lt=thirty_days_ago).count()
    trips_this = Trip.objects.filter(created_at__gte=thirty_days_ago).count()
    trips_prev = Trip.objects.filter(created_at__gte=sixty_days_ago, created_at__lt=thirty_days_ago).count()
    exp_this = Expense.objects.filter(created_at__gte=thirty_days_ago).aggregate(s=Sum('amount'))['s'] or 0
    exp_prev = Expense.objects.filter(created_at__gte=sixty_days_ago, created_at__lt=thirty_days_ago).aggregate(s=Sum('amount'))['s'] or 0

    def growth_pct(current, previous):
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round((current - previous) / previous * 100, 1)

    # Recent users per day (last 30 days)
    recent_users = []
    for i in range(29, -1, -1):
        day = (now - timedelta(days=i)).date()
        count = User.objects.filter(created_at__date=day).count()
        recent_users.append({'date': str(day), 'count': count})

    # Expenses by category
    category_totals = (
        Expense.objects
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    category_label = {
        'accommodation': 'Accommodation',
        'food': 'Food & Dining',
        'transport': 'Transport',
        'activity': 'Entertainment',
        'shopping': 'Shopping',
        'other': 'Other',
    }
    expenses_by_category = [
        {
            'category': category_label.get(row['category'], row['category'].title()),
            'total': float(row['total'] or 0),
        }
        for row in category_totals
    ]

    # Trips by week (last 12 weeks)
    trips_by_week = []
    for i in range(11, -1, -1):
        week_start = (now - timedelta(weeks=i)).date()
        week_end = week_start + timedelta(days=6)
        count = Trip.objects.filter(created_at__date__range=[week_start, week_end]).count()
        trips_by_week.append({'week': f'Week {12 - i}', 'count': count})

    # Recent activity (last 20 events across users, groups, trips, expenses)
    activity = []

    recent_joined = User.objects.order_by('-created_at')[:5]
    for u in recent_joined:
        activity.append({
            'id': f'user-joined-{u.id}',
            'type': 'user_joined',
            'description': f'{u.get_full_name() or u.email} joined Tag Along',
            'userName': u.get_full_name() or u.email,
            'userAvatar': u.avatar or None,
            'timestamp': u.created_at.isoformat(),
        })

    recent_groups = Group.objects.select_related('created_by').order_by('-created_at')[:5]
    for g in recent_groups:
        name = g.created_by.get_full_name() or g.created_by.email
        activity.append({
            'id': f'group-created-{g.id}',
            'type': 'group_created',
            'description': f'{name} created group "{g.name}"',
            'userName': name,
            'userAvatar': g.created_by.avatar or None,
            'timestamp': g.created_at.isoformat(),
        })

    recent_trips = Trip.objects.select_related('created_by').order_by('-created_at')[:5]
    for t in recent_trips:
        name = t.created_by.get_full_name() or t.created_by.email
        activity.append({
            'id': f'trip-created-{t.id}',
            'type': 'trip_created',
            'description': f'{name} planned trip "{t.name}"',
            'userName': name,
            'userAvatar': t.created_by.avatar or None,
            'timestamp': t.created_at.isoformat(),
        })

    recent_expenses = Expense.objects.select_related('paid_by').order_by('-created_at')[:5]
    for e in recent_expenses:
        name = e.paid_by.get_full_name() or e.paid_by.email
        activity.append({
            'id': f'expense-added-{e.id}',
            'type': 'expense_added',
            'description': f'{name} added expense "{e.description}"',
            'userName': name,
            'userAvatar': e.paid_by.avatar or None,
            'timestamp': e.created_at.isoformat(),
        })

    activity.sort(key=lambda x: x['timestamp'], reverse=True)
    activity = activity[:10]

    return Response({
        'success': True,
        'data': {
            'totalUsers': total_users,
            'totalGroups': total_groups,
            'totalTrips': total_trips,
            'totalExpenses': float(total_expenses),
            'userGrowth': growth_pct(users_this, users_prev),
            'groupGrowth': growth_pct(groups_this, groups_prev),
            'tripGrowth': growth_pct(trips_this, trips_prev),
            'expenseGrowth': growth_pct(float(exp_this), float(exp_prev)),
            'recentUsers': recent_users,
            'expensesByCategory': expenses_by_category,
            'tripsByWeek': trips_by_week,
            'recentActivity': activity,
        },
    })


# ---------------------------------------------------------------------------
# Admin Users
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_users_list(request):
    search = request.query_params.get('search', '').strip()
    page = int(request.query_params.get('page', 1))
    limit = int(request.query_params.get('limit', 20))

    qs = User.objects.annotate(
        group_count=Count('group_memberships', distinct=True),
        trip_count_ann=Count('created_trips', distinct=True),
    ).order_by('-created_at')

    if search:
        qs = qs.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    total = qs.count()
    offset = (page - 1) * limit
    users = list(qs[offset: offset + limit])

    users_data = []
    for u in users:
        full_name = u.get_full_name() or u.email.split('@')[0]
        users_data.append({
            'id': str(u.id),
            'email': u.email,
            'displayName': full_name,
            'firstName': u.first_name or '',
            'lastName': u.last_name or '',
            'avatarUrl': u.avatar or None,
            'phone': getattr(u, 'phone', '') or '',
            'status': 'active' if u.is_active else 'inactive',
            'role': 'admin' if u.is_staff else 'user',
            'groupCount': u.group_count,
            'tripCount': u.trip_count_ann,
            'createdAt': u.created_at.isoformat(),
            'updatedAt': u.updated_at.isoformat(),
            'lastLoginAt': u.last_login.isoformat() if u.last_login else u.created_at.isoformat(),
        })

    return Response({
        'success': True,
        'data': {
            'users': users_data,
            'total': total,
            'totalPages': max(1, (total + limit - 1) // limit),
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_user_detail(request, user_id):
    try:
        u = User.objects.annotate(
            group_count=Count('group_memberships', distinct=True),
            trip_count_ann=Count('created_trips', distinct=True),
        ).get(id=user_id)
    except User.DoesNotExist:
        return Response({'success': False, 'error': {'message': 'User not found'}}, status=404)

    full_name = u.get_full_name() or u.email.split('@')[0]
    return Response({
        'success': True,
        'data': {
            'id': str(u.id),
            'email': u.email,
            'displayName': full_name,
            'firstName': u.first_name or '',
            'lastName': u.last_name or '',
            'avatarUrl': u.avatar or None,
            'phone': getattr(u, 'phone', '') or '',
            'status': 'active' if u.is_active else 'inactive',
            'role': 'admin' if u.is_staff else 'user',
            'groupCount': u.group_count,
            'tripCount': u.trip_count_ann,
            'createdAt': u.created_at.isoformat(),
            'updatedAt': u.updated_at.isoformat(),
            'lastLoginAt': u.last_login.isoformat() if u.last_login else u.created_at.isoformat(),
        },
    })


# ---------------------------------------------------------------------------
# Admin Groups
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_groups_list(request):
    search = request.query_params.get('search', '').strip()
    page = int(request.query_params.get('page', 1))
    limit = int(request.query_params.get('limit', 20))

    qs = Group.objects.select_related('created_by').annotate(
        trip_count=Count('trips', distinct=True),
        member_count_ann=Count('members', distinct=True),
    ).order_by('-created_at')

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

    total = qs.count()
    offset = (page - 1) * limit
    groups = qs[offset: offset + limit]

    groups_data = []
    for g in groups:
        creator_name = g.created_by.get_full_name() or g.created_by.email
        members_qs = GroupMember.objects.select_related('user').filter(group=g)
        members_data = []
        for m in members_qs:
            members_data.append({
                'id': str(m.id),
                'userId': str(m.user.id),
                'displayName': m.user.get_full_name() or m.user.email,
                'avatarUrl': m.user.avatar or None,
                'email': m.user.email,
                'role': 'owner' if m.role == 'admin' else 'member',
                'joinedAt': m.joined_at.isoformat(),
            })
        groups_data.append({
            'id': str(g.id),
            'name': g.name,
            'description': g.description or '',
            'imageUrl': g.photo or None,
            'createdBy': str(g.created_by.id),
            'createdByName': creator_name,
            'memberCount': g.member_count_ann,
            'tripCount': g.trip_count,
            'status': 'active' if g.is_active else 'archived',
            'members': members_data,
            'createdAt': g.created_at.isoformat(),
            'updatedAt': g.updated_at.isoformat(),
        })

    return Response({
        'success': True,
        'data': {
            'groups': groups_data,
            'total': total,
            'totalPages': max(1, (total + limit - 1) // limit),
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_group_detail(request, group_id):
    try:
        g = Group.objects.select_related('created_by').annotate(
            trip_count=Count('trips', distinct=True),
            member_count_ann=Count('members', distinct=True),
        ).get(id=group_id)
    except Group.DoesNotExist:
        return Response({'success': False, 'error': {'message': 'Group not found'}}, status=404)

    members_qs = GroupMember.objects.select_related('user').filter(group=g)
    members_data = [{
        'id': str(m.id),
        'userId': str(m.user.id),
        'displayName': m.user.get_full_name() or m.user.email,
        'avatarUrl': m.user.avatar or None,
        'email': m.user.email,
        'role': 'owner' if m.role == 'admin' else 'member',
        'joinedAt': m.joined_at.isoformat(),
    } for m in members_qs]

    creator_name = g.created_by.get_full_name() or g.created_by.email
    return Response({
        'success': True,
        'data': {
            'id': str(g.id),
            'name': g.name,
            'description': g.description or '',
            'imageUrl': g.photo or None,
            'createdBy': str(g.created_by.id),
            'createdByName': creator_name,
            'memberCount': g.member_count_ann,
            'tripCount': g.trip_count,
            'status': 'active' if g.is_active else 'archived',
            'members': members_data,
            'createdAt': g.created_at.isoformat(),
            'updatedAt': g.updated_at.isoformat(),
        },
    })


# ---------------------------------------------------------------------------
# Admin Trips
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_trips_list(request):
    search = request.query_params.get('search', '').strip()
    status_filter = request.query_params.get('status', '').strip()
    page = int(request.query_params.get('page', 1))
    limit = int(request.query_params.get('limit', 20))

    qs = Trip.objects.select_related('group', 'created_by').annotate(
        stop_count_ann=Count('stops', distinct=True),
        expense_count_ann=Count('expenses', distinct=True),
        total_expenses_ann=Sum('expenses__amount'),
    ).order_by('-created_at')

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(group__name__icontains=search))
    if status_filter:
        qs = qs.filter(status=status_filter)

    total = qs.count()
    offset = (page - 1) * limit
    trips = qs[offset: offset + limit]

    trips_data = []
    for t in trips:
        creator_name = t.created_by.get_full_name() or t.created_by.email
        trips_data.append({
            'id': str(t.id),
            'name': t.name,
            'description': t.description or '',
            'groupId': str(t.group.id),
            'groupName': t.group.name,
            'startDate': str(t.start_date) if t.start_date else None,
            'endDate': str(t.end_date) if t.end_date else None,
            'status': t.status,
            'stopCount': t.stop_count_ann,
            'expenseCount': t.expense_count_ann,
            'totalExpenses': float(t.total_expenses_ann or 0),
            'currency': 'USD',
            'stops': [],
            'createdBy': str(t.created_by.id),
            'createdByName': creator_name,
            'createdAt': t.created_at.isoformat(),
            'updatedAt': t.updated_at.isoformat(),
        })

    return Response({
        'success': True,
        'data': {
            'trips': trips_data,
            'total': total,
            'totalPages': max(1, (total + limit - 1) // limit),
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_trip_detail(request, trip_id):
    try:
        t = Trip.objects.select_related('group', 'created_by').annotate(
            stop_count_ann=Count('stops', distinct=True),
            expense_count_ann=Count('expenses', distinct=True),
            total_expenses_ann=Sum('expenses__amount'),
        ).get(id=trip_id)
    except Trip.DoesNotExist:
        return Response({'success': False, 'error': {'message': 'Trip not found'}}, status=404)

    creator_name = t.created_by.get_full_name() or t.created_by.email
    return Response({
        'success': True,
        'data': {
            'id': str(t.id),
            'name': t.name,
            'description': t.description or '',
            'groupId': str(t.group.id),
            'groupName': t.group.name,
            'startDate': str(t.start_date) if t.start_date else None,
            'endDate': str(t.end_date) if t.end_date else None,
            'status': t.status,
            'stopCount': t.stop_count_ann,
            'expenseCount': t.expense_count_ann,
            'totalExpenses': float(t.total_expenses_ann or 0),
            'currency': 'USD',
            'stops': [],
            'createdBy': str(t.created_by.id),
            'createdByName': creator_name,
            'createdAt': t.created_at.isoformat(),
            'updatedAt': t.updated_at.isoformat(),
        },
    })


# ---------------------------------------------------------------------------
# Admin Expenses
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_expenses_list(request):
    search = request.query_params.get('search', '').strip()
    category_filter = request.query_params.get('category', '').strip()
    page = int(request.query_params.get('page', 1))
    limit = int(request.query_params.get('limit', 20))

    qs = Expense.objects.select_related('group', 'trip', 'paid_by').order_by('-created_at')

    if search:
        qs = qs.filter(
            Q(description__icontains=search) |
            Q(group__name__icontains=search) |
            Q(paid_by__first_name__icontains=search) |
            Q(paid_by__last_name__icontains=search)
        )
    if category_filter:
        qs = qs.filter(category=category_filter)

    total = qs.count()
    offset = (page - 1) * limit
    expenses = qs[offset: offset + limit]

    expenses_data = []
    for e in expenses:
        paid_by_name = e.paid_by.get_full_name() or e.paid_by.email
        # Map backend category to frontend expected values
        cat_map = {
            'accommodation': 'accommodation',
            'food': 'food',
            'transport': 'transport',
            'activity': 'entertainment',
            'shopping': 'shopping',
            'other': 'other',
        }
        expenses_data.append({
            'id': str(e.id),
            'description': e.description,
            'amount': float(e.amount),
            'currency': e.currency,
            'category': cat_map.get(e.category, e.category),
            'paidBy': str(e.paid_by.id),
            'paidByName': paid_by_name,
            'paidByAvatar': e.paid_by.avatar or None,
            'groupId': str(e.group.id),
            'groupName': e.group.name,
            'tripId': str(e.trip.id) if e.trip else None,
            'tripName': e.trip.name if e.trip else None,
            'receiptUrl': e.receipt_url or None,
            'splits': [],
            'createdAt': e.created_at.isoformat(),
            'updatedAt': e.updated_at.isoformat(),
        })

    return Response({
        'success': True,
        'data': {
            'expenses': expenses_data,
            'total': total,
            'totalPages': max(1, (total + limit - 1) // limit),
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_expense_detail(request, expense_id):
    try:
        e = Expense.objects.select_related('group', 'trip', 'paid_by').get(id=expense_id)
    except Expense.DoesNotExist:
        return Response({'success': False, 'error': {'message': 'Expense not found'}}, status=404)

    paid_by_name = e.paid_by.get_full_name() or e.paid_by.email
    cat_map = {
        'accommodation': 'accommodation',
        'food': 'food',
        'transport': 'transport',
        'activity': 'entertainment',
        'shopping': 'shopping',
        'other': 'other',
    }
    return Response({
        'success': True,
        'data': {
            'id': str(e.id),
            'description': e.description,
            'amount': float(e.amount),
            'currency': e.currency,
            'category': cat_map.get(e.category, e.category),
            'paidBy': str(e.paid_by.id),
            'paidByName': paid_by_name,
            'paidByAvatar': e.paid_by.avatar or None,
            'groupId': str(e.group.id),
            'groupName': e.group.name,
            'tripId': str(e.trip.id) if e.trip else None,
            'tripName': e.trip.name if e.trip else None,
            'receiptUrl': e.receipt_url or None,
            'splits': [],
            'createdAt': e.created_at.isoformat(),
            'updatedAt': e.updated_at.isoformat(),
        },
    })
