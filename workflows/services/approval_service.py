"""
Service layer for Approval operations.

This module contains business logic for approving and rejecting requests.
"""

import logging
from typing import Dict, Any
from django.utils import timezone
from django.db import transaction

from core.exceptions import (
    ValidationError,
    PermissionError,
    BusinessLogicError,
)
from workflows.models import Approval

logger = logging.getLogger(__name__)


class ApprovalService:
    """Service for approval operations.
    
    Encapsulates business logic for approving and rejecting requests.
    All methods are static and accept validated data from serializers.
    """

    @staticmethod
    def approve_request(approval: Approval, user, approval_data: Dict[str, Any]) -> Approval:
        """
        Approve a request.
        
        Args:
            approval: The approval record to process
            user: The user approving (must be the assigned approver)
            approval_data: Data containing comments and other approval info
            
        Returns:
            Updated Approval instance
            
        Raises:
            PermissionError: If user lacks permission to approve
            ValidationError: If approval not in correct state
            BusinessLogicError: If unexpected error occurs
        """
        # Check permissions: only the assigned approver can approve
        if approval.approver != user:
            raise PermissionError("You are not authorized to approve this request")
        
        # Check if approval is pending
        if approval.status != 'pending':
            raise ValidationError({'status': 'Only pending approvals can be approved'})
        
        try:
            with transaction.atomic():
                comments = approval_data.get('comments', '')
                
                # Update approval
                approval.status = 'approved'
                approval.comments = comments
                approval.approved_at = timezone.now()
                approval.save()
                
                # Update request status and store approver info
                request_obj = approval.request
                request_obj.status = 'approved'
                request_obj.completion_date = timezone.now()
                
                # Store approver information in request data
                if request_obj.data is None:
                    request_obj.data = {}
                request_obj.data['approvedBy'] = user.full_name
                request_obj.data['approvedAt'] = timezone.now().isoformat()
                request_obj.save()
                
                # Create notification for requester
                ApprovalService._notify_request_approved(request_obj, user, comments)
                
                return approval
                
        except Exception as e:
            logger.exception(
                "Unexpected error in ApprovalService.approve_request",
                extra={'approval_id': approval.id, 'user_id': user.id}
            )
            raise BusinessLogicError(f"Failed to approve request: {str(e)}")

    @staticmethod
    def reject_request(approval: Approval, user, rejection_data: Dict[str, Any]) -> Approval:
        """
        Reject a request.
        
        Args:
            approval: The approval record to process
            user: The user rejecting (must be the assigned approver)
            rejection_data: Data containing comments/reason for rejection
            
        Returns:
            Updated Approval instance
            
        Raises:
            PermissionError: If user lacks permission to reject
            ValidationError: If approval not in correct state
            BusinessLogicError: If unexpected error occurs
        """
        # Check permissions: only the assigned approver can reject
        if approval.approver != user:
            raise PermissionError("You are not authorized to reject this request")
        
        # Check if approval is pending
        if approval.status != 'pending':
            raise ValidationError({'status': 'Only pending approvals can be rejected'})
        
        try:
            with transaction.atomic():
                comments = rejection_data.get('comments', '')
                
                # Update approval
                approval.status = 'rejected'
                approval.comments = comments
                approval.approved_at = timezone.now()
                approval.save()
                
                # Update request status to rejected and store rejector info
                request_obj = approval.request
                request_obj.status = 'rejected'
                request_obj.completion_date = timezone.now()
                
                # Store rejector information in request data
                if request_obj.data is None:
                    request_obj.data = {}
                request_obj.data['rejectedBy'] = user.full_name
                request_obj.data['rejectedAt'] = timezone.now().isoformat()
                request_obj.save()
                
                # Create notification for requester
                ApprovalService._notify_request_rejected(request_obj, user, comments)
                
                return approval
                
        except Exception as e:
            logger.exception(
                "Unexpected error in ApprovalService.reject_request",
                extra={'approval_id': approval.id, 'user_id': user.id}
            )
            raise BusinessLogicError(f"Failed to reject request: {str(e)}")

    # Helper methods

    @staticmethod
    def _notify_request_approved(request_obj, approver, comments: str) -> None:
        """Create notification for requester about approval."""
        try:
            from notifications.models import Notification
            
            notification_type = f"{request_obj.request_type}_approved"
            title = f"{request_obj.get_request_type_display()} Approved"
            message = f"Your {request_obj.get_request_type_display().lower()} request has been approved"
            if comments:
                message += f" with comments: {comments}"
            
            Notification.objects.create(
                user=request_obj.requester,
                notification_type=notification_type,
                title=title,
                message=message,
                related_entity_type='request',
                related_entity_id=str(request_obj.id),
                metadata={
                    'request_id': str(request_obj.id),
                    'request_type': request_obj.request_type,
                    'approved_by': approver.full_name,
                    'comments': comments,
                    'link': '/requests'
                }
            )
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to create approval notification: {e}")

    @staticmethod
    def _notify_request_rejected(request_obj, rejector, comments: str) -> None:
        """Create notification for requester about rejection."""
        try:
            from notifications.models import Notification
            
            notification_type = f"{request_obj.request_type}_rejected"
            title = f"{request_obj.get_request_type_display()} Rejected"
            message = f"Your {request_obj.get_request_type_display().lower()} request has been rejected"
            if comments:
                message += f" with reason: {comments}"
            
            Notification.objects.create(
                user=request_obj.requester,
                notification_type=notification_type,
                title=title,
                message=message,
                related_entity_type='request',
                related_entity_id=str(request_obj.id),
                metadata={
                    'request_id': str(request_obj.id),
                    'request_type': request_obj.request_type,
                    'rejected_by': rejector.full_name,
                    'comments': comments,
                    'link': '/requests'
                }
            )
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to create rejection notification: {e}")
