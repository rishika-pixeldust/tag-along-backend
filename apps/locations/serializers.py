"""
Serializers for the Locations app.
"""
from django.utils import timezone
from rest_framework import serializers

from apps.locations.models import AlertConsent, LocationConsent, RouteAlert
from apps.users.serializers import UserSerializer


class LocationConsentSerializer(serializers.ModelSerializer):
    """
    Read serializer for LocationConsent instances.
    """
    user = UserSerializer(read_only=True)

    class Meta:
        model = LocationConsent
        fields = [
            'id',
            'user',
            'group',
            'start_date',
            'end_date',
            'is_active',
            'agreed_at',
            'revoked_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'is_active',
            'agreed_at',
            'revoked_at',
            'created_at',
            'updated_at',
        ]


class LocationConsentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new location consent.
    """

    class Meta:
        model = LocationConsent
        fields = [
            'group',
            'start_date',
            'end_date',
        ]

    def validate(self, attrs):
        # Ensure start_date < end_date
        if attrs['start_date'] >= attrs['end_date']:
            raise serializers.ValidationError(
                {'end_date': 'End date must be after start date.'}
            )

        # Ensure end_date is in the future
        if attrs['end_date'] <= timezone.now():
            raise serializers.ValidationError(
                {'end_date': 'End date must be in the future.'}
            )

        # Verify the user is a member of the group
        from apps.groups.models import GroupMember
        user = self.context['request'].user
        group = attrs['group']
        if not GroupMember.objects.filter(group=group, user=user).exists():
            raise serializers.ValidationError(
                {'group': 'You must be a member of this group.'}
            )

        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AlertConsentSerializer(serializers.ModelSerializer):
    """Read serializer for AlertConsent."""
    user = UserSerializer(read_only=True)

    class Meta:
        model = AlertConsent
        fields = [
            'id', 'user', 'group', 'is_active',
            'agreed_at', 'revoked_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'is_active', 'agreed_at',
            'revoked_at', 'created_at', 'updated_at',
        ]


class AlertConsentCreateSerializer(serializers.ModelSerializer):
    """
    Create or reactivate an alert consent for a group.
    Uses upsert logic — if a revoked consent already exists for this
    user+group pair, it gets reactivated instead of creating a duplicate.
    """

    class Meta:
        model = AlertConsent
        fields = ['group']

    def validate(self, attrs):
        from apps.groups.models import GroupMember
        user = self.context['request'].user
        group = attrs['group']
        if not GroupMember.objects.filter(group=group, user=user).exists():
            raise serializers.ValidationError(
                {'group': 'You must be a member of this group.'}
            )
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        consent, _ = AlertConsent.objects.update_or_create(
            user=validated_data['user'],
            group=validated_data['group'],
            defaults={'is_active': True, 'revoked_at': None},
        )
        return consent


class RouteAlertCreateSerializer(serializers.Serializer):
    """Validates and creates a route deviation alert."""
    recipient_id = serializers.UUIDField()
    group_id = serializers.UUIDField()
    trip_id = serializers.UUIDField()
    message = serializers.CharField(max_length=500)

    def validate(self, attrs):
        from apps.groups.models import GroupMember
        from apps.trips.models import Trip

        user = self.context['request'].user
        group_id = attrs['group_id']
        recipient_id = attrs['recipient_id']
        trip_id = attrs['trip_id']

        # Sender must be a group member
        if not GroupMember.objects.filter(group_id=group_id, user=user).exists():
            raise serializers.ValidationError(
                {'group_id': 'You are not a member of this group.'}
            )

        # Recipient must be a group member
        if not GroupMember.objects.filter(
            group_id=group_id, user_id=recipient_id
        ).exists():
            raise serializers.ValidationError(
                {'recipient_id': 'Recipient is not a member of this group.'}
            )

        # Recipient must have active alert consent
        if not AlertConsent.objects.filter(
            user_id=recipient_id, group_id=group_id, is_active=True,
        ).exists():
            raise serializers.ValidationError(
                {'recipient_id': 'Recipient has not consented to receive alerts.'}
            )

        # Trip must belong to this group and be active
        try:
            trip = Trip.objects.get(id=trip_id, group_id=group_id)
            if trip.status != Trip.Status.ACTIVE:
                raise serializers.ValidationError(
                    {'trip_id': 'Trip is not currently active.'}
                )
        except Trip.DoesNotExist:
            raise serializers.ValidationError(
                {'trip_id': 'Trip not found in this group.'}
            )

        return attrs


class RouteAlertSerializer(serializers.ModelSerializer):
    """Read serializer for RouteAlert."""
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)

    class Meta:
        model = RouteAlert
        fields = [
            'id', 'sender', 'recipient', 'group', 'trip',
            'message', 'delivered_at', 'created_at',
        ]
