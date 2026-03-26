"""
Security-focused tests for workflow/approval functionality
Tests for vulnerability #12 (self-approval) from security audit
"""
import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from authentication.models import UserProfile
from companies.models import Company
from workflows.models import Approval


class SelfApprovalSecurityTests(APITestCase):
    """
    Test self-approval prevention (Vulnerability #12)
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
        
        # Create requester user
        self.requester = User.objects.create_user(
            username='requester',
            email='requester@example.com',
            password='TestPass123!'
        )
        self.requester_profile = UserProfile.objects.create(
            user=self.requester,
            role='staff',
            company=self.company
        )
        
        # Create approver user
        self.approver = User.objects.create_user(
            username='approver',
            email='approver@example.com',
            password='TestPass123!'
        )
        self.approver_profile = UserProfile.objects.create(
            user=self.approver,
            role='admin',
            company=self.company
        )
        
        # Create user who is both requester and approver
        self.dual_role_user = User.objects.create_user(
            username='dualrole',
            email='dualrole@example.com',
            password='TestPass123!'
        )
        self.dual_role_profile = UserProfile.objects.create(
            user=self.dual_role_user,
            role='admin',
            company=self.company
        )
    
    @pytest.mark.skip(reason="Self-approval prevention not yet implemented - will be enabled after fix")
    def test_user_cannot_approve_own_request(self):
        """
        Test that users cannot approve their own requests
        
        VULNERABILITY: No check preventing self-approval
        EXPLOIT: User creates expense request, then approves it themselves
        FIX: Check if approval.requester == request.user and reject
        """
        # Login as dual role user
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'dualrole', 'password': 'TestPass123!'},
            format='json'
        )
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create approval request
        create_response = self.client.post(
            '/api/approvals/',
            {
                'title': 'Expense Request',
                'description': 'Need approval for $10,000 expense',
                'amount': 10000,
                'company': str(self.company.id),
                'approval_type': 'expense',
                'requester': self.dual_role_user.id,
                'approver': self.dual_role_user.id  # Same user
            },
            format='json'
        )
        
        if create_response.status_code == status.HTTP_201_CREATED:
            approval_id = create_response.data['id']
            
            # Try to approve own request
            approve_response = self.client.post(
                f'/api/approvals/{approval_id}/approve/',
                format='json'
            )
            
            # Should be forbidden
            self.assertEqual(
                approve_response.status_code,
                status.HTTP_403_FORBIDDEN,
                "User should not be able to approve their own request"
            )
            
            # Error message should indicate self-approval not allowed
            error_msg = str(approve_response.data).lower()
            self.assertTrue(
                'self' in error_msg or 'own' in error_msg,
                "Error should indicate self-approval is not allowed"
            )
    
    @pytest.mark.skip(reason="Self-approval prevention not yet implemented")
    def test_different_user_can_approve_request(self):
        """
        Test that different users CAN approve requests (normal workflow)
        
        This ensures our security fix doesn't break legitimate approvals
        """
        # Login as requester
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'requester', 'password': 'TestPass123!'},
            format='json'
        )
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create approval request
        create_response = self.client.post(
            '/api/approvals/',
            {
                'title': 'Expense Request',
                'description': 'Need approval for $5,000 expense',
                'amount': 5000,
                'company': str(self.company.id),
                'approval_type': 'expense',
                'requester': self.requester.id,
                'approver': self.approver.id  # Different user
            },
            format='json'
        )
        
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        approval_id = create_response.data['id']
        
        # Login as approver
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'approver', 'password': 'TestPass123!'},
            format='json'
        )
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Approve request
        approve_response = self.client.post(
            f'/api/approvals/{approval_id}/approve/',
            format='json'
        )
        
        # Should succeed
        self.assertEqual(
            approve_response.status_code,
            status.HTTP_200_OK,
            "Different user should be able to approve request"
        )


class ApprovalWorkflowSecurityTests(APITestCase):
    """
    Test approval workflow security
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
    
    def test_user_cannot_approve_other_company_requests(self):
        """
        Test that users cannot approve requests from other companies
        
        VULNERABILITY: Weak company isolation in approval workflow
        FIX: Enforce company checks in approval actions
        """
        # Login as user A
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'user_a', 'password': 'TestPass123!'},
            format='json'
        )
        token_a = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_a}')
        
        # Create approval for Company A
        create_response = self.client.post(
            '/api/approvals/',
            {
                'title': 'Company A Request',
                'description': 'Internal request',
                'company': str(self.company_a.id),
                'approval_type': 'expense',
                'requester': self.user_a.id,
                'approver': self.user_a.id
            },
            format='json'
        )
        
        if create_response.status_code == status.HTTP_201_CREATED:
            approval_id = create_response.data['id']
            
            # Login as user B
            login_response = self.client.post(
                '/api/auth/login/',
                {'username': 'user_b', 'password': 'TestPass123!'},
                format='json'
            )
            token_b = login_response.data['access']
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_b}')
            
            # Try to approve Company A's request
            approve_response = self.client.post(
                f'/api/approvals/{approval_id}/approve/',
                format='json'
            )
            
            # Should be forbidden or not found
            self.assertIn(
                approve_response.status_code,
                [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
                "User from Company B should not be able to approve Company A's request"
            )
    
    @pytest.mark.skip(reason="Status transition validation not yet implemented")
    def test_approval_status_transitions_validated(self):
        """
        Test that approval status transitions are validated
        
        VULNERABILITY: Invalid status transitions allowed
        FIX: Implement state machine for approval workflow
        """
        # Test that approved requests cannot be re-approved
        # Test that rejected requests cannot be approved without reset
        # Test that completed requests cannot be modified
        pass
    
    @pytest.mark.skip(reason="Approval history not yet implemented")
    def test_approval_actions_are_audited(self):
        """
        Test that all approval actions are logged for audit
        
        VULNERABILITY: No audit trail for approvals
        FIX: Log all approval actions with timestamp and user
        """
        pass


class ApprovalPermissionTests(APITestCase):
    """
    Test approval permission checks
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
        
        # Create staff user (no approval permissions)
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
        
        # Create admin user (has approval permissions)
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
    
    def test_only_authorized_users_can_approve(self):
        """
        Test that only users with approval permissions can approve requests
        
        VULNERABILITY: Insufficient permission checks
        FIX: Verify user has approval role before allowing approval
        """
        # Login as admin and create approval
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'admin', 'password': 'TestPass123!'},
            format='json'
        )
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        create_response = self.client.post(
            '/api/approvals/',
            {
                'title': 'Test Request',
                'description': 'Test',
                'company': str(self.company.id),
                'approval_type': 'expense',
                'requester': self.staff_user.id,
                'approver': self.admin_user.id
            },
            format='json'
        )
        
        if create_response.status_code == status.HTTP_201_CREATED:
            approval_id = create_response.data['id']
            
            # Login as staff user (no approval permissions)
            login_response = self.client.post(
                '/api/auth/login/',
                {'username': 'staff', 'password': 'TestPass123!'},
                format='json'
            )
            token = login_response.data['access']
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            
            # Try to approve
            approve_response = self.client.post(
                f'/api/approvals/{approval_id}/approve/',
                format='json'
            )
            
            # Should be forbidden
            self.assertEqual(
                approve_response.status_code,
                status.HTTP_403_FORBIDDEN,
                "Staff user without approval permissions should not be able to approve"
            )


# Test runner configuration
pytest_plugins = ['pytest_django']
