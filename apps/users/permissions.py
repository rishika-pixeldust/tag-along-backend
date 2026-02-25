"""
Custom permissions for the Users app.
"""
from rest_framework.permissions import BasePermission


class IsSelf(BasePermission):
    """
    Object-level permission that allows users to only access their own profile.
    """

    def has_object_permission(self, request, view, obj):
        return obj == request.user


class IsAdminOrSelf(BasePermission):
    """
    Allows access to admin users or the user themselves.
    """

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj == request.user
