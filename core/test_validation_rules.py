"""
Unit tests for validation rules module.

Tests verify that validation patterns and rules work correctly for:
- Email validation
- Password validation
- Phone number validation
- Tax ID validation
"""

import pytest
from core.validation_rules import (
    validate_email,
    validate_password,
    validate_phone,
    validate_tax_id,
    get_validation_rules,
    VERSION,
)


class TestEmailValidation:
    """Test email validation"""
    
    def test_valid_email(self):
        """Test valid email addresses"""
        valid_emails = [
            "user@example.com",
            "test.user@example.co.uk",
            "user+tag@example.com",
            "user_name@example.com",
        ]
        for email in valid_emails:
            is_valid, message = validate_email(email)
            assert is_valid, f"Email {email} should be valid, got message: {message}"
    
    def test_invalid_email(self):
        """Test invalid email addresses"""
        invalid_emails = [
            "invalid",
            "user@",
            "@example.com",
            "user @example.com",
            "user@example",
        ]
        for email in invalid_emails:
            is_valid, message = validate_email(email)
            assert not is_valid, f"Email {email} should be invalid"
            assert message, f"Error message should be provided for {email}"
    
    def test_empty_email(self):
        """Test empty email"""
        is_valid, message = validate_email("")
        assert not is_valid
        assert "required" in message.lower()


class TestPasswordValidation:
    """Test password validation"""
    
    def test_valid_password(self):
        """Test valid passwords"""
        valid_passwords = [
            "ValidPass123!",
            "MyPassword@2024",
            "SecureP@ss1",
        ]
        for password in valid_passwords:
            is_valid, message = validate_password(password)
            assert is_valid, f"Password {password} should be valid, got message: {message}"
    
    def test_password_too_short(self):
        """Test password too short"""
        is_valid, message = validate_password("Short1!")
        assert not is_valid
        assert "8 characters" in message
    
    def test_password_missing_uppercase(self):
        """Test password missing uppercase"""
        is_valid, message = validate_password("validpass123!")
        assert not is_valid
        assert "uppercase" in message.lower()
    
    def test_password_missing_lowercase(self):
        """Test password missing lowercase"""
        is_valid, message = validate_password("VALIDPASS123!")
        assert not is_valid
        assert "lowercase" in message.lower()
    
    def test_password_missing_number(self):
        """Test password missing number"""
        is_valid, message = validate_password("ValidPass!")
        assert not is_valid
        assert "number" in message.lower()
    
    def test_password_missing_special(self):
        """Test password missing special character"""
        is_valid, message = validate_password("ValidPass123")
        assert not is_valid
        assert "special" in message.lower()
    
    def test_empty_password(self):
        """Test empty password"""
        is_valid, message = validate_password("")
        assert not is_valid
        assert "required" in message.lower()


class TestPhoneValidation:
    """Test phone number validation"""
    
    def test_valid_phone(self):
        """Test valid phone numbers"""
        valid_phones = [
            "1234567890",
            "+1234567890",
            "+1 (234) 567-8900",
            "123-456-7890",
        ]
        for phone in valid_phones:
            is_valid, message = validate_phone(phone)
            assert is_valid, f"Phone {phone} should be valid, got message: {message}"
    
    def test_invalid_phone(self):
        """Test invalid phone numbers"""
        invalid_phones = [
            "123",  # Too short
            "abc1234567",  # Contains letters
        ]
        for phone in invalid_phones:
            is_valid, message = validate_phone(phone)
            assert not is_valid, f"Phone {phone} should be invalid"
    
    def test_empty_phone(self):
        """Test empty phone (optional)"""
        is_valid, message = validate_phone("")
        assert is_valid  # Phone is optional


class TestTaxIdValidation:
    """Test tax ID validation"""
    
    def test_valid_kenya_tax_id(self):
        """Test valid Kenya tax ID"""
        is_valid, message = validate_tax_id("1234567890", "KE")
        assert is_valid, f"Kenya tax ID should be valid, got message: {message}"
    
    def test_valid_uganda_tax_id(self):
        """Test valid Uganda tax ID"""
        is_valid, message = validate_tax_id("12345678901234", "UG")
        assert is_valid, f"Uganda tax ID should be valid, got message: {message}"
    
    def test_invalid_kenya_tax_id(self):
        """Test invalid Kenya tax ID (wrong length)"""
        is_valid, message = validate_tax_id("123456789", "KE")
        assert not is_valid
        assert message
    
    def test_invalid_country(self):
        """Test invalid country code"""
        is_valid, message = validate_tax_id("1234567890", "XX")
        assert not is_valid
        assert "Unsupported" in message or "country" in message.lower()
    
    def test_empty_tax_id(self):
        """Test empty tax ID"""
        is_valid, message = validate_tax_id("", "KE")
        assert not is_valid
        assert "required" in message.lower()


class TestValidationRulesAPI:
    """Test validation rules API"""
    
    def test_get_validation_rules(self):
        """Test getting all validation rules"""
        rules = get_validation_rules()
        
        # Check structure
        assert "version" in rules
        assert "email" in rules
        assert "password" in rules
        assert "phone" in rules
        assert "taxId" in rules
        
        # Check version
        assert rules["version"] == VERSION
        
        # Check email rules
        assert "pattern" in rules["email"]
        assert "message" in rules["email"]
        
        # Check password rules
        assert "min_length" in rules["password"]
        assert "uppercase" in rules["password"]
        assert "lowercase" in rules["password"]
        assert "number" in rules["password"]
        assert "special" in rules["password"]
        
        # Check phone rules
        assert "pattern" in rules["phone"]
        assert "message" in rules["phone"]
        
        # Check tax ID rules
        assert "patterns" in rules["taxId"]
        assert "KE" in rules["taxId"]["patterns"]
        assert "UG" in rules["taxId"]["patterns"]
