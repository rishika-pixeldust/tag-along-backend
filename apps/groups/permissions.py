"""
Custom permissions for the Groups app.
"""
from rest_framework.permissions import BasePermission

from apps.groups.models import GroupMember


class IsGroupAdmin(BasePermission):
    """
    Allows access only to group admins.
    Checks the group from the object or from URL kwargs.
    """
    message = 'You must be a group admin to perform this action.'

    def has_object_permission(self, request, view, obj):
        # obj can be a Group or GroupMember
        group = obj if hasattr(obj, 'invite_code') else getattr(obj, 'group', None)
        if group is None:
            return False

        return GroupMember.objects.filter(
            group=group,
            user=request.user,
            role=GroupMember.Role.ADMIN,
        ).exists()

    def has_permission(self, request, view):
        group_pk = view.kwargs.get('group_pk') or view.kwargs.get('pk')
        if group_pk is None:
            return True  # Let object permission handle it

        return GroupMember.objects.filter(
            group_id=group_pk,
            user=request.user,
            role=GroupMember.Role.ADMIN,
        ).exists()


class IsGroupMember(BasePermission):
    """
    Allows access only to group members (any role).
    """
    message = 'You must be a group member to perform this action.'

    def has_object_permission(self, request, view, obj):
        group = obj if hasattr(obj, 'invite_code') else getattr(obj, 'group', None)
        if group is None:
            return False

        return GroupMember.objects.filter(
            group=group,
            user=request.user,
        ).exists()

    def has_permission(self, request, view):
        group_pk = view.kwargs.get('group_pk') or view.kwargs.get('pk')
        if group_pk is None:
            return True

        return GroupMember.objects.filter(
            group_id=group_pk,
            user=request.user,
        ).exists()
