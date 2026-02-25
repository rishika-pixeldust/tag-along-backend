"""
Common permission classes for the Tag Along project.
"""
from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    Object-level permission: only the object owner can access it.
    Assumes the model has a ``user`` or ``created_by`` field.
    """

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        return False


class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level permission: anyone can read, only the owner can modify.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True

        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        return False


class IsPremiumUser(BasePermission):
    """
    Allows access only to premium users.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_premium
        )
