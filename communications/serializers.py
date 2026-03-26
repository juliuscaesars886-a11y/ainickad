"""
Serializers for communications app
"""
from rest_framework import serializers
from .models import Message, Notification


class MessageListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing messages (minimal fields)
    """
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    recipient_name = serializers.SerializerMethodField()
    is_reply = serializers.ReadOnlyField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'sender_name', 'recipient', 'recipient_name',
            'subject', 'content', 'is_broadcast', 'is_read', 'is_reply', 'sent_at'
        ]
        read_only_fields = ['id', 'sent_at']
    
    def get_recipient_name(self, obj):
        """Get recipient name or 'All Staff' for broadcasts"""
        if obj.is_broadcast:
            return 'All Staff'
        return obj.recipient.full_name if obj.recipient else 'Unknown'


class MessageDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for message details (all fields)
    """
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    recipient_name = serializers.SerializerMethodField()
    is_reply = serializers.ReadOnlyField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'sender_name', 'recipient', 'recipient_name',
            'subject', 'content', 'is_broadcast', 'parent_message', 'is_read', 'read_at',
            'is_reply', 'sent_at', 'metadata'
        ]
        read_only_fields = ['id', 'sender', 'is_read', 'read_at', 'sent_at']
    
    def get_recipient_name(self, obj):
        """Get recipient name or 'All Staff' for broadcasts"""
        if obj.is_broadcast:
            return 'All Staff'
        return obj.recipient.full_name if obj.recipient else 'Unknown'


class MessageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating messages
    """
    class Meta:
        model = Message
        fields = ['recipient', 'subject', 'content', 'is_broadcast', 'parent_message', 'metadata']
    
    def validate(self, data):
        """Validate message data"""
        is_broadcast = data.get('is_broadcast', False)
        recipient = data.get('recipient')
        
        # Broadcast messages should not have a recipient
        if is_broadcast and recipient:
            raise serializers.ValidationError("Broadcast messages cannot have a recipient.")
        
        # Non-broadcast messages must have a recipient
        if not is_broadcast and not recipient:
            raise serializers.ValidationError("Direct messages must have a recipient.")
        
        return data
    
    def validate_content(self, value):
        """Validate content is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Content cannot be empty.")
        return value


class NotificationListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing notifications (minimal fields)
    """
    is_unread = serializers.ReadOnlyField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'is_read',
            'is_unread', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for notification details (all fields)
    """
    is_unread = serializers.ReadOnlyField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'title', 'message',
            'related_entity_type', 'related_entity_id', 'is_read',
            'read_at', 'is_unread', 'created_at', 'metadata'
        ]
        read_only_fields = ['id', 'is_read', 'read_at', 'created_at']
