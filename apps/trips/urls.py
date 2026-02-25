"""
URL configuration for the Trips app.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.trips.views import TripStopViewSet, TripViewSet

app_name = 'trips'

router = DefaultRouter()
router.register(r'trips', TripViewSet, basename='trip')

# Nested routes for trip stops
stop_list = TripStopViewSet.as_view({
    'get': 'list',
    'post': 'create',
})
stop_detail = TripStopViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',
    'put': 'update',
    'delete': 'destroy',
})
stop_reorder = TripStopViewSet.as_view({
    'post': 'reorder',
})

urlpatterns = [
    path('', include(router.urls)),
    path(
        'trips/<uuid:trip_pk>/stops/',
        stop_list,
        name='trip-stop-list',
    ),
    path(
        'trips/<uuid:trip_pk>/stops/reorder/',
        stop_reorder,
        name='trip-stop-reorder',
    ),
    path(
        'trips/<uuid:trip_pk>/stops/<uuid:pk>/',
        stop_detail,
        name='trip-stop-detail',
    ),
]
