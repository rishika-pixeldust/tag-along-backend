"""
URL configuration for the Locations app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.locations.views import (
    AlertConsentViewSet,
    GroupLocationView,
    LocationConsentViewSet,
    SendRouteAlertView,
)

app_name = 'locations'

router = DefaultRouter()
router.register(r'consents', LocationConsentViewSet, basename='location-consent')
router.register(r'alert-consents', AlertConsentViewSet, basename='alert-consent')

urlpatterns = [
    path('', include(router.urls)),
    path(
        '<uuid:group_id>/members/',
        GroupLocationView.as_view(),
        name='group-member-locations',
    ),
    path(
        'route-alerts/send/',
        SendRouteAlertView.as_view(),
        name='send-route-alert',
    ),
]
