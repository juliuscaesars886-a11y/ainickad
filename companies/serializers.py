"""
Serializers for companies app
"""
from rest_framework import serializers
from .models import Company, Director


class CompanyListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing companies (minimal fields)
    """
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'registration_number', 'tax_id',
            'contact_email', 'contact_phone', 'logo_url',
            'risk_level', 'risk_category',
            'is_active', 'user_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_user_count(self, obj):
        """Get count of users in this company"""
        try:
            return obj.users.filter(is_active=True).count()
        except AttributeError:
            return 0


class CompanyDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for company details (all fields)
    """
    user_count = serializers.SerializerMethodField()
    active_employee_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'registration_number', 'tax_id',
            'address', 'contact_email', 'contact_phone',
            'logo_url', 'risk_level', 'risk_category', 'settings', 'is_active',
            'user_count', 'active_employee_count', 'document_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_user_count(self, obj):
        """Get count of users in this company"""
        try:
            return obj.users.filter(is_active=True).count()
        except AttributeError:
            return 0
    
    def get_active_employee_count(self, obj):
        """Get count of active employees"""
        return obj.has_active_employees()
    
    def get_document_count(self, obj):
        """Get count of documents"""
        try:
            return obj.documents.count()
        except AttributeError:
            return 0


class CompanyCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating companies
    """
    
    class Meta:
        model = Company
        fields = [
            'name', 'registration_number', 'tax_id',
            'address', 'contact_email', 'contact_phone',
            'logo_url', 'risk_level', 'risk_category', 'settings'
        ]
    
    def validate_registration_number(self, value):
        """Validate registration number is unique"""
        if Company.objects.filter(registration_number=value).exists():
            raise serializers.ValidationError(
                "A company with this registration number already exists."
            )
        return value
    
    def validate_tax_id(self, value):
        """Validate tax ID is unique"""
        if Company.objects.filter(tax_id=value).exists():
            raise serializers.ValidationError(
                "A company with this tax ID already exists."
            )
        return value


class CompanyUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating companies
    Supports both 'is_active' (backend) and 'status' (frontend) fields
    """
    status = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Company
        fields = [
            'name', 'address', 'contact_email', 'contact_phone',
            'logo_url', 'settings', 'is_active', 'status'
        ]
    
    def validate(self, data):
        """Map 'status' field to 'is_active' for frontend compatibility"""
        if 'status' in data:
            status_value = data.pop('status')
            data['is_active'] = status_value == 'active'
        return data
    
    # registration_number and tax_id are not updatable



class DirectorListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing directors (minimal fields)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    is_current = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Director
        fields = [
            'id', 'company', 'company_name', 'name',
            'appointment_date', 'resignation_date', 'position',
            'is_active', 'is_current', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DirectorDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for director details (all fields)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    is_current = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Director
        fields = [
            'id', 'company', 'company_name', 'name',
            'appointment_date', 'resignation_date', 'position',
            'metadata', 'is_active', 'is_current',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DirectorCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating directors
    """
    class Meta:
        model = Director
        fields = [
            'company', 'name', 'appointment_date',
            'resignation_date', 'position', 'metadata'
        ]
    
    def validate(self, data):
        """Validate resignation date is after appointment date"""
        if data.get('resignation_date') and data.get('appointment_date'):
            if data['resignation_date'] < data['appointment_date']:
                raise serializers.ValidationError({
                    'resignation_date': 'Resignation date must be after appointment date.'
                })
        return data


class DirectorUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating directors
    """
    class Meta:
        model = Director
        fields = [
            'name', 'appointment_date', 'resignation_date',
            'position', 'metadata', 'is_active'
        ]
    
    def validate(self, data):
        """Validate resignation date is after appointment date"""
        instance = self.instance
        appointment_date = data.get('appointment_date', instance.appointment_date if instance else None)
        resignation_date = data.get('resignation_date')
        
        if resignation_date and appointment_date:
            if resignation_date < appointment_date:
                raise serializers.ValidationError({
                    'resignation_date': 'Resignation date must be after appointment date.'
                })
        return data
