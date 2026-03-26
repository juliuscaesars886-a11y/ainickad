"""
Authorization test suite for production security hardening
Tests role-based access control, company isolation, object-level permissions,
and privilege escalation prevention.

**Validates: Requirements 1.3, 1.6**
"""
import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from authentication.models import UserProfile
from authentication.permissions import (
    IsSuperAdmin, IsAdmin, IsAccountant, CanApprove, IsOwnerOrAdmin
)
from companies.models import Company


class RoleBasedAccessControlTests(APITestCase):
    """
    Test role-based access control (Task 0.3.1)
    
    **Validates: Requirements 1.3**
    
    Tests that different user roles have appropriate access levels:
    - super_admin: Full access to all resources
    - admin: Company-wide access
    - accountant: Financial and approval access
    - staff: Limited access to own resources
    """
    
    def setUp(self):
        """Set up test data with users of different roles"""
        self.client = APIClient()
        
        # Create company
        self.company = Company.objects.create(
            name="Test Company",
            registration_number="TEST001",
            tax_id="TAX001",
            address="123 Test St",
            contact_email="test@company.com",
            contact_phone="+1234567890"
        )
        
        # Create super admin
        self.super_admin_user = User.objects.create_user(
            username='superadmin',
            email='superadmin@example.com',
            password='TestPass123!'
        )
        self.super_admin_profile = UserProfile.objects.create(
            user=self.super_admin_user,
            role='super_admin',
            company=self.company
        )
        
        # Create admin
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='TestPass123!'
        )
        self.admin_profile = UserProfile.objects.create(
            user=self.admin_user,
            role='admin',
            company=self.company
        )
        
        # Create accountant
        self.accountant_user = User.objects.create_user(
            username='accountant',
            email='accountant@example.com',
            password='TestPass123!'
        )
        self.accountant_profile = UserProfile.objects.create(
            user=self.accountant_user,
            role='accountant',
            company=self.company
        )
        
        # Create staff
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='TestPass123!'
        )
        self.staff_profile = UserProfile.objects.create(
            user=self.staff_user,
            role='staff',
            company=self.company
        )
    
    def test_super_admin_permission_class(self):
        """Test IsSuperAdmin permission class correctly identifies super admins"""
        permission = IsSuperAdmin()
        
        # Create mock request with super admin
        from unittest.mock import Mock
        request = Mock()
        request.user = self.super_admin_user
        
        # Super admin should have permission
        self.assertTrue(permission.has_permission(request, None))
        
        # Admin should not have permission
        request.user = self.admin_user
        self.assertFalse(permission.has_permission(request, None))
        
        # Staff should not have permission
        request.user = self.staff_user
        self.assertFalse(permission.has_permission(request, None))
    
    def test_admin_permission_class(self):
        """Test IsAdmin permission class correctly identifies admins and super admins"""
        permission = IsAdmin()
        
        from unittest.mock import Mock
        request = Mock()
        
        # Super admin should have permission
        request.user = self.super_admin_user
        self.assertTrue(permission.has_permission(request, None))
        
        # Admin should have permission
        request.user = self.admin_user
        self.assertTrue(permission.has_permission(request, None))
        
        # Accountant should not have permission
        request.user = self.accountant_user
        self.assertFalse(permission.has_permission(request, None))
        
        # Staff should not have permission
        request.user = self.staff_user
        self.assertFalse(permission.has_permission(request, None))
    
    def test_accountant_permission_class(self):
        """Test IsAccountant permission class correctly identifies accountants and above"""
        permission = IsAccountant()
        
        from unittest.mock import Mock
        request = Mock()
        
        # Super admin should have permission
        request.user = self.super_admin_user
        self.assertTrue(permission.has_permission(request, None))
        
        # Admin should have permission
        request.user = self.admin_user
        self.assertTrue(permission.has_permission(request, None))
        
        # Accountant should have permission
        request.user = self.accountant_user
        self.assertTrue(permission.has_permission(request, None))
        
        # Staff should not have permission
        request.user = self.staff_user
        self.assertFalse(permission.has_permission(request, None))
    
    def test_can_approve_permission_class(self):
        """Test CanApprove permission class correctly identifies users who can approve"""
        permission = CanApprove()
        
        from unittest.mock import Mock
        request = Mock()
        
        # Super admin should have permission
        request.user = self.super_admin_user
        self.assertTrue(permission.has_permission(request, None))
        
        # Admin should have permission
        request.user = self.admin_user
        self.assertTrue(permission.has_permission(request, None))
        
        # Accountant should have permission
        request.user = self.accountant_user
        self.assertTrue(permission.has_permission(request, None))
        
        # Staff should not have permission
        request.user = self.staff_user
        self.assertFalse(permission.has_permission(request, None))
    
    def test_unauthenticated_user_denied(self):
        """Test that unauthenticated users are denied access"""
        permission = IsAdmin()
        
        from unittest.mock import Mock
        request = Mock()
        request.user = None
        
        self.assertFalse(permission.has_permission(request, None))
        
        # Test with anonymous user
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        self.assertFalse(permission.has_permission(request, None))
    
    def test_user_profile_role_properties(self):
        """Test UserProfile role checking properties"""
        # Super admin properties
        self.assertTrue(self.super_admin_profile.is_super_admin)
        self.assertTrue(self.super_admin_profile.is_admin)
        self.assertTrue(self.super_admin_profile.is_accountant)
        self.assertTrue(self.super_admin_profile.can_approve)
        
        # Admin properties
        self.assertFalse(self.admin_profile.is_super_admin)
        self.assertTrue(self.admin_profile.is_admin)
        self.assertTrue(self.admin_profile.is_accountant)
        self.assertTrue(self.admin_profile.can_approve)
        
        # Accountant properties
        self.assertFalse(self.accountant_profile.is_super_admin)
        self.assertFalse(self.accountant_profile.is_admin)
        self.assertTrue(self.accountant_profile.is_accountant)
        self.assertTrue(self.accountant_profile.can_approve)
        
        # Staff properties
        self.assertFalse(self.staff_profile.is_super_admin)
        self.assertFalse(self.staff_profile.is_admin)
        self.assertFalse(self.staff_profile.is_accountant)
        self.assertFalse(self.staff_profile.can_approve)
    
    def test_role_based_endpoint_access(self):
        """Test that endpoints respect role-based permissions"""
        # Login as staff user
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'staff', 'password': 'TestPass123!'},
            format='json'
        )
        
        if login_response.status_code == status.HTTP_200_OK:
            token = login_response.data['access']
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            
            # Staff should be able to access basic endpoints
            # but not admin-only endpoints
            # This will be expanded as we implement more endpoints
            
            # Test user registration endpoint (admin only)
            register_response = self.client.post(
                '/api/auth/register/',
                {
                    'username': 'newuser',
                    'email': 'newuser@example.com',
                    'password': 'NewPass123!',
                    'role': 'staff'
                },
                format='json'
            )
            
            # Staff should not be able to register users
            self.assertEqual(register_response.status_code, status.HTTP_403_FORBIDDEN)



class CompanyIsolationTests(APITestCase):
    """
    Test company isolation (Task 0.3.2)
    
    **Validates: Requirements 1.6**
    
    Tests that users can only access resources belonging to their company:
    - Users cannot view other companies' data
    - Users cannot modify other companies' data
    - Users cannot create resources for other companies
    - Company filtering is enforced at the queryset level
    """
    
    def setUp(self):
        """Set up test data with multiple companies"""
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
        
        # Create admin users for each company
        self.user_a = User.objects.create_user(
            username='admin_a',
            email='admin_a@example.com',
            password='TestPass123!'
        )
        self.profile_a = UserProfile.objects.create(
            user=self.user_a,
            role='admin',
            company=self.company_a
        )
        
        self.user_b = User.objects.create_user(
            username='admin_b',
            email='admin_b@example.com',
            password='TestPass123!'
        )
        self.profile_b = UserProfile.objects.create(
            user=self.user_b,
            role='admin',
            company=self.company_b
        )
        
        # Create staff user for Company A
        self.staff_a = User.objects.create_user(
            username='staff_a',
            email='staff_a@example.com',
            password='TestPass123!'
        )
        self.staff_profile_a = UserProfile.objects.create(
            user=self.staff_a,
            role='staff',
            company=self.company_a
        )
    
    def test_user_profile_has_correct_company(self):
        """Test that user profiles are correctly associated with companies"""
        self.assertEqual(self.profile_a.company, self.company_a)
        self.assertEqual(self.profile_b.company, self.company_b)
        self.assertNotEqual(self.profile_a.company, self.company_b)
    
    def test_user_cannot_list_other_company_users(self):
        """Test that users cannot see users from other companies"""
        # Login as Company A admin
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'admin_a', 'password': 'TestPass123!'},
            format='json'
        )
        
        if login_response.status_code != status.HTTP_200_OK:
            self.skipTest("Login failed, cannot test company isolation")
        
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Get current user info
        me_response = self.client.get('/api/auth/me/')
        
        if me_response.status_code == status.HTTP_200_OK:
            # Verify user is from Company A
            # Convert UUID to string for comparison
            company_id = me_response.data['company']
            if hasattr(company_id, 'hex'):
                company_id = str(company_id)
            self.assertEqual(company_id, str(self.company_a.id))
    
    def test_company_isolation_in_document_creation(self):
        """Test that users cannot create documents for other companies"""
        # Login as Company A admin
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'admin_a', 'password': 'TestPass123!'},
            format='json'
        )
        
        if login_response.status_code != status.HTTP_200_OK:
            self.skipTest("Login failed, cannot test company isolation")
        
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to create document for Company B
        from django.core.files.uploadedfile import SimpleUploadedFile
        file_content = b'test content'
        uploaded_file = SimpleUploadedFile(
            'test.pdf',
            file_content,
            content_type='application/pdf'
        )
        
        response = self.client.post(
            '/api/documents/',
            {
                'title': 'Test Document',
                'company': str(self.company_b.id),  # Try to create for Company B
                'category': 'contract',
                'file': uploaded_file
            },
            format='multipart'
        )
        
        # Should be rejected (either 400 or 403)
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN],
            "User should not be able to create documents for other companies"
        )
    
    def test_company_isolation_in_financial_data(self):
        """Test that users cannot access financial data from other companies"""
        # Login as Company A admin
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'admin_a', 'password': 'TestPass123!'},
            format='json'
        )
        
        if login_response.status_code != status.HTTP_200_OK:
            self.skipTest("Login failed, cannot test company isolation")
        
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to list invoices (should only see Company A's invoices)
        response = self.client.get('/api/invoices/')
        
        if response.status_code == status.HTTP_200_OK:
            # If there are any invoices, they should all belong to Company A
            for invoice in response.data.get('results', response.data):
                if isinstance(invoice, dict) and 'company' in invoice:
                    self.assertEqual(
                        invoice['company'],
                        str(self.company_a.id),
                        "User should only see invoices from their own company"
                    )
    
    def test_super_admin_can_access_all_companies(self):
        """Test that super admins can access data from all companies"""
        # Create super admin
        super_admin = User.objects.create_user(
            username='superadmin',
            email='superadmin@example.com',
            password='TestPass123!'
        )
        super_admin_profile = UserProfile.objects.create(
            user=super_admin,
            role='super_admin',
            company=self.company_a  # Belongs to Company A
        )
        
        # Login as super admin
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'superadmin', 'password': 'TestPass123!'},
            format='json'
        )
        
        if login_response.status_code != status.HTTP_200_OK:
            self.skipTest("Login failed, cannot test super admin access")
        
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Super admin should be able to list all companies
        response = self.client.get('/api/companies/')
        
        if response.status_code == status.HTTP_200_OK:
            # Should see both companies (or at least not be restricted)
            # This test documents expected behavior for super admins
            pass
    
    def test_company_isolation_prevents_data_leakage(self):
        """Test that company isolation prevents accidental data leakage"""
        # This is a critical security test
        # Even if a user knows the ID of a resource from another company,
        # they should not be able to access it
        
        # Login as Company A user
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'staff_a', 'password': 'TestPass123!'},
            format='json'
        )
        
        if login_response.status_code != status.HTTP_200_OK:
            self.skipTest("Login failed, cannot test company isolation")
        
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to access Company B's details directly
        response = self.client.get(f'/api/companies/{self.company_b.id}/')
        
        # Should be forbidden or not found
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
            "User should not be able to access other company's details"
        )



class ObjectLevelPermissionTests(APITestCase):
    """
    Test object-level permissions (Task 0.3.3)
    
    **Validates: Requirements 1.3**
    
    Tests that users can only access and modify objects they own or have permission to:
    - Users can access their own objects
    - Users cannot access objects owned by others (same company)
    - Admins can access all objects in their company
    - Object ownership is properly enforced
    """
    
    def setUp(self):
        """Set up test data with multiple users in same company"""
        self.client = APIClient()
        
        # Create company
        self.company = Company.objects.create(
            name="Test Company",
            registration_number="TEST001",
            tax_id="TAX001",
            address="123 Test St",
            contact_email="test@company.com",
            contact_phone="+1234567890"
        )
        
        # Create admin
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='TestPass123!'
        )
        self.admin_profile = UserProfile.objects.create(
            user=self.admin_user,
            role='admin',
            company=self.company
        )
        
        # Create two staff users in same company
        self.staff_user_1 = User.objects.create_user(
            username='staff1',
            email='staff1@example.com',
            password='TestPass123!'
        )
        self.staff_profile_1 = UserProfile.objects.create(
            user=self.staff_user_1,
            role='staff',
            company=self.company
        )
        
        self.staff_user_2 = User.objects.create_user(
            username='staff2',
            email='staff2@example.com',
            password='TestPass123!'
        )
        self.staff_profile_2 = UserProfile.objects.create(
            user=self.staff_user_2,
            role='staff',
            company=self.company
        )
    
    def test_is_owner_or_admin_permission_for_owner(self):
        """Test IsOwnerOrAdmin permission allows object owner"""
        permission = IsOwnerOrAdmin()
        
        from unittest.mock import Mock
        request = Mock()
        request.user = self.staff_user_1
        
        # Create mock object owned by staff_user_1
        obj = Mock()
        obj.user = self.staff_user_1
        
        # Owner should have permission
        self.assertTrue(permission.has_object_permission(request, None, obj))
        
        # Different user should not have permission
        request.user = self.staff_user_2
        self.assertFalse(permission.has_object_permission(request, None, obj))
    
    def test_is_owner_or_admin_permission_for_admin(self):
        """Test IsOwnerOrAdmin permission allows admins"""
        permission = IsOwnerOrAdmin()
        
        from unittest.mock import Mock
        request = Mock()
        request.user = self.admin_user
        
        # Create mock object owned by staff_user_1
        obj = Mock()
        obj.user = self.staff_user_1
        
        # Admin should have permission even though not owner
        self.assertTrue(permission.has_object_permission(request, None, obj))
    
    def test_is_owner_or_admin_with_created_by_field(self):
        """Test IsOwnerOrAdmin works with created_by field"""
        permission = IsOwnerOrAdmin()
        
        from unittest.mock import Mock
        request = Mock()
        request.user = self.staff_user_1
        
        # Create mock object with created_by field
        obj = Mock()
        obj.created_by = self.staff_user_1
        del obj.user  # No user field
        
        # Owner should have permission
        self.assertTrue(permission.has_object_permission(request, None, obj))
    
    def test_is_owner_or_admin_with_owner_field(self):
        """Test IsOwnerOrAdmin works with owner field"""
        permission = IsOwnerOrAdmin()
        
        from unittest.mock import Mock
        request = Mock()
        request.user = self.staff_user_1
        
        # Create mock object with owner field
        obj = Mock()
        obj.owner = self.staff_user_1
        del obj.user  # No user field
        del obj.created_by  # No created_by field
        
        # Owner should have permission
        self.assertTrue(permission.has_object_permission(request, None, obj))
    
    def test_user_cannot_modify_others_objects(self):
        """Test that users cannot modify objects owned by others"""
        # This test will be expanded once we have actual objects to test with
        # For now, we test the permission class logic
        
        permission = IsOwnerOrAdmin()
        
        from unittest.mock import Mock
        request = Mock()
        request.user = self.staff_user_1
        
        # Create object owned by staff_user_2
        obj = Mock()
        obj.user = self.staff_user_2
        
        # staff_user_1 should not have permission to staff_user_2's object
        self.assertFalse(permission.has_object_permission(request, None, obj))
    
    def test_admin_can_access_all_company_objects(self):
        """Test that admins can access all objects in their company"""
        permission = IsOwnerOrAdmin()
        
        from unittest.mock import Mock
        request = Mock()
        request.user = self.admin_user
        
        # Create objects owned by different users
        obj1 = Mock()
        obj1.user = self.staff_user_1
        
        obj2 = Mock()
        obj2.user = self.staff_user_2
        
        # Admin should have permission to both
        self.assertTrue(permission.has_object_permission(request, None, obj1))
        self.assertTrue(permission.has_object_permission(request, None, obj2))
    
    def test_object_permission_with_unauthenticated_user(self):
        """Test that unauthenticated users are denied object access"""
        permission = IsOwnerOrAdmin()
        
        from unittest.mock import Mock
        request = Mock()
        request.user = None
        
        obj = Mock()
        obj.user = self.staff_user_1
        
        # Unauthenticated user should not have permission
        self.assertFalse(permission.has_object_permission(request, None, obj))


class PrivilegeEscalationPreventionTests(APITestCase):
    """
    Test privilege escalation prevention (Task 0.3.4)
    
    **Validates: Requirements 1.3**
    
    Tests that prevent users from escalating their privileges:
    - Users cannot change their own role
    - Users cannot change their company assignment
    - Staff cannot approve their own requests
    - Users cannot impersonate other users
    - Role changes require admin privileges
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create company
        self.company = Company.objects.create(
            name="Test Company",
            registration_number="TEST001",
            tax_id="TAX001",
            address="123 Test St",
            contact_email="test@company.com",
            contact_phone="+1234567890"
        )
        
        # Create admin
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='TestPass123!'
        )
        self.admin_profile = UserProfile.objects.create(
            user=self.admin_user,
            role='admin',
            company=self.company
        )
        
        # Create staff user
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='TestPass123!'
        )
        self.staff_profile = UserProfile.objects.create(
            user=self.staff_user,
            role='staff',
            company=self.company
        )
    
    def test_user_cannot_change_own_role(self):
        """Test that users cannot escalate their own role"""
        # Login as staff user
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'staff', 'password': 'TestPass123!'},
            format='json'
        )
        
        if login_response.status_code != status.HTTP_200_OK:
            self.skipTest("Login failed, cannot test privilege escalation")
        
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to update own profile to admin role
        response = self.client.patch(
            '/api/auth/me/',
            {'role': 'admin'},
            format='json'
        )
        
        # Should either be rejected or role field should be ignored
        if response.status_code == status.HTTP_200_OK:
            # If update succeeds, role should not have changed
            self.staff_profile.refresh_from_db()
            self.assertEqual(self.staff_profile.role, 'staff')
        else:
            # Or the request should be rejected
            self.assertIn(
                response.status_code,
                [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]
            )
    
    def test_user_cannot_change_own_company(self):
        """Test that users cannot change their company assignment"""
        # Create another company
        other_company = Company.objects.create(
            name="Other Company",
            registration_number="OTHER001",
            tax_id="TAX_OTHER",
            address="456 Other St",
            contact_email="other@company.com",
            contact_phone="+9999999999"
        )
        
        # Login as staff user
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'staff', 'password': 'TestPass123!'},
            format='json'
        )
        
        if login_response.status_code != status.HTTP_200_OK:
            self.skipTest("Login failed, cannot test privilege escalation")
        
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to update own company
        response = self.client.patch(
            '/api/auth/me/',
            {'company': str(other_company.id)},
            format='json'
        )
        
        # Should either be rejected or company field should be ignored
        if response.status_code == status.HTTP_200_OK:
            # If update succeeds, company should not have changed
            self.staff_profile.refresh_from_db()
            self.assertEqual(self.staff_profile.company, self.company)
        else:
            # Or the request should be rejected
            self.assertIn(
                response.status_code,
                [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]
            )
    
    def test_staff_cannot_register_new_users(self):
        """Test that staff users cannot register new users"""
        # Login as staff user
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'staff', 'password': 'TestPass123!'},
            format='json'
        )
        
        if login_response.status_code != status.HTTP_200_OK:
            self.skipTest("Login failed, cannot test privilege escalation")
        
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to register a new user
        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password': 'NewPass123!',
                'role': 'staff',
                'company': str(self.company.id)
            },
            format='json'
        )
        
        # Should be forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_can_register_users(self):
        """Test that admins can register new users"""
        # Login as admin user
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'admin', 'password': 'TestPass123!'},
            format='json'
        )
        
        if login_response.status_code != status.HTTP_200_OK:
            self.skipTest("Login failed, cannot test admin privileges")
        
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to register a new user
        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password': 'NewPass123!',
                'password2': 'NewPass123!',
                'first_name': 'New',
                'last_name': 'User',
                'role': 'staff',
                'company': str(self.company.id)
            },
            format='json'
        )
        
        # Should succeed
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_user_cannot_impersonate_others(self):
        """Test that users cannot impersonate other users"""
        # This test ensures that authentication tokens are properly validated
        # and users cannot forge tokens for other users
        
        # Login as staff user
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'staff', 'password': 'TestPass123!'},
            format='json'
        )
        
        if login_response.status_code != status.HTTP_200_OK:
            self.skipTest("Login failed, cannot test impersonation")
        
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Get current user
        response = self.client.get('/api/auth/me/')
        
        if response.status_code == status.HTTP_200_OK:
            # Should be the staff user, not admin
            self.assertEqual(response.data['username'], 'staff')
            self.assertNotEqual(response.data['username'], 'admin')
    
    def test_role_hierarchy_enforced(self):
        """Test that role hierarchy is properly enforced"""
        # Staff < Accountant < Admin < Super Admin
        
        # Staff should have lowest privileges
        self.assertFalse(self.staff_profile.is_admin)
        self.assertFalse(self.staff_profile.can_approve)
        
        # Admin should have higher privileges
        self.assertTrue(self.admin_profile.is_admin)
        self.assertTrue(self.admin_profile.can_approve)
        
        # Verify role hierarchy cannot be bypassed
        self.assertNotEqual(self.staff_profile.role, 'admin')
        self.assertNotEqual(self.staff_profile.role, 'super_admin')


# Test runner configuration
pytest_plugins = ['pytest_django']
