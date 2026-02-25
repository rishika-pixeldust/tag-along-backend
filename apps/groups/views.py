"""
Views for the Groups app.
"""
import logging

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.groups.models import Group, GroupMember
from apps.groups.permissions import IsGroupAdmin, IsGroupMember
from apps.groups.serializers import (
    GroupCreateSerializer,
    GroupMemberSerializer,
    GroupSerializer,
    GroupUpdateSerializer,
    JoinGroupSerializer,
)
from apps.groups.utils import generate_invite_code

logger = logging.getLogger(__name__)


class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Group CRUD operations.

    list:   GET    /api/v1/groups/
    create: POST   /api/v1/groups/
    read:   GET    /api/v1/groups/{id}/
    update: PATCH  /api/v1/groups/{id}/
    delete: DELETE /api/v1/groups/{id}/
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Group.objects.filter(
            members__user=self.request.user,
            is_active=True,
        ).prefetch_related('members__user').distinct()

    def get_serializer_class(self):
        if self.action == 'create':
            return GroupCreateSerializer
        if self.action in ('update', 'partial_update'):
            return GroupUpdateSerializer
        return GroupSerializer

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsGroupAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        return Response(
            {
                'success': True,
                'data': GroupSerializer(group).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = GroupSerializer(instance)
        return Response({'success': True, 'data': serializer.data})

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = GroupSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = GroupSerializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(
            {'success': True, 'message': 'Group deactivated.'},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='regenerate-code')
    def regenerate_invite_code(self, request, pk=None):
        """Regenerate the invite code for a group."""
        group = self.get_object()
        group.invite_code = generate_invite_code()
        group.save(update_fields=['invite_code'])
        return Response(
            {
                'success': True,
                'invite_code': group.invite_code,
            }
        )


class GroupMemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing group members.

    list:    GET    /api/v1/groups/{group_id}/members/
    update:  PATCH  /api/v1/groups/{group_id}/members/{id}/
    destroy: DELETE /api/v1/groups/{group_id}/members/{id}/
    """
    serializer_class = GroupMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GroupMember.objects.filter(
            group_id=self.kwargs['group_pk'],
        ).select_related('user')

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsGroupAdmin()]
        return [IsAuthenticated(), IsGroupMember()]

    def destroy(self, request, *args, **kwargs):
        member = self.get_object()
        if member.role == GroupMember.Role.ADMIN:
            # Check if there are other admins
            admin_count = GroupMember.objects.filter(
                group=member.group,
                role=GroupMember.Role.ADMIN,
            ).count()
            if admin_count <= 1:
                return Response(
                    {
                        'success': False,
                        'error': {
                            'code': 'last_admin',
                            'message': 'Cannot remove the last admin. Transfer admin role first.',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        member.delete()
        return Response(
            {'success': True, 'message': 'Member removed.'},
            status=status.HTTP_200_OK,
        )


class JoinGroupView(generics.CreateAPIView):
    """
    Join a group using an invite code.

    POST /api/v1/groups/join/
    """
    serializer_class = JoinGroupSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group = serializer.group
        GroupMember.objects.create(
            group=group,
            user=request.user,
            role=GroupMember.Role.MEMBER,
        )

        return Response(
            {
                'success': True,
                'data': GroupSerializer(group).data,
                'message': f'Successfully joined {group.name}.',
            },
            status=status.HTTP_201_CREATED,
        )


class LeaveGroupView(generics.DestroyAPIView):
    """
    Leave a group.

    DELETE /api/v1/groups/{group_id}/leave/
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, group_pk=None, *args, **kwargs):
        try:
            membership = GroupMember.objects.get(
                group_id=group_pk,
                user=request.user,
            )
        except GroupMember.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'not_member',
                        'message': 'You are not a member of this group.',
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if membership.role == GroupMember.Role.ADMIN:
            admin_count = GroupMember.objects.filter(
                group_id=group_pk,
                role=GroupMember.Role.ADMIN,
            ).count()
            if admin_count <= 1:
                return Response(
                    {
                        'success': False,
                        'error': {
                            'code': 'last_admin',
                            'message': 'You are the last admin. Transfer admin role before leaving.',
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        membership.delete()
        return Response(
            {'success': True, 'message': 'Successfully left the group.'},
            status=status.HTTP_200_OK,
        )
