from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter notifications for the current user
        """
        if not self.request.user or not self.request.user.is_authenticated:
            return Notification.objects.none()
        
        return Notification.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """
        Prevent direct creation via API
        """
        return Response(
            {'error': 'Notifications cannot be created directly via API'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def update(self, request, *args, **kwargs):
        """
        Prevent direct updates via API (use mark_read action instead)
        """
        return Response(
            {'error': 'Use mark_read action to update notifications'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark a notification as read
        """
        notification = self.get_object()
        notification.mark_as_read()
        
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Mark all notifications as read for the current user
        """
        queryset = self.get_queryset().filter(is_read=False)
        count = queryset.count()
        
        # Update all unread notifications
        queryset.update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return Response({
            'message': f'Marked {count} notifications as read',
            'count': count
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread notifications
        """
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})