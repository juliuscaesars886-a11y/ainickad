"""
Unit tests for TaskService.

Tests cover task creation, updates, completion, and approval workflows.
"""

import pytest
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth import get_user_model

from workflows.models import Task
from workflows.services import TaskService
from companies.models import Company
from core.exceptions import (
    ValidationError,
    PermissionError,
    BusinessLogicError,
)

User = get_user_model()


@pytest.mark.django_db
class TestTaskServiceCreate:
    """Tests for TaskService.create_task"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            registration_number='REG123',
            tax_id='TAX12345',
            address='123 Test St',
            contact_email='test@company.com',
            contact_phone='555-0000'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            full_name='Admin User',
            company=self.company,
            role='admin'
        )
        
        self.regular_user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            full_name='Regular User',
            company=self.company,
            role='staff'
        )
        
        self.assignee = User.objects.create_user(
            email='assignee@test.com',
            password='testpass123',
            full_name='Assignee User',
            company=self.company,
            role='staff'
        )

    def test_create_task_success(self):
        """Test successful task creation by admin"""
        data = {
            'title': 'Test Task',
            'description': 'Test Description',
            'priority': 'high',
            'company': self.company,
            'assignee': self.assignee,
            'due_date': timezone.now() + timezone.timedelta(days=7)
        }
        
        task = TaskService.create_task(self.admin_user, data)
        
        assert task.title == 'Test Task'
        assert task.creator == self.admin_user
        assert task.assignee == self.assignee
        assert task.status == 'pending'

    def test_create_task_regular_user_own_company(self):
        """Test regular user can create task for own company"""
        data = {
            'title': 'Test Task',
            'description': 'Test Description',
            'priority': 'high',
            'company': self.company,
            'assignee': self.assignee,
            'due_date': timezone.now() + timezone.timedelta(days=7)
        }
        
        task = TaskService.create_task(self.regular_user, data)
        
        assert task.creator == self.regular_user
        assert task.company == self.company

    def test_create_task_regular_user_different_company(self):
        """Test regular user cannot create task for different company"""
        other_company = Company.objects.create(
            name='Other Company',
            registration_number='REG456',
            tax_id='TAX54321',
            address='456 Other St',
            contact_email='other@company.com',
            contact_phone='555-1111'
        )
        
        data = {
            'title': 'Test Task',
            'description': 'Test Description',
            'priority': 'high',
            'company': other_company,
            'assignee': self.assignee,
            'due_date': timezone.now() + timezone.timedelta(days=7)
        }
        
        with pytest.raises(PermissionError):
            TaskService.create_task(self.regular_user, data)

    def test_create_task_unauthenticated_user(self):
        """Test user without company cannot create task"""
        # This test is actually testing a user without a company, not an unauthenticated user
        # because is_authenticated is always True for UserProfile instances
        user_no_company = User.objects.create_user(
            email='nocompany@test.com',
            password='testpass123',
            full_name='No Company User',
            role='staff'
        )
        
        data = {
            'title': 'Test Task',
            'company': self.company,
            'assignee': self.assignee,
        }
        
        with pytest.raises(ValidationError):
            TaskService.create_task(user_no_company, data)

    def test_create_task_no_company_assigned(self):
        """Test user without company cannot create task"""
        user_no_company = User.objects.create_user(
            email='nocompany@test.com',
            password='testpass123',
            full_name='No Company User',
            role='staff'
        )
        
        data = {
            'title': 'Test Task',
            'company': self.company,
            'assignee': self.assignee,
        }
        
        with pytest.raises(ValidationError):
            TaskService.create_task(user_no_company, data)


@pytest.mark.django_db
class TestTaskServiceUpdate:
    """Tests for TaskService.update_task"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            registration_number='REG123',
            tax_id='TAX12345',
            address='123 Test St',
            contact_email='test@company.com',
            contact_phone='555-0000'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            full_name='Admin User',
            company=self.company,
            role='admin'
        )
        
        self.creator = User.objects.create_user(
            email='creator@test.com',
            password='testpass123',
            full_name='Creator User',
            company=self.company,
            role='staff'
        )
        
        self.assignee = User.objects.create_user(
            email='assignee@test.com',
            password='testpass123',
            full_name='Assignee User',
            company=self.company,
            role='staff'
        )
        
        self.task = Task.objects.create(
            title='Test Task',
            description='Test Description',
            priority='high',
            company=self.company,
            creator=self.creator,
            assignee=self.assignee,
            status='pending',
            due_date=timezone.now() + timezone.timedelta(days=7)
        )

    def test_update_task_by_creator(self):
        """Test creator can update task"""
        data = {'title': 'Updated Title'}
        
        updated_task = TaskService.update_task(self.task, self.creator, data)
        
        assert updated_task.title == 'Updated Title'

    def test_update_task_by_assignee(self):
        """Test assignee can update task"""
        data = {'status': 'in_progress'}
        
        updated_task = TaskService.update_task(self.task, self.assignee, data)
        
        assert updated_task.status == 'in_progress'

    def test_update_task_by_admin(self):
        """Test admin can update task"""
        data = {'title': 'Admin Updated'}
        
        updated_task = TaskService.update_task(self.task, self.admin_user, data)
        
        assert updated_task.title == 'Admin Updated'

    def test_update_task_unauthorized_user(self):
        """Test unauthorized user cannot update task"""
        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            full_name='Other User',
            company=self.company,
            role='staff'
        )
        
        data = {'title': 'Unauthorized Update'}
        
        with pytest.raises(PermissionError):
            TaskService.update_task(self.task, other_user, data)


@pytest.mark.django_db
class TestTaskServiceComplete:
    """Tests for TaskService.complete_task"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            registration_number='REG123',
            tax_id='TAX12345',
            address='123 Test St',
            contact_email='test@company.com',
            contact_phone='555-0000'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            full_name='Admin User',
            company=self.company,
            role='admin'
        )
        
        self.creator = User.objects.create_user(
            email='creator@test.com',
            password='testpass123',
            full_name='Creator User',
            company=self.company,
            role='staff'
        )
        
        self.assignee = User.objects.create_user(
            email='assignee@test.com',
            password='testpass123',
            full_name='Assignee User',
            company=self.company,
            role='staff'
        )
        
        self.task = Task.objects.create(
            title='Test Task',
            description='Test Description',
            priority='high',
            company=self.company,
            creator=self.creator,
            assignee=self.assignee,
            status='in_progress',
            due_date=timezone.now() + timezone.timedelta(days=7)
        )

    def test_complete_task_by_assignee(self):
        """Test assignee can complete task"""
        data = {'notes': 'Task completed successfully'}
        
        completed_task = TaskService.complete_task(self.task, self.assignee, data)
        
        assert completed_task.status == 'completed'
        assert completed_task.completed_at is not None
        assert completed_task.metadata['pending_approval'] is True

    def test_complete_task_by_admin(self):
        """Test admin can directly complete task"""
        data = {'notes': 'Admin completed'}
        
        completed_task = TaskService.complete_task(self.task, self.admin_user, data)
        
        assert completed_task.status == 'completed'
        assert completed_task.completed_at is not None

    def test_complete_task_unauthorized_user(self):
        """Test unauthorized user cannot complete task"""
        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            full_name='Other User',
            company=self.company,
            role='staff'
        )
        
        data = {'notes': 'Unauthorized completion'}
        
        with pytest.raises(PermissionError):
            TaskService.complete_task(self.task, other_user, data)

    def test_complete_task_idempotent(self):
        """Test completing already completed task is idempotent"""
        self.task.status = 'completed'
        self.task.completed_at = timezone.now()
        self.task.save()
        
        data = {'notes': 'Already completed'}
        
        result = TaskService.complete_task(self.task, self.assignee, data)
        
        assert result.status == 'completed'


@pytest.mark.django_db
class TestTaskServiceApproval:
    """Tests for TaskService approval methods"""

    def setup_method(self):
        """Set up test data"""
        self.company = Company.objects.create(
            name='Test Company',
            registration_number='REG123',
            tax_id='TAX12345',
            address='123 Test St',
            contact_email='test@company.com',
            contact_phone='555-0000'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            full_name='Admin User',
            company=self.company,
            role='admin'
        )
        
        self.creator = User.objects.create_user(
            email='creator@test.com',
            password='testpass123',
            full_name='Creator User',
            company=self.company,
            role='staff'
        )
        
        self.assignee = User.objects.create_user(
            email='assignee@test.com',
            password='testpass123',
            full_name='Assignee User',
            company=self.company,
            role='staff'
        )
        
        self.task = Task.objects.create(
            title='Test Task',
            description='Test Description',
            priority='high',
            company=self.company,
            creator=self.creator,
            assignee=self.assignee,
            status='completed',
            completed_at=timezone.now(),
            due_date=timezone.now() + timezone.timedelta(days=7),
            metadata={'pending_approval': True}
        )

    def test_approve_completion_success(self):
        """Test admin can approve task completion"""
        approved_task = TaskService.approve_completion(self.task, self.admin_user)
        
        assert approved_task.status == 'approved'
        assert approved_task.metadata['pending_approval'] is False
        assert 'approved_by' in approved_task.metadata

    def test_approve_completion_unauthorized(self):
        """Test non-admin cannot approve task"""
        with pytest.raises(PermissionError):
            TaskService.approve_completion(self.task, self.assignee)

    def test_reject_completion_success(self):
        """Test admin can reject task completion"""
        data = {'reason': 'Work not complete'}
        
        rejected_task = TaskService.reject_completion(self.task, self.admin_user, data)
        
        assert rejected_task.status == 'rejected'
        assert rejected_task.metadata['pending_approval'] is False
        assert rejected_task.metadata['rejection_reason'] == 'Work not complete'

    def test_reject_completion_unauthorized(self):
        """Test non-admin cannot reject task"""
        data = {'reason': 'Work not complete'}
        
        with pytest.raises(PermissionError):
            TaskService.reject_completion(self.task, self.assignee, data)
