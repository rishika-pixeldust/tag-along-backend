"""
Serializers for the Trips app.
"""
from rest_framework import serializers

from apps.trips.models import Trip, TripStop
from apps.users.serializers import UserSerializer


class TripStopSerializer(serializers.ModelSerializer):
    """
    Serializer for TripStop instances.
    """
    added_by = UserSerializer(read_only=True)

    class Meta:
        model = TripStop
        fields = [
            'id',
            'name',
            'description',
            'lat',
            'lng',
            'order',
            'planned_arrival',
            'planned_departure',
            'added_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'added_by', 'created_at', 'updated_at']


class TripSerializer(serializers.ModelSerializer):
    """
    Read serializer for Trip instances.
    """
    created_by = UserSerializer(read_only=True)
    stops = TripStopSerializer(many=True, read_only=True)
    stop_count = serializers.ReadOnlyField()

    class Meta:
        model = Trip
        fields = [
            'id',
            'group',
            'name',
            'description',
            'start_date',
            'end_date',
            'status',
            'start_location_name',
            'start_lat',
            'start_lng',
            'end_location_name',
            'end_lat',
            'end_lng',
            'created_by',
            'stops',
            'stop_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class TripCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new trip.
    """
    class Meta:
        model = Trip
        fields = [
            'group',
            'name',
            'description',
            'start_date',
            'end_date',
            'start_location_name',
            'start_lat',
            'start_lng',
            'end_location_name',
            'end_lat',
            'end_lng',
        ]

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {'end_date': 'End date must be after start date.'}
            )

        # Verify user is a member of the group
        from apps.groups.models import GroupMember
        user = self.context['request'].user
        group = attrs.get('group')
        if group and not GroupMember.objects.filter(group=group, user=user).exists():
            raise serializers.ValidationError(
                {'group': 'You must be a member of this group.'}
            )
        return attrs

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TripStopCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a trip stop.
    """
    class Meta:
        model = TripStop
        fields = [
            'name',
            'description',
            'lat',
            'lng',
            'order',
            'planned_arrival',
            'planned_departure',
        ]

    def create(self, validated_data):
        validated_data['added_by'] = self.context['request'].user
        validated_data['trip_id'] = self.context['trip_id']
        return super().create(validated_data)


class TripStopReorderSerializer(serializers.Serializer):
    """
    Serializer for reordering trip stops.
    """
    stop_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text='Ordered list of stop IDs.',
    )

    def validate_stop_ids(self, value):
        trip_id = self.context.get('trip_id')
        existing_ids = set(
            TripStop.objects.filter(trip_id=trip_id).values_list('id', flat=True)
        )
        provided_ids = set(value)

        if existing_ids != provided_ids:
            raise serializers.ValidationError(
                'Provided stop IDs do not match existing stops for this trip.'
            )
        return value
