"""
URL configuration for the Expenses app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.expenses.views import DebtViewSet, ExpenseSummaryView, ExpenseViewSet

app_name = 'expenses'

router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'debts', DebtViewSet, basename='debt')

urlpatterns = [
    path('', include(router.urls)),
    path('expenses/summary/', ExpenseSummaryView.as_view(), name='expense-summary'),
]
