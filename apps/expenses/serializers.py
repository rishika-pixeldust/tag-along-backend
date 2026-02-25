"""
Serializers for the Expenses app.
"""
from decimal import Decimal

from rest_framework import serializers

from apps.expenses.models import Debt, Expense, ExpenseSplit
from apps.users.serializers import UserSerializer


class ExpenseSplitSerializer(serializers.ModelSerializer):
    """
    Serializer for ExpenseSplit instances.
    """
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = ExpenseSplit
        fields = [
            'id',
            'user',
            'user_id',
            'amount',
            'amount_base',
            'base_currency',
        ]
        read_only_fields = ['id', 'amount_base', 'base_currency']


class ExpenseSerializer(serializers.ModelSerializer):
    """
    Read serializer for Expense instances.
    """
    paid_by = UserSerializer(read_only=True)
    splits = ExpenseSplitSerializer(many=True, read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id',
            'group',
            'trip',
            'description',
            'amount',
            'currency',
            'category',
            'split_type',
            'paid_by',
            'receipt_url',
            'notes',
            'date',
            'splits',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ExpenseCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an expense with splits.
    """
    splits = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text='List of {"user_id": "uuid", "amount": 10.00} or {"user_id": "uuid", "percentage": 50}',
    )

    class Meta:
        model = Expense
        fields = [
            'group',
            'trip',
            'description',
            'amount',
            'currency',
            'category',
            'split_type',
            'receipt_url',
            'notes',
            'date',
            'splits',
        ]

    def validate(self, attrs):
        splits = attrs.get('splits', [])
        split_type = attrs.get('split_type', 'equal')
        amount = attrs.get('amount', Decimal('0'))

        if split_type == 'percentage' and splits:
            total_pct = sum(Decimal(str(s.get('percentage', 0))) for s in splits)
            if total_pct != Decimal('100'):
                raise serializers.ValidationError(
                    {'splits': 'Percentages must add up to 100.'}
                )

        if split_type == 'exact' and splits:
            total_exact = sum(Decimal(str(s.get('amount', 0))) for s in splits)
            if total_exact != amount:
                raise serializers.ValidationError(
                    {'splits': f'Split amounts must total {amount}.'}
                )

        # Verify user is a member of the group
        from apps.groups.models import GroupMember
        user = self.context['request'].user
        group = attrs.get('group')
        if group and not GroupMember.objects.filter(group=group, user=user).exists():
            raise serializers.ValidationError(
                {'group': 'You must be a member of this group.'}
            )

        return attrs

    def create(self, validated_data):
        splits_data = validated_data.pop('splits', [])
        validated_data['paid_by'] = self.context['request'].user
        expense = Expense.objects.create(**validated_data)

        if splits_data:
            from apps.expenses.services.split_calculator import (
                calculate_equal_split,
                calculate_exact_split,
                calculate_percentage_split,
            )

            if expense.split_type == Expense.SplitType.EQUAL:
                user_ids = [s['user_id'] for s in splits_data]
                calculated = calculate_equal_split(expense.amount, user_ids)
                for user_id, amount in calculated.items():
                    ExpenseSplit.objects.create(
                        expense=expense,
                        user_id=user_id,
                        amount=amount,
                    )
            elif expense.split_type == Expense.SplitType.PERCENTAGE:
                percentages = {s['user_id']: Decimal(str(s['percentage'])) for s in splits_data}
                calculated = calculate_percentage_split(expense.amount, percentages)
                for user_id, amount in calculated.items():
                    ExpenseSplit.objects.create(
                        expense=expense,
                        user_id=user_id,
                        amount=amount,
                    )
            elif expense.split_type == Expense.SplitType.EXACT:
                for split in splits_data:
                    ExpenseSplit.objects.create(
                        expense=expense,
                        user_id=split['user_id'],
                        amount=Decimal(str(split['amount'])),
                    )
        else:
            # Auto equal split among all group members
            from apps.expenses.services.split_calculator import calculate_equal_split
            from apps.groups.models import GroupMember

            member_ids = list(
                GroupMember.objects.filter(group=expense.group)
                .values_list('user_id', flat=True)
            )
            calculated = calculate_equal_split(expense.amount, member_ids)
            for user_id, amount in calculated.items():
                ExpenseSplit.objects.create(
                    expense=expense,
                    user_id=user_id,
                    amount=amount,
                )

        return expense


class DebtSerializer(serializers.ModelSerializer):
    """
    Serializer for Debt instances.
    """
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)

    class Meta:
        model = Debt
        fields = [
            'id',
            'group',
            'from_user',
            'to_user',
            'amount',
            'currency',
            'is_settled',
            'settled_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SettleDebtSerializer(serializers.Serializer):
    """
    Serializer for settling a debt.
    """
    debt_id = serializers.UUIDField(required=True)
