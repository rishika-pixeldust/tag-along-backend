"""
Admin configuration for the Users app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email',
        'username',
        'first_name',
        'last_name',
        'is_premium',
        'is_active',
        'created_at',
    ]
    list_filter = [
        'is_premium',
        'is_active',
        'is_staff',
        'preferred_currency',
        'created_at',
    ]
    search_fields = ['email', 'username', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            'Tag Along Profile',
            {
                'fields': (
                    'phone',
                    'avatar',
                    'firebase_uid',
                    'preferred_currency',
                    'is_premium',
                ),
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            'Profile',
            {
                'fields': (
                    'email',
                    'first_name',
                    'last_name',
                    'phone',
                ),
            },
        ),
    )
