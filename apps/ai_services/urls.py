"""
URL configuration for the AI Services app.
"""
from django.urls import path

from apps.ai_services.views import (
    CategorizeExpenseView,
    PlanTripView,
    ScanBillView,
)

app_name = 'ai_services'

urlpatterns = [
    path('scan-bill/', ScanBillView.as_view(), name='scan-bill'),
    path('plan-trip/', PlanTripView.as_view(), name='plan-trip'),
    path('categorize-expense/', CategorizeExpenseView.as_view(), name='categorize-expense'),
]
