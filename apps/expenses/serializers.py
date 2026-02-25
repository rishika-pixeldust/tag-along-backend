"""
Serializers for the Expenses app.
All output uses camelCase to match the Flutter client.
"""
from decimal import Decimal

from rest_framework import serializers

from apps.expenses.models import Debt, Expense, ExpenseSplit


class ExpenseSplitSerializer(serializers.ModelSerializer):
    expenseId = serializers.CharField(source='expense_id', read_only=True)
    userId = serializers.CharField(source='user.id', read_only=True)
    userName = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseSplit
        fields = ['id', 'expenseId', 'userId', 'userName', 'amount']
        read_only_fields = fields

    def get_userName(self, obj):
        u = obj.user
        full = f'{u.first_name} {u.last_name}'.strip()
        return full or u.email


class ExpenseSerializer(serializers.ModelSerializer):
    groupId = serializers.CharField(source='group_id', read_only=True)
    tripId = serializers.CharField(source='trip_id', read_only=True, allow_null=True)
    paidBy = serializers.CharField(source='paid_by.id', read_only=True)
    paidByName = serializers.SerializerMethodField()
    splitType = serializers.CharField(source='split_type', read_only=True)
    receiptUrl = serializers.URLField(source='receipt_url', read_only=True, allow_blank=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'groupId', 'tripId', 'description', 'amount', 'currency',
            'category', 'paidBy', 'paidByName', 'splitType', 'receiptUrl', 'createdAt',
        ]
        read_only_fields = fields

    def get_paidByName(self, obj):
        u = obj.paid_by
        full = f'{u.first_name} {u.last_name}'.strip()
        return full or u.email


class ExpenseCreateSerializer(serializers.Serializer):
    """Accepts camelCase from Flutter, maps to snake_case model fields."""
    groupId = serializers.UUIDField()
    tripId = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(max_length=255)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='USD')
    category = serializers.CharField(max_length=20, default='other')
    splitType = serializers.CharField(max_length=20, default='equal')
    splits = serializers.ListField(child=serializers.DictField(), required=False, default=list)

    def validate(self, attrs):
        splits = attrs.get('splits', [])
        split_type = attrs.get('splitType', 'equal')
        amount = attrs.get('amount', Decimal('0'))

        if split_type == 'percentage' and splits:
            total_pct = sum(Decimal(str(s.get('percentage', 0))) for s in splits)
            if total_pct != Decimal('100'):
                raise serializers.ValidationError({'splits': 'Percentages must add up to 100.'})

        if split_type == 'exact' and splits:
            total_exact = sum(Decimal(str(s.get('amount', 0))) for s in splits)
            if total_exact != amount:
                raise serializers.ValidationError({'splits': f'Split amounts must total {amount}.'})

        from apps.groups.models import GroupMember
        user = self.context['request'].user
        group_id = attrs.get('groupId')
        if group_id and not GroupMember.objects.filter(group_id=group_id, user=user).exists():
            raise serializers.ValidationError({'groupId': 'You must be a member of this group.'})

        return attrs

    def create(self, validated_data):
        from django.utils import timezone
        splits_data = validated_data.pop('splits', [])
        expense = Expense.objects.create(
            group_id=validated_data['groupId'],
            trip_id=validated_data.get('tripId'),
            description=validated_data['description'],
            amount=validated_data['amount'],
            currency=validated_data.get('currency', 'USD'),
            category=validated_data.get('category', 'other'),
            split_type=validated_data.get('splitType', 'equal'),
            paid_by=self.context['request'].user,
            date=timezone.now().date(),
        )

        if splits_data:
            from apps.expenses.services.split_calculator import (
                calculate_equal_split,
                calculate_percentage_split,
            )

            if expense.split_type == Expense.SplitType.EQUAL:
                user_ids = [s.get('userId') or s.get('user_id') for s in splits_data]
                calculated = calculate_equal_split(expense.amount, user_ids)
                for user_id, amt in calculated.items():
                    ExpenseSplit.objects.create(expense=expense, user_id=user_id, amount=amt)
            elif expense.split_type == Expense.SplitType.PERCENTAGE:
                percentages = {
                    (s.get('userId') or s.get('user_id')): Decimal(str(s['percentage']))
                    for s in splits_data
                }
                calculated = calculate_percentage_split(expense.amount, percentages)
                for user_id, amt in calculated.items():
                    ExpenseSplit.objects.create(expense=expense, user_id=user_id, amount=amt)
            elif expense.split_type == Expense.SplitType.EXACT:
                for split in splits_data:
                    uid = split.get('userId') or split.get('user_id')
                    ExpenseSplit.objects.create(
                        expense=expense, user_id=uid,
                        amount=Decimal(str(split['amount'])),
                    )
        else:
            from apps.expenses.services.split_calculator import calculate_equal_split
            from apps.groups.models import GroupMember
            member_ids = list(
                GroupMember.objects.filter(group=expense.group).values_list('user_id', flat=True)
            )
            calculated = calculate_equal_split(expense.amount, member_ids)
            for user_id, amt in calculated.items():
                ExpenseSplit.objects.create(expense=expense, user_id=user_id, amount=amt)

        return expense


class DebtSerializer(serializers.ModelSerializer):
    groupId = serializers.CharField(source='group_id', read_only=True)
    fromUserId = serializers.CharField(source='from_user.id', read_only=True)
    fromUserName = serializers.SerializerMethodField()
    toUserId = serializers.CharField(source='to_user.id', read_only=True)
    toUserName = serializers.SerializerMethodField()
    isSettled = serializers.BooleanField(source='is_settled', read_only=True)
    settledAt = serializers.DateTimeField(source='settled_at', read_only=True)

    class Meta:
        model = Debt
        fields = [
            'id', 'groupId', 'fromUserId', 'fromUserName',
            'toUserId', 'toUserName', 'amount', 'currency',
            'isSettled', 'settledAt',
        ]
        read_only_fields = fields

    def get_fromUserName(self, obj):
        u = obj.from_user
        full = f'{u.first_name} {u.last_name}'.strip()
        return full or u.email

    def get_toUserName(self, obj):
        u = obj.to_user
        full = f'{u.first_name} {u.last_name}'.strip()
        return full or u.email


class SettleDebtSerializer(serializers.Serializer):
    debt_id = serializers.UUIDField(required=True)
