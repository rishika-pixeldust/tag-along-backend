from django.contrib import admin

from apps.locations.models import AlertConsent, LocationConsent, RouteAlert


@admin.register(LocationConsent)
class LocationConsentAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'is_active', 'start_date', 'end_date', 'agreed_at']
    list_filter = ['is_active', 'group']
    search_fields = ['user__email', 'group__name']
    readonly_fields = ['id', 'agreed_at', 'revoked_at', 'created_at', 'updated_at']


@admin.register(AlertConsent)
class AlertConsentAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'is_active', 'agreed_at', 'revoked_at']
    list_filter = ['is_active', 'group']
    search_fields = ['user__email', 'group__name']
    readonly_fields = ['id', 'agreed_at', 'revoked_at', 'created_at', 'updated_at']


@admin.register(RouteAlert)
class RouteAlertAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'group', 'trip', 'message_preview', 'delivered_at', 'created_at']
    list_filter = ['group', 'trip']
    search_fields = ['sender__email', 'recipient__email', 'message']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def message_preview(self, obj):
        return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
    message_preview.short_description = 'Message'
