"""
Views for communications app
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db import models
from .models import Message, Notification
from .serializers import (
    MessageListSerializer,
    MessageDetailSerializer,
    MessageCreateSerializer,
    NotificationListSerializer,
    NotificationDetailSerializer
)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Message CRUD operations.
    
    Endpoints:
    - GET /api/messages/ - List messages (sent or received by user)
    - POST /api/messages/ - Send message
    - GET /api/messages/{id}/ - Get message details
    - DELETE /api/messages/{id}/ - Delete message
    - POST /api/messages/{id}/mark_read/ - Mark message as read
    """
    queryset = Message.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['sender', 'recipient', 'is_read']
    search_fields = ['subject', 'content']
    ordering_fields = ['sent_at']
    ordering = ['-sent_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        # Use detail serializer for all actions to include sender/recipient fields
        return MessageDetailSerializer
    
    def get_queryset(self):
        """
        Filter messages to show only messages sent or received by the user.
        Includes broadcast messages for all users.
        Unauthenticated users see all (for development).
        """
        user = self.request.user
        
        # Allow unauthenticated access for development
        if not user or not user.is_authenticated:
            # For unauthenticated requests, try to filter by user_id from query params
            user_id = self.request.query_params.get('user_id')
            if user_id:
                return Message.objects.filter(
                    models.Q(sender_id=user_id) | 
                    models.Q(recipient_id=user_id) | 
                    models.Q(is_broadcast=True)
                ).order_by('-sent_at')
            return Message.objects.all().order_by('-sent_at')
        
        # Users see:
        # 1. Messages they sent
        # 2. Messages they received
        # 3. All broadcast messages
        return Message.objects.filter(
            models.Q(sender=user) | 
            models.Q(recipient=user) | 
            models.Q(is_broadcast=True)
        ).order_by('-sent_at')
    
    def create(self, request, *args, **kwargs):
        """
        Send a new message
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Set sender to current user
        message = serializer.save(sender=request.user)
        
        # TODO: Create notification for recipient
        # This will be implemented when notification creation is added
        
        # Return detailed serializer
        detail_serializer = MessageDetailSerializer(message)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Get message details and automatically mark as read if recipient
        """
        instance = self.get_object()
        
        # Automatically mark as read if recipient is viewing
        if instance.recipient == request.user and not instance.is_read:
            instance.is_read = True
            instance.read_at = timezone.now()
            instance.save()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a message (sender or recipient can delete)
        """
        instance = self.get_object()
        
        # Only sender or recipient can delete
        if instance.sender != request.user and instance.recipient != request.user:
            return Response(
                {'error': 'You can only delete your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark a message as read
        """
        message = self.get_object()
        
        # Only recipient can mark as read
        if message.recipient != request.user:
            return Response(
                {'error': 'Only the recipient can mark a message as read'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if message.is_read:
            return Response(
                {'error': 'Message is already marked as read'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message.is_read = True
        message.read_at = timezone.now()
        message.save()
        
        serializer = MessageDetailSerializer(message)
        return Response(serializer.data)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Notification operations.
    
    Endpoints:
    - GET /api/notifications/ - List notifications (unread first)
    - POST /api/notifications/ - Create notification
    - GET /api/notifications/unread/ - Get unread notifications
    - GET /api/notifications/{id}/ - Get notification details
    - POST /api/notifications/{id}/mark_read/ - Mark notification as read
    - POST /api/notifications/mark_all_read/ - Mark all notifications as read
    """
    queryset = Notification.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['notification_type', 'is_read']
    search_fields = ['title', 'message']
    ordering_fields = ['created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        # Use detail serializer for all actions to include user field
        return NotificationDetailSerializer
    
    def get_queryset(self):
        """
        Filter notifications to show only user's notifications.
        Order by unread first, then by creation date descending.
        Unauthenticated users see all (for development).
        """
        user = self.request.user
        
        # Allow unauthenticated access for development
        if not user or not user.is_authenticated:
            # For unauthenticated requests, try to filter by user_id from query params
            user_id = self.request.query_params.get('user_id')
            if user_id:
                return Notification.objects.filter(user_id=user_id).order_by('is_read', '-created_at')
            return Notification.objects.all().order_by('is_read', '-created_at')
        
        # Users see only their own notifications
        # Order by is_read (False first), then by created_at descending
        return Notification.objects.filter(user=user).order_by('is_read', '-created_at')
    
    def create(self, request, *args, **kwargs):
        """
        Create a new notification
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """
        Get unread notifications
        """
        notifications = self.get_queryset().filter(is_read=False)
        serializer = NotificationListSerializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark a notification as read
        """
        notification = self.get_object()
        
        if notification.is_read:
            return Response(
                {'error': 'Notification is already marked as read'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        serializer = NotificationDetailSerializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Mark all notifications as read
        """
        user = request.user
        
        # Update all unread notifications
        updated_count = Notification.objects.filter(
            user=user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return Response({
            'message': f'{updated_count} notifications marked as read',
            'count': updated_count
        })
