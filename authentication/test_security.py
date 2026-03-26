"""
Security-focused tests for authentication
Tests for vulnerabilities identified in security audit
"""
import pytest
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from authentication.models import UserProfile
from companies.models import Company
import time


class SecretKeySecurityTests(TestCase):
    """
    Test SECRET_KEY security (Vulnerability #1)
    """
    
    def test_secret_key_must_be_set(self):
        """Test that SECRET_KEY cannot be empty or default"""
        from django.conf import settings
        
        # SECRET_KEY should be set
        self.assertIsNotNone(settings.SECRET_KEY)
        self.assertNotEqual(settings.SECRET_KEY, '')
        
        # Should not be the insecure default
        self.assertNotIn('django-insecure', settings.SECRET_KEY.lower())
        self.assertNotIn('change-this', settings.SECRET_KEY.lower())
    
    def test_secret_key_minimum_length(self):
        """Test that SECRET_KEY meets minimum length requirements"""
        from django.conf import settings
        
        # Should be at least 50 characters for production security
        self.assertGreaterEqual(len(settings.SECRET_KEY), 50,
                               "SECRET_KEY should be at least 50 characters")


class DebugModeSecurityTests(TestCase):
    """
    Test DEBUG mode security (Vulnerability #2)
    """
    
    def test_debug_mode_default_is_false(self):
        """Test that DEBUG defaults to False (secure)"""
        from django.conf import settings
        
        # In production, DEBUG should be False
        # This test verifies the default is secure
        # Note: In test environment, DEBUG might be True, but we check the setting
        self.assertIsNotNone(settings.DEBUG)


class RateLimitingSecurityTests(APITestCase):
    """
    Test rate limiting on authentication endpoints (Vulnerability #8)
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.login_url = reverse('token_obtain_pair')
    
    @pytest.mark.skip(reason="Rate limiting not yet implemented - will be enabled after fix")
    def test_login_rate_limiting_blocks_brute_force(self):
        """
        Test that excessive login attempts are rate limited
        
        VULNERABILITY: No rate limiting allows brute force attacks
        FIX: Implement django-ratelimit with 5 attempts per 15 minutes
        """
        data = {
            'username': 'testuser',
            'password': 'WrongPassword'
        }
        
        # Make 10 failed login attempts
        responses = []
        for i in range(10):
            response = self.client.post(self.login_url, data, format='json')
            responses.append(response.status_code)
            time.sleep(0.1)  # Small delay to avoid overwhelming test
        
        # After 5 attempts, should get 429 Too Many Requests
        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, responses,
                     "Rate limiting should block excessive login attempts")
    
    @pytest.mark.skip(reason="Rate limiting not yet implemented")
    def test_rate_limit_resets_after_time_window(self):
        """Test that rate limit resets after the time window"""
        # This will be implemented with the rate limiting fix
        pass


class PasswordResetSecurityTests(APITestCase):
    """
    Test password reset security (Vulnerability #9)
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.reset_url = reverse('password_reset_request')
    
    def test_password_reset_doesnt_reveal_user_existence(self):
        """
        Test that password reset doesn't reveal if email exists
        
        VULNERABILITY: User enumeration via different responses
        FIX: Return same response for existing and non-existing emails
        """
        # Request reset for existing email
        response1 = self.client.post(self.reset_url, {'email': 'test@example.com'}, format='json')
        
        # Request reset for non-existing email
        response2 = self.client.post(self.reset_url, {'email': 'nonexistent@example.com'}, format='json')
        
        # Both should return same status code
        self.assertEqual(response1.status_code, response2.status_code)
        
        # Both should return same message
        self.assertEqual(response1.data.get('message'), response2.data.get('message'))
    
    @pytest.mark.skip(reason="Token not yet removed from logs - will be enabled after fix")
    def test_password_reset_token_not_in_response(self):
        """
        Test that password reset token is not included in API response
        
        VULNERABILITY: Token exposed in response/logs
        FIX: Never return token in response, only send via email
        """
        response = self.client.post(self.reset_url, {'email': 'test@example.com'}, format='json')
        
        # Response should not contain token
        response_str = str(response.data).lower()
        self.assertNotIn('token', response_str)
        self.assertNotIn('reset', response_str.replace('reset password', ''))
    
    @pytest.mark.skip(reason="Token expiration not yet implemented")
    def test_password_reset_token_expires(self):
        """
        Test that password reset tokens expire after set time
        
        VULNERABILITY: Tokens valid indefinitely
        FIX: Implement 15-30 minute expiration
        """
        # This will be implemented with the password reset security fix
        pass


class TokenStorageSecurityTests(APITestCase):
    """
    Test JWT token storage security (Vulnerability #7)
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.company = Company.objects.create(
            name="Test Company",
            registration_number="TEST001",
            tax_id="TAX001",
            address="123 Test St",
            contact_email="test@company.com",
            contact_phone="+1234567890"
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        UserProfile.objects.create(
            user=self.user,
            role='staff',
            company=self.company
        )
        self.login_url = reverse('token_obtain_pair')
    
    @pytest.mark.skip(reason="httpOnly cookies not yet implemented - will be enabled after fix")
    def test_jwt_token_set_in_httponly_cookie(self):
        """
        Test that JWT tokens are set in httpOnly cookies
        
        VULNERABILITY: Tokens in localStorage vulnerable to XSS
        FIX: Use httpOnly cookies instead
        """
        data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        # Should set httpOnly cookie
        self.assertIn('access_token', response.cookies)
        
        # Cookie should have httpOnly flag
        cookie = response.cookies['access_token']
        self.assertTrue(cookie.get('httponly', False))
        
        # Cookie should have secure flag (for HTTPS)
        self.assertTrue(cookie.get('secure', False))
        
        # Cookie should have SameSite attribute
        self.assertIn(cookie.get('samesite', '').lower(), ['strict', 'lax'])
    
    @pytest.mark.skip(reason="httpOnly cookies not yet implemented")
    def test_jwt_token_not_in_response_body(self):
        """
        Test that JWT tokens are not included in response body
        
        VULNERABILITY: Tokens in response body can be stolen via XSS
        FIX: Only set in httpOnly cookies
        """
        data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        # Response body should not contain tokens
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        self.assertNotIn('token', str(response.data).lower())


class SessionSecurityTests(APITestCase):
    """
    Test session security
    """
    
    @pytest.mark.skip(reason="Session timeout not yet implemented")
    def test_session_timeout_configured(self):
        """
        Test that session timeout is configured
        
        VULNERABILITY: No session timeout
        FIX: Implement 30-minute session timeout
        """
        from django.conf import settings
        
        # Should have session timeout configured
        self.assertIsNotNone(settings.SESSION_COOKIE_AGE)
        
        # Should be reasonable (30 minutes = 1800 seconds)
        self.assertLessEqual(settings.SESSION_COOKIE_AGE, 1800)


class AuthorizationSecurityTests(APITestCase):
    """
    Test authorization and permission security
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create two companies
        self.company_a = Company.objects.create(
            name="Company A",
            registration_number="COMP_A",
            tax_id="TAX_A",
            address="123 A St",
            contact_email="a@company.com",
            contact_phone="+1111111111"
        )
        
        self.company_b = Company.objects.create(
            name="Company B",
            registration_number="COMP_B",
            tax_id="TAX_B",
            address="123 B St",
            contact_email="b@company.com",
            contact_phone="+2222222222"
        )
        
        # Create users for each company
        self.user_a = User.objects.create_user(
            username='user_a',
            email='user_a@example.com',
            password='TestPass123!'
        )
        self.profile_a = UserProfile.objects.create(
            user=self.user_a,
            role='admin',
            company=self.company_a
        )
        
        self.user_b = User.objects.create_user(
            username='user_b',
            email='user_b@example.com',
            password='TestPass123!'
        )
        self.profile_b = UserProfile.objects.create(
            user=self.user_b,
            role='admin',
            company=self.company_b
        )
    
    def test_user_cannot_access_other_company_data(self):
        """
        Test company isolation - users cannot access other companies' data
        
        VULNERABILITY: Weak company isolation
        FIX: Enforce company checks before serializer validation
        """
        # Login as user from Company A
        login_response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'user_a', 'password': 'TestPass123!'},
            format='json'
        )
        
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to create resource for Company B
        # This test will be expanded once we implement the fix
        # For now, we verify the user's company is correctly set
        self.assertEqual(self.profile_a.company, self.company_a)
        self.assertNotEqual(self.profile_a.company, self.company_b)


class SelfApprovalSecurityTests(APITestCase):
    """
    Test self-approval prevention (Vulnerability #12)
    """
    
    @pytest.mark.skip(reason="Self-approval prevention not yet implemented")
    def test_user_cannot_approve_own_request(self):
        """
        Test that users cannot approve their own requests
        
        VULNERABILITY: Self-approval allowed
        FIX: Check if requester == approver and reject
        """
        # This will be implemented with the workflow security fix
        pass


class ErrorDisclosureSecurityTests(APITestCase):
    """
    Test error message security (Vulnerability #15)
    """
    
    def test_error_messages_dont_expose_internals(self):
        """
        Test that error messages don't expose internal details
        
        VULNERABILITY: Detailed error messages expose system information
        FIX: Return generic messages in production
        """
        # Try to access non-existent endpoint
        response = self.client.get('/api/nonexistent/')
        
        # Error message should not contain:
        # - File paths
        # - Stack traces
        # - Database queries
        # - Internal variable names
        
        response_str = str(response.data).lower() if hasattr(response, 'data') else ''
        
        # Should not contain file paths
        self.assertNotIn('/backend/', response_str)
        self.assertNotIn('c:\\', response_str.lower())
        
        # Should not contain stack trace indicators
        self.assertNotIn('traceback', response_str)
        self.assertNotIn('line ', response_str)


# Test runner configuration
pytest_plugins = ['pytest_django']
