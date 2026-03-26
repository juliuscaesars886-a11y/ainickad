"""
Views for workflows app
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db import models
from django.http import HttpResponse
import csv
from io import StringIO
import logging

from .models import Task, Request, Approval, LeaveBalance
from .serializers import (
    TaskListSerializer,
    TaskDetailSerializer,
    TaskCreateSerializer,
    TaskUpdateSerializer,
    RequestListSerializer,
    RequestDetailSerializer,
    RequestCreateSerializer,
    RequestUpdateSerializer,
    ApprovalSerializer,
    LeaveBalanceSerializer
)
from .services import TaskService, RequestService, ApprovalService
from core.exceptions import (
    ValidationError as DomainValidationError,
    PermissionError as DomainPermissionError,
    BusinessLogicError,
    ResourceNotFoundError,
)

logger = logging.getLogger(__name__)


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Task CRUD operations.
    
    Endpoints:
    - GET /api/tasks/ - List tasks (filtered by company)
    - POST /api/tasks/ - Create task
    - GET /api/tasks/{id}/ - Get task details
    - PATCH /api/tasks/{id}/ - Update task
    - DELETE /api/tasks/{id}/ - Delete task
    - POST /api/tasks/{id}/complete/ - Mark task as complete
    """
    queryset = Task.objects.all()
    permission_classes = [IsAuthenticated]  # Require authentication for all endpoints
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'priority', 'company', 'assignee', 'creator']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'created_at', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'create':
            return TaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskUpdateSerializer
        return TaskDetailSerializer
    
    def get_queryset(self):
        """
        Return all tasks - no company-based filtering.
        All authenticated users can view all tasks.
        """
        user = self.request.user
        
        # Check if user is authenticated
        if not user or not user.is_authenticated:
            return Task.objects.none()
        
        # All authenticated users can see all tasks
        # Optimized with select_related to prevent N+1 queries
        return Task.objects.select_related(
            'assignee',
            'creator',
            'company',
        ).all()
    
    def create(self, request, *args, **kwargs):
        """
        Create a new task and optionally assign company to staff member
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Delegate to service layer
            task = TaskService.create_task(request.user, serializer.validated_data)
            
            # Return detailed serializer
            detail_serializer = TaskDetailSerializer(task)
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
            
        except DomainValidationError as e:
            return Response(
                {'errors': e.field_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DomainPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except BusinessLogicError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.exception("Unexpected error in TaskViewSet.create")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """
        Update a task and optionally assign company to staff member
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            
            # Delegate to service layer
            task = TaskService.update_task(instance, request.user, serializer.validated_data)
            
            # Return detailed serializer
            detail_serializer = TaskDetailSerializer(task)
            return Response(detail_serializer.data)
            
        except DomainValidationError as e:
            return Response(
                {'errors': e.field_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DomainPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except BusinessLogicError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.exception("Unexpected error in TaskViewSet.update")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a task (creator or admin only)
        """
        instance = self.get_object()
        
        # Only creator or admin can delete
        if not request.user.is_admin and instance.creator != request.user:
            return Response(
                {'error': 'You can only delete tasks you created'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Mark a task as complete (staff) or request completion approval
        """
        try:
            task = self.get_object()
            
            # Delegate to service layer
            task = TaskService.complete_task(task, request.user, request.data)
            
            serializer = TaskDetailSerializer(task)
            return Response(serializer.data)
            
        except DomainPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except DomainValidationError as e:
            return Response(
                {'errors': e.field_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except BusinessLogicError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.exception("Unexpected error in TaskViewSet.complete")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def approve_completion(self, request, pk=None):
        """
        Approve a completed task (admin only)
        """
        try:
            task = self.get_object()
            
            # Delegate to service layer
            task = TaskService.approve_completion(task, request.user)
            
            serializer = TaskDetailSerializer(task)
            return Response(serializer.data)
            
        except DomainPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except DomainValidationError as e:
            return Response(
                {'errors': e.field_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except BusinessLogicError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.exception("Unexpected error in TaskViewSet.approve_completion")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def reject_completion(self, request, pk=None):
        """
        Reject a completed task (admin only)
        """
        try:
            task = self.get_object()
            
            # Delegate to service layer
            task = TaskService.reject_completion(task, request.user, request.data)
            
            serializer = TaskDetailSerializer(task)
            return Response(serializer.data)
            
        except DomainPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except DomainValidationError as e:
            return Response(
                {'errors': e.field_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except BusinessLogicError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.exception("Unexpected error in TaskViewSet.reject_completion")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def pending_completions(self, request):
        """
        Get tasks pending completion approval (admin only)
        """
        # Only admin can view pending completions
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can view pending completions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get completed tasks that are pending approval
        tasks = self.get_queryset().filter(
            status='completed',
            metadata__pending_approval=True
        )
        
        serializer = TaskListSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Start a task (assignee only)
        """
        task = self.get_object()
        
        # Only assignee can start the task
        if task.assignee != request.user:
            return Response(
                {'error': 'Only the assignee can start this task'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if task.status != 'pending':
            return Response(
                {'error': 'Task must be pending to start'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start the task
        task.status = 'in_progress'
        task.started_at = timezone.now()
        task.save()
        
        # Create notification for creator about task start
        try:
            from communications.models import Notification
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
            print(f"Failed to create task start notification: {e}")
        
        serializer = TaskDetailSerializer(task)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_time(self, request, pk=None):
        """
        Add time spent on a task (assignee only)
        """
        task = self.get_object()
        
        # Only assignee can add time
        if task.assignee != request.user:
            return Response(
                {'error': 'Only the assignee can add time to this task'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        seconds = request.data.get('seconds', 0)
        if not isinstance(seconds, int) or seconds <= 0:
            return Response(
                {'error': 'Invalid seconds value'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.add_time_spent(seconds)
        
        serializer = TaskDetailSerializer(task)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def generate_report(self, request, pk=None):
        """
        Generate and download timestamp report for approved task
        """
        task = self.get_object()
        
        # Only allow report generation for approved tasks
        if task.status != 'approved':
            return Response(
                {'error': 'Reports can only be generated for approved tasks'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Only assignee, creator, or admin can download report
        if not request.user.is_admin and task.assignee != request.user and task.creator != request.user:
            return Response(
                {'error': 'You do not have permission to download this report'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate report content
        from django.http import HttpResponse
        import csv
        from io import StringIO
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Task ID',
            'Task Title',
            'Assignee',
            'Creator',
            'Priority',
            'Due Date',
            'Started At',
            'Completed At',
            'Approved At',
            'Total Time Spent',
            'Status',
            'Completion Notes'
        ])
        
        # Write task data
        writer.writerow([
            str(task.id),
            task.title,
            task.assignee.full_name,
            task.creator.full_name,
            task.get_priority_display(),
            task.due_date.strftime('%Y-%m-%d %H:%M:%S') if task.due_date else '',
            task.started_at.strftime('%Y-%m-%d %H:%M:%S') if task.started_at else '',
            task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else '',
            task.metadata.get('approved_at', '') if task.metadata else '',
            task.time_spent_formatted,
            task.get_status_display(),
            task.metadata.get('completion_notes', '') if task.metadata else ''
        ])
        
        # Create HTTP response
        response = HttpResponse(
            output.getvalue(),
            content_type='text/csv'
        )
        response['Content-Disposition'] = f'attachment; filename="task_report_{task.id}.csv"'
        
        return response



class RequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Request CRUD operations.
    
    Endpoints:
    - GET /api/requests/ - List requests (filtered by company)
    - POST /api/requests/ - Create request
    - GET /api/requests/{id}/ - Get request details
    - PATCH /api/requests/{id}/ - Update request
    - DELETE /api/requests/{id}/ - Delete request
    - POST /api/requests/{id}/submit/ - Submit request for approval
    """
    queryset = Request.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['request_type', 'status', 'company', 'requester']
    search_fields = ['data']
    ordering_fields = ['submission_date', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return RequestListSerializer
        elif self.action == 'create':
            return RequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return RequestUpdateSerializer
        return RequestDetailSerializer
    
    def get_queryset(self):
        """
        Return all requests with optimized queries.
        Uses select_related to prevent N+1 queries.
        """
        user = self.request.user
        
        # Allow unauthenticated access for development
        if not user or not user.is_authenticated:
            return Request.objects.select_related(
                'requester',
                'company',
            ).all()
        
        # All authenticated users can see all requests
        return Request.objects.select_related(
            'requester',
            'company',
        ).all()
    
    def create(self, request, *args, **kwargs):
        """
        Create a new request
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Delegate to service layer
            req = RequestService.create_request(request.user, serializer.validated_data)
            
            # Return detailed serializer
            detail_serializer = RequestDetailSerializer(req)
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
            
        except DomainValidationError as e:
            return Response(
                {'errors': e.field_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DomainPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except BusinessLogicError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.exception("Unexpected error in RequestViewSet.create")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """
        Update a request (only if draft)
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            
            # Delegate to service layer
            req = RequestService.update_request(instance, request.user, serializer.validated_data)
            
            # Return detailed serializer
            detail_serializer = RequestDetailSerializer(req)
            return Response(detail_serializer.data)
            
        except DomainValidationError as e:
            return Response(
                {'errors': e.field_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DomainPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except BusinessLogicError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.exception("Unexpected error in RequestViewSet.update")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a request (only if draft)
        """
        try:
            instance = self.get_object()
            
            # Delegate to service layer
            RequestService.delete_request(instance, request.user)
            
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except DomainValidationError as e:
            return Response(
                {'errors': e.field_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DomainPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except BusinessLogicError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.exception("Unexpected error in RequestViewSet.destroy")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Submit a request for approval (changes status from draft to pending)
        """
        try:
            req = self.get_object()
            
            # Delegate to service layer
            req = RequestService.submit_request(req, request.user)
            
            serializer = RequestDetailSerializer(req)
            return Response(serializer.data)
            
        except DomainValidationError as e:
            return Response(
                {'errors': e.field_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except DomainPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except BusinessLogicError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.exception("Unexpected error in RequestViewSet.submit")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ApprovalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Approval operations (read-only with approve/reject actions).
    
    Endpoints:
    - GET /api/approvals/ - List approvals
    - GET /api/approvals/pending/ - Get pending approvals for current user
    - GET /api/approvals/{id}/ - Get approval details
    - POST /api/approvals/{id}/approve/ - Approve a request
    - POST /api/approvals/{id}/reject/ - Reject a request
    """
    queryset = Approval.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ApprovalSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'approver', 'request']
    ordering_fields = ['step_number', 'created_at']
    ordering = ['step_number', 'created_at']
    
    def get_queryset(self):
        """
        Return all approvals with optimized queries.
        Uses select_related to prevent N+1 queries.
        """
        user = self.request.user
        
        # Allow unauthenticated access for development
        if not user or not user.is_authenticated:
            return Approval.objects.select_related(
                'approver',
                'request',
                'request__requester',
                'request__company',
            ).all()
        
        # All authenticated users can see all approvals
        return Approval.objects.select_related(
            'approver',
            'request',
            'request__requester',
            'request__company',
        ).all()
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Get pending approvals for current user or all pending approvals if admin
        """
        print(f"[APPROVALS PENDING] User: {request.user}")
        print(f"[APPROVALS PENDING] User ID: {request.user.id if request.user else 'None'}")
        print(f"[APPROVALS PENDING] User authenticated: {request.user.is_authenticated if request.user else False}")
        print(f"[APPROVALS PENDING] User role: {getattr(request.user, 'role', 'N/A')}")
        print(f"[APPROVALS PENDING] User is_admin: {getattr(request.user, 'is_admin', False)}")
        print(f"[APPROVALS PENDING] User is_super_admin: {getattr(request.user, 'is_super_admin', False)}")
        
        # If user is admin/super_admin, return all pending approvals
        if request.user and (getattr(request.user, 'is_admin', False) or getattr(request.user, 'is_super_admin', False)):
            approvals = self.get_queryset().filter(status='pending')
            print(f"[APPROVALS PENDING] Admin user - returning {approvals.count()} pending approvals")
            print(f"[APPROVALS PENDING] All pending approvals in DB: {Approval.objects.filter(status='pending').count()}")
        else:
            # Regular users only see their own pending approvals
            approvals = self.get_queryset().filter(
                approver=request.user,
                status='pending'
            )
            print(f"[APPROVALS PENDING] Regular user - returning {approvals.count()} pending approvals for user {request.user}")
        
        serializer = ApprovalSerializer(approvals, many=True)
        print(f"[APPROVALS PENDING] Serialized data count: {len(serializer.data)}")
        if serializer.data:
            print(f"[APPROVALS PENDING] Sample approval: {serializer.data[0]}")
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a request
        """
        try:
            approval = self.get_object()
            
            # Delegate to service layer
            approval = ApprovalService.approve_request(approval, request.user, request.data)
            
            serializer = ApprovalSerializer(approval)
            return Response(serializer.data)
            
        except DomainPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except DomainValidationError as e:
            return Response(
                {'errors': e.field_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except BusinessLogicError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.exception("Unexpected error in ApprovalViewSet.approve")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a request
        """
        try:
            approval = self.get_object()
            
            # Delegate to service layer
            approval = ApprovalService.reject_request(approval, request.user, request.data)
            
            serializer = ApprovalSerializer(approval)
            return Response(serializer.data)
            
        except DomainPermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except DomainValidationError as e:
            return Response(
                {'errors': e.field_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except BusinessLogicError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.exception("Unexpected error in ApprovalViewSet.reject")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for LeaveBalance operations (read-only).
    
    Endpoints:
    - GET /api/leave-balance/ - List leave balances
    - GET /api/leave-balance/{id}/ - Get leave balance details
    - GET /api/leave-balance/by-email/?email=user@example.com - Get leave balance by email
    """
    queryset = LeaveBalance.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveBalanceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['staff', 'company']
    search_fields = ['staff__user__email', 'staff__user__first_name', 'staff__user__last_name']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Return all leave balances - no company-based filtering.
        All authenticated users can view all leave balances.
        """
        user = self.request.user
        
        # Allow unauthenticated access for development
        if not user or not user.is_authenticated:
            return LeaveBalance.objects.all()
        
        # All authenticated users can see all leave balances
        return LeaveBalance.objects.all()
    
    @action(detail=False, methods=['get'])
    def by_email(self, request):
        """
        Get leave balance by staff email
        """
        email = request.query_params.get('email')
        if not email:
            return Response(
                {'error': 'Email parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find staff by email
            from staff.models import Staff
            staff = Staff.objects.get(user__email=email)
            
            # Get or create leave balance for this staff
            leave_balance, created = LeaveBalance.objects.get_or_create(
                staff=staff,
                company=staff.company,
                defaults={
                    'annual_entitlement': 21,
                    'sick_entitlement': 10,
                    'maternity_entitlement': 90,
                    'paternity_entitlement': 14,
                    'emergency_entitlement': 5,
                }
            )
            
            serializer = LeaveBalanceSerializer(leave_balance)
            return Response(serializer.data)
            
        except Staff.DoesNotExist:
            return Response(
                {'error': f'Staff member with email {email} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve leave balance: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )