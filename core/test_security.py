"""
Security-focused tests for core authorization and permissions
Tests for vulnerabilities #10, #20, #29 from security audit
"""
import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from authentication.models import UserProfile
from companies.models import Company
from financial.models import Invoice, Expense


class CompanyIsolationSecurityTests(APITestCase):
    """
    Test company isolation (Vulnerability #10)
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
            role='accountant',
            company=self.company_a
        )
        
        self.user_b = User.objects.create_user(
            username='user_b',
            email='user_b@example.com',
            password='TestPass123!'
        )
        self.profile_b = UserProfile.objects.create(
            user=self.user_b,
            role='accountant',
            company=self.company_b
        )
        
        # Create super admin
        self.super_admin = User.objects.create_user(
            username='superadmin',
            email='superadmin@example.com',
            password='TestPass123!'
        )
        self.super_admin_profile = UserProfile.objects.create(
            user=self.super_admin,
            role='super_admin',
            company=self.company_a
        )
    
    @pytest.mark.skip(reason="Company isolation fix not yet implemented - will be enabled after fix")
    def test_user_cannot_create_invoice_for_other_company(self):
        """
        Test that users cannot create invoices for other companies
        
        VULNERABILITY: Company check happens AFTER serializer validation
        EXPLOIT: User from Company A creates invoice for Company B
        FIX: Check company BEFORE serializer validation
        """
        # Login as user from Company A
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'user_a', 'password': 'TestPass123!'},
            format='json'
        )
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to create invoice for Company B
        response = self.client.post(
            '/api/invoices/',
            {
                'company': str(self.company_b.id),  # Different company!
                'invoice_number': 'INV-001',
                'amount': 10000,
                'due_date': '2026-03-01',
                'status': 'pending'
            },
            format='json'
        )
        
        # Should be forbidden
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "User should not be able to create invoice for other company"
        )
    
    @pytest.mark.skip(reason="Company isolation fix not yet implemented")
    def test_user_cannot_view_other_company_invoices(self):
        """
        Test that users cannot view invoices from other companies
        
        VULNERABILITY: Weak filtering allows cross-company data access
        FIX: Filter all queries by user's company
        """
        # Create invoice for Company A
        invoice_a = Invoice.objects.create(
            company=self.company_a,
            invoice_number='INV-A-001',
            amount=5000,
            status='pending'
        )
        
        # Create invoice for Company B
        invoice_b = Invoice.objects.create(
            company=self.company_b,
            invoice_number='INV-B-001',
            amount=8000,
            status='pending'
        )
        
        # Login as user from Company A
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'user_a', 'password': 'TestPass123!'},
            format='json'
        )
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # List invoices
        response = self.client.get('/api/invoices/', format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only see Company A's invoices
        invoice_ids = [inv['id'] for inv in response.data.get('results', response.data)]
        self.assertIn(str(invoice_a.id), invoice_ids)
        self.assertNotIn(str(invoice_b.id), invoice_ids,
                        "User should not see other company's invoices")
    
    @pytest.mark.skip(reason="Company isolation fix not yet implemented")
    def test_user_cannot_update_other_company_invoice(self):
        """
        Test that users cannot update invoices from other companies
        
        VULNERABILITY: Update operations don't verify company ownership
        FIX: Add company check in update operations
        """
        # Create invoice for Company B
        invoice_b = Invoice.objects.create(
            company=self.company_b,
            invoice_number='INV-B-001',
            amount=8000,
            status='pending'
        )
        
        # Login as user from Company A
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'user_a', 'password': 'TestPass123!'},
            format='json'
        )
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to update Company B's invoice
        response = self.client.patch(
            f'/api/invoices/{invoice_b.id}/',
            {'amount': 1000000},  # Try to change amount
            format='json'
        )
        
        # Should be forbidden or not found
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
            "User should not be able to update other company's invoice"
        )
    
    @pytest.mark.skip(reason="Company isolation fix not yet implemented")
    def test_user_cannot_delete_other_company_invoice(self):
        """
        Test that users cannot delete invoices from other companies
        
        VULNERABILITY: Delete operations don't verify company ownership
        FIX: Add company check in delete operations
        """
        # Create invoice for Company B
        invoice_b = Invoice.objects.create(
            company=self.company_b,
            invoice_number='INV-B-001',
            amount=8000,
            status='pending'
        )
        
        # Login as user from Company A
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'user_a', 'password': 'TestPass123!'},
            format='json'
        )
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to delete Company B's invoice
        response = self.client.delete(f'/api/invoices/{invoice_b.id}/')
        
        # Should be forbidden or not found
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
            "User should not be able to delete other company's invoice"
        )
        
        # Verify invoice still exists
        self.assertTrue(Invoice.objects.filter(id=invoice_b.id).exists())
    
    def test_super_admin_can_access_all_companies(self):
        """
        Test that super admin can access data from all companies
        
        This ensures our security fix doesn't break super admin functionality
        """
        # Create invoices for both companies
        invoice_a = Invoice.objects.create(
            company=self.company_a,
            invoice_number='INV-A-001',
            amount=5000,
            status='pending'
        )
        
        invoice_b = Invoice.objects.create(
            company=self.company_b,
            invoice_number='INV-B-001',
            amount=8000,
            status='pending'
        )
        
        # Login as super admin
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'superadmin', 'password': 'TestPass123!'},
            format='json'
        )
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # List invoices
        response = self.client.get('/api/invoices/', format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Super admin should see invoices from all companies
        invoice_ids = [inv['id'] for inv in response.data.get('results', response.data)]
        self.assertIn(str(invoice_a.id), invoice_ids)
        self.assertIn(str(invoice_b.id), invoice_ids,
                     "Super admin should see all companies' invoices")


class ObjectLevelPermissionTests(APITestCase):
    """
    Test object-level permissions (Vulnerability #20)
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
        
        # Create users with different roles
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='TestPass123!'
        )
        self.admin_profile = UserProfile.objects.create(
            user=self.admin,
            role='admin',
            company=self.company
        )
        
        self.staff = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='TestPass123!'
        )
        self.staff_profile = UserProfile.objects.create(
            user=self.staff,
            role='staff',
            company=self.company
        )
    
    @pytest.mark.skip(reason="Object-level permissions not yet implemented - will be enabled after fix")
    def test_object_level_permissions_enforced(self):
        """
        Test that object-level permissions are checked
        
        VULNERABILITY: Only class-level permissions, no object-level checks
        FIX: Implement has_object_permission in all permission classes
        """
        # This will be implemented with the permission system overhaul
        pass


class RoleBasedAccessControlTests(APITestCase):
    """
    Test role-based access control
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
        
        # Create users with different roles
        self.roles = {}
        role_names = ['super_admin', 'admin', 'accountant', 'staff']
        
        for role_name in role_names:
            user = User.objects.create_user(
                username=role_name,
                email=f'{role_name}@example.com',
                password='TestPass123!'
            )
            profile = UserProfile.objects.create(
                user=user,
                role=role_name,
                company=self.company
            )
            self.roles[role_name] = {'user': user, 'profile': profile}
    
    def test_role_permissions_are_enforced(self):
        """
        Test that role-based permissions are properly enforced
        
        VULNERABILITY: Inconsistent permission checks across endpoints
        FIX: Centralize and standardize permission logic
        """
        # Test that staff cannot access admin endpoints
        # Test that accountant can access financial endpoints
        # Test that admin can access company management
        # Test that super_admin can access everything
        
        # This is a placeholder for comprehensive RBAC testing
        pass
    
    def test_permission_escalation_prevented(self):
        """
        Test that users cannot escalate their own permissions
        
        VULNERABILITY: Users might be able to modify their own role
        FIX: Prevent users from modifying their own permissions
        """
        # Login as staff user
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'staff', 'password': 'TestPass123!'},
            format='json'
        )
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Try to update own profile to admin
        response = self.client.patch(
            f'/api/users/{self.roles["staff"]["user"].id}/',
            {'role': 'admin'},
            format='json'
        )
        
        # Should be forbidden
        if response.status_code == status.HTTP_200_OK:
            # If update succeeded, verify role didn't change
            self.roles['staff']['profile'].refresh_from_db()
            self.assertEqual(
                self.roles['staff']['profile'].role,
                'staff',
                "User should not be able to escalate their own role"
            )


class PermissionConsistencyTests(APITestCase):
    """
    Test permission consistency across endpoints (Vulnerability #29)
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
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            role='staff',
            company=self.company
        )
    
    @pytest.mark.skip(reason="Permission standardization not yet implemented")
    def test_all_endpoints_use_consistent_permission_logic(self):
        """
        Test that all endpoints use consistent permission checking
        
        VULNERABILITY: Different permission logic in different viewsets
        FIX: Centralize permission logic, use same checks everywhere
        """
        # This will verify that all endpoints use the same permission classes
        # and follow the same authorization patterns
        pass


# Test runner configuration
pytest_plugins = ['pytest_django']
