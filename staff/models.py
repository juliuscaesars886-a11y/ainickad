"""
Staff models for Governance Hub
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Staff(models.Model):
    """
    Staff entity representing a staff member in a company.
    
    Staff members are linked to UserProfiles and Companies, storing
    employment-specific information like job title, salary, and status.
    """
    
    EMPLOYMENT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff_number = models.CharField(max_length=50, unique=True, db_index=True)
    user = models.OneToOneField(
        'authentication.UserProfile',
        on_delete=models.CASCADE,
        related_name='staff',
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='staff_members',
        db_index=True
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    job_title = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True)
    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS_CHOICES,
        default='active',
        db_index=True
    )
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True
    )
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'staff'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['staff_number']),
            models.Index(fields=['company', 'employment_status']),
            models.Index(fields=['email']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['staff_number'],
                name='unique_staff_number'
            ),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.staff_number})"
    
    @property
    def full_name(self):
        """Get staff member's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_active(self):
        """Check if staff member is active"""
        return self.employment_status == 'active'
    
    def save(self, *args, **kwargs):
        """Override save to validate user-company association"""
        if self.user and self.user.company and self.user.company != self.company:
            raise ValueError(
                f"User's company ({self.user.company}) must match staff member's company ({self.company})"
            )
        super().save(*args, **kwargs)
