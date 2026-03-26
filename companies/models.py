"""
Company models for Governance Hub
"""
import uuid
from django.db import models


class Company(models.Model):
    """
    Organization entity representing a company in the system.
    
    Companies are the primary organizational unit, with users and resources
    associated with specific companies.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True, db_index=True)
    tax_id = models.CharField(max_length=100, unique=True, db_index=True)
    address = models.TextField()
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    logo_url = models.URLField(blank=True, null=True)
    
    RISK_LEVEL_CHOICES = [
        ('level_1', 'Level 1 - Low Risk'),
        ('level_2', 'Level 2 - Medium Risk'),
        ('level_3', 'Level 3 - High Risk'),
    ]
    
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        default='level_2',
        help_text='Risk assessment level for the company'
    )
    risk_category = models.CharField(
        max_length=100,
        default='',
        blank=True,
        help_text='Specific risk category (e.g., retail_clients, financial_institutions)'
    )
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'companies'
        ordering = ['name']
        verbose_name_plural = 'Companies'
        indexes = [
            models.Index(fields=['registration_number']),
            models.Index(fields=['tax_id']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def has_active_employees(self):
        """Check if company has active employees"""
        try:
            return self.employees.filter(employment_status='active').exists()
        except AttributeError:
            # Employee model not yet created
            return False
    
    def has_documents(self):
        """Check if company has associated documents"""
        try:
            return self.documents.exists()
        except AttributeError:
            # Document model not yet created
            return False


class Director(models.Model):
    """
    Director model representing company directors/board members.
    
    Tracks director appointments, resignations, and positions within companies.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='directors',
        db_index=True
    )
    name = models.CharField(max_length=255)
    appointment_date = models.DateField()
    resignation_date = models.DateField(null=True, blank=True)
    position = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'directors'
        ordering = ['-appointment_date', 'name']
        verbose_name_plural = 'Directors'
        indexes = [
            models.Index(fields=['company', 'is_active']),
            models.Index(fields=['appointment_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.company.name}"
    
    @property
    def is_current(self):
        """Check if director is currently serving (no resignation date)"""
        return self.is_active and self.resignation_date is None
