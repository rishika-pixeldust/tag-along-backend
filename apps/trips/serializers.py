"""
Serializers for the Trips app.
All output uses camelCase to match the Flutter client.
"""
from rest_framework import serializers

from apps.trips.models import Trip, TripStop


class TripStopSerializer(serializers.ModelSerializer):
    tripId = serializers.CharField(source='trip_id', read_only=True)
    plannedArrival = serializers.DateTimeField(source='planned_arrival', read_only=True)
    plannedDeparture = serializers.DateTimeField(source='planned_departure', read_only=True)
    addedBy = serializers.CharField(source='added_by.id', read_only=True)

    class Meta:
        model = TripStop
        fields = [
            'id', 'tripId', 'name', 'description',
            'lat', 'lng', 'order',
            'plannedArrival', 'plannedDeparture', 'addedBy',
        ]
        read_only_fields = fields


class TripSerializer(serializers.ModelSerializer):
    groupId = serializers.CharField(source='group_id', read_only=True)
    startDate = serializers.DateField(source='start_date', read_only=True)
    endDate = serializers.DateField(source='end_date', read_only=True)
    startLocation = serializers.CharField(source='start_location_name', read_only=True, allow_blank=True)
    endLocation = serializers.CharField(source='end_location_name', read_only=True, allow_blank=True)
    createdBy = serializers.CharField(source='created_by.id', read_only=True)
    stopsCount = serializers.ReadOnlyField(source='stop_count')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Trip
        fields = [
            'id', 'groupId', 'name', 'description',
            'startDate', 'endDate', 'status',
            'startLocation', 'endLocation',
            'createdBy', 'stopsCount', 'createdAt',
        ]
        read_only_fields = fields


class TripCreateSerializer(serializers.Serializer):
    """Accepts camelCase from Flutter, maps to snake_case model fields."""
    groupId = serializers.UUIDField()
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    startDate = serializers.DateField()
    endDate = serializers.DateField()
    startLocation = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    endLocation = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')

    def validate(self, attrs):
        start_date = attrs.get('startDate')
        end_date = attrs.get('endDate')
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({'endDate': 'End date must be after start date.'})

        from apps.groups.models import GroupMember
        user = self.context['request'].user
        group_id = attrs.get('groupId')
        if group_id and not GroupMember.objects.filter(group_id=group_id, user=user).exists():
            raise serializers.ValidationError({'groupId': 'You must be a member of this group.'})
        return attrs

    def create(self, validated_data):
        return Trip.objects.create(
            group_id=validated_data['groupId'],
            name=validated_data['name'],
            description=validated_data.get('description', ''),
            start_date=validated_data['startDate'],
            end_date=validated_data['endDate'],
            start_location_name=validated_data.get('startLocation', ''),
            end_location_name=validated_data.get('endLocation', ''),
            created_by=self.context['request'].user,
        )


class TripStopCreateSerializer(serializers.Serializer):
    """Accepts camelCase from Flutter for creating a trip stop."""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    lat = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    lng = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    order = serializers.IntegerField(default=0)
    plannedArrival = serializers.DateTimeField(required=False, allow_null=True)
    plannedDeparture = serializers.DateTimeField(required=False, allow_null=True)

    def create(self, validated_data):
        return TripStop.objects.create(
            trip_id=self.context['trip_id'],
            added_by=self.context['request'].user,
            name=validated_data['name'],
            description=validated_data.get('description', ''),
            lat=validated_data.get('lat'),
            lng=validated_data.get('lng'),
            order=validated_data.get('order', 0),
            planned_arrival=validated_data.get('plannedArrival'),
            planned_departure=validated_data.get('plannedDeparture'),
        )


class TripStopReorderSerializer(serializers.Serializer):
    stop_ids = serializers.ListField(child=serializers.UUIDField())

    def validate_stop_ids(self, value):
        trip_id = self.context.get('trip_id')
        existing_ids = set(
            TripStop.objects.filter(trip_id=trip_id).values_list('id', flat=True)
        )
        if existing_ids != set(value):
            raise serializers.ValidationError('Provided stop IDs do not match existing stops for this trip.')
        return value
