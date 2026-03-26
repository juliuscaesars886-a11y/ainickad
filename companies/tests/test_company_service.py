"""
Unit tests for CompanyService.

Tests cover company creation, updates, email generation, and tax ID validation.
"""

import pytest
from django.contrib.auth import get_user_model

from companies.services import CompanyService
from companies.models import Company
from core.exceptions import ValidationError, PermissionError

User = get_user_model()


@pytest.mark.django_db
class TestCompanyServiceCreate:
    """Tests for CompanyService.create_company"""

    def setup_method(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            full_name='Admin User',
            role='admin'
        )
        
        self.regular_user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            full_name='Regular User',
            role='viewer'
        )

    def test_create_company_success(self):
        """Test successful company creation"""
        data = {
            'name': 'New Company',
            'registration_number': 'REG-123',
            'tax_id': '1234567890',
            'address': '123 Main St',
            'contact_email': 'contact@company.com',
            'contact_phone': '+254700000000'
        }
        
        company = CompanyService.create_company(self.admin_user, data)
        
        assert company.name == 'New Company'
        assert company.tax_id == '1234567890'
        assert company.is_active is True

    def test_create_company_permission_denied(self):
        """Test company creation without permission"""
        data = {
            'name': 'New Company',
            'registration_number': 'REG-123',
            'tax_id': '1234567890'
        }
        
        with pytest.raises(PermissionError):
            CompanyService.create_company(self.regular_user, data)

    def test_create_company_missing_name(self):
        """Test company creation with missing name"""
        data = {
            'registration_number': 'REG-123',
            'tax_id': '1234567890'
        }
        
        with pytest.raises(ValidationError):
            CompanyService.create_company(self.admin_user, data)

    def test_create_company_invalid_tax_id(self):
        """Test company creation with invalid tax ID"""
        data = {
            'name': 'New Company',
            'registration_number': 'REG-123',
            'tax_id': 'invalid',
            'country': 'KE'
        }
        
        with pytest.raises(ValidationError):
            CompanyService.create_company(self.admin_user, data)


@pytest.mark.django_db
class TestCompanyServiceTaxIdValidation:
    """Tests for CompanyService.validate_tax_id"""

    def test_validate_tax_id_kenya_valid(self):
        """Test valid Kenya tax ID"""
        assert CompanyService.validate_tax_id('1234567890', 'KE') is True

    def test_validate_tax_id_kenya_invalid_length(self):
        """Test invalid Kenya tax ID - wrong length"""
        assert CompanyService.validate_tax_id('123456789', 'KE') is False

    def test_validate_tax_id_kenya_invalid_format(self):
        """Test invalid Kenya tax ID - non-numeric"""
        assert CompanyService.validate_tax_id('123456789a', 'KE') is False

    def test_validate_tax_id_empty(self):
        """Test validation with empty tax ID"""
        assert CompanyService.validate_tax_id('', 'KE') is False
