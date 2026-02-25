"""
Serializers for the Groups app.
"""
from rest_framework import serializers

from apps.groups.models import Group, GroupMember
from apps.groups.utils import generate_invite_code
from apps.users.serializers import UserSerializer


class GroupMemberSerializer(serializers.ModelSerializer):
    """
    Serializer for GroupMember instances.
    """
    user = UserSerializer(read_only=True)

    class Meta:
        model = GroupMember
        fields = ['id', 'user', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class GroupSerializer(serializers.ModelSerializer):
    """
    Read serializer for Group instances.
    """
    created_by = UserSerializer(read_only=True)
    members = GroupMemberSerializer(many=True, read_only=True)
    member_count = serializers.ReadOnlyField()

    class Meta:
        model = Group
        fields = [
            'id',
            'name',
            'description',
            'invite_code',
            'photo',
            'created_by',
            'is_active',
            'members',
            'member_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'invite_code',
            'created_by',
            'created_at',
            'updated_at',
        ]


class GroupCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new group.
    """
    class Meta:
        model = Group
        fields = ['name', 'description', 'photo']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user
        validated_data['invite_code'] = generate_invite_code()

        group = Group.objects.create(**validated_data)

        # Add creator as admin member
        GroupMember.objects.create(
            group=group,
            user=user,
            role=GroupMember.Role.ADMIN,
        )

        return group


class GroupUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a group.
    """
    class Meta:
        model = Group
        fields = ['name', 'description', 'photo', 'is_active']


class JoinGroupSerializer(serializers.Serializer):
    """
    Serializer for joining a group via invite code.
    """
    invite_code = serializers.CharField(max_length=8, required=True)

    def validate_invite_code(self, value):
        try:
            group = Group.objects.get(invite_code=value.upper(), is_active=True)
        except Group.DoesNotExist:
            raise serializers.ValidationError('Invalid or expired invite code.')

        user = self.context['request'].user
        if GroupMember.objects.filter(group=group, user=user).exists():
            raise serializers.ValidationError('You are already a member of this group.')

        self.group = group
        return value
