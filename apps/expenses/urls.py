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

urlpatterns = [
    # Explicit paths BEFORE router to avoid conflicts with router's {pk} patterns
    path('group/<uuid:group_id>/', ExpensesByGroupView.as_view(), name='expenses-by-group'),
    path('trip/<uuid:trip_id>/', ExpensesByTripView.as_view(), name='expenses-by-trip'),
    path('summary/', ExpenseSummaryView.as_view(), name='expense-summary'),
    # Debt endpoints — NOT using router (avoids {pk} vs {group_id} conflict)
    path('debts/<uuid:group_id>/', DebtsByGroupView.as_view(), name='debts-by-group'),
    path('debts/<uuid:pk>/settle/', DebtViewSet.as_view({'post': 'settle'}), name='debt-settle'),
    path('debts/simplify/', DebtViewSet.as_view({'post': 'simplify'}), name='debt-simplify'),
    path('', include(router.urls)),
]
