"""
Models for the Trips app.
"""
from django.conf import settings
from django.db import models

from common.models import TimestampedModel


class Trip(TimestampedModel):
    """
    A trip planned within a group.
    """
    class Status(models.TextChoices):
        PLANNING = 'planning', 'Planning'
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='trips',
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
        db_index=True,
    )

    # Start location
    start_location_name = models.CharField(max_length=255, blank=True, default='')
    start_lat = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    start_lng = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    # End location
    end_location_name = models.CharField(max_length=255, blank=True, default='')
    end_lat = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    end_lng = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_trips',
    )

    class Meta:
        db_table = 'trips'
        ordering = ['-start_date', '-created_at']

    def __str__(self):
        return f'{self.name} ({self.group.name})'

    @property
    def stop_count(self):
        return self.stops.count()

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('End date must be after start date.')


class TripStop(TimestampedModel):
    """
    A stop/waypoint within a trip.
    """
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='stops',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    lat = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    lng = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    order = models.PositiveIntegerField(default=0)
    planned_arrival = models.DateTimeField(null=True, blank=True)
    planned_departure = models.DateTimeField(null=True, blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='added_stops',
    )

    class Meta:
        db_table = 'trip_stops'
        ordering = ['order']

    def __str__(self):
        return f'{self.name} (Stop #{self.order})'
