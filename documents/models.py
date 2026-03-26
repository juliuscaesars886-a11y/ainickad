"""
Document models for Governance Hub
"""
import uuid
import os
from django.db import models
from django.core.validators import FileExtensionValidator


class Document(models.Model):
    """
    Document entity for storing file metadata and references.
    
    Documents are associated with companies and uploaded by users.
    Actual files are stored in Django's file storage backend.
    Supports subfolder organization within companies for better document management.
    """
    
    CATEGORY_CHOICES = [
        ('received', 'Received'),
        ('sent', 'Sent'),
        ('sealed', 'Sealed'),
        ('certified', 'Certified'),
        ('commissioned', 'Commissioned'),
        ('notarised', 'Notarised'),
        ('contract', 'Contract'),
        ('invoice', 'Invoice'),
        ('report', 'Report'),
        ('certificate', 'Certificate'),
        ('correspondence', 'Correspondence'),
        ('other', 'Other'),
    ]
    
    SUBFOLDER_CHOICES = [
        ('engagement', 'Engagement & Onboarding'),
        ('incorporation', 'Incorporation & Formation'),
        ('annual-returns', 'Annual Returns'),
        ('statutory-returns', 'Other Statutory Returns'),
        ('board-meetings', 'Board Meetings'),
        ('shareholder-meetings', 'Shareholder Meetings'),
        ('corporate-governance', 'Corporate Governance'),
        ('fee-notes', 'Fee Notes'),
        ('correspondence', 'Correspondence'),
        ('sealed', 'Sealed Documents'),
        ('register', 'Register'),
        ('resolutions', 'Resolutions'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other',
        db_index=True
    )
    subfolder = models.CharField(
        max_length=50,
        choices=SUBFOLDER_CHOICES,
        default='other',
        db_index=True,
        help_text='Subfolder within company for document organization'
    )
    file_path = models.CharField(max_length=500)  # Path in storage
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()  # Size in bytes
    mime_type = models.CharField(max_length=100)
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='documents',
        db_index=True
    )
    uploaded_by = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
    metadata = models.JSONField(default=dict, blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'category', 'subfolder']),
            models.Index(fields=['company', 'subfolder']),
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['is_archived']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.file_name})"
    
    @property
    def file_extension(self):
        """Get file extension"""
        return os.path.splitext(self.file_name)[1].lower()
    
    @property
    def size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)


class Template(models.Model):
    """
    Template model for storing document templates.
    
    Templates are reusable document formats that can be used to create new documents.
    Tracks usage statistics and supports categorization.
    """
    
    CATEGORY_CHOICES = [
        ('annual-return', 'Annual Return'),
        ('board-resolution', 'Board Resolution'),
        ('contract', 'Contract'),
        ('letter', 'Letter'),
        ('report', 'Report'),
        ('form', 'Form'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='other',
        db_index=True
    )
    description = models.TextField(blank=True)
    file_path = models.CharField(max_length=500)  # Path in storage
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField(null=True, blank=True)  # Size in bytes
    usage_count = models.IntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'templates'
        ordering = ['name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['-last_used']),
            models.Index(fields=['-usage_count']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    @property
    def file_extension(self):
        """Get file extension"""
        return os.path.splitext(self.file_name)[1].lower()
    
    @property
    def size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
    
    def record_usage(self):
        """Increment usage count and update last_used timestamp"""
        from django.utils import timezone
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])
