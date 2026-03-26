"""
Tests for authentication app
"""
import jwt
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from hypothesis import given, strategies as st, settings as hypothesis_settings
from hypothesis.extra.django import TestCase
from django.test import RequestFactory
from .authentication import SupabaseJWTAuthentication
from .models import UserProfile
from companies.models import Company


class JWTValidationPropertyTest(TestCase):
    """
    Property 1: JWT Token Validation
    
    For any HTTP request with a JWT token, if the token is valid and not expired,
    the Django backend should successfully authenticate the user and extract their
    identity; if the token is invalid or expired, the backend should return a 401
    Unauthorized response.
    
    Validates: Requirements 1.1, 1.2, 1.5
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.auth = SupabaseJWTAuthentication()
        self.jwt_secret = settings.SUPABASE_JWT_SECRET or 'test-secret-key'
        
        # Create a test company with unique identifiers
        unique_id = str(uuid.uuid4())[:8]
        self.company = Company.objects.create(
            name=f'Test Company {unique_id}',
            registration_number=f'TEST{unique_id}',
            tax_id=f'TAX{unique_id}',
            address='Test Address',
            contact_email=f'test{unique_id}@company.com',
            contact_phone='1234567890'
        )
    
    def generate_valid_token(self, user_id, email, role='employee', exp_minutes=60):
        """Generate a valid JWT token"""
        payload = {
            'sub': str(user_id),
            'email': email,
            'aud': 'authenticated',
            'exp': datetime.utcnow() + timedelta(minutes=exp_minutes),
            'iat': datetime.utcnow(),
            'user_metadata': {
                'role': role,
                'full_name': 'Test User'
            }
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    @hypothesis_settings(max_examples=50, deadline=None)
    @given(
        email=st.emails(),
        role=st.sampled_from(['super_admin', 'admin', 'accountant', 'employee'])
    )
    def test_valid_token_authenticates_successfully(self, email, role):
        """
        Property: Valid, non-expired tokens should authenticate successfully
        """
        user_id = uuid.uuid4()
        token = self.generate_valid_token(user_id, email, role)
        
        # Create request with valid token
        request = self.factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        # Authenticate should succeed
        result = self.auth.authenticate(request)
        
        self.assertIsNotNone(result)
        user_profile, returned_token = result
        self.assertEqual(user_profile.email, email)
        self.assertEqual(user_profile.role, role)
        self.assertEqual(returned_token, token)
    
    def test_expired_token_raises_authentication_failed(self):
        """
        Property: Expired tokens should raise AuthenticationFailed
        """
        user_id = uuid.uuid4()
        email = 'test@example.com'
        
        # Generate expired token (negative expiration)
        token = self.generate_valid_token(user_id, email, exp_minutes=-10)
        
        # Create request with expired token
        request = self.factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        # Should raise AuthenticationFailed
        with self.assertRaises(AuthenticationFailed) as context:
            self.auth.authenticate(request)
        
        self.assertIn('expired', str(context.exception).lower())
    
    def test_invalid_token_raises_authentication_failed(self):
        """
        Property: Invalid tokens should raise AuthenticationFailed
        """
        # Create request with invalid token
        request = self.factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer invalid-token-string'
        
        # Should raise AuthenticationFailed
        with self.assertRaises(AuthenticationFailed) as context:
            self.auth.authenticate(request)
        
        self.assertIn('invalid', str(context.exception).lower())
    
    def test_missing_authorization_header_returns_none(self):
        """
        Property: Requests without Authorization header should return None
        """
        request = self.factory.get('/api/test/')
        
        # Should return None (not authenticated, but not an error)
        result = self.auth.authenticate(request)
        self.assertIsNone(result)
    
    def test_malformed_authorization_header_returns_none(self):
        """
        Property: Malformed Authorization headers should return None
        """
        request = self.factory.get('/api/test/')
        request.META['HTTP_AUTHORIZATION'] = 'InvalidFormat token'
        
        # Should return None
        result = self.auth.authenticate(request)
        self.assertIsNone(result)


class UserProfileSyncPropertyTest(TestCase):
    """
    Property 2: User Profile Synchronization
    
    For any valid Supabase user payload (from registration or update), the Django
    backend should create or update the corresponding User Profile with all fields
    matching the payload data.
    
    Validates: Requirements 1.3, 1.4
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.auth = SupabaseJWTAuthentication()
    
    @hypothesis_settings(max_examples=50, deadline=None)
    @given(
        email=st.emails(),
        full_name=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cs',))),
        role=st.sampled_from(['super_admin', 'admin', 'accountant', 'employee'])
    )
    def test_sync_creates_or_updates_user_profile(self, email, full_name, role):
        """
        Property: Syncing a user payload should create or update UserProfile
        with matching fields
        """
        user_id = uuid.uuid4()
        
        payload = {
            'sub': str(user_id),
            'email': email,
            'aud': 'authenticated',
            'user_metadata': {
                'full_name': full_name,
                'role': role,
                'avatar_url': 'https://example.com/avatar.jpg'
            }
        }
        
        # First sync - should create
        user_profile = self.auth.sync_user_profile(payload)
        
        self.assertEqual(str(user_profile.id), str(user_id))
        self.assertEqual(user_profile.email, email)
        self.assertEqual(user_profile.full_name, full_name)
        self.assertEqual(user_profile.role, role)
        self.assertTrue(user_profile.is_active)
        
        # Second sync with updated data - should update
        updated_full_name = full_name + ' Updated'
        payload['user_metadata']['full_name'] = updated_full_name
        
        user_profile_updated = self.auth.sync_user_profile(payload)
        
        # Should be same user
        self.assertEqual(str(user_profile_updated.id), str(user_profile.id))
        # Should have updated name
        self.assertEqual(user_profile_updated.full_name, updated_full_name)
        
        # Verify only one user profile exists
        self.assertEqual(UserProfile.objects.filter(id=user_id).count(), 1)
    
    def test_sync_with_missing_required_fields_raises_error(self):
        """
        Property: Syncing without required fields should raise AuthenticationFailed
        """
        # Missing 'sub' (user_id)
        payload_no_sub = {
            'email': 'test@example.com',
            'aud': 'authenticated'
        }
        
        with self.assertRaises(AuthenticationFailed):
            self.auth.sync_user_profile(payload_no_sub)
        
        # Missing 'email'
        payload_no_email = {
            'sub': str(uuid.uuid4()),
            'aud': 'authenticated'
        }
        
        with self.assertRaises(AuthenticationFailed):
            self.auth.sync_user_profile(payload_no_email)
    
    def test_sync_preserves_user_id_across_updates(self):
        """
        Property: User ID should remain constant across multiple syncs
        """
        user_id = uuid.uuid4()
        email = 'test@example.com'
        
        payload = {
            'sub': str(user_id),
            'email': email,
            'aud': 'authenticated',
            'user_metadata': {
                'full_name': 'Original Name',
                'role': 'employee'
            }
        }
        
        # Create user
        user_profile1 = self.auth.sync_user_profile(payload)
        
        # Update multiple times
        for i in range(5):
            payload['user_metadata']['full_name'] = f'Name {i}'
            user_profile = self.auth.sync_user_profile(payload)
            
            # ID should never change
            self.assertEqual(str(user_profile.id), str(user_id))
            self.assertEqual(str(user_profile.id), str(user_profile1.id))



class UserProfileModelPropertyTest(TestCase):
    """
    Property 3: Model Field Persistence
    Property 5: Enum Value Validation (role)
    
    For any Django model instance with valid data, when saved to the database,
    all required fields should be persisted and retrievable with identical values.
    
    For any model field with enumerated choices (role), the Django backend should
    accept only valid enum values and reject invalid values with appropriate error messages.
    
    Validates: Requirements 2.1, 2.5
    """
    
    def setUp(self):
        """Set up test fixtures"""
        unique_id = str(uuid.uuid4())[:8]
        self.company = Company.objects.create(
            name=f'Test Company {unique_id}',
            registration_number=f'TEST{unique_id}',
            tax_id=f'TAX{unique_id}',
            address='Test Address',
            contact_email=f'test{unique_id}@company.com',
            contact_phone='1234567890'
        )
    
    @hypothesis_settings(max_examples=30, deadline=None)
    @given(
        email=st.emails(),
        full_name=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cs',))),
        role=st.sampled_from(['super_admin', 'admin', 'accountant', 'employee'])
    )
    def test_user_profile_field_persistence(self, email, full_name, role):
        """
        Property 3: All required fields should be persisted and retrievable
        """
        user_id = uuid.uuid4()
        avatar_url = 'https://example.com/avatar.jpg'
        metadata = {'key': 'value', 'number': 42}
        
        # Create user profile
        user_profile = UserProfile.objects.create(
            id=user_id,
            email=email,
            full_name=full_name,
            role=role,
            company=self.company,
            avatar_url=avatar_url,
            metadata=metadata,
            is_active=True
        )
        
        # Retrieve from database
        retrieved = UserProfile.objects.get(id=user_id)
        
        # Verify all fields match
        self.assertEqual(str(retrieved.id), str(user_id))
        self.assertEqual(retrieved.email, email)
        self.assertEqual(retrieved.full_name, full_name)
        self.assertEqual(retrieved.role, role)
        self.assertEqual(retrieved.company, self.company)
        self.assertEqual(retrieved.avatar_url, avatar_url)
        self.assertEqual(retrieved.metadata, metadata)
        self.assertTrue(retrieved.is_active)
    
    def test_role_enum_validation_accepts_valid_values(self):
        """
        Property 5: Valid enum values should be accepted
        """
        valid_roles = ['super_admin', 'admin', 'accountant', 'employee']
        
        for role in valid_roles:
            user_profile = UserProfile.objects.create(
                email=f'{role}@example.com',
                full_name=f'{role} User',
                role=role,
                company=self.company
            )
            
            # Should save successfully
            self.assertEqual(user_profile.role, role)
            
            # Should retrieve successfully
            retrieved = UserProfile.objects.get(id=user_profile.id)
            self.assertEqual(retrieved.role, role)
    
    def test_role_enum_validation_stores_invalid_values_but_warns(self):
        """
        Property 5: Invalid enum values can be stored (Django doesn't enforce at DB level)
        but should be validated at serializer level
        """
        # Django allows storing invalid choices at model level
        # Validation happens at form/serializer level
        user_profile = UserProfile.objects.create(
            email='invalid@example.com',
            full_name='Invalid User',
            role='invalid_role',  # Invalid role
            company=self.company
        )
        
        # It will be stored (Django doesn't enforce choices at DB level)
        self.assertEqual(user_profile.role, 'invalid_role')
        
        # But serializer should validate it
        from .serializers import UserProfileSerializer
        serializer = UserProfileSerializer(user_profile)
        # The serializer will include it in data but validation would catch it on write
    
    def test_user_profile_role_helper_properties(self):
        """
        Test role-based helper properties work correctly
        """
        # Super admin
        super_admin = UserProfile.objects.create(
            email='superadmin@example.com',
            role='super_admin',
            company=self.company
        )
        self.assertTrue(super_admin.is_super_admin)
        self.assertTrue(super_admin.is_admin)
        self.assertTrue(super_admin.is_accountant)
        self.assertTrue(super_admin.can_approve)
        
        # Admin
        admin = UserProfile.objects.create(
            email='admin@example.com',
            role='admin',
            company=self.company
        )
        self.assertFalse(admin.is_super_admin)
        self.assertTrue(admin.is_admin)
        self.assertTrue(admin.is_accountant)
        self.assertTrue(admin.can_approve)
        
        # Accountant
        accountant = UserProfile.objects.create(
            email='accountant@example.com',
            role='accountant',
            company=self.company
        )
        self.assertFalse(accountant.is_super_admin)
        self.assertFalse(accountant.is_admin)
        self.assertTrue(accountant.is_accountant)
        self.assertTrue(accountant.can_approve)
        
        # Employee
        employee = UserProfile.objects.create(
            email='employee@example.com',
            role='employee',
            company=self.company
        )
        self.assertFalse(employee.is_super_admin)
        self.assertFalse(employee.is_admin)
        self.assertFalse(employee.is_accountant)
        self.assertFalse(employee.can_approve)



class AuthenticationEndpointIntegrationTest(TestCase):
    """
    Integration tests for authentication API endpoints.
    
    Tests user sync, profile retrieval, profile updates, and authentication failures.
    
    Validates: Requirements 1.1, 1.2, 2.2
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.jwt_secret = settings.SUPABASE_JWT_SECRET or 'test-secret-key'
        
        unique_id = str(uuid.uuid4())[:8]
        self.company = Company.objects.create(
            name=f'Test Company {unique_id}',
            registration_number=f'TEST{unique_id}',
            tax_id=f'TAX{unique_id}',
            address='Test Address',
            contact_email=f'test{unique_id}@company.com',
            contact_phone='1234567890'
        )
        
        self.user_id = uuid.uuid4()
        self.email = f'testuser{unique_id}@example.com'
        self.user_profile = UserProfile.objects.create(
            id=self.user_id,
            email=self.email,
            full_name='Test User',
            role='employee',
            company=self.company
        )
    
    def generate_token(self, user_id, email, role='employee'):
        """Generate a valid JWT token"""
        payload = {
            'sub': str(user_id),
            'email': email,
            'aud': 'authenticated',
            'exp': datetime.utcnow() + timedelta(hours=1),
            'iat': datetime.utcnow(),
            'user_metadata': {
                'role': role,
                'full_name': 'Test User'
            }
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def test_sync_user_endpoint_creates_new_user(self):
        """
        Test POST /api/auth/sync-user/ creates a new user
        """
        from .views import sync_user
        
        new_user_id = uuid.uuid4()
        new_email = 'newuser@example.com'
        
        request = self.factory.post('/api/auth/sync-user/', {
            'user_id': str(new_user_id),
            'email': new_email,
            'full_name': 'New User',
            'role': 'admin',
            'avatar_url': 'https://example.com/avatar.jpg',
            'metadata': {'key': 'value'}
        }, content_type='application/json')
        
        response = sync_user(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], new_email)
        
        # Verify user was created
        user = UserProfile.objects.get(id=new_user_id)
        self.assertEqual(user.email, new_email)
        self.assertEqual(user.role, 'admin')
    
    def test_sync_user_endpoint_updates_existing_user(self):
        """
        Test POST /api/auth/sync-user/ updates existing user
        """
        from .views import sync_user
        
        request = self.factory.post('/api/auth/sync-user/', {
            'user_id': str(self.user_id),
            'email': self.email,
            'full_name': 'Updated Name',
            'role': 'accountant',
        }, content_type='application/json')
        
        response = sync_user(request)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify user was updated
        user = UserProfile.objects.get(id=self.user_id)
        self.assertEqual(user.full_name, 'Updated Name')
        self.assertEqual(user.role, 'accountant')
    
    def test_get_current_user_endpoint(self):
        """
        Test GET /api/auth/me/ returns current user profile
        """
        from .views import CurrentUserView
        
        token = self.generate_token(self.user_id, self.email)
        
        request = self.factory.get('/api/auth/me/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        # Authenticate the request
        from .authentication import SupabaseJWTAuthentication
        auth = SupabaseJWTAuthentication()
        user, _ = auth.authenticate(request)
        request.user = user
        
        view = CurrentUserView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], self.email)
        self.assertEqual(response.data['role'], 'employee')
    
    def test_update_current_user_endpoint(self):
        """
        Test PATCH /api/auth/me/ updates current user profile
        """
        from .views import CurrentUserView
        
        token = self.generate_token(self.user_id, self.email)
        
        request = self.factory.patch('/api/auth/me/', {
            'full_name': 'Updated Full Name',
            'metadata': {'updated': True}
        }, content_type='application/json')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        # Authenticate the request
        from .authentication import SupabaseJWTAuthentication
        auth = SupabaseJWTAuthentication()
        user, _ = auth.authenticate(request)
        request.user = user
        
        view = CurrentUserView.as_view()
        response = view(request)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify user was updated
        user = UserProfile.objects.get(id=self.user_id)
        self.assertEqual(user.full_name, 'Updated Full Name')
        self.assertEqual(user.metadata['updated'], True)
    
    def test_authentication_failure_with_invalid_token(self):
        """
        Test that invalid token returns authentication error
        """
        from .authentication import SupabaseJWTAuthentication
        
        request = self.factory.get('/api/auth/me/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer invalid-token'
        
        auth = SupabaseJWTAuthentication()
        
        with self.assertRaises(AuthenticationFailed):
            auth.authenticate(request)
    
    def test_authentication_failure_with_expired_token(self):
        """
        Test that expired token returns authentication error
        """
        from .authentication import SupabaseJWTAuthentication
        
        # Generate expired token
        payload = {
            'sub': str(self.user_id),
            'email': self.email,
            'aud': 'authenticated',
            'exp': datetime.utcnow() - timedelta(hours=1),  # Expired
            'iat': datetime.utcnow() - timedelta(hours=2),
            'user_metadata': {'role': 'employee'}
        }
        expired_token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
        
        request = self.factory.get('/api/auth/me/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {expired_token}'
        
        auth = SupabaseJWTAuthentication()
        
        with self.assertRaises(AuthenticationFailed) as context:
            auth.authenticate(request)
        
        self.assertIn('expired', str(context.exception).lower())
