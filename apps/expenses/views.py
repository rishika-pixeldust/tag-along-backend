"""
Views for the Expenses app.
"""
import logging
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.expenses.models import Debt, Expense, ExpenseSplit
from apps.expenses.serializers import (
    DebtSerializer,
    ExpenseCreateSerializer,
    ExpenseSerializer,
    SettleDebtSerializer,
)
from apps.groups.models import GroupMember

logger = logging.getLogger(__name__)


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Expense CRUD operations.

    list:   GET    /api/v1/expenses/?group=<group_id>&trip=<trip_id>
    create: POST   /api/v1/expenses/
    read:   GET    /api/v1/expenses/{id}/
    update: PATCH  /api/v1/expenses/{id}/
    delete: DELETE /api/v1/expenses/{id}/
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Expense.objects.filter(
            group__members__user=self.request.user,
        ).select_related('paid_by', 'group', 'trip').prefetch_related(
            'splits__user'
        ).distinct()

        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)

        trip_id = self.request.query_params.get('trip')
        if trip_id:
            queryset = queryset.filter(trip_id=trip_id)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return ExpenseCreateSerializer
        return ExpenseSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expense = serializer.save()
        return Response(
            {
                'success': True,
                'data': ExpenseSerializer(expense).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ExpenseSerializer(instance)
        return Response({'success': True, 'data': serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {'success': True, 'message': 'Expense deleted.'},
            status=status.HTTP_200_OK,
        )


class DebtViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Debt operations.

    list:      GET  /api/v1/debts/?group=<group_id>
    retrieve:  GET  /api/v1/debts/{id}/
    simplify:  POST /api/v1/debts/simplify/
    settle:    POST /api/v1/debts/settle/
    """
    serializer_class = DebtSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Debt.objects.filter(
            Q(from_user=self.request.user) | Q(to_user=self.request.user),
        ).select_related('from_user', 'to_user', 'group')

        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)

        settled = self.request.query_params.get('settled')
        if settled is not None:
            queryset = queryset.filter(is_settled=settled.lower() == 'true')

        return queryset.distinct()

    @action(detail=False, methods=['post'])
    def simplify(self, request):
        """
        Simplify debts within a group using the min-cash-flow algorithm.

        POST /api/v1/debts/simplify/
        Body: {"group_id": "uuid"}
        """
        group_id = request.data.get('group_id')
        if not group_id:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'validation_error',
                        'message': 'group_id is required.',
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify user is a member
        if not GroupMember.objects.filter(group_id=group_id, user=request.user).exists():
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'forbidden',
                        'message': 'You are not a member of this group.',
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        from apps.expenses.services.debt_simplifier import simplify_debts
        simplified = simplify_debts(group_id)

        return Response(
            {
                'success': True,
                'data': DebtSerializer(simplified, many=True).data,
                'message': 'Debts simplified successfully.',
            }
        )

    @action(detail=True, methods=['post'])
    def settle(self, request, pk=None):
        """
        Mark a debt as settled.

        POST /api/v1/expenses/debts/{id}/settle/
        """
        try:
            debt = Debt.objects.get(
                id=pk,
                from_user=request.user,
                is_settled=False,
            )
        except Debt.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'not_found',
                        'message': 'Debt not found or already settled.',
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        debt.is_settled = True
        debt.settled_at = timezone.now()
        debt.save(update_fields=['is_settled', 'settled_at', 'updated_at'])

        return Response(
            {
                'success': True,
                'data': DebtSerializer(debt).data,
                'message': 'Debt settled successfully.',
            }
        )


class DebtsByGroupView(generics.ListAPIView):
    """
    List debts for a specific group.
    GET /api/v1/expenses/debts/<group_id>/
    """
    serializer_class = DebtSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        group_id = self.kwargs['group_id']
        return Debt.objects.filter(
            group_id=group_id,
        ).filter(
            Q(from_user=self.request.user) | Q(to_user=self.request.user),
        ).select_related('from_user', 'to_user', 'group').distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})


class ExpensesByGroupView(generics.ListAPIView):
    """
    List expenses for a specific group.

    GET /api/v1/expenses/group/{group_id}/
    """
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        group_id = self.kwargs['group_id']
        return Expense.objects.filter(
            group_id=group_id,
            group__members__user=self.request.user,
        ).select_related('paid_by', 'group', 'trip').prefetch_related(
            'splits__user'
        ).distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})


class ExpensesByTripView(generics.ListAPIView):
    """
    List expenses for a specific trip.

    GET /api/v1/expenses/trip/{trip_id}/
    """
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trip_id = self.kwargs['trip_id']
        return Expense.objects.filter(
            trip_id=trip_id,
            group__members__user=self.request.user,
        ).select_related('paid_by', 'group', 'trip').prefetch_related(
            'splits__user'
        ).distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})


class ExpenseSummaryView(APIView):
    """
    Get expense summary for a group.

    GET /api/v1/expenses/summary/?group=<group_id>
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        group_id = request.query_params.get('group')
        if not group_id:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'validation_error',
                        'message': 'group query parameter is required.',
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify membership
        if not GroupMember.objects.filter(group_id=group_id, user=request.user).exists():
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'forbidden',
                        'message': 'You are not a member of this group.',
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Total expenses
        total = Expense.objects.filter(group_id=group_id).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        # Per-category breakdown
        category_totals = (
            Expense.objects.filter(group_id=group_id)
            .values('category')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )

        # Per-user spending
        user_spending = (
            Expense.objects.filter(group_id=group_id)
            .values('paid_by__id', 'paid_by__first_name', 'paid_by__last_name', 'paid_by__email')
            .annotate(total_paid=Sum('amount'))
            .order_by('-total_paid')
        )

        # User's own totals
        my_paid = Expense.objects.filter(
            group_id=group_id,
            paid_by=request.user,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        my_owed = ExpenseSplit.objects.filter(
            expense__group_id=group_id,
            user=request.user,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Outstanding debts
        debts_i_owe = Debt.objects.filter(
            group_id=group_id,
            from_user=request.user,
            is_settled=False,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        debts_owed_to_me = Debt.objects.filter(
            group_id=group_id,
            to_user=request.user,
            is_settled=False,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        return Response({
            'success': True,
            'data': {
                'total_expenses': str(total),
                'category_breakdown': list(category_totals),
                'user_spending': list(user_spending),
                'my_summary': {
                    'total_paid': str(my_paid),
                    'total_owed': str(my_owed),
                    'net_balance': str(my_paid - my_owed),
                    'debts_i_owe': str(debts_i_owe),
                    'debts_owed_to_me': str(debts_owed_to_me),
                },
            },
        })
