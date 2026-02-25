"""
Custom permissions for the Trips app.
"""
from rest_framework.permissions import BasePermission

from apps.groups.models import GroupMember


class IsTripGroupMember(BasePermission):
    """
    Allows access only to members of the group that owns the trip.
    """
    message = 'You must be a member of the trip group.'

    def has_object_permission(self, request, view, obj):
        return GroupMember.objects.filter(
            group=obj.group,
            user=request.user,
        ).exists()
