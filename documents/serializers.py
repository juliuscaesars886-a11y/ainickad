"""
Serializers for documents app
"""
from rest_framework import serializers
from .models import Document, Template


class DocumentListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing documents (minimal fields)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    file_extension = serializers.ReadOnlyField()
    size_mb = serializers.ReadOnlyField()
    subfolder_display = serializers.CharField(source='get_subfolder_display', read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'category', 'subfolder', 'subfolder_display', 'file_name', 'file_extension',
            'file_size', 'size_mb', 'company_name', 'uploaded_by_name', 'metadata',
            'is_archived', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DocumentDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for document details (all fields)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    file_extension = serializers.ReadOnlyField()
    size_mb = serializers.ReadOnlyField()
    subfolder_display = serializers.CharField(source='get_subfolder_display', read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'category', 'subfolder', 'subfolder_display', 'file_path',
            'file_name', 'file_extension', 'file_size', 'size_mb',
            'mime_type', 'company', 'uploaded_by', 'company_name',
            'uploaded_by_name', 'metadata', 'is_archived',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_path', 'file_name', 'file_size', 'mime_type',
            'uploaded_by', 'created_at', 'updated_at'
        ]


class DocumentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/uploading documents
    """
    file = serializers.FileField(write_only=True, required=True)
    
    class Meta:
        model = Document
        fields = ['title', 'description', 'category', 'subfolder', 'company', 'file', 'metadata']
        extra_kwargs = {
            'title': {'required': True},
            'company': {'required': False},
            'category': {'required': False},
            'subfolder': {'required': False}
        }
    
    def validate_file(self, value):
        """Validate file size, type, and filename for security"""
        import os
        from pathlib import Path
        
        if not value:
            raise serializers.ValidationError("No file was provided.")
        
        # 1. Sanitize filename - prevent path traversal
        original_name = value.name
        safe_name = Path(original_name).name  # Get only filename, no path
        
        if '..' in safe_name or '/' in safe_name or '\\' in safe_name:
            raise serializers.ValidationError("Invalid filename: path traversal detected")
        
        # 2. Validate file extension
        allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.gif', '.txt']
        file_ext = Path(safe_name).suffix.lower()
        
        if not file_ext or file_ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File extension '{file_ext}' is not allowed. "
                f"Allowed: {', '.join(allowed_extensions)}"
            )
        
        # 3. Max file size: 50MB
        max_size = 50 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size cannot exceed 50MB. Current size: {value.size / (1024 * 1024):.2f}MB"
            )
        
        # 4. Validate MIME type (client-provided, but still useful)
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/jpeg',
            'image/png',
            'image/gif',
            'text/plain',
        ]
        
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"File type '{value.content_type}' is not allowed. "
                f"Allowed types: PDF, Word, Excel, Images, Text"
            )
        
        # 5. Prevent double extensions (e.g., file.php.jpg)
        if safe_name.count('.') > 1:
            # Check if any part before the last extension is executable
            dangerous_exts = ['.php', '.exe', '.sh', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js']
            name_parts = safe_name.split('.')
            for part in name_parts[:-1]:  # Check all parts except the last extension
                if f'.{part.lower()}' in dangerous_exts:
                    raise serializers.ValidationError(
                        f"Suspicious filename detected: potential double extension attack"
                    )
        
        return value
    
    def validate_subfolder(self, value):
        """Validate subfolder"""
        if value:
            valid_subfolders = [choice[0] for choice in Document.SUBFOLDER_CHOICES]
            if value not in valid_subfolders:
                raise serializers.ValidationError(
                    f"Invalid subfolder: {value}. Must be one of: {', '.join(valid_subfolders)}"
                )
        return value or 'other'
    
    def validate_company(self, value):
        """Validate company - allow None for Documents page uploads"""
        # Company is optional for documents uploaded from Documents page
        return value


class DocumentUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating document metadata
    """
    class Meta:
        model = Document
        fields = ['title', 'description', 'category', 'subfolder', 'is_archived', 'metadata']



class TemplateListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing templates (minimal fields)
    """
    file_extension = serializers.ReadOnlyField()
    size_mb = serializers.ReadOnlyField()
    
    class Meta:
        model = Template
        fields = [
            'id', 'name', 'category', 'file_name', 'file_extension',
            'file_size', 'size_mb', 'usage_count', 'last_used',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'usage_count', 'last_used', 'created_at']


class TemplateDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for template details (all fields)
    """
    file_extension = serializers.ReadOnlyField()
    size_mb = serializers.ReadOnlyField()
    
    class Meta:
        model = Template
        fields = [
            'id', 'name', 'category', 'description', 'file_path',
            'file_name', 'file_extension', 'file_size', 'size_mb',
            'usage_count', 'last_used', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_path', 'file_name', 'file_size',
            'usage_count', 'last_used', 'created_at', 'updated_at'
        ]


class TemplateCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/uploading templates
    """
    file = serializers.FileField(write_only=True, required=False)
    
    class Meta:
        model = Template
        fields = ['name', 'category', 'description', 'file', 'file_path', 'file_name']
    
    def validate_file(self, value):
        """Validate file size and type"""
        # Max file size: 50MB
        max_size = 50 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size cannot exceed 50MB. Current size: {value.size / (1024 * 1024):.2f}MB"
            )
        
        # Allowed file types for templates
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.oasis.opendocument.text',
            'application/vnd.oasis.opendocument.spreadsheet',
        ]
        
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"File type '{value.content_type}' is not allowed for templates. "
                f"Allowed types: PDF, Word, Excel, OpenDocument"
            )
        
        return value


class TemplateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating template metadata
    """
    class Meta:
        model = Template
        fields = ['name', 'description', 'category', 'is_active']
