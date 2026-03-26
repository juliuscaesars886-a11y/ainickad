from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model
    """
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'user',
            'notification_type',
            'title',
            'message',
            'related_entity_type',
            'related_entity_id',
            'is_read',
            'read_at',
            'created_at',
            'metadata'
        ]
        read_only_fields = [
            'id',
            'user',
            'created_at',
            'read_at'
        ]