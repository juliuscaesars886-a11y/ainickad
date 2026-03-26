"""
API tests for validation rules endpoint.

Tests verify that the ValidationRulesView API endpoint:
- Returns 200 status code
- Returns all validation rules
- Returns correct version
- Returns correct structure
"""

import pytest
from django.test import Client
from rest_framework import status


@pytest.mark.django_db
class TestValidationRulesAPI:
    """Test ValidationRulesView API endpoint"""
    
    def setup_method(self):
        """Set up test client"""
        self.client = Client()
    
    def test_get_validation_rules_success(self):
        """Test successful GET request to validation rules endpoint"""
        response = self.client.get("/api/validation-rules/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check structure
        assert "version" in data
        assert "email" in data
        assert "password" in data
        assert "phone" in data
        assert "taxId" in data
    
    def test_validation_rules_email_structure(self):
        """Test email validation rules structure"""
        response = self.client.get("/api/validation-rules/")
        data = response.json()
        
        email_rules = data["email"]
        assert "pattern" in email_rules
        assert "message" in email_rules
        assert isinstance(email_rules["pattern"], str)
        assert isinstance(email_rules["message"], str)
    
    def test_validation_rules_password_structure(self):
        """Test password validation rules structure"""
        response = self.client.get("/api/validation-rules/")
        data = response.json()
        
        password_rules = data["password"]
        assert "min_length" in password_rules
        assert "uppercase" in password_rules
        assert "lowercase" in password_rules
        assert "number" in password_rules
        assert "special" in password_rules
        assert "message" in password_rules
        
        assert isinstance(password_rules["min_length"], int)
        assert isinstance(password_rules["uppercase"], bool)
        assert isinstance(password_rules["lowercase"], bool)
        assert isinstance(password_rules["number"], bool)
        assert isinstance(password_rules["special"], bool)
    
    def test_validation_rules_phone_structure(self):
        """Test phone validation rules structure"""
        response = self.client.get("/api/validation-rules/")
        data = response.json()
        
        phone_rules = data["phone"]
        assert "pattern" in phone_rules
        assert "message" in phone_rules
        assert isinstance(phone_rules["pattern"], str)
        assert isinstance(phone_rules["message"], str)
    
    def test_validation_rules_tax_id_structure(self):
        """Test tax ID validation rules structure"""
        response = self.client.get("/api/validation-rules/")
        data = response.json()
        
        tax_id_rules = data["taxId"]
        assert "patterns" in tax_id_rules
        assert "message" in tax_id_rules
        assert isinstance(tax_id_rules["patterns"], dict)
        
        # Check country patterns
        assert "KE" in tax_id_rules["patterns"]
        assert "UG" in tax_id_rules["patterns"]
        assert "TZ" in tax_id_rules["patterns"]
    
    def test_validation_rules_version(self):
        """Test validation rules version"""
        response = self.client.get("/api/validation-rules/")
        data = response.json()
        
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0
    
    def test_post_not_allowed(self):
        """Test that POST is not allowed"""
        response = self.client.post("/api/validation-rules/", {})
        assert response.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN]
    
    def test_put_not_allowed(self):
        """Test that PUT is not allowed"""
        response = self.client.put("/api/validation-rules/", {})
        assert response.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN]
    
    def test_delete_not_allowed(self):
        """Test that DELETE is not allowed"""
        response = self.client.delete("/api/validation-rules/")
        assert response.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN]
