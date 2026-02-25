"""
Serializers for the Locations app.
All output uses camelCase to match the Flutter client.
"""
from django.utils import timezone
from rest_framework import serializers

from apps.locations.models import AlertConsent, LocationConsent, RouteAlert


class LocationConsentSerializer(serializers.ModelSerializer):
    userId = serializers.CharField(source='user.id', read_only=True)
    groupId = serializers.CharField(source='group_id', read_only=True)
    isGranted = serializers.BooleanField(source='is_active', read_only=True)
    startDate = serializers.DateTimeField(source='start_date', read_only=True)
    endDate = serializers.DateTimeField(source='end_date', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = LocationConsent
        fields = ['id', 'userId', 'groupId', 'isGranted', 'startDate', 'endDate', 'createdAt']
        read_only_fields = fields


class LocationConsentCreateSerializer(serializers.Serializer):
    """Accepts camelCase from Flutter."""
    groupId = serializers.UUIDField()
    startDate = serializers.DateTimeField()
    endDate = serializers.DateTimeField()

    def validate(self, attrs):
        if attrs['startDate'] >= attrs['endDate']:
            raise serializers.ValidationError({'endDate': 'End date must be after start date.'})

        if attrs['endDate'] <= timezone.now():
            raise serializers.ValidationError({'endDate': 'End date must be in the future.'})

        from apps.groups.models import GroupMember
        user = self.context['request'].user
        group_id = attrs['groupId']
        if not GroupMember.objects.filter(group_id=group_id, user=user).exists():
            raise serializers.ValidationError({'groupId': 'You must be a member of this group.'})

        return attrs

    def create(self, validated_data):
        return LocationConsent.objects.create(
            user=self.context['request'].user,
            group_id=validated_data['groupId'],
            start_date=validated_data['startDate'],
            end_date=validated_data['endDate'],
        )


class AlertConsentSerializer(serializers.ModelSerializer):
    userId = serializers.CharField(source='user.id', read_only=True)
    groupId = serializers.CharField(source='group_id', read_only=True)
    isActive = serializers.BooleanField(source='is_active', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = AlertConsent
        fields = ['id', 'userId', 'groupId', 'isActive', 'createdAt']
        read_only_fields = fields


class AlertConsentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertConsent
        fields = ['group']

    def validate(self, attrs):
        from apps.groups.models import GroupMember
        user = self.context['request'].user
        group = attrs['group']
        if not GroupMember.objects.filter(group=group, user=user).exists():
            raise serializers.ValidationError({'group': 'You must be a member of this group.'})
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

        if not GroupMember.objects.filter(group_id=group_id, user=user).exists():
            raise serializers.ValidationError({'group_id': 'You are not a member of this group.'})

        if not GroupMember.objects.filter(group_id=group_id, user_id=recipient_id).exists():
            raise serializers.ValidationError({'recipient_id': 'Recipient is not a member of this group.'})

        if not AlertConsent.objects.filter(
            user_id=recipient_id, group_id=group_id, is_active=True,
        ).exists():
            raise serializers.ValidationError({'recipient_id': 'Recipient has not consented to receive alerts.'})

        try:
            trip = Trip.objects.get(id=trip_id, group_id=group_id)
            if trip.status != Trip.Status.ACTIVE:
                raise serializers.ValidationError({'trip_id': 'Trip is not currently active.'})
        except Trip.DoesNotExist:
            raise serializers.ValidationError({'trip_id': 'Trip not found in this group.'})

        return attrs


class RouteAlertSerializer(serializers.ModelSerializer):
    senderId = serializers.CharField(source='sender.id', read_only=True)
    senderName = serializers.SerializerMethodField()
    recipientId = serializers.CharField(source='recipient.id', read_only=True)
    groupId = serializers.CharField(source='group_id', read_only=True)
    tripId = serializers.CharField(source='trip_id', read_only=True)
    deliveredAt = serializers.DateTimeField(source='delivered_at', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = RouteAlert
        fields = [
            'id', 'senderId', 'senderName', 'recipientId',
            'groupId', 'tripId', 'message', 'deliveredAt', 'createdAt',
        ]
        read_only_fields = fields

    def get_senderName(self, obj):
        u = obj.sender
        full = f'{u.first_name} {u.last_name}'.strip()
        return full or u.email
