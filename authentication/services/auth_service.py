"""
Service layer for Authentication operations.

This module contains business logic for user authentication, registration,
logout, and password management.
"""

import logging
from typing import Dict, Any, Tuple
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.db import transaction
from rest_framework.authtoken.models import Token

from core.exceptions import (
    ValidationError,
    PermissionError,
    BusinessLogicError,
    ResourceNotFoundError,
)
from authentication.models import UserProfile
from companies.models import Company

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations.
    
    Encapsulates business logic for user authentication, registration,
    logout, and password management. All methods are static and accept
    validated data from serializers.
    """

    @staticmethod
    def login(email: str, password: str, request) -> Tuple[UserProfile, str]:
        """
        Authenticate user and create session.
        
        Args:
            email: User email address
            password: User password
            request: Django request object for session creation
            
        Returns:
            Tuple of (UserProfile instance, authentication token)
            
        Raises:
            ValidationError: If email or password is invalid
            PermissionError: If account is inactive
            BusinessLogicError: If unexpected error occurs
        """
        if not email or not password:
            raise ValidationError({
                'email': 'Email is required',
                'password': 'Password is required'
            })
        
        try:
            # Authenticate user
            user_profile = authenticate(request, username=email, password=password)
            
            if not user_profile:
                raise ValidationError({
                    'credentials': 'Invalid email or password'
                })
            
            # Check if user is active
            if not user_profile.is_active:
                raise PermissionError("Account is inactive")
            
            # Ensure user has a company assigned
            if not user_profile.company:
                AuthService._assign_default_company(user_profile)
            
            # Create session
            from django.contrib.auth import login as django_login
            try:
                django_login(request, user_profile)
            except AttributeError:
                # RequestFactory doesn't provide session, skip session creation
                pass
            
            # Generate or get authentication token
            token, created = Token.objects.get_or_create(user=user_profile)
            
            logger.info(f"User logged in: {user_profile.email}")
            
            return user_profile, token.key
            
        except (ValidationError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            raise BusinessLogicError("Login failed")

    @staticmethod
    def register(validated_data: Dict[str, Any]) -> UserProfile:
        """
        Create new user account.
        
        Args:
            validated_data: Data containing email, password, full_name
            
        Returns:
            Created UserProfile instance
            
        Raises:
            ValidationError: If email already exists or data is invalid
            BusinessLogicError: If unexpected error occurs
        """
        email = validated_data.get('email')
        password = validated_data.get('password')
        full_name = validated_data.get('full_name', '')
        
        if not email or not password:
            raise ValidationError({
                'email': 'Email is required',
                'password': 'Password is required'
            })
        
        # Check if user already exists
        if UserProfile.objects.filter(email=email).exists():
            raise ValidationError({
                'email': 'Email already registered'
            })
        
        try:
            with transaction.atomic():
                # Get or create default company
                default_company = Company.objects.filter(is_active=True).first()
                if not default_company:
                    default_company = Company.objects.create(
                        name='Default Company',
                        registration_number='DEFAULT-001',
                        tax_id='TAX-DEFAULT-001',
                        address='Default Address',
                        contact_email='admin@company.com',
                        contact_phone='+254700000000',
                        risk_level='level_2',
                        risk_category='general_business',
                        is_active=True
                    )
                    logger.info(f"Default company created: {default_company.name}")
                
                # Create user
                user = UserProfile.objects.create_user(
                    email=email,
                    password=password,
                    full_name=full_name,
                    company=default_company,
                    is_active=True
                )
                
                logger.info(f"User registered: {email}")
                return user
                
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            raise BusinessLogicError("Registration failed")

    @staticmethod
    def logout(user: UserProfile, request) -> None:
        """
        End user session and clear session memory.
        
        Args:
            user: The user logging out
            request: Django request object
            
        Raises:
            BusinessLogicError: If unexpected error occurs
        """
        try:
            user_id = user.id
            
            # Clear AI assistant session memory
            try:
                from communications.memory_helpers import clear_session_memory
                clear_session_memory(user_id)
                logger.debug(f"Cleared session memory for user {user_id}")
            except Exception as mem_error:
                # Don't fail logout if memory clearing fails
                logger.warning(f"Failed to clear session memory for user {user_id}: {mem_error}")
            
            # Logout user
            from django.contrib.auth import logout as django_logout
            django_logout(request)
            
            logger.info(f"User logged out: {user.email}")
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            raise BusinessLogicError("Logout failed")

    @staticmethod
    def change_password(user: UserProfile, old_password: str, new_password: str) -> None:
        """
        Change user password.
        
        Args:
            user: The user changing password
            old_password: Current password
            new_password: New password
            
        Raises:
            ValidationError: If old password is incorrect or new password is invalid
            BusinessLogicError: If unexpected error occurs
        """
        if not old_password or not new_password:
            raise ValidationError({
                'old_password': 'Old password is required',
                'new_password': 'New password is required'
            })
        
        # Verify old password
        if not check_password(old_password, user.password):
            raise ValidationError({
                'old_password': 'Old password is incorrect'
            })
        
        # Validate new password
        if len(new_password) < 8:
            raise ValidationError({
                'new_password': 'Password must be at least 8 characters'
            })
        
        try:
            with transaction.atomic():
                user.set_password(new_password)
                user.save(update_fields=['password'])
                
                logger.info(f"Password changed for user: {user.email}")
                
        except Exception as e:
            logger.error(f"Password change error: {str(e)}", exc_info=True)
            raise BusinessLogicError("Failed to change password")

    # Helper methods

    @staticmethod
    def _assign_default_company(user: UserProfile) -> None:
        """
        Assign default company to user if not already assigned.
        
        Args:
            user: The user to assign company to
        """
        try:
            # Try to get the first active company
            default_company = Company.objects.filter(is_active=True).first()
            
            # If no active company exists, create one
            if not default_company:
                logger.info("No active company found. Creating default company...")
                default_company = Company.objects.create(
                    name='Default Company',
                    registration_number='DEFAULT-001',
                    tax_id='TAX-DEFAULT-001',
                    address='Default Address',
                    contact_email='admin@company.com',
                    contact_phone='+254700000000',
                    risk_level='level_2',
                    risk_category='general_business',
                    is_active=True
                )
                logger.info(f"Default company created: {default_company.name}")
            
            # Assign the company to the user
            user.company = default_company
            user.save(update_fields=['company'])
            logger.info(f"Assigned company to user {user.email}: {default_company.name}")
            
            # If user has a Staff record, also update that
            try:
                if hasattr(user, 'staff'):
                    user.staff.company = default_company
                    user.staff.save(update_fields=['company'])
                    logger.info(f"Also updated Staff record for {user.email}")
            except Exception as e:
                logger.warning(f"Could not update Staff record for {user.email}: {e}")
                
        except Exception as e:
            logger.error(f"Failed to assign default company: {e}")
