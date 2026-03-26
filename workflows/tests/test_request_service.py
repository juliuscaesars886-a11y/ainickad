"""
Unit tests for RequestService.

Tests cover request creation, submission, and approval workflows.
"""

import pytest
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth import get_user_model

from workflows.models import Request, Approval
from workflows.services import RequestService
from companies.models import Company
from core.exceptions import (
    ValidationError,
    PermissionError,
    BusinessLogicError,
)

User = get_user_model()


@pytest.mark.django_db
class TestRequestServiceCreate:
    """Tests for RequestService.create_request"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            email='test@company.com',
            tax_id='12345'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            company=self.company,
            is_admin=True
        )
        
        self.regular_user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            first_name='Regular',
            last_name='User',
            company=self.company
        )

    def test_create_request_success(self):
        """Test successful request creation"""
        data = {
            'request_type': 'leave',
            'company': self.company,
            'data': {'leave_type': 'annual', 'days': 5}
        }
        
        request_obj = RequestService.create_request(self.regular_user, data)
        
        assert request_obj.request_type == 'leave'
        assert request_obj.requester == self.regular_user
        assert request_obj.status == 'draft'

    def test_create_request_admin(self):
        """Test admin can create request"""
        data = {
            'request_type': 'leave',
            'company': self.company,
            'data': {'leave_type': 'annual', 'days': 5}
        }
        
        request_obj = RequestService.create_request(self.admin_user, data)
        
        assert request_obj.requester == self.admin_user

    def test_create_request_different_company(self):
        """Test user cannot create request for different company"""
        other_company = Company.objects.create(
            name='Other Company',
            email='other@company.com',
            tax_id='54321'
        )
        
        data = {
            'request_type': 'leave',
            'company': other_company,
            'data': {'leave_type': 'annual', 'days': 5}
        }
        
        with pytest.raises(PermissionError):
            RequestService.create_request(self.regular_user, data)

    def test_create_request_no_company(self):
        """Test user without company cannot create request"""
        user_no_company = User.objects.create_user(
            email='nocompany@test.com',
            password='testpass123',
            first_name='No',
            last_name='Company'
        )
        
        data = {
            'request_type': 'leave',
            'company': self.company,
            'data': {'leave_type': 'annual', 'days': 5}
        }
        
        with pytest.raises(ValidationError):
            RequestService.create_request(user_no_company, data)


@pytest.mark.django_db
class TestRequestServiceUpdate:
    """Tests for RequestService.update_request"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            email='test@company.com',
            tax_id='12345'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
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
            status='draft',
            data={'leave_type': 'annual', 'days': 5}
        )

    def test_update_request_success(self):
        """Test requester can update draft request"""
        data = {'data': {'leave_type': 'sick', 'days': 3}}
        
        updated_request = RequestService.update_request(
            self.request_obj, self.requester, data
        )
        
        assert updated_request.data['leave_type'] == 'sick'

    def test_update_request_admin(self):
        """Test admin can update draft request"""
        data = {'data': {'leave_type': 'maternity', 'days': 90}}
        
        updated_request = RequestService.update_request(
            self.request_obj, self.admin_user, data
        )
        
        assert updated_request.data['leave_type'] == 'maternity'

    def test_update_request_not_draft(self):
        """Test cannot update non-draft request"""
        self.request_obj.status = 'pending'
        self.request_obj.save()
        
        data = {'data': {'leave_type': 'sick', 'days': 3}}
        
        with pytest.raises(ValidationError):
            RequestService.update_request(
                self.request_obj, self.requester, data
            )

    def test_update_request_unauthorized(self):
        """Test unauthorized user cannot update request"""
        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            first_name='Other',
            last_name='User',
            company=self.company
        )
        
        data = {'data': {'leave_type': 'sick', 'days': 3}}
        
        with pytest.raises(PermissionError):
            RequestService.update_request(
                self.request_obj, other_user, data
            )


@pytest.mark.django_db
class TestRequestServiceDelete:
    """Tests for RequestService.delete_request"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            email='test@company.com',
            tax_id='12345'
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
            status='draft',
            data={'leave_type': 'annual', 'days': 5}
        )

    def test_delete_request_success(self):
        """Test requester can delete draft request"""
        request_id = self.request_obj.id
        
        RequestService.delete_request(self.request_obj, self.requester)
        
        assert not Request.objects.filter(id=request_id).exists()

    def test_delete_request_not_draft(self):
        """Test cannot delete non-draft request"""
        self.request_obj.status = 'pending'
        self.request_obj.save()
        
        with pytest.raises(ValidationError):
            RequestService.delete_request(self.request_obj, self.requester)

    def test_delete_request_unauthorized(self):
        """Test unauthorized user cannot delete request"""
        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            first_name='Other',
            last_name='User',
            company=self.company
        )
        
        with pytest.raises(PermissionError):
            RequestService.delete_request(self.request_obj, other_user)


@pytest.mark.django_db
class TestRequestServiceSubmit:
    """Tests for RequestService.submit_request"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            email='test@company.com',
            tax_id='12345'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
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
            status='draft',
            data={'leave_type': 'annual', 'days': 5}
        )

    def test_submit_request_success(self):
        """Test requester can submit draft request"""
        submitted_request = RequestService.submit_request(
            self.request_obj, self.requester
        )
        
        assert submitted_request.status == 'pending'
        assert submitted_request.submission_date is not None

    def test_submit_request_admin(self):
        """Test admin can submit request"""
        submitted_request = RequestService.submit_request(
            self.request_obj, self.admin_user
        )
        
        assert submitted_request.status == 'pending'

    def test_submit_request_not_draft(self):
        """Test cannot submit non-draft request"""
        self.request_obj.status = 'pending'
        self.request_obj.save()
        
        with pytest.raises(ValidationError):
            RequestService.submit_request(self.request_obj, self.requester)

    def test_submit_request_unauthorized(self):
        """Test unauthorized user cannot submit request"""
        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            first_name='Other',
            last_name='User',
            company=self.company
        )
        
        with pytest.raises(PermissionError):
            RequestService.submit_request(self.request_obj, other_user)

    def test_submit_request_creates_approvals(self):
        """Test submitting request creates approval records"""
        RequestService.submit_request(self.request_obj, self.requester)
        
        approvals = Approval.objects.filter(request=self.request_obj)
        
        # Should have at least one approval for the admin
        assert approvals.count() >= 1
        assert all(a.status == 'pending' for a in approvals)
