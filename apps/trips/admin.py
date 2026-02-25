"""
Admin configuration for the Trips app.
"""
from django.contrib import admin

from apps.trips.models import Trip, TripStop


class TripStopInline(admin.TabularInline):
    model = TripStop
    extra = 0
    ordering = ['order']


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['name', 'group', 'status', 'start_date', 'end_date', 'created_by', 'created_at']
    list_filter = ['status', 'start_date', 'created_at']
    search_fields = ['name', 'description', 'group__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [TripStopInline]


@admin.register(TripStop)
class TripStopAdmin(admin.ModelAdmin):
    list_display = ['name', 'trip', 'order', 'planned_arrival', 'planned_departure']
    list_filter = ['trip__group']
    search_fields = ['name', 'description']
    ordering = ['trip', 'order']
