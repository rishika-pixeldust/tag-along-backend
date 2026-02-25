"""
Views for the Locations app.

Provides endpoints for managing location-sharing consent and
retrieving group member locations from Firestore.
"""
import logging

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.groups.models import GroupMember
from apps.locations.models import AlertConsent, LocationConsent, RouteAlert
from apps.locations.serializers import (
    AlertConsentCreateSerializer,
    AlertConsentSerializer,
    LocationConsentCreateSerializer,
    LocationConsentSerializer,
    RouteAlertCreateSerializer,
    RouteAlertSerializer,
)

logger = logging.getLogger(__name__)


class LocationConsentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for LocationConsent CRUD.

    list:    GET    /api/v1/locations/consents/
    create:  POST   /api/v1/locations/consents/
    read:    GET    /api/v1/locations/consents/{id}/
    revoke:  POST   /api/v1/locations/consents/{id}/revoke/
    """
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = LocationConsent.objects.filter(
            user=self.request.user,
        ).select_related('user', 'group')

        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)

        active_only = self.request.query_params.get('active')
        if active_only is not None and active_only.lower() == 'true':
            queryset = queryset.filter(is_active=True, end_date__gte=timezone.now())

        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return LocationConsentCreateSerializer
        return LocationConsentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consent = serializer.save()
        return Response(
            {
                'success': True,
                'data': LocationConsentSerializer(consent).data,
                'message': 'Location consent granted.',
            },
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = LocationConsentSerializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """
        Revoke an active location consent.

        POST /api/v1/locations/consents/{id}/revoke/
        """
        try:
            consent = LocationConsent.objects.get(
                id=pk,
                user=request.user,
                is_active=True,
            )
        except LocationConsent.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'not_found',
                        'message': 'Active consent not found.',
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        consent.is_active = False
        consent.revoked_at = timezone.now()
        consent.save(update_fields=['is_active', 'revoked_at', 'updated_at'])

        return Response(
            {
                'success': True,
                'data': LocationConsentSerializer(consent).data,
                'message': 'Location consent revoked.',
            }
        )


class GroupLocationView(APIView):
    """
    Retrieve the current locations of group members who have given
    active consent.

    GET /api/v1/locations/groups/{group_id}/members/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        # Verify the requester is a member of the group
        if not GroupMember.objects.filter(group_id=group_id, user=request.user).exists():
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'forbidden',
                        'message': 'You are not a member of this group.',
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Find members with active, non-expired consent
        now = timezone.now()
        consented_user_ids = list(
            LocationConsent.objects.filter(
                group_id=group_id,
                is_active=True,
                start_date__lte=now,
                end_date__gte=now,
            ).values_list('user_id', flat=True)
        )

        if not consented_user_ids:
            return Response({
                'success': True,
                'data': [],
                'message': 'No members are currently sharing their location.',
            })

        # Fetch locations from Firestore
        try:
            from apps.locations.services.firebase_location import FirebaseLocationService
            location_service = FirebaseLocationService()
            locations = location_service.get_group_member_locations(
                group_id=str(group_id),
                member_ids=[str(uid) for uid in consented_user_ids],
            )
        except Exception as exc:
            logger.error(
                'Failed to fetch locations for group %s: %s',
                group_id,
                exc,
            )
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'service_error',
                        'message': 'Unable to retrieve locations at this time.',
                    },
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            'success': True,
            'data': locations,
        })


class AlertConsentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for alert consent (voice route-deviation alerts on loudspeaker).

    list:           GET    /api/v1/locations/alert-consents/
    create:         POST   /api/v1/locations/alert-consents/
    revoke:         POST   /api/v1/locations/alert-consents/{id}/revoke/
    group_consents: GET    /api/v1/locations/alert-consents/group/{group_id}/
    """
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = AlertConsent.objects.filter(
            user=self.request.user,
        ).select_related('user', 'group')

        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)

        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return AlertConsentCreateSerializer
        return AlertConsentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consent = serializer.save()
        return Response(
            {
                'success': True,
                'data': AlertConsentSerializer(consent).data,
                'message': 'Alert consent granted.',
            },
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = AlertConsentSerializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke an active alert consent."""
        try:
            consent = AlertConsent.objects.get(
                id=pk,
                user=request.user,
                is_active=True,
            )
        except AlertConsent.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'not_found',
                        'message': 'Active alert consent not found.',
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        consent.is_active = False
        consent.revoked_at = timezone.now()
        consent.save(update_fields=['is_active', 'revoked_at', 'updated_at'])

        return Response({
            'success': True,
            'data': AlertConsentSerializer(consent).data,
            'message': 'Alert consent revoked.',
        })

    @action(detail=False, methods=['get'], url_path='group/(?P<group_id>[^/.]+)')
    def group_consents(self, request, group_id=None):
        """
        List all members with active alert consent in a group.
        Useful for senders to know who can receive alerts.

        GET /api/v1/locations/alert-consents/group/{group_id}/
        """
        if not GroupMember.objects.filter(
            group_id=group_id, user=request.user
        ).exists():
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'forbidden',
                        'message': 'You are not a member of this group.',
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        consents = AlertConsent.objects.filter(
            group_id=group_id,
            is_active=True,
        ).select_related('user', 'group')

        return Response({
            'success': True,
            'data': AlertConsentSerializer(consents, many=True).data,
        })


class SendRouteAlertView(APIView):
    """
    Send a route deviation alert to a group member.
    Creates a RouteAlert record, writes a Firestore notification for
    real-time delivery, and sends an FCM push notification as backup.

    POST /api/v1/locations/route-alerts/send/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RouteAlertCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        sender = request.user

        # Create audit record
        alert = RouteAlert.objects.create(
            sender=sender,
            recipient_id=data['recipient_id'],
            group_id=data['group_id'],
            trip_id=data['trip_id'],
            message=data['message'],
        )

        # Deliver via Firestore + FCM
        try:
            from apps.locations.services.firebase_alert import FirebaseAlertService
            alert_service = FirebaseAlertService()
            alert_service.send_alert_notification(
                alert_id=str(alert.id),
                recipient_id=str(data['recipient_id']),
                sender_id=str(sender.id),
                sender_name=sender.get_full_name() or sender.email,
                message=data['message'],
                group_id=str(data['group_id']),
                trip_id=str(data['trip_id']),
            )
            alert.delivered_at = timezone.now()
            alert.save(update_fields=['delivered_at', 'updated_at'])
        except Exception as exc:
            logger.error(
                'Failed to deliver route alert %s: %s',
                alert.id,
                exc,
            )
            # Alert record still exists — delivery can be retried

        return Response(
            {
                'success': True,
                'data': RouteAlertSerializer(alert).data,
                'message': 'Route alert sent.',
            },
            status=status.HTTP_201_CREATED,
        )
