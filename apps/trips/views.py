"""
Views for the Trips app.
"""
import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.groups.models import GroupMember
from apps.trips.models import Trip, TripStop
from apps.trips.permissions import IsTripGroupMember
from apps.trips.serializers import (
    TripCreateSerializer,
    TripSerializer,
    TripStopCreateSerializer,
    TripStopReorderSerializer,
    TripStopSerializer,
)

logger = logging.getLogger(__name__)


class TripViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Trip CRUD operations.

    list:   GET    /api/v1/trips/?group=<group_id>
    create: POST   /api/v1/trips/
    read:   GET    /api/v1/trips/{id}/
    update: PATCH  /api/v1/trips/{id}/
    delete: DELETE /api/v1/trips/{id}/
    """
    permission_classes = [IsAuthenticated, IsTripGroupMember]

    def get_queryset(self):
        queryset = Trip.objects.filter(
            group__members__user=self.request.user,
        ).select_related('created_by', 'group').prefetch_related('stops__added_by').distinct()

        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)

        trip_status = self.request.query_params.get('status')
        if trip_status:
            queryset = queryset.filter(status=trip_status)

        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return TripCreateSerializer
        return TripSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip = serializer.save()
        return Response(
            {
                'success': True,
                'data': TripSerializer(trip).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = TripSerializer(instance)
        return Response({'success': True, 'data': serializer.data})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = TripSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'data': serializer.data})


class TripStopViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TripStop CRUD operations.

    list:    GET    /api/v1/trips/{trip_id}/stops/
    create:  POST   /api/v1/trips/{trip_id}/stops/
    read:    GET    /api/v1/trips/{trip_id}/stops/{id}/
    update:  PATCH  /api/v1/trips/{trip_id}/stops/{id}/
    delete:  DELETE /api/v1/trips/{trip_id}/stops/{id}/
    reorder: POST   /api/v1/trips/{trip_id}/stops/reorder/
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TripStop.objects.filter(
            trip_id=self.kwargs['trip_pk'],
        ).select_related('added_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return TripStopCreateSerializer
        if self.action == 'reorder':
            return TripStopReorderSerializer
        return TripStopSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['trip_id'] = self.kwargs.get('trip_pk')
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stop = serializer.save()
        return Response(
            {
                'success': True,
                'data': TripStopSerializer(stop).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'])
    def reorder(self, request, trip_pk=None):
        """
        Reorder stops within a trip.

        POST /api/v1/trips/{trip_id}/stops/reorder/
        Body: {"stop_ids": ["uuid1", "uuid2", "uuid3"]}
        """
        serializer = TripStopReorderSerializer(
            data=request.data,
            context={'trip_id': trip_pk},
        )
        serializer.is_valid(raise_exception=True)

        stop_ids = serializer.validated_data['stop_ids']
        for order, stop_id in enumerate(stop_ids):
            TripStop.objects.filter(id=stop_id, trip_id=trip_pk).update(order=order)

        stops = TripStop.objects.filter(trip_id=trip_pk).order_by('order')
        return Response(
            {
                'success': True,
                'data': TripStopSerializer(stops, many=True).data,
            }
        )
