"""
Service layer for Task operations.

This module contains business logic for task creation, updates, completion, and assignment.
Services handle authorization, validation, database operations, and notifications.
"""

import logging
from typing import Optional, Dict, Any
from django.utils import timezone
from django.db import transaction

from core.exceptions import (
    ValidationError,
    PermissionError,
    BusinessLogicError,
    ResourceNotFoundError,
)
from workflows.models import Task

logger = logging.getLogger(__name__)


class TaskService:
    """Service for task operations.
    
    Encapsulates business logic for task creation, updates, completion, and assignment.
    All methods are static and accept validated data from serializers.
    """

    @staticmethod
    def create_task(user, validated_data: Dict[str, Any]) -> Task:
        """
        Create a new task with business logic.
        
        Args:
            user: The user creating the task (UserProfile instance)
            validated_data: Data validated by TaskCreateSerializer
            
        Returns:
            Created Task instance
            
        Raises:
            PermissionError: If user lacks permission to create task
            ValidationError: If business rules violated
            BusinessLogicError: If unexpected error occurs
        """
        # Check authentication
        if not user or not user.is_authenticated:
            raise PermissionError("Authentication required. Please log in to create tasks.")
        
        # Check permissions
        is_super_admin = getattr(user, 'is_super_admin', False)
        is_admin = getattr(user, 'is_admin', False)
        
        # Get company from validated data
        company = validated_data.get('company')
        if not company:
            raise ValidationError({'company': 'Company is required'})
        
        # Permission check: non-admins can only create tasks for their own company
        if not is_super_admin and not is_admin:
            user_company = user.company
            if not user_company:
                raise ValidationError({
                    'company': 'Your profile does not have a company assigned. '
                              'Please contact an administrator to assign you to a company.'
                })
            if company.id != user_company.id:
                raise PermissionError("You can only create tasks for your own company")
        
        # Permission check: company admins can only create tasks for their own company
        elif is_admin and not is_super_admin:
            user_company = user.company
            if not user_company:
                raise ValidationError({
                    'company': 'Your admin profile does not have a company assigned. '
                              'Please contact a super administrator.'
                })
            if company.id != user_company.id:
                raise PermissionError("As a company admin, you can only create tasks for your own company")
        
        try:
            with transaction.atomic():
                # Create task with creator set to current user
                task = Task.objects.create(
                    creator=user,
                    **validated_data
                )
                
                # Handle company assignment to assignee if requested
                assign_company = validated_data.get('assign_company', False)
                if assign_company and (is_admin or is_super_admin):
                    TaskService._assign_company_to_assignee(
                        task=task,
                        assigner=user,
                        action='assigned'
                    )
                
                # Create notification for assignee
                TaskService._notify_task_assigned(task, user)
                
                return task
                
        except Exception as e:
            logger.exception(
                "Unexpected error in TaskService.create_task",
                extra={'user_id': user.id, 'company_id': company.id}
            )
            raise BusinessLogicError(f"Failed to create task: {str(e)}")

    @staticmethod
    def update_task(task: Task, user, validated_data: Dict[str, Any]) -> Task:
        """
        Update a task with business logic.
        
        Args:
            task: The task to update
            user: The user updating the task
            validated_data: Data validated by TaskUpdateSerializer
            
        Returns:
            Updated Task instance
            
        Raises:
            PermissionError: If user lacks permission to update task
            ValidationError: If business rules violated
            BusinessLogicError: If unexpected error occurs
        """
        # Check permissions: creator, assignee, or admin can update
        is_admin = getattr(user, 'is_admin', False)
        if not is_admin and task.creator != user and task.assignee != user:
            raise PermissionError("You can only update tasks you created or are assigned to")
        
        try:
            with transaction.atomic():
                # Store old values to detect changes
                old_status = task.status
                old_assignee = task.assignee
                
                # Update task fields
                for field, value in validated_data.items():
                    if field != 'assign_company':
                        setattr(task, field, value)
                task.save()
                
                # Handle company assignment if requested and assignee changed
                assign_company = validated_data.get('assign_company', False)
                if assign_company and is_admin and task.assignee != old_assignee:
                    TaskService._assign_company_to_assignee(
                        task=task,
                        assigner=user,
                        action='reassigned'
                    )
                
                # Create notification if status changed
                if old_status != task.status:
                    TaskService._notify_task_status_changed(task, old_status)
                
                return task
                
        except Exception as e:
            logger.exception(
                "Unexpected error in TaskService.update_task",
                extra={'task_id': task.id, 'user_id': user.id}
            )
            raise BusinessLogicError(f"Failed to update task: {str(e)}")

    @staticmethod
    def complete_task(task: Task, user, completion_data: Dict[str, Any]) -> Task:
        """
        Mark a task as complete.
        
        Args:
            task: The task to complete
            user: The user completing the task
            completion_data: Data containing notes and other completion info
            
        Returns:
            Updated Task instance
            
        Raises:
            PermissionError: If user lacks permission to complete task
            ValidationError: If business rules violated
            BusinessLogicError: If unexpected error occurs
        """
        # Check permissions: only assignee or admin can complete
        is_admin = getattr(user, 'is_admin', False)
        if not is_admin and task.assignee != user:
            raise PermissionError("Only the assignee can mark a task as complete")
        
        # Check if already completed (idempotent)
        if task.status == 'completed':
            return task
        
        try:
            with transaction.atomic():
                notes = completion_data.get('notes', '')
                
                # Admin directly completes the task
                if is_admin:
                    task.status = 'completed'
                    task.completed_at = timezone.now()
                    task.save()
                    TaskService._notify_admin_completion(task, user)
                else:
                    # Staff member marks as completed and pending approval
                    task.status = 'completed'
                    task.completed_at = timezone.now()
                    
                    # Store completion notes in metadata
                    if not task.metadata:
                        task.metadata = {}
                    task.metadata['completion_notes'] = notes
                    task.metadata['pending_approval'] = True
                    task.save()
                    
                    TaskService._notify_approval_required(task, notes)
                
                return task
                
        except Exception as e:
            logger.exception(
                "Unexpected error in TaskService.complete_task",
                extra={'task_id': task.id, 'user_id': user.id}
            )
            raise BusinessLogicError(f"Failed to complete task: {str(e)}")

    @staticmethod
    def assign_task(task: Task, assignee, assigner) -> Task:
        """
        Assign a task to a user.
        
        Args:
            task: The task to assign
            assignee: The user to assign the task to
            assigner: The user assigning the task
            
        Returns:
            Updated Task instance
            
        Raises:
            PermissionError: If user lacks permission to assign task
            BusinessLogicError: If unexpected error occurs
        """
        # Check permissions: only admin can assign
        is_admin = getattr(assigner, 'is_admin', False)
        if not is_admin:
            raise PermissionError("Only admins can assign tasks")
        
        try:
            with transaction.atomic():
                old_assignee = task.assignee
                task.assignee = assignee
                task.save()
                
                # Notify new assignee
                TaskService._notify_task_assigned(task, assigner)
                
                return task
                
        except Exception as e:
            logger.exception(
                "Unexpected error in TaskService.assign_task",
                extra={'task_id': task.id, 'assignee_id': assignee.id}
            )
            raise BusinessLogicError(f"Failed to assign task: {str(e)}")

    @staticmethod
    def approve_completion(task: Task, user) -> Task:
        """
        Approve a completed task.
        
        Args:
            task: The task to approve
            user: The user approving (must be admin)
            
        Returns:
            Updated Task instance
            
        Raises:
            PermissionError: If user lacks permission
            ValidationError: If task not in correct state
            BusinessLogicError: If unexpected error occurs
        """
        # Check permissions: only admin can approve
        is_admin = getattr(user, 'is_admin', False)
        if not is_admin:
            raise PermissionError("Only admins can approve task completions")
        
        # Check task state
        if task.status != 'completed':
            raise ValidationError({'status': 'Task must be completed to approve'})
        
        if not task.metadata or not task.metadata.get('pending_approval'):
            raise ValidationError({'status': 'Task is not pending approval'})
        
        try:
            with transaction.atomic():
                task.status = 'approved'
                if not task.metadata:
                    task.metadata = {}
                task.metadata['pending_approval'] = False
                task.metadata['approved_by'] = str(user.id)
                task.metadata['approved_at'] = timezone.now().isoformat()
                task.save()
                
                # Notify assignee about approval
                TaskService._notify_task_approved(task, user)
                
                return task
                
        except Exception as e:
            logger.exception(
                "Unexpected error in TaskService.approve_completion",
                extra={'task_id': task.id, 'user_id': user.id}
            )
            raise BusinessLogicError(f"Failed to approve task: {str(e)}")

    @staticmethod
    def reject_completion(task: Task, user, rejection_data: Dict[str, Any]) -> Task:
        """
        Reject a completed task.
        
        Args:
            task: The task to reject
            user: The user rejecting (must be admin)
            rejection_data: Data containing rejection reason
            
        Returns:
            Updated Task instance
            
        Raises:
            PermissionError: If user lacks permission
            ValidationError: If task not in correct state
            BusinessLogicError: If unexpected error occurs
        """
        # Check permissions: only admin can reject
        is_admin = getattr(user, 'is_admin', False)
        if not is_admin:
            raise PermissionError("Only admins can reject task completions")
        
        # Check task state
        if task.status != 'completed':
            raise ValidationError({'status': 'Task must be completed to reject'})
        
        if not task.metadata or not task.metadata.get('pending_approval'):
            raise ValidationError({'status': 'Task is not pending approval'})
        
        try:
            with transaction.atomic():
                reason = rejection_data.get('reason', '')
                
                task.status = 'rejected'
                if not task.metadata:
                    task.metadata = {}
                task.metadata['pending_approval'] = False
                task.metadata['rejected_by'] = str(user.id)
                task.metadata['rejected_at'] = timezone.now().isoformat()
                task.metadata['rejection_reason'] = reason
                task.save()
                
                # Notify assignee about rejection
                TaskService._notify_task_rejected(task, user, reason)
                
                return task
                
        except Exception as e:
            logger.exception(
                "Unexpected error in TaskService.reject_completion",
                extra={'task_id': task.id, 'user_id': user.id}
            )
            raise BusinessLogicError(f"Failed to reject task: {str(e)}")

    # Helper methods for notifications and company assignment

    @staticmethod
    def _assign_company_to_assignee(task: Task, assigner, action: str) -> None:
        """Assign company to task assignee."""
        try:
            assignee = task.assignee
            company = task.company
            
            # Update assignee's company
            assignee.company = company
            assignee.save()
            
            # Update Staff record if exists
            if hasattr(assignee, 'staff'):
                assignee.staff.company = company
                assignee.staff.save()
            
            # Store in metadata for audit trail
            if not task.metadata:
                task.metadata = {}
            
            if action == 'assigned':
                task.metadata['company_assigned_by'] = assigner.full_name
                task.metadata['company_assigned_at'] = timezone.now().isoformat()
                task.metadata['company_assigned_to'] = assignee.full_name
            else:  # reassigned
                task.metadata['company_reassigned_by'] = assigner.full_name
                task.metadata['company_reassigned_at'] = timezone.now().isoformat()
                task.metadata['company_reassigned_to'] = assignee.full_name
            
            task.save()
        except Exception as e:
            logger.error(f"Error assigning company to staff: {e}")
            # Don't fail the parent operation

    @staticmethod
    def _notify_task_assigned(task: Task, assigner) -> None:
        """Create notification for task assignment."""
        try:
            from communications.models import Notification
            
            Notification.objects.create(
                user=task.assignee,
                notification_type='task_assigned',
                title='New Task Assigned',
                message=f'You have been assigned a new task: "{task.title}"',
                related_entity_type='task',
                related_entity_id=str(task.id),
                metadata={
                    'task_id': str(task.id),
                    'task_title': task.title,
                    'assigned_by': assigner.full_name,
                    'company': task.company.name if task.company else 'N/A',
                    'link': '/tasks'
                }
            )
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to create task assignment notification: {e}")

    @staticmethod
    def _notify_task_status_changed(task: Task, old_status: str) -> None:
        """Create notification when task status changes."""
        try:
            from communications.models import Notification
            
            if task.status == 'completed':
                Notification.objects.create(
                    user=task.creator,
                    notification_type='task_completed',
                    title='Task Completed',
                    message=f'Task "{task.title}" has been completed by {task.assignee.full_name}',
                    related_entity_type='task',
                    related_entity_id=str(task.id),
                    metadata={
                        'task_id': str(task.id),
                        'task_title': task.title,
                        'completed_by': task.assignee.full_name,
                        'link': '/tasks'
                    }
                )
            elif task.status == 'in_progress':
                Notification.objects.create(
                    user=task.creator,
                    notification_type='task_started',
                    title='Task Started',
                    message=f'Task "{task.title}" has been started by {task.assignee.full_name}',
                    related_entity_type='task',
                    related_entity_id=str(task.id),
                    metadata={
                        'task_id': str(task.id),
                        'task_title': task.title,
                        'started_by': task.assignee.full_name,
                        'link': '/tasks'
                    }
                )
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to create task status notification: {e}")

    @staticmethod
    def _notify_admin_completion(task: Task, admin) -> None:
        """Create notification when admin completes a task."""
        try:
            from communications.models import Notification
            
            Notification.objects.create(
                user=task.assignee,
                notification_type='task_completed',
                title='Task Marked Complete',
                message=f'Your task "{task.title}" has been marked as complete by an admin',
                related_entity_type='task',
                related_entity_id=str(task.id),
                metadata={
                    'task_id': str(task.id),
                    'task_title': task.title,
                    'completed_by_admin': admin.full_name,
                    'link': '/tasks'
                }
            )
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to create admin completion notification: {e}")

    @staticmethod
    def _notify_approval_required(task: Task, notes: str) -> None:
        """Create notification when task completion requires approval."""
        try:
            from communications.models import Notification
            
            Notification.objects.create(
                user=task.creator,
                notification_type='approval_required',
                title='Task Completion Pending Approval',
                message=f'Task "{task.title}" has been completed by {task.assignee.full_name} and requires your approval',
                related_entity_type='task',
                related_entity_id=str(task.id),
                metadata={
                    'task_id': str(task.id),
                    'task_title': task.title,
                    'completed_by': task.assignee.full_name,
                    'completion_notes': notes,
                    'link': '/tasks'
                }
            )
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to create approval required notification: {e}")

    @staticmethod
    def _notify_task_approved(task: Task, approver) -> None:
        """Create notification when task is approved."""
        try:
            from communications.models import Notification
            
            Notification.objects.create(
                user=task.assignee,
                notification_type='task_approved',
                title='Task Completion Approved',
                message=f'Your task "{task.title}" completion has been approved by {approver.full_name}',
                related_entity_type='task',
                related_entity_id=str(task.id),
                metadata={
                    'task_id': str(task.id),
                    'task_title': task.title,
                    'approved_by': approver.full_name,
                    'link': '/tasks'
                }
            )
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to create approval notification: {e}")

    @staticmethod
    def _notify_task_rejected(task: Task, rejector, reason: str) -> None:
        """Create notification when task is rejected."""
        try:
            from communications.models import Notification
            
            Notification.objects.create(
                user=task.assignee,
                notification_type='task_rejected',
                title='Task Completion Rejected',
                message=f'Your task "{task.title}" completion has been rejected by {rejector.full_name}. Reason: {reason}',
                related_entity_type='task',
                related_entity_id=str(task.id),
                metadata={
                    'task_id': str(task.id),
                    'task_title': task.title,
                    'rejected_by': rejector.full_name,
                    'rejection_reason': reason,
                    'link': '/tasks'
                }
            )
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Failed to create rejection notification: {e}")
