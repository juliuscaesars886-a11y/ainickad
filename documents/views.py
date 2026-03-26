"""
Views for documents app
"""
import os
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from .models import Document, Template
from .serializers import (
    DocumentListSerializer,
    DocumentDetailSerializer,
    DocumentCreateSerializer,
    DocumentUpdateSerializer,
    TemplateListSerializer,
    TemplateDetailSerializer,
    TemplateCreateSerializer,
    TemplateUpdateSerializer
)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Document CRUD operations and file management.
    
    Endpoints:
    - GET /api/documents/ - List documents (filtered by company)
    - POST /api/documents/ - Upload document
    - GET /api/documents/{id}/ - Get document details
    - PATCH /api/documents/{id}/ - Update document metadata
    - DELETE /api/documents/{id}/ - Delete document
    - GET /api/documents/{id}/download/ - Download document file
    """
    queryset = Document.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'subfolder', 'company', 'is_archived']
    search_fields = ['title', 'description', 'file_name']
    ordering_fields = ['created_at', 'title', 'file_size']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return DocumentListSerializer
        elif self.action == 'create':
            return DocumentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DocumentUpdateSerializer
        return DocumentDetailSerializer
    
    def get_queryset(self):
        """
        Return all documents - no company-based filtering.
        All authenticated users can view all documents.
        """
        return Document.objects.all()
    
    def create(self, request, *args, **kwargs):
        """
        Upload a new document with subfolder organization
        """
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            print(f"Serializer errors: {serializer.errors}")
            print(f"Request data keys: {request.data.keys()}")
            print(f"File in request: {'file' in request.FILES}")
            return Response(
                {'errors': serializer.errors, 'detail': 'Validation failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # All authenticated users can upload documents for any company
        # No company-based restrictions
        
        # Get the uploaded file
        uploaded_file = serializer.validated_data.pop('file')
        
        # Get company - use first company if not specified
        company = serializer.validated_data.get('company')
        if not company:
            # Try to get user's company or first available company
            from companies.models import Company
            if hasattr(request, 'user') and hasattr(request.user, 'profile') and hasattr(request.user.profile, 'company'):
                company = request.user.profile.company
            else:
                company = Company.objects.first()
            
            if not company:
                return Response(
                    {'error': 'No company available. Please ensure at least one company exists.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer.validated_data['company'] = company
        
        company_id = company.id if company else 'shared'
        subfolder = serializer.validated_data.get('subfolder', 'other')
        file_extension = os.path.splitext(uploaded_file.name)[1]
        file_path = f"documents/{company_id}/{subfolder}/{uploaded_file.name}"
        
        print(f"Uploading file: {file_path}")
        
        # Save file to storage
        saved_path = default_storage.save(file_path, uploaded_file)
        
        print(f"File saved to: {saved_path}")
        
        # Create document record
        document = Document.objects.create(
            **serializer.validated_data,
            file_path=saved_path,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            mime_type=uploaded_file.content_type,
            uploaded_by=request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        )
        
        # Return detailed serializer
        detail_serializer = DocumentDetailSerializer(document)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        Update document metadata (not the file itself)
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # All authenticated users can update documents
        # No company-based restrictions
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        
        # Return detailed serializer
        detail_serializer = DocumentDetailSerializer(document)
        return Response(detail_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a document and its file - All authenticated users can delete
        """
        instance = self.get_object()
        
        # Allow all authenticated users to delete documents
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required to delete documents'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # All authenticated users can delete documents
        # No role-based restrictions
        
        # Delete file from storage
        if default_storage.exists(instance.file_path):
            default_storage.delete(instance.file_path)
        
        # Delete document record
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download or preview document file
        
        Parameters:
        - preview=true: Returns file with Content-Disposition: inline (for browser preview)
        - Otherwise: Returns file with Content-Disposition: attachment (for download)
        """
        document = self.get_object()
        
        # Check if file exists
        if not default_storage.exists(document.file_path):
            raise Http404("File not found")
        
        # Determine if this is a preview or download request
        is_preview = request.query_params.get('preview', 'false').lower() == 'true'
        
        # Open and return file
        file_handle = default_storage.open(document.file_path, 'rb')
        response = FileResponse(file_handle, content_type=document.mime_type)
        
        # Set appropriate Content-Disposition based on request type
        if is_preview:
            # Inline for browser preview/display
            response['Content-Disposition'] = f'inline; filename="{document.file_name}"'
        else:
            # Attachment for download
            response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
        
        response['Content-Length'] = document.file_size
        # Add headers to prevent caching issues with iframes
        response['Cache-Control'] = 'public, max-age=3600'
        
        return response



class TemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Template CRUD operations and usage tracking.
    
    Endpoints:
    - GET /api/templates/ - List active templates (filterable by category)
    - POST /api/templates/ - Create template
    - GET /api/templates/{id}/ - Get template details
    - PATCH /api/templates/{id}/ - Update template metadata
    - DELETE /api/templates/{id}/ - Delete template
    - POST /api/templates/{id}/record-usage/ - Record template usage
    - GET /api/templates/recent/ - Get recently used templates
    """
    queryset = Template.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'usage_count', 'last_used', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return TemplateListSerializer
        elif self.action == 'create':
            return TemplateCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TemplateUpdateSerializer
        return TemplateDetailSerializer
    
    def get_queryset(self):
        """
        Return active templates by default.
        Super admins can see all templates including inactive ones.
        """
        user = self.request.user
        
        # Allow unauthenticated access for development
        if not user or not user.is_authenticated:
            return Template.objects.filter(is_active=True)
        
        if user.is_super_admin:
            return Template.objects.all()
        
        return Template.objects.filter(is_active=True)
    
    def create(self, request, *args, **kwargs):
        """
        Create a new template
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Handle file upload if provided
        uploaded_file = serializer.validated_data.pop('file', None)
        
        if uploaded_file:
            # Generate unique file path
            file_extension = os.path.splitext(uploaded_file.name)[1]
            file_path = f"templates/{uploaded_file.name}"
            
            # Save file to storage
            saved_path = default_storage.save(file_path, uploaded_file)
            
            # Create template record with file info
            template = Template.objects.create(
                **serializer.validated_data,
                file_path=saved_path,
                file_name=uploaded_file.name,
                file_size=uploaded_file.size
            )
        else:
            # Create template without file (file_path and file_name should be in validated_data)
            template = Template.objects.create(**serializer.validated_data)
        
        # Return detailed serializer
        detail_serializer = TemplateDetailSerializer(template)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        Update template metadata
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        
        # Return detailed serializer
        detail_serializer = TemplateDetailSerializer(template)
        return Response(detail_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a template and its file
        """
        instance = self.get_object()
        
        # Delete file from storage if it exists
        if instance.file_path and default_storage.exists(instance.file_path):
            default_storage.delete(instance.file_path)
        
        # Delete template record
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def record_usage(self, request, pk=None):
        """
        Record template usage - increments usage_count and updates last_used
        """
        template = self.get_object()
        template.record_usage()
        
        return Response({
            'status': 'usage recorded',
            'usage_count': template.usage_count,
            'last_used': template.last_used
        })
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recently used templates (ordered by last_used, most recent first)
        """
        templates = Template.objects.filter(
            is_active=True,
            last_used__isnull=False
        ).order_by('-last_used')[:10]
        
        serializer = TemplateListSerializer(templates, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download template file
        """
        template = self.get_object()
        
        # Check if file exists
        if not template.file_path or not default_storage.exists(template.file_path):
            raise Http404("File not found")
        
        # Open and return file
        file_handle = default_storage.open(template.file_path, 'rb')
        response = FileResponse(file_handle)
        response['Content-Disposition'] = f'attachment; filename="{template.file_name}"'
        if template.file_size:
            response['Content-Length'] = template.file_size
        
        return response
