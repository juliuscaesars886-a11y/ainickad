"""
Views for staff app
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Staff
from .serializers import (
    StaffListSerializer,
    StaffDetailSerializer,
    StaffCreateSerializer,
    StaffUpdateSerializer
)


class StaffViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Staff CRUD operations.
    
    Endpoints:
    - GET /api/staff/ - List staff members (filtered by company)
    - POST /api/staff/ - Create staff member
    - GET /api/staff/{id}/ - Get staff member details
    - PATCH /api/staff/{id}/ - Update staff member
    - DELETE /api/staff/{id}/ - Delete staff member
    """
    queryset = Staff.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employment_status', 'department', 'company']
    search_fields = ['first_name', 'last_name', 'email', 'staff_number', 'job_title']
    ordering_fields = ['last_name', 'first_name', 'hire_date', 'created_at']
    ordering = ['last_name', 'first_name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return StaffListSerializer
        elif self.action == 'create':
            return StaffCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return StaffUpdateSerializer
        return StaffDetailSerializer
    
    def get_queryset(self):
        """
        Return all staff members - no company-based filtering.
        All authenticated users can view all staff members.
        """
        return Staff.objects.all()
    
    def create(self, request, *args, **kwargs):
        """
        Create a new staff member (admin or super_admin only, or unauthenticated for development)
        """
        user = request.user
        
        # Allow unauthenticated access for development
        if user and user.is_authenticated and not user.is_admin:
            return Response(
                {'error': 'Only admins can create staff members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Non-super admins can only create staff members in their own company
        if user and user.is_authenticated and not user.is_super_admin:
            company_id = serializer.validated_data.get('company').id
            user_company_id = user.company.id if user.company else None
            
            if user_company_id is None:
                return Response(
                    {'error': 'Your profile does not have a company assigned. Please contact an administrator to assign you to a company.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if company_id != user_company_id:
                return Response(
                    {'error': 'You can only create staff members in your own company'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        staff = serializer.save()
        
        # Return detailed serializer
        detail_serializer = StaffDetailSerializer(staff)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        Update a staff member (admin or super_admin only)
        """
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can update staff members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Non-super admins can only update staff members in their own company
        if not request.user.is_super_admin:
            user_company_id = request.user.company.id if request.user.company else None
            
            if user_company_id is None:
                return Response(
                    {'error': 'Your profile does not have a company assigned. Please contact an administrator to assign you to a company.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if instance.company.id != user_company_id:
                return Response(
                    {'error': 'You can only update staff members in your own company'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        staff = serializer.save()
        
        # Return detailed serializer
        detail_serializer = StaffDetailSerializer(staff)
        return Response(detail_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a staff member (admin or super_admin only)
        """
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can delete staff members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        instance = self.get_object()
        
        # Non-super admins can only delete staff members in their own company
        if not request.user.is_super_admin:
            user_company_id = request.user.company.id if request.user.company else None
            
            if user_company_id is None:
                return Response(
                    {'error': 'Your profile does not have a company assigned. Please contact an administrator to assign you to a company.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if instance.company.id != user_company_id:
                return Response(
                    {'error': 'You can only delete staff members in your own company'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get all active staff members
        """
        queryset = self.get_queryset().filter(employment_status='active')
        serializer = StaffListSerializer(queryset, many=True)
        return Response(serializer.data)
