"""
Views for companies app
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Company, Director
from .serializers import (
    CompanyListSerializer,
    CompanyDetailSerializer,
    CompanyCreateSerializer,
    CompanyUpdateSerializer,
    DirectorListSerializer,
    DirectorDetailSerializer,
    DirectorCreateSerializer,
    DirectorUpdateSerializer
)


class CompanyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Company CRUD operations.
    
    Endpoints:
    - GET /api/companies/ - List companies
    - POST /api/companies/ - Create company (super_admin only)
    - GET /api/companies/{id}/ - Get company details
    - PATCH /api/companies/{id}/ - Update company
    - DELETE /api/companies/{id}/ - Delete company (super_admin only)
    """
    queryset = Company.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'registration_number', 'tax_id', 'contact_email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return CompanyListSerializer
        elif self.action == 'create':
            return CompanyCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CompanyUpdateSerializer
        return CompanyDetailSerializer
    
    def get_queryset(self):
        """
        Return all companies - no company-based filtering.
        All authenticated users can view all companies.
        """
        return Company.objects.all()
    
    def create(self, request, *args, **kwargs):
        """
        Create a new company (all authenticated users can create)
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = serializer.save()
        
        # Return detailed serializer
        detail_serializer = CompanyDetailSerializer(company)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        Update a company (all authenticated users can update)
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # All authenticated users can update companies
        # No role-based restrictions
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        company = serializer.save()
        
        # Return detailed serializer
        detail_serializer = CompanyDetailSerializer(company)
        return Response(detail_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a company (all authenticated users can delete)
        """
        instance = self.get_object()
        
        # Check if company has users
        if instance.users.exists():
            return Response(
                {'error': 'Cannot delete company with associated users'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """
        Get all users for a company
        """
        company = self.get_object()
        
        # All authenticated users can view users from any company
        # No role-based restrictions
        
        from authentication.serializers import UserProfileSerializer
        users = company.users.filter(is_active=True)
        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data)



class DirectorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Director CRUD operations.
    
    Endpoints:
    - GET /api/directors/ - List directors
    - POST /api/directors/ - Create director
    - GET /api/directors/{id}/ - Get director details
    - PATCH /api/directors/{id}/ - Update director
    - DELETE /api/directors/{id}/ - Delete director
    """
    queryset = Director.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['company', 'is_active']
    search_fields = ['name', 'position']
    ordering_fields = ['name', 'appointment_date', 'created_at']
    ordering = ['-appointment_date', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return DirectorListSerializer
        elif self.action == 'create':
            return DirectorCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DirectorUpdateSerializer
        return DirectorDetailSerializer
    
    def get_queryset(self):
        """
        Filter directors based on user role and company access.
        
        - Super admins see all directors
        - Other users see only directors from their company
        - Unauthenticated users see all (for development)
        - Supports filtering by company_id query parameter
        """
        user = self.request.user
        queryset = Director.objects.all()
        
        # Allow unauthenticated access for development
        if not user or not user.is_authenticated:
            # Still apply company_id filter if provided
            company_id = self.request.query_params.get('company_id')
            if company_id:
                queryset = queryset.filter(company_id=company_id)
            return queryset
        
        # Super admins see all directors
        if user.is_super_admin:
            company_id = self.request.query_params.get('company_id')
            if company_id:
                queryset = queryset.filter(company_id=company_id)
            return queryset
        
        # Other users see only directors from their company
        if user.company:
            return queryset.filter(company=user.company)
        
        return Director.objects.none()
    
    def create(self, request, *args, **kwargs):
        """
        Create a new director
        """
        user = request.user
        
        # Check if user has permission to create directors for the specified company
        if user and user.is_authenticated:
            company_id = request.data.get('company')
            if not user.is_super_admin and str(user.company.id) != str(company_id):
                return Response(
                    {'error': 'You can only create directors for your own company'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        director = serializer.save()
        
        # Return detailed serializer
        detail_serializer = DirectorDetailSerializer(director)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        Update a director
        """
        user = request.user
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if user has permission to update this director
        if user and user.is_authenticated:
            if not user.is_super_admin and instance.company != user.company:
                return Response(
                    {'error': 'You can only update directors from your own company'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        director = serializer.save()
        
        # Return detailed serializer
        detail_serializer = DirectorDetailSerializer(director)
        return Response(detail_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a director
        """
        user = request.user
        instance = self.get_object()
        
        # Check if user has permission to delete this director
        if user and user.is_authenticated:
            if not user.is_super_admin and instance.company != user.company:
                return Response(
                    {'error': 'You can only delete directors from your own company'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
