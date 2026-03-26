"""
Serializers for staff app
"""
from rest_framework import serializers
from .models import Staff
from authentication.serializers import UserProfileSerializer


class StaffListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing staff members (minimal fields)
    """
    full_name = serializers.ReadOnlyField()
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = Staff
        fields = [
            'id', 'staff_number', 'full_name', 'first_name', 'last_name',
            'email', 'job_title', 'department', 'employment_status',
            'company_name', 'hire_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class StaffDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for staff member details (all fields)
    """
    full_name = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    company_name = serializers.CharField(source='company.name', read_only=True)
    user_profile = UserProfileSerializer(source='user', read_only=True)
    
    class Meta:
        model = Staff
        fields = [
            'id', 'staff_number', 'user', 'company', 'first_name', 'last_name',
            'full_name', 'email', 'phone', 'job_title', 'department',
            'employment_status', 'is_active', 'hire_date', 'termination_date',
            'salary', 'emergency_contact_name', 'emergency_contact_phone',
            'address', 'metadata', 'company_name', 'user_profile',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate user-company association"""
        user = data.get('user')
        company = data.get('company')
        
        if user and user.company and company and user.company != company:
            raise serializers.ValidationError({
                'user': f"User's company must match staff member's company"
            })
        
        return data


class StaffCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating staff members
    """
    class Meta:
        model = Staff
        fields = [
            'staff_number', 'user', 'company', 'first_name', 'last_name',
            'email', 'phone', 'job_title', 'department', 'employment_status',
            'hire_date', 'salary', 'emergency_contact_name',
            'emergency_contact_phone', 'address', 'metadata'
        ]
        extra_kwargs = {
            'user': {'required': False, 'allow_null': True}
        }
    
    def validate_staff_number(self, value):
        """Validate staff number is unique"""
        if Staff.objects.filter(staff_number=value).exists():
            raise serializers.ValidationError(
                "A staff member with this staff number already exists."
            )
        return value
    
    def validate(self, data):
        """Validate user-company association"""
        user = data.get('user')
        company = data.get('company')
        
        if user and user.company and company and user.company != company:
            raise serializers.ValidationError({
                'user': f"User's company must match staff member's company"
            })
        
        return data


class StaffUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating staff members
    """
    class Meta:
        model = Staff
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'job_title',
            'department', 'employment_status', 'termination_date', 'salary',
            'emergency_contact_name', 'emergency_contact_phone', 'address', 'metadata'
        ]
    
    # staff_number and company are not updatable
