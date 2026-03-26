"""
Service layer for Company operations.

This module contains business logic for company creation, updates,
email generation, and tax ID validation.
"""

import logging
import re
from typing import Dict, Any
from django.db import transaction
from django.utils import timezone

from core.exceptions import (
    ValidationError,
    PermissionError,
    BusinessLogicError,
    ResourceNotFoundError,
)
from companies.models import Company
from authentication.models import UserProfile

logger = logging.getLogger(__name__)


class CompanyService:
    """Service for company operations.
    
    Encapsulates business logic for company creation, updates,
    email generation, and tax ID validation. All methods are static
    and accept validated data from serializers.
    """

    @staticmethod
    def create_company(user: UserProfile, validated_data: Dict[str, Any]) -> Company:
        """
        Create a new company.
        
        Args:
            user: The user creating the company
            validated_data: Data containing company details
            
        Returns:
            Created Company instance
            
        Raises:
            PermissionError: If user lacks permission to create companies
            ValidationError: If data is invalid
            BusinessLogicError: If unexpected error occurs
        """
        # Check permission - only admins can create companies
        if user.role not in ['admin', 'super_admin']:
            raise PermissionError("You do not have permission to create companies")
        
        try:
            with transaction.atomic():
                # Validate required fields
                company_name = validated_data.get('name')
                if not company_name:
                    raise ValidationError({'name': 'Company name is required'})
                
                registration_number = validated_data.get('registration_number')
                if not registration_number:
                    raise ValidationError({'registration_number': 'Registration number is required'})
                
                tax_id = validated_data.get('tax_id')
                if not tax_id:
                    raise ValidationError({'tax_id': 'Tax ID is required'})
                
                # Validate tax ID if provided
                country = validated_data.get('country', 'KE')
                if not CompanyService.validate_tax_id(tax_id, country):
                    raise ValidationError({
                        'tax_id': f'Invalid tax ID format for {country}'
                    })
                
                # Create company
                company = Company.objects.create(
                    **validated_data,
                    is_active=True
                )
                
                logger.info(f"Company created: {company.name}")
                return company
                
        except (ValidationError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"Company creation error: {str(e)}", exc_info=True)
            raise BusinessLogicError("Failed to create company")

    @staticmethod
    def update_company(company: Company, user: UserProfile, validated_data: Dict[str, Any]) -> Company:
        """
        Update company details.
        
        Args:
            company: The company to update
            user: The user updating the company
            validated_data: Data containing updated company details
            
        Returns:
            Updated Company instance
            
        Raises:
            PermissionError: If user lacks permission to update companies
            ValidationError: If data is invalid
            BusinessLogicError: If unexpected error occurs
        """
        # Check permission - only admins can update companies
        if user.role not in ['admin', 'super_admin']:
            raise PermissionError("You do not have permission to update companies")
        
        try:
            with transaction.atomic():
                # Validate tax ID if provided
                if 'tax_id' in validated_data and validated_data['tax_id']:
                    country = validated_data.get('country', company.country or 'KE')
                    if not CompanyService.validate_tax_id(validated_data['tax_id'], country):
                        raise ValidationError({
                            'tax_id': f'Invalid tax ID format for {country}'
                        })
                
                # Update fields
                for field, value in validated_data.items():
                    if hasattr(company, field):
                        setattr(company, field, value)
                
                company.save()
                
                logger.info(f"Company updated: {company.name} by {user.email}")
                return company
                
        except (ValidationError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"Company update error: {str(e)}", exc_info=True)
            raise BusinessLogicError("Failed to update company")

    @staticmethod
    def generate_company_email(company_name: str) -> str:
        """
        Generate a unique company email from company name.
        
        Args:
            company_name: The company name
            
        Returns:
            Generated email address
            
        Raises:
            ValidationError: If email cannot be generated
        """
        if not company_name:
            raise ValidationError({'name': 'Company name is required'})
        
        try:
            # Convert to lowercase and replace spaces with underscores
            base_email = company_name.lower().replace(' ', '_')
            # Remove special characters except underscores
            base_email = re.sub(r'[^a-z0-9_]', '', base_email)
            
            # Ensure it's not empty after sanitization
            if not base_email:
                raise ValidationError({'name': 'Company name must contain alphanumeric characters'})
            
            # Check for uniqueness and add suffix if needed
            email = f"{base_email}@company.local"
            counter = 1
            
            while Company.objects.filter(contact_email=email).exists():
                email = f"{base_email}{counter}@company.local"
                counter += 1
            
            return email
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Email generation error: {str(e)}")
            raise BusinessLogicError("Failed to generate company email")

    @staticmethod
    def validate_tax_id(tax_id: str, country: str = 'KE') -> bool:
        """
        Validate tax ID format for a given country.
        
        Args:
            tax_id: The tax ID to validate
            country: The country code (default: 'KE' for Kenya)
            
        Returns:
            True if valid, False otherwise
        """
        if not tax_id:
            return False
        
        # Kenya PIN format: 10 digits
        if country == 'KE':
            # PIN should be 10 digits
            return bool(re.match(r'^\d{10}$', tax_id))
        
        # Default: accept any non-empty string
        return bool(tax_id.strip())
