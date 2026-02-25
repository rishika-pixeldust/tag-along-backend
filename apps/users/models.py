"""
Custom User model for the Tag Along application.
"""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Extended User model with additional profile fields.

    Uses email as the primary login identifier instead of username.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    email = models.EmailField(
        unique=True,
        db_index=True,
        error_messages={
            'unique': 'A user with that email already exists.',
        },
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text='Phone number with country code.',
    )
    avatar = models.URLField(
        max_length=500,
        blank=True,
        default='',
        help_text='URL to the user avatar image.',
    )
    firebase_uid = models.CharField(
        max_length=128,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        help_text='Firebase Authentication UID.',
    )
    preferred_currency = models.CharField(
        max_length=3,
        default='USD',
        help_text='ISO 4217 currency code (e.g., USD, EUR, INR).',
    )
    is_premium = models.BooleanField(
        default=False,
        help_text='Whether the user has a premium subscription.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.email})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()
