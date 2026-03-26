"""
Admin configuration for staff app
"""
from django.contrib import admin
from .models import Staff


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    """Admin interface for Staff model"""
    
    list_display = ['staff_number', 'full_name', 'email', 'job_title', 'department', 'employment_status', 'company', 'created_at']
    list_filter = ['employment_status', 'department', 'company', 'created_at']
    search_fields = ['staff_number', 'first_name', 'last_name', 'email', 'job_title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Staff Information', {
            'fields': ('id', 'staff_number', 'user', 'company')
        }),
        ('Personal Details', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Employment Details', {
            'fields': ('job_title', 'department', 'employment_status', 'hire_date', 'termination_date', 'salary')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'address'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def full_name(self, obj):
        """Display full name"""
        return obj.full_name
    full_name.short_description = 'Full Name'

