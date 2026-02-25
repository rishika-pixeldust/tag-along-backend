"""
Models for the Expenses app.
"""
from django.conf import settings
from django.db import models

from common.models import TimestampedModel


class Expense(TimestampedModel):
    """
    An expense recorded within a group, optionally tied to a trip.
    """
    class Category(models.TextChoices):
        FOOD = 'food', 'Food & Drinks'
        TRANSPORT = 'transport', 'Transport'
        ACCOMMODATION = 'accommodation', 'Accommodation'
        ACTIVITY = 'activity', 'Activity'
        SHOPPING = 'shopping', 'Shopping'
        OTHER = 'other', 'Other'

    class SplitType(models.TextChoices):
        EQUAL = 'equal', 'Equal'
        PERCENTAGE = 'percentage', 'Percentage'
        EXACT = 'exact', 'Exact Amount'

    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='expenses',
    )
    trip = models.ForeignKey(
        'trips.Trip',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses',
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text='ISO 4217 currency code.',
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
        db_index=True,
    )
    split_type = models.CharField(
        max_length=20,
        choices=SplitType.choices,
        default=SplitType.EQUAL,
    )
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='paid_expenses',
    )
    receipt_url = models.URLField(max_length=500, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    date = models.DateField()

    class Meta:
        db_table = 'expenses'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.description} - {self.currency} {self.amount}'


class ExpenseSplit(TimestampedModel):
    """
    How an expense is split among users.
    """
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name='splits',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expense_splits',
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Amount owed by this user in the expense currency.',
    )
    amount_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Amount converted to the base/group currency.',
    )
    base_currency = models.CharField(
        max_length=3,
        blank=True,
        default='',
        help_text='The base currency this was converted to.',
    )

    class Meta:
        db_table = 'expense_splits'
        unique_together = ['expense', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} owes {self.amount} for {self.expense}'


class Debt(TimestampedModel):
    """
    A simplified debt between two users within a group.
    """
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='debts',
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='debts_owed',
        help_text='The user who owes money.',
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='debts_receivable',
        help_text='The user who is owed money.',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text='ISO 4217 currency code.',
    )
    is_settled = models.BooleanField(default=False, db_index=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'debts'
        ordering = ['-created_at']

    def __str__(self):
        status_str = 'settled' if self.is_settled else 'pending'
        return (
            f'{self.from_user} -> {self.to_user}: '
            f'{self.currency} {self.amount} ({status_str})'
        )
