from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at', 'related_entity_type']
    search_fields = ['title', 'message', 'user__email']
    readonly_fields = ['id', 'created_at', 'read_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'notification_type', 'title', 'message')
        }),
        ('Related Entity', {
            'fields': ('related_entity_type', 'related_entity_id')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'created_at')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )