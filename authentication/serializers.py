"""
Serializers for authentication app
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for UserProfile model - used for API responses.
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    is_super_admin = serializers.BooleanField(read_only=True)
    is_admin = serializers.BooleanField(read_only=True)
    is_accountant = serializers.BooleanField(read_only=True)
    can_approve = serializers.BooleanField(read_only=True)
    company_name = serializers.SerializerMethodField(read_only=True)
    
    def get_company_name(self, obj):
        """Get the company name from the related company object"""
        if obj.company:
            return obj.company.name
        return 'Unassigned'
    
    class Meta:
        model = UserProfile
        fields = [
            'id',
            'email',
            'full_name',
            'role',
            'role_display',
            'company',
            'company_name',
            'avatar_url',
            'metadata',
            'is_active',
            'is_super_admin',
            'is_admin',
            'is_accountant',
            'can_approve',
            'temp_password',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating UserProfile - allows limited field updates.
    """
    
    class Meta:
        model = UserProfile
        fields = [
            'full_name',
            'avatar_url',
            'metadata',
        ]
    
    def validate_metadata(self, value):
        """Ensure metadata is a valid dictionary"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a dictionary")
        return value


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class RegisterSerializer(serializers.Serializer):
    """
    Serializer for user registration.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    full_name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        default='staff'
    )
    temp_password = serializers.CharField(required=False, write_only=True, allow_blank=True)
    
    def validate_email(self, value):
        """Validate email is unique"""
        if UserProfile.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing user password.
    Super admins can change any user's password by providing user_id.
    Regular users can only change their own password.
    """
    user_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    
    def validate_new_password(self, value):
        """Validate the new password"""
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long")
        return value
