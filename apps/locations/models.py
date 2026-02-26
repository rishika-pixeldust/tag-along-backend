"""
Models for the Locations app.

Manages user consent for location sharing within a group during a
specified time window (typically aligned with a trip's dates).
"""
import uuid

from django.db import models

from common.models import TimestampedModel


class LocationConsent(TimestampedModel):
    """
    Records a user's explicit consent to share their real-time location
    with other members of a group for a bounded time period.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='location_consents',
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='location_consents',
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    agreed_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'location_consents'
        ordering = ['-agreed_at']

    def __str__(self):
        return f"{self.user.email} -> {self.group.name} ({self.start_date} to {self.end_date})"


class AlertConsent(TimestampedModel):
    """
    Records a user's explicit consent to receive voice route-deviation
    alerts via loudspeaker from other members of a group.

    Separate from LocationConsent — this is a persistent toggle (no time
    window) that can be revoked at any time.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='alert_consents',
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='alert_consents',
    )
    is_active = models.BooleanField(default=True)
    agreed_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'alert_consents'
        ordering = ['-agreed_at']
        unique_together = ['user', 'group']

    def __str__(self):
        status = 'active' if self.is_active else 'revoked'
        return f"{self.user.email} -> {self.group.name} alert consent ({status})"


class MemberLocation(models.Model):
    """
    Stores the latest known location of a user within a group.
    Used as the primary location store (replaces Firestore dependency).
    One row per (user, group) — upserted on each location update.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='member_locations',
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='member_locations',
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    accuracy = models.FloatField(null=True, blank=True)
    speed = models.FloatField(null=True, blank=True)
    user_name = models.CharField(max_length=255, blank=True, default='')
    user_avatar = models.URLField(max_length=500, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'member_locations'
        unique_together = ['user', 'group']

    def __str__(self):
        return f"{self.user_name or self.user_id} @ ({self.latitude}, {self.longitude})"


class RouteAlert(TimestampedModel):
    """
    Audit record of a route deviation alert sent from one group member
    to another. The actual real-time delivery goes through Firestore
    (notifications collection) and FCM push.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='sent_route_alerts',
    )
    recipient = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='received_route_alerts',
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='route_alerts',
    )
    trip = models.ForeignKey(
        'trips.Trip',
        on_delete=models.CASCADE,
        related_name='route_alerts',
    )
    message = models.TextField(max_length=500)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'route_alerts'
        ordering = ['-created_at']

    def __str__(self):
        return f"Alert from {self.sender.email} to {self.recipient.email}: {self.message[:50]}"
