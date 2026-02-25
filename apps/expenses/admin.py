"""
Admin configuration for the Expenses app.
"""
from django.contrib import admin

from apps.expenses.models import Debt, Expense, ExpenseSplit


class ExpenseSplitInline(admin.TabularInline):
    model = ExpenseSplit
    extra = 0


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = [
        'description',
        'amount',
        'currency',
        'category',
        'split_type',
        'paid_by',
        'group',
        'date',
    ]
    list_filter = ['category', 'split_type', 'currency', 'date']
    search_fields = ['description', 'notes', 'paid_by__email']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ExpenseSplitInline]


@admin.register(ExpenseSplit)
class ExpenseSplitAdmin(admin.ModelAdmin):
    list_display = ['expense', 'user', 'amount', 'amount_base', 'base_currency']
    list_filter = ['base_currency']
    search_fields = ['user__email', 'expense__description']


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = [
        'from_user',
        'to_user',
        'amount',
        'currency',
        'is_settled',
        'group',
        'created_at',
    ]
    list_filter = ['is_settled', 'currency', 'created_at']
    search_fields = ['from_user__email', 'to_user__email']
