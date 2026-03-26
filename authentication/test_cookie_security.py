"""
Cookie Security Test Suite

Tests for JWT tokens stored in httpOnly cookies.
This prevents XSS attacks from accessing the tokens.

Validates: Requirement 2.7 from production-security-hardening spec
"""
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from authentication.models import UserProfile
from companies.models import Company


class CookieSecurityTest(TestCase):
    """
    Test Suite 1.7.4: Test cookie security attributes
    
    Validates that JWT tokens are stored in httpOnly cookies with proper security attributes.
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        
        # Create test company
        self.company = Company.objects.create(
            name='Test Company',
            registration_number='TEST001',
            tax_id='TAX001',
            address='Test Address',
            contact_email='test@company.com',
            contact_phone='1234567890'
        )
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        
        # Create user profile
        self.profile = UserProfile.objects.create(
            user=self.user,
            role='staff',
            company=self.company,
            phone='+254712345678',
            department='IT'
        )
        
        # Login credentials
        self.valid_credentials = {
            'email': 'testuser@example.com',
            'password': 'TestPass123!'
        }
    
    def test_login_sets_httponly_cookies(self):
        """
        Test that login sets httpOnly cookies for access and refresh tokens
        
        Expected: Cookies are set with httpOnly flag
        """
        response = self.client.post(
            '/api/auth/login/',
            self.valid_credentials,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that cookies are set
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        
        # Check httpOnly flag
        access_cookie = response.cookies['access_token']
        refresh_cookie = response.cookies['refresh_token']
        
        self.assertTrue(access_cookie['httponly'])
        self.assertTrue(refresh_cookie['httponly'])
    
    def test_cookies_have_samesite_attribute(self):
        """
        Test that cookies have SameSite attribute for CSRF protection
        
        Expected: Cookies have SameSite=Lax
        """
        response = self.client.post(
            '/api/auth/login/',
            self.valid_credentials,
            format='json'
        )
        
        access_cookie = response.cookies['access_token']
        refresh_cookie = response.cookies['refresh_token']
        
        self.assertEqual(access_cookie['samesite'], 'Lax')
        self.assertEqual(refresh_cookie['samesite'], 'Lax')
    
    @override_settings(DEBUG=False)
    def test_cookies_have_secure_flag_in_production(self):
        """
        Test that cookies have Secure flag in production (HTTPS only)
        
        Expected: Cookies have Secure flag when DEBUG=False
        """
        response = self.client.post(
            '/api/auth/login/',
            self.valid_credentials,
            format='json'
        )
        
        access_cookie = response.cookies['access_token']
        refresh_cookie = response.cookies['refresh_token']
        
        self.assertTrue(access_cookie['secure'])
        self.assertTrue(refresh_cookie['secure'])
    
    def test_cookies_have_appropriate_max_age(self):
        """
        Test that cookies have appropriate max_age values
        
        Expected: Access token expires in 1 hour, refresh token in 7 days
        """
        response = self.client.post(
            '/api/auth/login/',
            self.valid_credentials,
            format='json'
        )
        
        access_cookie = response.cookies['access_token']
        refresh_cookie = response.cookies['refresh_token']
        
        # Access token: 1 hour = 3600 seconds
        self.assertEqual(access_cookie['max-age'], 3600)
        
        # Refresh token: 7 days = 604800 seconds
        self.assertEqual(refresh_cookie['max-age'], 604800)
    
    def test_tokens_not_in_response_body(self):
        """
        Test that tokens are NOT included in the response body
        
        Expected: Response contains user data but no access/refresh tokens
        """
        response = self.client.post(
            '/api/auth/login/',
            self.valid_credentials,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Tokens should NOT be in response body
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        
        # User data should be present
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], self.user.email)
    
    def test_logout_clears_cookies(self):
        """
        Test that logout clears the httpOnly cookies
        
        Expected: Cookies are deleted on logout
        """
        # Login first
        login_response = self.client.post(
            '/api/auth/login/',
            self.valid_credentials,
            format='json'
        )
        
        # Set cookies in client
        self.client.cookies['access_token'] = login_response.cookies['access_token'].value
        self.client.cookies['refresh_token'] = login_response.cookies['refresh_token'].value
        
        # Logout
        logout_response = self.client.post(
            '/api/auth/logout/',
            format='json'
        )
        
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        
        # Check that cookies are cleared
        access_cookie = logout_response.cookies.get('access_token')
        refresh_cookie = logout_response.cookies.get('refresh_token')
        
        # Cookies should be present in response (to clear them)
        self.assertIsNotNone(access_cookie)
        self.assertIsNotNone(refresh_cookie)
        
        # Cookies should have empty value
        self.assertEqual(access_cookie.value, '')
        self.assertEqual(refresh_cookie.value, '')
    
    def test_authenticated_request_uses_cookie(self):
        """
        Test that authenticated requests can use token from cookie
        
        Expected: API accepts authentication from cookie
        """
        # Login to get cookies
        login_response = self.client.post(
            '/api/auth/login/',
            self.valid_credentials,
            format='json'
        )
        
        # Set cookie in client
        access_token = login_response.cookies['access_token'].value
        self.client.cookies['access_token'] = access_token
        
        # Make authenticated request (no Authorization header needed)
        response = self.client.get('/api/auth/me/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
    
    def test_refresh_token_uses_cookie(self):
        """
        Test that token refresh reads refresh token from cookie
        
        Expected: Refresh endpoint accepts token from cookie
        """
        # Login to get cookies
        login_response = self.client.post(
            '/api/auth/login/',
            self.valid_credentials,
            format='json'
        )
        
        # Set cookies in client
        self.client.cookies['access_token'] = login_response.cookies['access_token'].value
        self.client.cookies['refresh_token'] = login_response.cookies['refresh_token'].value
        
        # Refresh token (no body needed, reads from cookie)
        refresh_response = self.client.post(
            '/api/auth/refresh/',
            format='json'
        )
        
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        
        # New tokens should be set in cookies
        self.assertIn('access_token', refresh_response.cookies)
        
        # Response body should not contain tokens
        self.assertNotIn('access', refresh_response.data)
    
    def test_cookie_authentication_backward_compatible(self):
        """
        Test that Authorization header still works for backward compatibility
        
        Expected: Both cookie and header authentication work
        """
        # Login to get token
        login_response = self.client.post(
            '/api/auth/login/',
            self.valid_credentials,
            format='json'
        )
        
        access_token = login_response.cookies['access_token'].value
        
        # Use Authorization header (old method)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get('/api/auth/me/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
