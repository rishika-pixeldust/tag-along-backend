"""
Serializers for the Groups app.
All output uses camelCase to match the Flutter client.
"""
from rest_framework import serializers

from apps.groups.models import Group, GroupMember
from apps.groups.utils import generate_invite_code


class GroupMemberSerializer(serializers.ModelSerializer):
    userId = serializers.CharField(source='user.id', read_only=True)
    groupId = serializers.CharField(source='group.id', read_only=True)
    userName = serializers.SerializerMethodField()
    userAvatar = serializers.SerializerMethodField()
    joinedAt = serializers.DateTimeField(source='joined_at', read_only=True)

    class Meta:
        model = GroupMember
        fields = ['id', 'userId', 'groupId', 'role', 'userName', 'userAvatar', 'joinedAt']
        read_only_fields = fields

    def get_userName(self, obj):
        u = obj.user
        full = f'{u.first_name} {u.last_name}'.strip()
        return full or u.email

    def get_userAvatar(self, obj):
        url = getattr(obj.user, 'avatar', None) or ''
        return url.strip() or None


class GroupSerializer(serializers.ModelSerializer):
    inviteCode = serializers.CharField(source='invite_code', read_only=True)
    photoUrl = serializers.SerializerMethodField()
    createdBy = serializers.CharField(source='created_by.id', read_only=True)
    isActive = serializers.BooleanField(source='is_active', read_only=True)
    memberCount = serializers.ReadOnlyField(source='member_count')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'inviteCode', 'photoUrl',
            'createdBy', 'isActive', 'memberCount', 'createdAt',
        ]
        read_only_fields = fields

    def get_photoUrl(self, obj):
        url = getattr(obj, 'photo', None) or ''
        return url.strip() or None


class GroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name', 'description', 'photo']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user
        validated_data['invite_code'] = generate_invite_code()
        group = Group.objects.create(**validated_data)
        GroupMember.objects.create(group=group, user=user, role=GroupMember.Role.ADMIN)
        return group


class GroupUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name', 'description', 'photo', 'is_active']


class JoinGroupSerializer(serializers.Serializer):
    inviteCode = serializers.CharField(max_length=8, required=True)

    def validate_inviteCode(self, value):
        try:
            group = Group.objects.get(invite_code=value.upper(), is_active=True)
        except Group.DoesNotExist:
            raise serializers.ValidationError('Invalid or expired invite code.')

        user = self.context['request'].user
        if GroupMember.objects.filter(group=group, user=user).exists():
            raise serializers.ValidationError('You are already a member of this group.')

        self.group = group
        return value
