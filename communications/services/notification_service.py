"""
Service layer for Notification operations.

This module contains business logic for creating notifications
and handling notification-related operations.
"""

import logging
from typing import List, Dict, Any, Optional
from django.db import transaction

from core.exceptions import (
    ValidationError,
    BusinessLogicError,
)
from authentication.models import UserProfile

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for notification operations.
    
    Encapsulates business logic for creating notifications.
    Failures in notification creation do not break parent operations.
    All methods are static and handle errors gracefully.
    """

    @staticmethod
    def create_notification(
        user: UserProfile,
        notification_type: str,
        message: str,
        title: Optional[str] = None,
        related_object: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Create a single notification for a user.
        
        Args:
            user: The user to notify
            notification_type: Type of notification
            message: Notification message
            title: Optional notification title
            related_object: Optional related object (Task, Request, etc.)
            metadata: Optional metadata dictionary
            
        Returns:
            Created Notification instance or None if creation fails
            
        Note:
            Failures are logged but do not raise exceptions.
            This ensures notification failures don't break parent operations.
        """
        if not user or not notification_type or not message:
            logger.warning(
                "Invalid notification parameters",
                extra={
                    'user_id': user.id if user else None,
                    'notification_type': notification_type,
                    'message': message
                }
            )
            return None
        
        try:
            from communications.models import Notification
            
            # Prepare notification data
            notification_data = {
                'user': user,
                'notification_type': notification_type,
                'message': message,
                'title': title or notification_type.replace('_', ' ').title(),
                'is_read': False,
            }
            
            # Add related object info if provided
            if related_object:
                notification_data['related_entity_type'] = related_object.__class__.__name__.lower()
                notification_data['related_entity_id'] = str(related_object.id)
            
            # Add metadata if provided
            if metadata:
                notification_data['metadata'] = metadata
            
            # Create notification
            notification = Notification.objects.create(**notification_data)
            
            logger.debug(
                f"Notification created for user {user.email}",
                extra={'notification_id': notification.id, 'type': notification_type}
            )
            
            return notification
            
        except Exception as e:
            logger.error(
                f"Failed to create notification for user {user.email}: {str(e)}",
                exc_info=True,
                extra={'user_id': user.id, 'notification_type': notification_type}
            )
            # Don't raise - return None to allow parent operation to continue
            return None

    @staticmethod
    def bulk_create_notifications(
        users: List[UserProfile],
        notification_type: str,
        message: str,
        title: Optional[str] = None,
        related_object: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Create notifications for multiple users.
        
        Args:
            users: List of users to notify
            notification_type: Type of notification
            message: Notification message
            title: Optional notification title
            related_object: Optional related object
            metadata: Optional metadata dictionary
            
        Returns:
            List of created Notification instances (excludes failed creations)
            
        Note:
            Failures for individual users are logged but do not stop
            notification creation for other users.
        """
        if not users or not notification_type or not message:
            logger.warning(
                "Invalid bulk notification parameters",
                extra={
                    'user_count': len(users) if users else 0,
                    'notification_type': notification_type,
                    'message': message
                }
            )
            return []
        
        created_notifications = []
        
        try:
            for user in users:
                notification = NotificationService.create_notification(
                    user=user,
                    notification_type=notification_type,
                    message=message,
                    title=title,
                    related_object=related_object,
                    metadata=metadata
                )
                
                if notification:
                    created_notifications.append(notification)
            
            logger.info(
                f"Bulk notifications created",
                extra={
                    'total_users': len(users),
                    'created': len(created_notifications),
                    'failed': len(users) - len(created_notifications),
                    'notification_type': notification_type
                }
            )
            
            return created_notifications
            
        except Exception as e:
            logger.error(
                f"Error in bulk notification creation: {str(e)}",
                exc_info=True,
                extra={'user_count': len(users), 'notification_type': notification_type}
            )
            # Return what we've created so far
            return created_notifications

    @staticmethod
    def notify_task_assigned(task: Any) -> Optional[Any]:
        """
        Send task assignment notification to assignee.
        
        Args:
            task: The task that was assigned
            
        Returns:
            Created Notification instance or None if creation fails
        """
        if not task or not task.assignee:
            return None
        
        try:
            return NotificationService.create_notification(
                user=task.assignee,
                notification_type='task_assigned',
                message=f"You have been assigned task: {task.title}",
                title='Task Assigned',
                related_object=task,
                metadata={
                    'task_id': str(task.id),
                    'task_title': task.title,
                    'assigned_by': task.creator.full_name if task.creator else 'Unknown',
                    'link': f'/tasks/{task.id}'
                }
            )
        except Exception as e:
            logger.error(f"Failed to notify task assignment: {e}")
            return None

    @staticmethod
    def notify_task_completed(task: Any) -> Optional[Any]:
        """
        Send task completion notification to creator.
        
        Args:
            task: The task that was completed
            
        Returns:
            Created Notification instance or None if creation fails
        """
        if not task or not task.creator:
            return None
        
        try:
            return NotificationService.create_notification(
                user=task.creator,
                notification_type='task_completed',
                message=f"Task completed: {task.title}",
                title='Task Completed',
                related_object=task,
                metadata={
                    'task_id': str(task.id),
                    'task_title': task.title,
                    'completed_by': task.assignee.full_name if task.assignee else 'Unknown',
                    'link': f'/tasks/{task.id}'
                }
            )
        except Exception as e:
            logger.error(f"Failed to notify task completion: {e}")
            return None

    @staticmethod
    def notify_approval_required(approval: Any) -> Optional[Any]:
        """
        Send approval request notification to approver.
        
        Args:
            approval: The approval record
            
        Returns:
            Created Notification instance or None if creation fails
        """
        if not approval or not approval.approver:
            return None
        
        try:
            request_obj = approval.request
            return NotificationService.create_notification(
                user=approval.approver,
                notification_type='approval_required',
                message=f"Approval required for {request_obj.get_request_type_display()}",
                title='Approval Required',
                related_object=approval,
                metadata={
                    'approval_id': str(approval.id),
                    'request_id': str(request_obj.id),
                    'request_type': request_obj.request_type,
                    'requester': request_obj.requester.full_name if request_obj.requester else 'Unknown',
                    'link': '/approvals'
                }
            )
        except Exception as e:
            logger.error(f"Failed to notify approval required: {e}")
            return None

    @staticmethod
    def notify_request_approved(request_obj: Any, approver: UserProfile, comments: str = '') -> Optional[Any]:
        """
        Send request approval notification to requester.
        
        Args:
            request_obj: The request that was approved
            approver: The user who approved
            comments: Optional approval comments
            
        Returns:
            Created Notification instance or None if creation fails
        """
        if not request_obj or not request_obj.requester:
            return None
        
        try:
            message = f"Your {request_obj.get_request_type_display().lower()} request has been approved"
            if comments:
                message += f" with comments: {comments}"
            
            return NotificationService.create_notification(
                user=request_obj.requester,
                notification_type=f"{request_obj.request_type}_approved",
                message=message,
                title=f"{request_obj.get_request_type_display()} Approved",
                related_object=request_obj,
                metadata={
                    'request_id': str(request_obj.id),
                    'request_type': request_obj.request_type,
                    'approved_by': approver.full_name,
                    'comments': comments,
                    'link': '/requests'
                }
            )
        except Exception as e:
            logger.error(f"Failed to notify request approval: {e}")
            return None

    @staticmethod
    def notify_request_rejected(request_obj: Any, rejector: UserProfile, comments: str = '') -> Optional[Any]:
        """
        Send request rejection notification to requester.
        
        Args:
            request_obj: The request that was rejected
            rejector: The user who rejected
            comments: Optional rejection reason
            
        Returns:
            Created Notification instance or None if creation fails
        """
        if not request_obj or not request_obj.requester:
            return None
        
        try:
            message = f"Your {request_obj.get_request_type_display().lower()} request has been rejected"
            if comments:
                message += f" with reason: {comments}"
            
            return NotificationService.create_notification(
                user=request_obj.requester,
                notification_type=f"{request_obj.request_type}_rejected",
                message=message,
                title=f"{request_obj.get_request_type_display()} Rejected",
                related_object=request_obj,
                metadata={
                    'request_id': str(request_obj.id),
                    'request_type': request_obj.request_type,
                    'rejected_by': rejector.full_name,
                    'comments': comments,
                    'link': '/requests'
                }
            )
        except Exception as e:
            logger.error(f"Failed to notify request rejection: {e}")
            return None
