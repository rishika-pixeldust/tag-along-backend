"""
URL configuration for the Expenses app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.expenses.views import (
    DebtsByGroupView,
    DebtViewSet,
    ExpensesByGroupView,
    ExpensesByTripView,
    ExpenseSummaryView,
    ExpenseViewSet,
)

app_name = 'expenses'

router = DefaultRouter()
router.register(r'', ExpenseViewSet, basename='expense')
router.register(r'debts', DebtViewSet, basename='debt')

urlpatterns = [
    path('', include(router.urls)),
    path('group/<uuid:group_id>/', ExpensesByGroupView.as_view(), name='expenses-by-group'),
    path('trip/<uuid:trip_id>/', ExpensesByTripView.as_view(), name='expenses-by-trip'),
    path('debts/<uuid:group_id>/', DebtsByGroupView.as_view(), name='debts-by-group'),
    path('summary/', ExpenseSummaryView.as_view(), name='expense-summary'),
]
