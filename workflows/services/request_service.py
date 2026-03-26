"""
Service layer for Request operations.

This module contains business logic for request creation, submission, and approval workflows.
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
from workflows.models import Request, Approval

logger = logging.getLogger(__name__)


class RequestService:
    """Service for request operations.
    
    Encapsulates business logic for request creation, submission, and approval workflows.
    All methods are static and accept validated data from serializers.
    """

    @staticmethod
    def create_request(user, validated_data: Dict[str, Any]) -> Request:
        """
        Create a new request.
        
        Args:
            user: The user creating the request (UserProfile instance)
            validated_data: Data validated by RequestCreateSerializer
            
        Returns:
            Created Request instance
            
        Raises:
            PermissionError: If user lacks permission to create request
            ValidationError: If business rules violated
            BusinessLogicError: If unexpected error occurs
        """
        # Check authentication
        if not user or not user.is_authenticated:
            raise PermissionError("Authentication required. Please log in to create requests.")
        
        # Check permissions
        is_super_admin = getattr(user, 'is_super_admin', False)
        is_admin = getattr(user, 'is_admin', False)
        
        # Get company from validated data
        company = validated_data.get('company')
        if not company:
            raise ValidationError({'company': 'Company is required'})
        
        # Permission check: non-admins can only create requests for their own company
        if not is_super_admin and not is_admin:
            user_company = user.company
            if not user_company:
                raise ValidationError({
                    'company': 'Your profile does not have a company assigned. '
                              'Please contact an administrator to assign you to a company.'
                })
            if company.id != user_company.id:
                raise PermissionError("You can only create requests for your own company")
        
        # Permission check: company admins can only create requests for their own company
        elif is_admin and not is_super_admin:
            user_company = user.company
            if not user_company:
                raise ValidationError({
                    'company': 'Your admin profile does not have a company assigned. '
                              'Please contact a super administrator.'
                })
            if company.id != user_company.id:
                raise PermissionError("As a company admin, you can only create requests for your own company")
        
        try:
            with transaction.atomic():
                # Create request with requester set to current user
                request_obj = Request.objects.create(
                    requester=user,
                    **validated_data
                )
                return request_obj
                
        except Exception as e:
            logger.exception(
                "Unexpected error in RequestService.create_request",
                extra={'user_id': user.id, 'company_id': company.id}
            )
            raise BusinessLogicError(f"Failed to create request: {str(e)}")

    @staticmethod
    def update_request(request_obj: Request, user, validated_data: Dict[str, Any]) -> Request:
        """
        Update a request (only if draft).
        
        Args:
            request_obj: The request to update
            user: The user updating the request
            validated_data: Data validated by RequestUpdateSerializer
            
        Returns:
            Updated Request instance
            
        Raises:
            PermissionError: If user lacks permission to update request
            ValidationError: If business rules violated
            BusinessLogicError: If unexpected error occurs
        """
        # Check if request is still in draft status
        if request_obj.status != 'draft':
            raise ValidationError({'status': 'Only draft requests can be updated'})
        
        # Check permissions: non-admins can only update their own requests
        is_admin = getattr(user, 'is_admin', False)
        if not is_admin and request_obj.requester != user:
            raise PermissionError("You can only update your own requests")
        
        try:
            with transaction.atomic():
                # Update request fields
                for field, value in validated_data.items():
                    setattr(request_obj, field, value)
                request_obj.save()
                return request_obj
                
        except Exception as e:
            logger.exception(
                "Unexpected error in RequestService.update_request",
                extra={'request_id': request_obj.id, 'user_id': user.id}
            )
            raise BusinessLogicError(f"Failed to update request: {str(e)}")

    @staticmethod
    def delete_request(request_obj: Request, user) -> None:
        """
        Delete a request (only if draft).
        
        Args:
            request_obj: The request to delete
            user: The user deleting the request
            
        Raises:
            PermissionError: If user lacks permission to delete request
            ValidationError: If business rules violated
            BusinessLogicError: If unexpected error occurs
        """
        # Check if request is still in draft status
        if request_obj.status != 'draft':
            raise ValidationError({'status': 'Only draft requests can be deleted'})
        
        # Check permissions: non-admins can only delete their own requests
        is_admin = getattr(user, 'is_admin', False)
        if not is_admin and request_obj.requester != user:
            raise PermissionError("You can only delete your own requests")
        
        try:
            with transaction.atomic():
                request_obj.delete()
                
        except Exception as e:
            logger.exception(
                "Unexpected error in RequestService.delete_request",
                extra={'request_id': request_obj.id, 'user_id': user.id}
            )
            raise BusinessLogicError(f"Failed to delete request: {str(e)}")

    @staticmethod
    def submit_request(request_obj: Request, user) -> Request:
        """
        Submit a request for approval (changes status from draft to pending).
        
        Args:
            request_obj: The request to submit
            user: The user submitting the request
            
        Returns:
            Updated Request instance
            
        Raises:
            PermissionError: If user lacks permission to submit request
            ValidationError: If business rules violated
            BusinessLogicError: If unexpected error occurs
        """
        # Check permissions: only requester or admin can submit
        is_admin = getattr(user, 'is_admin', False)
        if not is_admin and request_obj.requester != user:
            raise PermissionError("You can only submit your own requests")
        
        # Check if request is in draft status
        if request_obj.status != 'draft':
            raise ValidationError({'status': 'Only draft requests can be submitted'})
        
        try:
            with transaction.atomic():
                # Change status to pending
                request_obj.status = 'pending'
                request_obj.submission_date = timezone.now()
                request_obj.save()
                
                # Create notifications for admins
                RequestService._notify_admins_of_submission(request_obj)
                
                # Create approval records for designated approvers
                RequestService._create_approval_records(request_obj)
                
                return request_obj
                
        except Exception as e:
            logger.exception(
                "Unexpected error in RequestService.submit_request",
                extra={'request_id': request_obj.id, 'user_id': user.id}
            )
            raise BusinessLogicError(f"Failed to submit request: {str(e)}")

    # Helper methods

    @staticmethod
    def _notify_admins_of_submission(request_obj: Request) -> None:
        """Create notifications for admins about new request requiring approval."""
        try:
            from notifications.models import Notification
            from authentication.models import UserProfile
            
            # Get all admins in the same company
            admins = UserProfile.objects.filter(
                company=request_obj.company,
                role__in=['admin', 'super_admin']
            )
            
            notification_type = f"{request_obj.request_type}_submitted"
            title = f"New {request_obj.get_request_type_display()} Request"
            message = f"{request_obj.requester.full_name} submitted a {request_obj.get_request_type_display().lower()} request for approval"
            
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    related_entity_type='request',
                    related_entity_id=str(request_obj.id),
                    metadata={
                        'request_id': str(request_obj.id),
                        'request_type': request_obj.request_type,
                        'submitted_by': request_obj.requester.full_name,
                        'link': '/approvals'
                    }
                )
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to create submission notification: {e}")

    @staticmethod
    def _create_approval_records(request_obj: Request) -> None:
        """Create approval records for designated approvers."""
        try:
            from authentication.models import UserProfile
            
            # Get all admins in the same company who can approve
            approvers = UserProfile.objects.filter(
                company=request_obj.company,
                role__in=['admin', 'super_admin']
            )
            
            # Create approval records for each approver
            for i, approver in enumerate(approvers, 1):
                Approval.objects.create(
                    request=request_obj,
                    approver=approver,
                    step_number=i,
                    status='pending'
                )
        except Exception as e:
            logger.error(f"Failed to create approval records: {e}")
