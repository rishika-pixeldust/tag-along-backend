"""
Models for the Groups app.
"""
from django.conf import settings
from django.db import models

from common.models import TimestampedModel


class Group(TimestampedModel):
    """
    A travel group that users can create and join.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    invite_code = models.CharField(
        max_length=8,
        unique=True,
        db_index=True,
        help_text='Unique 8-character code used to join the group.',
    )
    photo = models.URLField(max_length=500, blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_groups',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'groups'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()


class GroupMember(TimestampedModel):
    """
    Membership record linking a user to a group with a role.
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='members',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_memberships',
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'group_members'
        unique_together = ['group', 'user']
        ordering = ['joined_at']

    def __str__(self):
        return f'{self.user} in {self.group} ({self.role})'
