"""
Unit tests for AuthService.

Tests cover login, registration, logout, and password change operations.
"""

import pytest
from django.test import RequestFactory
from django.contrib.auth import get_user_model

from authentication.services import AuthService
from companies.models import Company
from core.exceptions import ValidationError, PermissionError

User = get_user_model()


@pytest.mark.django_db
class TestAuthServiceLogin:
    """Tests for AuthService.login"""

    def setup_method(self):
        """Set up test data"""
        self.factory = RequestFactory()
        self.company = Company.objects.create(
            name='Test Company',
            registration_number='REG-001',
            tax_id='1234567890',
            address='123 Main St',
            contact_email='test@company.com',
            contact_phone='+254700000000',
            is_active=True
        )
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User',
            company=self.company,
            is_active=True
        )

    def test_login_success(self):
        """Test successful login"""
        request = self.factory.post('/login/')
        user, token = AuthService.login('test@example.com', 'testpass123', request)
        
        assert user.email == 'test@example.com'
        assert token is not None
        assert len(token) > 0

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        request = self.factory.post('/login/')
        
        with pytest.raises(ValidationError):
            AuthService.login('test@example.com', 'wrongpassword', request)

    def test_login_missing_email(self):
        """Test login with missing email"""
        request = self.factory.post('/login/')
        
        with pytest.raises(ValidationError):
            AuthService.login('', 'testpass123', request)

    def test_login_inactive_user(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()
        
        request = self.factory.post('/login/')
        
        with pytest.raises(PermissionError):
            AuthService.login('test@example.com', 'testpass123', request)


@pytest.mark.django_db
class TestAuthServiceRegister:
    """Tests for AuthService.register"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            registration_number='REG-001',
            tax_id='1234567890',
            address='123 Main St',
            contact_email='test@company.com',
            contact_phone='+254700000000',
            is_active=True
        )

    def test_register_success(self):
        """Test successful registration"""
        data = {
            'email': 'newuser@example.com',
            'password': 'testpass123',
            'full_name': 'New User'
        }
        
        user = AuthService.register(data)
        
        assert user.email == 'newuser@example.com'
        assert user.is_active is True
        assert user.company is not None

    def test_register_duplicate_email(self):
        """Test registration with duplicate email"""
        User.objects.create_user(
            email='existing@example.com',
            password='testpass123'
        )
        
        data = {
            'email': 'existing@example.com',
            'password': 'testpass123'
        }
        
        with pytest.raises(ValidationError):
            AuthService.register(data)

    def test_register_missing_email(self):
        """Test registration with missing email"""
        data = {
            'password': 'testpass123'
        }
        
        with pytest.raises(ValidationError):
            AuthService.register(data)


@pytest.mark.django_db
class TestAuthServiceChangePassword:
    """Tests for AuthService.change_password"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            registration_number='REG-001',
            tax_id='1234567890',
            address='123 Main St',
            contact_email='test@company.com',
            contact_phone='+254700000000',
            is_active=True
        )
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='oldpass123',
            full_name='Test User',
            company=self.company,
            is_active=True
        )

    def test_change_password_success(self):
        """Test successful password change"""
        AuthService.change_password(self.user, 'oldpass123', 'newpass123')
        
        self.user.refresh_from_db()
        assert self.user.check_password('newpass123')

    def test_change_password_wrong_old_password(self):
        """Test password change with wrong old password"""
        with pytest.raises(ValidationError):
            AuthService.change_password(self.user, 'wrongpass', 'newpass123')

    def test_change_password_too_short(self):
        """Test password change with too short new password"""
        with pytest.raises(ValidationError):
            AuthService.change_password(self.user, 'oldpass123', 'short')
