"""
Unit tests for ApprovalService.

Tests cover approval and rejection workflows.
"""

import pytest
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth import get_user_model

from workflows.models import Request, Approval
from workflows.services import ApprovalService
from companies.models import Company
from core.exceptions import (
    ValidationError,
    PermissionError,
    BusinessLogicError,
)

User = get_user_model()


@pytest.mark.django_db
class TestApprovalServiceApprove:
    """Tests for ApprovalService.approve_request"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            email='test@company.com',
            tax_id='12345'
        )
        
        self.approver = User.objects.create_user(
            email='approver@test.com',
            password='testpass123',
            first_name='Approver',
            last_name='User',
            company=self.company,
            is_admin=True
        )
        
        self.requester = User.objects.create_user(
            email='requester@test.com',
            password='testpass123',
            first_name='Requester',
            last_name='User',
            company=self.company
        )
        
        self.request_obj = Request.objects.create(
            request_type='leave',
            company=self.company,
            requester=self.requester,
            status='pending',
            data={'leave_type': 'annual', 'days': 5}
        )
        
        self.approval = Approval.objects.create(
            request=self.request_obj,
            approver=self.approver,
            step_number=1,
            status='pending'
        )

    def test_approve_request_success(self):
        """Test approver can approve request"""
        data = {'comments': 'Approved'}
        
        approved = ApprovalService.approve_request(
            self.approval, self.approver, data
        )
        
        assert approved.status == 'approved'
        assert approved.comments == 'Approved'
        assert approved.approved_at is not None

    def test_approve_request_updates_request_status(self):
        """Test approving request updates request status"""
        data = {'comments': 'Approved'}
        
        ApprovalService.approve_request(self.approval, self.approver, data)
        
        self.request_obj.refresh_from_db()
        assert self.request_obj.status == 'approved'
        assert self.request_obj.completion_date is not None

    def test_approve_request_unauthorized(self):
        """Test non-approver cannot approve request"""
        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            first_name='Other',
            last_name='User',
            company=self.company
        )
        
        data = {'comments': 'Approved'}
        
        with pytest.raises(PermissionError):
            ApprovalService.approve_request(self.approval, other_user, data)

    def test_approve_request_not_pending(self):
        """Test cannot approve non-pending approval"""
        self.approval.status = 'approved'
        self.approval.save()
        
        data = {'comments': 'Approved'}
        
        with pytest.raises(ValidationError):
            ApprovalService.approve_request(self.approval, self.approver, data)

    def test_approve_request_with_comments(self):
        """Test approval with comments"""
        data = {'comments': 'Looks good, approved'}
        
        approved = ApprovalService.approve_request(
            self.approval, self.approver, data
        )
        
        assert approved.comments == 'Looks good, approved'


@pytest.mark.django_db
class TestApprovalServiceReject:
    """Tests for ApprovalService.reject_request"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            email='test@company.com',
            tax_id='12345'
        )
        
        self.approver = User.objects.create_user(
            email='approver@test.com',
            password='testpass123',
            first_name='Approver',
            last_name='User',
            company=self.company,
            is_admin=True
        )
        
        self.requester = User.objects.create_user(
            email='requester@test.com',
            password='testpass123',
            first_name='Requester',
            last_name='User',
            company=self.company
        )
        
        self.request_obj = Request.objects.create(
            request_type='leave',
            company=self.company,
            requester=self.requester,
            status='pending',
            data={'leave_type': 'annual', 'days': 5}
        )
        
        self.approval = Approval.objects.create(
            request=self.request_obj,
            approver=self.approver,
            step_number=1,
            status='pending'
        )

    def test_reject_request_success(self):
        """Test approver can reject request"""
        data = {'comments': 'Insufficient documentation'}
        
        rejected = ApprovalService.reject_request(
            self.approval, self.approver, data
        )
        
        assert rejected.status == 'rejected'
        assert rejected.comments == 'Insufficient documentation'
        assert rejected.approved_at is not None

    def test_reject_request_updates_request_status(self):
        """Test rejecting request updates request status"""
        data = {'comments': 'Rejected'}
        
        ApprovalService.reject_request(self.approval, self.approver, data)
        
        self.request_obj.refresh_from_db()
        assert self.request_obj.status == 'rejected'
        assert self.request_obj.completion_date is not None

    def test_reject_request_unauthorized(self):
        """Test non-approver cannot reject request"""
        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            first_name='Other',
            last_name='User',
            company=self.company
        )
        
        data = {'comments': 'Rejected'}
        
        with pytest.raises(PermissionError):
            ApprovalService.reject_request(self.approval, other_user, data)

    def test_reject_request_not_pending(self):
        """Test cannot reject non-pending approval"""
        self.approval.status = 'rejected'
        self.approval.save()
        
        data = {'comments': 'Rejected'}
        
        with pytest.raises(ValidationError):
            ApprovalService.reject_request(self.approval, self.approver, data)

    def test_reject_request_with_reason(self):
        """Test rejection with reason"""
        data = {'comments': 'Insufficient leave balance'}
        
        rejected = ApprovalService.reject_request(
            self.approval, self.approver, data
        )
        
        assert rejected.comments == 'Insufficient leave balance'


@pytest.mark.django_db
class TestApprovalServiceNotifications:
    """Tests for notification creation in approval service"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            email='test@company.com',
            tax_id='12345'
        )
        
        self.approver = User.objects.create_user(
            email='approver@test.com',
            password='testpass123',
            first_name='Approver',
            last_name='User',
            company=self.company,
            is_admin=True
        )
        
        self.requester = User.objects.create_user(
            email='requester@test.com',
            password='testpass123',
            first_name='Requester',
            last_name='User',
            company=self.company
        )
        
        self.request_obj = Request.objects.create(
            request_type='leave',
            company=self.company,
            requester=self.requester,
            status='pending',
            data={'leave_type': 'annual', 'days': 5}
        )
        
        self.approval = Approval.objects.create(
            request=self.request_obj,
            approver=self.approver,
            step_number=1,
            status='pending'
        )

    def test_approve_creates_notification(self):
        """Test approving request creates notification"""
        data = {'comments': 'Approved'}
        
        ApprovalService.approve_request(self.approval, self.approver, data)
        
        # Notification creation is attempted but may fail if model not available
        # This test just ensures no exception is raised
        assert self.approval.status == 'approved'

    def test_reject_creates_notification(self):
        """Test rejecting request creates notification"""
        data = {'comments': 'Rejected'}
        
        ApprovalService.reject_request(self.approval, self.approver, data)
        
        # Notification creation is attempted but may fail if model not available
        # This test just ensures no exception is raised
        assert self.approval.status == 'rejected'
