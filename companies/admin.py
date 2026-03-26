"""
Admin configuration for companies app
"""
from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Admin interface for Company model"""
    
    list_display = ['name', 'registration_number', 'tax_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'registration_number', 'tax_id', 'contact_email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Company Information', {
            'fields': ('id', 'name', 'registration_number', 'tax_id')
        }),
        ('Contact Details', {
            'fields': ('address', 'contact_email', 'contact_phone')
        }),
        ('Branding', {
            'fields': ('logo_url',)
        }),
        ('Settings', {
            'fields': ('settings', 'is_active'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
