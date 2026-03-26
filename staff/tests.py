"""
Tests for staff app
"""
import uuid
from datetime import date
from decimal import Decimal
from django.db import IntegrityError
from hypothesis import given, strategies as st, settings as hypothesis_settings
from hypothesis.extra.django import TestCase
from .models import Staff
from companies.models import Company
from authentication.models import UserProfile


class StaffModelTest(TestCase):
    """
    Property 3: Model Field Persistence (Staff)
    Property 5: Enum Value Validation (employment_status)
    Property 9: Cross-Entity Validation
    
    Validates: Requirements 4.1, 4.2, 4.3
    """
    
    def setUp(self):
        """Set up test fixtures"""
        unique_id = str(uuid.uuid4())[:8]
        self.company = Company.objects.create(
            name=f'Test Company {unique_id}',
            registration_number=f'REG{unique_id}',
            tax_id=f'TAX{unique_id}',
            address='Test Address',
            contact_email=f'test{unique_id}@company.com',
            contact_phone='1234567890'
        )
    
    def test_staff_field_persistence(self):
        """
        Property 3: All required fields should be persisted and retrievable
        """
        unique_id = str(uuid.uuid4())[:8]
        staff_number = f'STF{unique_id}'
        
        staff = Staff.objects.create(
            staff_number=staff_number,
            company=self.company,
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            job_title='Software Engineer',
            department='Engineering',
            employment_status='active',
            hire_date=date(2024, 1, 1),
            salary=Decimal('75000.00'),
            emergency_contact_name='Jane Doe',
            emergency_contact_phone='0987654321',
            address='123 Main St',
            metadata={'skills': ['Python', 'Django']}
        )
        
        # Retrieve from database
        retrieved = Staff.objects.get(id=staff.id)
        
        # Verify all fields match
        self.assertEqual(retrieved.staff_number, staff_number)
        self.assertEqual(retrieved.company, self.company)
        self.assertEqual(retrieved.first_name, 'John')
        self.assertEqual(retrieved.last_name, 'Doe')
        self.assertEqual(retrieved.full_name, 'John Doe')
        self.assertEqual(retrieved.email, 'john.doe@example.com')
        self.assertEqual(retrieved.job_title, 'Software Engineer')
        self.assertEqual(retrieved.employment_status, 'active')
        self.assertTrue(retrieved.is_active)
        self.assertEqual(retrieved.salary, Decimal('75000.00'))
    
    def test_staff_number_uniqueness(self):
        """
        Property 7: staff_number must be unique
        """
        unique_id = str(uuid.uuid4())[:8]
        staff_number = f'STF{unique_id}'
        
        # Create first staff member
        Staff.objects.create(
            staff_number=staff_number,
            company=self.company,
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            job_title='Engineer',
            hire_date=date(2024, 1, 1)
        )
        
        # Try to create second staff member with same number
        with self.assertRaises(IntegrityError):
            Staff.objects.create(
                staff_number=staff_number,  # Duplicate
                company=self.company,
                first_name='Jane',
                last_name='Smith',
                email='jane@example.com',
                job_title='Manager',
                hire_date=date(2024, 1, 1)
            )
    
    def test_employment_status_choices(self):
        """
        Property 5: Valid employment status values should be accepted
        """
        valid_statuses = ['active', 'on_leave', 'suspended', 'terminated']
        
        for status in valid_statuses:
            unique_id = str(uuid.uuid4())[:8]
            staff = Staff.objects.create(
                staff_number=f'STF{unique_id}',
                company=self.company,
                first_name='Test',
                last_name='User',
                email=f'test{unique_id}@example.com',
                job_title='Tester',
                employment_status=status,
                hire_date=date(2024, 1, 1)
            )
            
            self.assertEqual(staff.employment_status, status)
            retrieved = Staff.objects.get(id=staff.id)
            self.assertEqual(retrieved.employment_status, status)
    
    def test_user_company_association_validation(self):
        """
        Property 9: User's company must match staff member's company
        """
        # Create another company
        unique_id2 = str(uuid.uuid4())[:8]
        company2 = Company.objects.create(
            name=f'Company 2 {unique_id2}',
            registration_number=f'REG{unique_id2}',
            tax_id=f'TAX{unique_id2}',
            address='Address 2',
            contact_email=f'company2{unique_id2}@example.com',
            contact_phone='1234567890'
        )
        
        # Create user in company2
        user = UserProfile.objects.create(
            email=f'user{unique_id2}@example.com',
            full_name='Test User',
            role='employee',
            company=company2
        )
        
        # Try to create staff member in company1 with user from company2
        unique_id = str(uuid.uuid4())[:8]
        with self.assertRaises(ValueError) as context:
            Staff.objects.create(
                staff_number=f'STF{unique_id}',
                user=user,  # User from company2
                company=self.company,  # company1
                first_name='Test',
                last_name='User',
                email='test@example.com',
                job_title='Tester',
                hire_date=date(2024, 1, 1)
            )
        
        self.assertIn('must match', str(context.exception))


class StaffFilteringTest(TestCase):
    """
    Property 8: Company-Based Data Filtering (Staff)
    
    Validates: Requirements 4.4
    """
    
    def setUp(self):
        """Set up test fixtures"""
        # Create two companies
        unique_id1 = str(uuid.uuid4())[:8]
        self.company1 = Company.objects.create(
            name='Company 1',
            registration_number=f'REG{unique_id1}',
            tax_id=f'TAX{unique_id1}',
            address='Address 1',
            contact_email=f'company1{unique_id1}@example.com',
            contact_phone='1234567890'
        )
        
        unique_id2 = str(uuid.uuid4())[:8]
        self.company2 = Company.objects.create(
            name='Company 2',
            registration_number=f'REG{unique_id2}',
            tax_id=f'TAX{unique_id2}',
            address='Address 2',
            contact_email=f'company2{unique_id2}@example.com',
            contact_phone='0987654321'
        )
        
        # Create staff members in each company
        self.staff1 = Staff.objects.create(
            staff_number=f'STF{unique_id1}',
            company=self.company1,
            first_name='John',
            last_name='Doe',
            email='john@company1.com',
            job_title='Engineer',
            hire_date=date(2024, 1, 1)
        )
        
        self.staff2 = Staff.objects.create(
            staff_number=f'STF{unique_id2}',
            company=self.company2,
            first_name='Jane',
            last_name='Smith',
            email='jane@company2.com',
            job_title='Manager',
            hire_date=date(2024, 1, 1)
        )
        
        # Create users
        self.super_admin = UserProfile.objects.create(
            email=f'superadmin{unique_id1}@example.com',
            role='super_admin',
            company=self.company1
        )
        
        self.employee_user = UserProfile.objects.create(
            email=f'employee{unique_id2}@example.com',
            role='employee',
            company=self.company2
        )
    
    def test_super_admin_sees_all_staff(self):
        """Super admins should see all staff members"""
        from .views import StaffViewSet
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/api/staff/')
        request.user = self.super_admin
        
        viewset = StaffViewSet()
        viewset.request = request
        queryset = viewset.get_queryset()
        
        self.assertEqual(queryset.count(), 2)
        self.assertIn(self.staff1, queryset)
        self.assertIn(self.staff2, queryset)
    
    def test_regular_user_sees_only_company_staff(self):
        """Regular users should see only staff members from their company"""
        from .views import StaffViewSet
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/api/staff/')
        request.user = self.employee_user
        
        viewset = StaffViewSet()
        viewset.request = request
        queryset = viewset.get_queryset()
        
        self.assertEqual(queryset.count(), 1)
        self.assertIn(self.staff2, queryset)
        self.assertNotIn(self.staff1, queryset)



class StaffSignalTest(TestCase):
    """
    Tests for automatic staff creation via signals.
    
    Validates: Requirements 1.1, 1.2
    """
    
    def setUp(self):
        """Set up test fixtures"""
        unique_id = str(uuid.uuid4())[:8]
        self.company = Company.objects.create(
            name=f'Test Company {unique_id}',
            registration_number=f'REG{unique_id}',
            tax_id=f'TAX{unique_id}',
            address='Test Address',
            contact_email=f'test{unique_id}@company.com',
            contact_phone='1234567890'
        )
    
    def test_staff_created_on_user_creation(self):
        """
        Test that staff is automatically created when user is created.
        
        Validates: Requirement 1.1 - Automatic Staff Creation
        """
        unique_id = str(uuid.uuid4())[:8]
        user = UserProfile.objects.create(
            email=f'test{unique_id}@example.com',
            full_name='Test User',
            role='employee',
            company=self.company
        )
        
        # Check staff was created
        self.assertTrue(hasattr(user, 'staff'))
        self.assertIsNotNone(user.staff)
        self.assertEqual(user.staff.email, user.email)
        self.assertEqual(user.staff.company, user.company)
        self.assertEqual(user.staff.first_name, 'Test')
        self.assertEqual(user.staff.last_name, 'User')
        self.assertEqual(user.staff.employment_status, 'active')
    
    def test_staff_number_uniqueness(self):
        """
        Test that staff numbers are unique across multiple users.
        
        Validates: Requirement 1.2 - Backend Signal-Based Sync
        """
        staff_numbers = set()
        
        for i in range(10):
            unique_id = str(uuid.uuid4())[:8]
            user = UserProfile.objects.create(
                email=f'test{i}_{unique_id}@example.com',
                full_name=f'Test User {i}',
                role='employee',
                company=self.company
            )
            staff_numbers.add(user.staff.staff_number)
        
        # All staff numbers should be unique
        self.assertEqual(len(staff_numbers), 10)
    
    def test_job_title_mapping_from_role(self):
        """
        Test that job titles are correctly mapped from user roles.
        
        Validates: Requirement 1.1 - Automatic Staff Creation
        """
        role_title_map = {
            'super_admin': 'Super Administrator',
            'admin': 'Administrator',
            'accountant': 'Accountant',
            'employee': 'Staff Member',
        }
        
        for role, expected_title in role_title_map.items():
            unique_id = str(uuid.uuid4())[:8]
            user = UserProfile.objects.create(
                email=f'{role}_{unique_id}@example.com',
                full_name=f'{role.title()} User',
                role=role,
                company=self.company
            )
            
            self.assertEqual(user.staff.job_title, expected_title)
    
    def test_staff_not_created_on_user_update(self):
        """
        Test that staff is not duplicated when user is updated.
        
        Validates: Requirement 1.2 - Idempotency
        """
        unique_id = str(uuid.uuid4())[:8]
        user = UserProfile.objects.create(
            email=f'test{unique_id}@example.com',
            full_name='Test User',
            role='employee',
            company=self.company
        )
        
        original_staff_id = user.staff.id
        
        # Update user
        user.full_name = 'Updated User'
        user.save()
        
        # Staff should not be duplicated
        self.assertEqual(user.staff.id, original_staff_id)
        self.assertEqual(Staff.objects.filter(user=user).count(), 1)
    
    def test_staff_creation_with_no_full_name(self):
        """
        Test that staff is created even when user has no full name.
        
        Validates: Requirement 1.4 - Error Handling
        """
        unique_id = str(uuid.uuid4())[:8]
        user = UserProfile.objects.create(
            email=f'test{unique_id}@example.com',
            full_name='',
            role='employee',
            company=self.company
        )
        
        # Staff should be created with email prefix as first name
        self.assertTrue(hasattr(user, 'staff'))
        self.assertIsNotNone(user.staff.first_name)
        self.assertTrue(user.staff.first_name.startswith('test'))
    
    def test_staff_creation_with_single_name(self):
        """
        Test that staff is created correctly with single name.
        
        Validates: Requirement 1.1 - Automatic Staff Creation
        """
        unique_id = str(uuid.uuid4())[:8]
        user = UserProfile.objects.create(
            email=f'test{unique_id}@example.com',
            full_name='Madonna',
            role='employee',
            company=self.company
        )
        
        # Staff should be created with first name only
        self.assertEqual(user.staff.first_name, 'Madonna')
        self.assertEqual(user.staff.last_name, '')
    
    def test_staff_hire_date_matches_user_creation(self):
        """
        Test that staff hire date matches user creation date.
        
        Validates: Requirement 1.1 - Automatic Staff Creation
        """
        unique_id = str(uuid.uuid4())[:8]
        user = UserProfile.objects.create(
            email=f'test{unique_id}@example.com',
            full_name='Test User',
            role='employee',
            company=self.company
        )
        
        # Hire date should match user creation date
        self.assertEqual(user.staff.hire_date, user.created_at.date())
