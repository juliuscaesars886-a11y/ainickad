from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

class Notification(models.Model):
    """
    Notification model for user notifications
    """
    NOTIFICATION_TYPES = [
        ('task_assigned', 'Task Assigned'),
        ('task_completed', 'Task Completed'),
        ('task_approved', 'Task Approved'),
        ('task_rejected', 'Task Rejected'),
        ('approval_required', 'Approval Required'),
        ('request_submitted', 'Request Submitted'),
        ('request_approved', 'Request Approved'),
        ('request_rejected', 'Request Rejected'),
        ('system', 'System Notification'),
        ('general', 'General Notification'),
    ]
    
    ENTITY_TYPES = [
        ('task', 'Task'),
        ('request', 'Request'),
        ('user', 'User'),
        ('company', 'Company'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_entity_type = models.CharField(max_length=50, choices=ENTITY_TYPES, null=True, blank=True)
    related_entity_id = models.CharField(max_length=255, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])