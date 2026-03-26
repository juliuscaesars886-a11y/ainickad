"""
Comprehensive Authentication Security Test Suite

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5 from production-security-hardening spec
"""
import time
from datetime import timedelta
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from authentication.models import UserProfile
from companies.models import Company


class AuthenticationSecurityTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            name="Test Company", registration_number="TEST001", tax_id="TAX001",
            address="Test Address", contact_email="test@company.com", contact_phone="1234567890"
        )
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="TestPass123!",
            first_name="Test", last_name="User"
        )
        self.profile = UserProfile.objects.create(
            user=self.user, role="staff", company=self.company,
            phone="+254712345678", department="IT"
        )
        self.valid_credentials = {"email": "testuser@example.com", "password": "TestPass123!"}
        self.invalid_credentials = {"email": "testuser@example.com", "password": "WrongPassword123!"}


class LoginWithValidCredentialsTest(AuthenticationSecurityTestCase):
    """Test Suite 0.1.1: Test login with valid credentials"""
    
    def test_login_with_valid_email_and_password(self):
        response = self.client.post("/api/auth/login/", self.valid_credentials, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], self.user.email)
    
    def test_access_token_is_valid_jwt(self):
        response = self.client.post("/api/auth/login/", self.valid_credentials, format="json")
        token = AccessToken(response.data["access"])
        self.assertEqual(token["user_id"], self.user.id)
        self.assertIn("exp", token)


class LoginWithInvalidCredentialsTest(AuthenticationSecurityTestCase):
    """Test Suite 0.1.2: Test login with invalid credentials"""
    
    def test_login_with_wrong_password(self):
        response = self.client.post("/api/auth/login/", self.invalid_credentials, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.data)
    
    def test_login_with_nonexistent_email(self):
        response = self.client.post("/api/auth/login/", {"email": "nonexistent@example.com", "password": "Pass123!"}, format="json")
        # Should return 400 (validation error) or 401 (authentication failed)
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED])
    
    def test_login_with_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post("/api/auth/login/", self.valid_credentials, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.user.is_active = True
        self.user.save()


class LogoutAndTokenBlacklistingTest(AuthenticationSecurityTestCase):
    """Test Suite 0.1.3: Test logout and token blacklisting"""
    
    def test_logout_blacklists_refresh_token(self):
        login_response = self.client.post("/api/auth/login/", self.valid_credentials, format="json")
        refresh_token = login_response.data["refresh"]
        access_token = login_response.data["access"]
        
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        logout_response = self.client.post("/api/auth/logout/", {"refresh": refresh_token}, format="json")
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        
        refresh_response = self.client.post("/api/auth/refresh/", {"refresh": refresh_token}, format="json")
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_logout_requires_authentication(self):
        response = self.client.post("/api/auth/logout/", {"refresh": "some-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_blacklisted_token_recorded_in_database(self):
        login_response = self.client.post("/api/auth/login/", self.valid_credentials, format="json")
        initial_count = BlacklistedToken.objects.count()
        
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")
        self.client.post("/api/auth/logout/", {"refresh": login_response.data["refresh"]}, format="json")
        
        self.assertEqual(BlacklistedToken.objects.count(), initial_count + 1)


class TokenRefreshTest(AuthenticationSecurityTestCase):
    """Test Suite 0.1.4: Test token refresh"""
    
    def test_refresh_token_generates_new_access_token(self):
        login_response = self.client.post("/api/auth/login/", self.valid_credentials, format="json")
        refresh_response = self.client.post("/api/auth/refresh/", {"refresh": login_response.data["refresh"]}, format="json")
        
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)
        self.assertNotEqual(refresh_response.data["access"], login_response.data["access"])
    
    def test_new_access_token_is_valid(self):
        login_response = self.client.post("/api/auth/login/", self.valid_credentials, format="json")
        refresh_response = self.client.post("/api/auth/refresh/", {"refresh": login_response.data["refresh"]}, format="json")
        
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_response.data['access']}")
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_refresh_with_invalid_token_fails(self):
        response = self.client.post("/api/auth/refresh/", {"refresh": "invalid-token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ExpiredTokenHandlingTest(AuthenticationSecurityTestCase):
    """Test Suite 0.1.5: Test expired token handling"""
    
    def test_expired_access_token_is_rejected(self):
        """Test that expired access token cannot access protected endpoints"""
        # Create a token that's already expired
        from datetime import datetime, timezone
        
        token = AccessToken.for_user(self.user)
        # Manually set expiration to past
        token.set_exp(from_time=datetime.now(timezone.utc) - timedelta(hours=1))
        
        expired_token = str(token)
        
        # Try to use expired token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired_token}")
        response = self.client.get("/api/auth/me/")
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_valid_token_works_before_expiration(self):
        login_response = self.client.post("/api/auth/login/", self.valid_credentials, format="json")
        
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
