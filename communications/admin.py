from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta

# Import models with error handling for migrations
try:
    from .models import Message, Notification, FeatureUpdate, ClassificationLog, AssistantMemory
except ImportError:
    # Handle case where models don't exist yet (during migrations)
    Message = None
    Notification = None
    FeatureUpdate = None
    ClassificationLog = None
    AssistantMemory = None


# Only register admin classes if models exist (handles migration scenarios)
if Message:
    @admin.register(Message)
    class MessageAdmin(admin.ModelAdmin):
        """Admin interface for Message model"""
        list_display = ['subject', 'sender', 'recipient', 'is_broadcast', 'is_read', 'sent_at']
        list_filter = ['is_broadcast', 'is_read', 'sent_at']
        search_fields = ['subject', 'content', 'sender__email', 'recipient__email']
        readonly_fields = ['id', 'sent_at', 'read_at']
        date_hierarchy = 'sent_at'


if Notification:
    @admin.register(Notification)
    class NotificationAdmin(admin.ModelAdmin):
        """Admin interface for Notification model"""
        list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
        list_filter = ['notification_type', 'is_read', 'created_at']
        search_fields = ['title', 'message', 'user__email']
        readonly_fields = ['id', 'created_at', 'read_at']
        date_hierarchy = 'created_at'


if FeatureUpdate:
    @admin.register(FeatureUpdate)
    class FeatureUpdateAdmin(admin.ModelAdmin):
        """Admin interface for FeatureUpdate model"""
        list_display = ['date', 'feature_name', 'category', 'is_active']
        list_filter = ['category', 'is_active', 'date']
        search_fields = ['feature_name', 'description']
        readonly_fields = ['id', 'created_at']
        date_hierarchy = 'date'
        
        fieldsets = (
            ('Feature Information', {
                'fields': ('feature_name', 'description', 'category')
            }),
            ('Status', {
                'fields': ('is_active',)
            }),
            ('Metadata', {
                'fields': ('id', 'date', 'created_at'),
                'classes': ('collapse',)
            }),
        )



if ClassificationLog:
    @admin.register(ClassificationLog)
    class ClassificationLogAdmin(admin.ModelAdmin):
        """
        Admin interface for ClassificationLog model with metrics display.
        
        Provides comprehensive view of classification logs with:
        - Total classifications
        - Average confidence
        - Type distribution
        - Performance metrics
        - Low confidence warnings
        """
        
        list_display = [
            'timestamp',
            'user',
            'message_preview',
            'classification_type',
            'confidence_badge',
            'processing_time_badge',
            'user_feedback'
        ]
        
        list_filter = [
            'classification_type',
            'user_feedback',
            'timestamp',
            ('confidence_score', admin.EmptyFieldListFilter),
        ]
        
        search_fields = ['message', 'user__email', 'user__full_name']
        
        readonly_fields = [
            'id',
            'timestamp',
            'user',
            'message',
            'classification_type',
            'confidence_score',
            'all_scores',
            'processing_time_ms',
            'context_data',
            'metrics_summary'
        ]
        
        date_hierarchy = 'timestamp'
        
        fieldsets = (
            ('Classification Details', {
                'fields': (
                    'timestamp',
                    'user',
                    'message',
                    'classification_type',
                    'confidence_score',
                )
            }),
            ('Detailed Scores', {
                'fields': ('all_scores',),
                'classes': ('collapse',)
            }),
            ('Performance', {
                'fields': ('processing_time_ms',)
            }),
            ('Context', {
                'fields': ('context_data',),
                'classes': ('collapse',)
            }),
            ('Feedback', {
                'fields': ('user_feedback',)
            }),
            ('Metrics Summary', {
                'fields': ('metrics_summary',),
                'description': 'System-wide classification metrics for the last 7 days'
            }),
        )
        
        def message_preview(self, obj):
            """Show truncated message preview."""
            max_length = 50
            if len(obj.message) > max_length:
                return f"{obj.message[:max_length]}..."
            return obj.message
        message_preview.short_description = 'Message'
        
        def confidence_badge(self, obj):
            """Display confidence score with color coding."""
            confidence = obj.confidence_score
            
            if confidence > 0.8:
                color = 'green'
                label = 'High'
            elif confidence >= 0.6:
                color = 'orange'
                label = 'Medium'
            else:
                color = 'red'
                label = 'Low'
            
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-weight: bold;">{}: {:.2f}</span>',
                color,
                label,
                confidence
            )
        confidence_badge.short_description = 'Confidence'
        
        def processing_time_badge(self, obj):
            """Display processing time with color coding."""
            time_ms = obj.processing_time_ms
            
            if time_ms > 500:
                color = 'red'
                label = 'Slow'
            elif time_ms > 200:
                color = 'orange'
                label = 'OK'
            else:
                color = 'green'
                label = 'Fast'
            
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 8px; '
                'border-radius: 3px;">{}: {}ms</span>',
                color,
                label,
                time_ms
            )
        processing_time_badge.short_description = 'Processing Time'
        
        def metrics_summary(self, obj):
            """Display system-wide metrics summary."""
            # Calculate metrics for last 7 days
            end_date = timezone.now()
            start_date = end_date - timedelta(days=7)
            
            logs = ClassificationLog.objects.filter(
                timestamp__gte=start_date,
                timestamp__lte=end_date
            )
            
            total_count = logs.count()
            
            if total_count == 0:
                return format_html('<p>No classifications in the last 7 days</p>')
            
            # Calculate metrics
            avg_confidence = logs.aggregate(Avg('confidence_score'))['confidence_score__avg']
            avg_processing_time = logs.aggregate(Avg('processing_time_ms'))['processing_time_ms__avg']
            
            # Confidence distribution
            high_confidence = logs.filter(confidence_score__gt=0.8).count()
            medium_confidence = logs.filter(
                confidence_score__gte=0.6,
                confidence_score__lte=0.8
            ).count()
            low_confidence = logs.filter(confidence_score__lt=0.6).count()
            
            # Type distribution
            type_counts = logs.values('classification_type').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Performance warnings
            slow_classifications = logs.filter(processing_time_ms__gt=500).count()
            
            # Build HTML summary
            html = f"""
            <div style="font-family: monospace; background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
                <h3 style="margin-top: 0;">Classification Metrics (Last 7 Days)</h3>
                
                <h4>Overall Statistics</h4>
                <ul>
                    <li><strong>Total Classifications:</strong> {total_count:,}</li>
                    <li><strong>Average Confidence:</strong> {avg_confidence:.2f}</li>
                    <li><strong>Average Processing Time:</strong> {avg_processing_time:.1f}ms</li>
                </ul>
                
                <h4>Confidence Distribution</h4>
                <ul>
                    <li><strong>High (&gt;0.8):</strong> {high_confidence:,} ({(high_confidence/total_count*100):.1f}%)</li>
                    <li><strong>Medium (0.6-0.8):</strong> {medium_confidence:,} ({(medium_confidence/total_count*100):.1f}%)</li>
                    <li><strong>Low (&lt;0.6):</strong> {low_confidence:,} ({(low_confidence/total_count*100):.1f}%)</li>
                </ul>
                
                <h4>Type Distribution</h4>
                <ul>
            """
            
            for type_data in type_counts:
                type_name = type_data['classification_type']
                count = type_data['count']
                percentage = (count / total_count) * 100
                html += f'<li><strong>{type_name}:</strong> {count:,} ({percentage:.1f}%)</li>'
            
            html += '</ul>'
            
            # Performance warnings
            if slow_classifications > 0:
                html += f"""
                <h4 style="color: red;">Performance Warnings</h4>
                <ul>
                    <li><strong>Slow Classifications (&gt;500ms):</strong> {slow_classifications:,} ({(slow_classifications/total_count*100):.1f}%)</li>
                </ul>
                """
            
            # Accuracy warnings
            if avg_confidence < 0.7:
                html += f"""
                <h4 style="color: red;">Accuracy Warnings</h4>
                <ul>
                    <li><strong>Average confidence below 0.7:</strong> Consider tuning thresholds</li>
                </ul>
                """
            
            if low_confidence / total_count > 0.15:
                html += f"""
                <h4 style="color: orange;">Quality Warnings</h4>
                <ul>
                    <li><strong>High rate of low confidence classifications:</strong> {(low_confidence/total_count*100):.1f}%</li>
                </ul>
                """
            
            html += '</div>'
            
            return format_html(html)
        
        metrics_summary.short_description = 'System Metrics'
        
        def has_add_permission(self, request):
            """Disable manual creation of classification logs."""
            return False
        
        def has_change_permission(self, request, obj=None):
            """Allow changing only user_feedback field."""
            return True
        
        def get_readonly_fields(self, request, obj=None):
            """Make all fields readonly except user_feedback."""
            if obj:
                # Allow editing user_feedback for existing logs
                return [f for f in self.readonly_fields if f != 'user_feedback']
            return self.readonly_fields



if AssistantMemory:
    @admin.register(AssistantMemory)
    class AssistantMemoryAdmin(admin.ModelAdmin):
        """Admin interface for AssistantMemory model"""
        list_display = ['user', 'preferred_name', 'tone_preference', 'topic_count', 'updated_at']
        list_filter = ['tone_preference', 'created_at', 'updated_at']
        search_fields = ['user__email', 'user__full_name', 'preferred_name']
        readonly_fields = ['created_at', 'updated_at']
        
        fieldsets = (
            ('User Information', {
                'fields': ('user', 'preferred_name')
            }),
            ('Preferences', {
                'fields': ('tone_preference', 'role_context')
            }),
            ('Conversation History', {
                'fields': ('last_topics',)
            }),
            ('Metadata', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            }),
        )
        
        def topic_count(self, obj):
            """Display number of stored topics."""
            if obj.last_topics:
                return len(obj.last_topics)
            return 0
        topic_count.short_description = 'Topics Stored'
