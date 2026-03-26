"""
Workflow models for Governance Hub
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Task(models.Model):
    """
    Task entity for task management and tracking.
    """
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='tasks',
        db_index=True
    )
    creator = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.CASCADE,
        related_name='created_tasks'
    )
    assignee = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.CASCADE,
        related_name='assigned_tasks',
        db_index=True
    )
    due_date = models.DateTimeField()
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    tags = models.JSONField(default=list, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)  # When task was started
    total_time_seconds = models.IntegerField(default=0)  # Total time spent in seconds
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tasks'
        ordering = ['-created_at']
        indexes = [
            # Existing indexes
            models.Index(fields=['company', 'assignee', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['priority', 'status']),
            # New optimized indexes for common query patterns
            models.Index(fields=['status', 'company'], name='task_status_company_idx'),
            models.Index(fields=['assignee', 'status'], name='task_assignee_status_idx'),
            models.Index(fields=['status', 'due_date'], name='task_status_duedate_idx'),
            models.Index(fields=['company', 'status', 'due_date'], name='task_company_status_due_idx'),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.assignee.full_name}"
    
    @property
    def is_completed(self):
        """Check if task is completed"""
        return self.status == 'completed'
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.status in ['completed', 'cancelled']:
            return False
        return self.due_date < timezone.now()
    
    @property
    def is_urgent(self):
        """Check if task is urgent priority"""
        return self.priority == 'urgent'
    
    @property
    def time_spent_formatted(self):
        """Get formatted time spent (HH:MM:SS)"""
        if not self.total_time_seconds:
            return "00:00:00"
        
        hours = self.total_time_seconds // 3600
        minutes = (self.total_time_seconds % 3600) // 60
        seconds = self.total_time_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def add_time_spent(self, seconds):
        """Add time spent to the task"""
        self.total_time_seconds += seconds
        self.save(update_fields=['total_time_seconds'])



class Request(models.Model):
    """
    Generic request entity for approval workflows.
    """
    
    TYPE_CHOICES = [
        ('leave', 'Leave Request'),
        ('expense_reimbursement', 'Expense Reimbursement'),
        ('purchase', 'Purchase Request'),
        ('document_approval', 'Document Approval'),
        ('document_deletion', 'Document Deletion'),
        ('petty_cash', 'Petty Cash'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        db_index=True
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='requests',
        db_index=True
    )
    requester = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.CASCADE,
        related_name='requests'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )
    data = models.JSONField(default=dict)  # Request-specific data
    submission_date = models.DateTimeField(null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['request_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_request_type_display()} - {self.requester.full_name} - {self.status}"
    
    @property
    def is_pending(self):
        """Check if request is pending"""
        return self.status == 'pending'
    
    @property
    def is_approved(self):
        """Check if request is approved"""
        return self.status == 'approved'
    
    @property
    def is_rejected(self):
        """Check if request is rejected"""
        return self.status == 'rejected'


class Approval(models.Model):
    """
    Approval workflow tracking entity.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name='approvals'
    )
    approver = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.CASCADE,
        related_name='approvals',
        db_index=True
    )
    step_number = models.IntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    comments = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'approvals'
        ordering = ['step_number', 'created_at']
        indexes = [
            models.Index(fields=['request', 'step_number']),
            models.Index(fields=['approver', 'status']),
        ]
    
    def __str__(self):
        return f"Approval Step {self.step_number} - {self.approver.full_name} - {self.status}"
    
    @property
    def is_pending(self):
        """Check if approval is pending"""
        return self.status == 'pending'
    
    @property
    def is_approved(self):
        """Check if approval is approved"""
        return self.status == 'approved'
    
    @property
    def is_rejected(self):
        """Check if approval is rejected"""
        return self.status == 'rejected'



class LeaveBalance(models.Model):
    """
    Leave balance tracking for staff members.
    Tracks annual, maternity, and paternity leave entitlements and usage.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.OneToOneField(
        'staff.Staff',
        on_delete=models.CASCADE,
        related_name='leave_balance'
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='leave_balances',
        db_index=True
    )
    
    # Annual leave
    annual_leave_entitlement = models.IntegerField(default=20, validators=[MinValueValidator(0)])
    annual_leave_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Maternity leave
    maternity_leave_entitlement = models.IntegerField(default=90, validators=[MinValueValidator(0)])
    maternity_leave_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Paternity leave
    paternity_leave_entitlement = models.IntegerField(default=14, validators=[MinValueValidator(0)])
    paternity_leave_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Sick leave
    sick_leave_entitlement = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    sick_leave_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Emergency leave
    emergency_leave_entitlement = models.IntegerField(default=3, validators=[MinValueValidator(0)])
    emergency_leave_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'leave_balances'
        indexes = [
            models.Index(fields=['staff', 'company']),
        ]
    
    def __str__(self):
        return f"Leave Balance - {self.staff.full_name}"
    
    @property
    def annual_leave_remaining(self):
        """Get remaining annual leave days"""
        return max(0, self.annual_leave_entitlement - self.annual_leave_used)
    
    @property
    def maternity_leave_remaining(self):
        """Get remaining maternity leave days"""
        return max(0, self.maternity_leave_entitlement - self.maternity_leave_used)
    
    @property
    def paternity_leave_remaining(self):
        """Get remaining paternity leave days"""
        return max(0, self.paternity_leave_entitlement - self.paternity_leave_used)
    
    @property
    def sick_leave_remaining(self):
        """Get remaining sick leave days"""
        return max(0, self.sick_leave_entitlement - self.sick_leave_used)
    
    @property
    def emergency_leave_remaining(self):
        """Get remaining emergency leave days"""
        return max(0, self.emergency_leave_entitlement - self.emergency_leave_used)
    
    def deduct_leave(self, leave_type, days):
        """Deduct leave days from the balance"""
        if leave_type == 'annual':
            self.annual_leave_used += days
        elif leave_type == 'maternity':
            self.maternity_leave_used += days
        elif leave_type == 'paternity':
            self.paternity_leave_used += days
        elif leave_type == 'sick':
            self.sick_leave_used += days
        elif leave_type == 'emergency':
            self.emergency_leave_used += days
        self.save()
    
    def restore_leave(self, leave_type, days):
        """Restore leave days (e.g., when leave request is rejected)"""
        if leave_type == 'annual':
            self.annual_leave_used = max(0, self.annual_leave_used - days)
        elif leave_type == 'maternity':
            self.maternity_leave_used = max(0, self.maternity_leave_used - days)
        elif leave_type == 'paternity':
            self.paternity_leave_used = max(0, self.paternity_leave_used - days)
        elif leave_type == 'sick':
            self.sick_leave_used = max(0, self.sick_leave_used - days)
        elif leave_type == 'emergency':
            self.emergency_leave_used = max(0, self.emergency_leave_used - days)
        self.save()
