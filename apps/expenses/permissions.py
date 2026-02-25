"""
Custom permissions for the Expenses app.
"""
from rest_framework.permissions import BasePermission

from apps.groups.models import GroupMember


class IsExpenseGroupMember(BasePermission):
    """
    Allows access only to members of the group that owns the expense.
    """
    message = 'You must be a member of the expense group.'

    def has_object_permission(self, request, view, obj):
        return GroupMember.objects.filter(
            group=obj.group,
            user=request.user,
        ).exists()


class IsExpensePayer(BasePermission):
    """
    Only the user who paid the expense can modify it.
    """
    message = 'Only the payer can modify this expense.'

    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return obj.paid_by == request.user
