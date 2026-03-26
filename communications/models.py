"""
Communication models for Governance Hub
"""
import uuid
from django.db import models


class Message(models.Model):
    """
    Message entity for internal messaging system.
    Supports both direct messages and broadcast messages.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.CASCADE,
        related_name='received_messages',
        null=True,
        blank=True,
        db_index=True
    )
    subject = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField()
    is_broadcast = models.BooleanField(default=False, db_index=True)
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'messages'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['sender', 'sent_at']),
            models.Index(fields=['parent_message']),
            models.Index(fields=['is_broadcast', 'sent_at']),
        ]
    
    def __str__(self):
        if self.is_broadcast:
            return f"Broadcast: {self.subject or 'No subject'} - From {self.sender.full_name}"
        return f"{self.subject or 'No subject'} - From {self.sender.full_name} to {self.recipient.full_name if self.recipient else 'Unknown'}"
    
    @property
    def is_reply(self):
        """Check if message is a reply"""
        return self.parent_message is not None


class FeatureUpdate(models.Model):
    """
    Track feature updates for AI context.
    Used to inform AI assistant about new features and changes.
    """
    
    CATEGORY_CHOICES = [
        ('new_feature', 'New Feature'),
        ('improvement', 'Improvement'),
        ('bug_fix', 'Bug Fix'),
        ('documentation', 'Documentation'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(auto_now_add=True)
    feature_name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='new_feature'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether to include this update in AI context'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'feature_updates'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['is_active', 'date']),
        ]
    
    def __str__(self):
        return f"{self.date}: {self.feature_name}"


class Notification(models.Model):
    """
    Notification entity for user notifications.
    """
    
    TYPE_CHOICES = [
        ('task_assigned', 'Task Assigned'),
        ('task_started', 'Task Started'),
        ('task_completed', 'Task Completed'),
        ('task_approved', 'Task Approved'),
        ('task_rejected', 'Task Rejected'),
        ('approval_required', 'Approval Required'),
        ('message_received', 'Message Received'),
        ('document_shared', 'Document Shared'),
        ('deadline_approaching', 'Deadline Approaching'),
        ('status_changed', 'Status Changed'),
        ('expense_approved', 'Expense Approved'),
        ('expense_rejected', 'Expense Rejected'),
        ('petty_cash_approved', 'Petty Cash Approved'),
        ('petty_cash_rejected', 'Petty Cash Rejected'),
        ('request_submitted', 'Request Submitted'),
        ('request_approved', 'Request Approved'),
        ('request_rejected', 'Request Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True
    )
    notification_type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        db_index=True
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_entity_type = models.CharField(max_length=50, blank=True)
    related_entity_id = models.UUIDField(null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['related_entity_type', 'related_entity_id']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.full_name}"
    
    @property
    def is_unread(self):
        """Check if notification is unread"""
        return not self.is_read


class ClassificationLog(models.Model):
    """
    Log of AI message classifications for monitoring and analysis.
    Tracks every classification decision for accuracy metrics and debugging.
    """
    
    CLASSIFICATION_TYPES = [
        ('Navigation', 'Navigation'),
        ('Feature_Guide', 'Feature Guide'),
        ('Company_Data', 'Company Data'),
        ('Kenya_Governance', 'Kenya Governance'),
        ('Web_Search', 'Web Search'),
        ('Tip', 'Tip'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        'authentication.UserProfile',
        on_delete=models.CASCADE,
        related_name='classification_logs',
        null=True,
        blank=True,
        db_index=True
    )
    message = models.TextField(help_text='User message that was classified')
    classification_type = models.CharField(
        max_length=50,
        choices=CLASSIFICATION_TYPES,
        db_index=True,
        help_text='Classified message type'
    )
    confidence_score = models.FloatField(
        help_text='Confidence score for the classification (0.0-1.0)'
    )
    all_scores = models.JSONField(
        default=dict,
        help_text='Confidence scores for all classification types'
    )
    processing_time_ms = models.IntegerField(
        help_text='Time taken to classify message in milliseconds'
    )
    user_feedback = models.CharField(
        max_length=20,
        choices=[
            ('correct', 'Correct'),
            ('incorrect', 'Incorrect'),
            ('partial', 'Partially Correct'),
            ('none', 'No Feedback'),
        ],
        default='none',
        help_text='User feedback on classification accuracy'
    )
    context_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Context used for classification (user role, company, etc.)'
    )
    
    class Meta:
        db_table = 'classification_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['classification_type']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['confidence_score']),
        ]
    
    def __str__(self):
        return f"{self.classification_type} ({self.confidence_score:.2f}) - {self.timestamp}"


class AssistantMemory(models.Model):
    """
    Persistent storage for user preferences and learning data.
    One record per user for the AI Assistant.
    
    Stores:
    - Preferred name for personalized greetings
    - Role context for understanding user's responsibilities
    - Tone preference for matching conversational style
    - Last topics for contextual conversation continuity
    """
    
    TONE_CHOICES = [
        ('formal', 'Formal'),
        ('casual', 'Casual'),
        ('balanced', 'Balanced'),
    ]
    
    user = models.OneToOneField(
        'authentication.UserProfile',
        on_delete=models.CASCADE,
        related_name='assistant_memory',
        help_text='User this memory belongs to'
    )
    preferred_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="User's preferred name for greetings"
    )
    role_context = models.TextField(
        blank=True,
        help_text="Context about user's role and responsibilities"
    )
    tone_preference = models.CharField(
        max_length=20,
        choices=TONE_CHOICES,
        default='balanced',
        help_text="User's preferred conversational tone"
    )
    last_topics = models.JSONField(
        default=list,
        help_text="List of recent conversation topics (max 10)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assistant_memory'
        verbose_name = 'Assistant Memory'
        verbose_name_plural = 'Assistant Memories'
    
    def __str__(self):
        return f"Memory for {self.user.full_name}"
