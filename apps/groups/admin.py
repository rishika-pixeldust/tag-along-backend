"""
Admin configuration for the Groups app.
"""
from django.contrib import admin

from apps.groups.models import Group, GroupMember


class GroupMemberInline(admin.TabularInline):
    model = GroupMember
    extra = 0
    readonly_fields = ['joined_at']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'invite_code', 'created_by', 'is_active', 'member_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'invite_code', 'description']
    readonly_fields = ['invite_code', 'created_at', 'updated_at']
    inlines = [GroupMemberInline]


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'role', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['user__email', 'user__first_name', 'group__name']
