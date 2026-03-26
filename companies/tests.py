"""
Tests for companies app
"""
import uuid
from django.db import IntegrityError
from hypothesis import given, strategies as st, settings as hypothesis_settings
from hypothesis.extra.django import TestCase
from .models import Company
from authentication.models import UserProfile


class CompanyModelPropertyTest(TestCase):
    """
    Property 3: Model Field Persistence (Company)
    Property 7: Uniqueness Constraint Enforcement
    
    For any Django model instance with valid data, when saved to the database,
    all required fields should be persisted and retrievable with identical values.
    
    For any model field with uniqueness constraints (registration_number, tax_id),
    the Django backend should enforce uniqueness and reject duplicate values with
    appropriate error messages.
    
    Validates: Requirements 3.1, 3.2, 3.5
    """
    
    @hypothesis_settings(max_examples=30, deadline=None)
    @given(
        name=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cs',))),
        address=st.text(min_size=1, max_size=200, alphabet=st.characters(blacklist_categories=('Cs',))),
        contact_email=st.emails(),
        contact_phone=st.text(min_size=10, max_size=20, alphabet=st.characters(whitelist_categories=('Nd',)))
    )
    def test_company_field_persistence(self, name, address, contact_email, contact_phone):
        """
        Property 3: All required fields should be persisted and retrievable
        """
        company_id = uuid.uuid4()
        unique_suffix = str(uuid.uuid4())[:8]
        registration_number = f'REG{unique_suffix}'
        tax_id = f'TAX{unique_suffix}'
        logo_url = 'https://example.com/logo.png'
        settings = {'currency': 'KES', 'timezone': 'Africa/Nairobi'}
        
        # Create company
        company = Company.objects.create(
            id=company_id,
            name=name,
            registration_number=registration_number,
            tax_id=tax_id,
            address=address,
            contact_email=contact_email,
            contact_phone=contact_phone,
            logo_url=logo_url,
            settings=settings,
            is_active=True
        )
        
        # Retrieve from database
        retrieved = Company.objects.get(id=company_id)
        
        # Verify all fields match
        self.assertEqual(str(retrieved.id), str(company_id))
        self.assertEqual(retrieved.name, name)
        self.assertEqual(retrieved.registration_number, registration_number)
        self.assertEqual(retrieved.tax_id, tax_id)
        self.assertEqual(retrieved.address, address)
        self.assertEqual(retrieved.contact_email, contact_email)
        self.assertEqual(retrieved.contact_phone, contact_phone)
        self.assertEqual(retrieved.logo_url, logo_url)
        self.assertEqual(retrieved.settings, settings)
        self.assertTrue(retrieved.is_active)
    
    def test_registration_number_uniqueness_constraint(self):
        """
        Property 7: registration_number must be unique
        """
        unique_suffix = str(uuid.uuid4())[:8]
        registration_number = f'REG{unique_suffix}'
        
        # Create first company
        Company.objects.create(
            name='Company 1',
            registration_number=registration_number,
            tax_id=f'TAX{unique_suffix}1',
            address='Address 1',
            contact_email='company1@example.com',
            contact_phone='1234567890'
        )
        
        # Try to create second company with same registration_number
        with self.assertRaises(IntegrityError):
            Company.objects.create(
                name='Company 2',
                registration_number=registration_number,  # Duplicate
                tax_id=f'TAX{unique_suffix}2',
                address='Address 2',
                contact_email='company2@example.com',
                contact_phone='0987654321'
            )
    
    def test_tax_id_uniqueness_constraint(self):
        """
        Property 7: tax_id must be unique
        """
        unique_suffix = str(uuid.uuid4())[:8]
        tax_id = f'TAX{unique_suffix}'
        
        # Create first company
        Company.objects.create(
            name='Company 1',
            registration_number=f'REG{unique_suffix}1',
            tax_id=tax_id,
            address='Address 1',
            contact_email='company1@example.com',
            contact_phone='1234567890'
        )
        
        # Try to create second company with same tax_id
        with self.assertRaises(IntegrityError):
            Company.objects.create(
                name='Company 2',
                registration_number=f'REG{unique_suffix}2',
                tax_id=tax_id,  # Duplicate
                address='Address 2',
                contact_email='company2@example.com',
                contact_phone='0987654321'
            )
    
    def test_company_helper_methods(self):
        """
        Test company helper methods work correctly
        """
        unique_suffix = str(uuid.uuid4())[:8]
        company = Company.objects.create(
            name='Test Company',
            registration_number=f'REG{unique_suffix}',
            tax_id=f'TAX{unique_suffix}',
            address='Test Address',
            contact_email='test@company.com',
            contact_phone='1234567890'
        )
        
        # Initially no employees or documents
        self.assertFalse(company.has_active_employees())
        self.assertFalse(company.has_documents())


class CompanyFilteringPropertyTest(TestCase):
    """
    Property 8: Company-Based Data Filtering
    
    For any user with a company association, when querying company data,
    the Django backend should return only data associated with that user's company,
    unless the user is a super admin who can see all companies.
    
    Validates: Requirements 3.4
    """
    
    def setUp(self):
        """Set up test fixtures"""
        # Create multiple companies
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
        
        # Create users with different roles
        self.super_admin = UserProfile.objects.create(
            email=f'superadmin{unique_id1}@example.com',
            full_name='Super Admin',
            role='super_admin',
            company=self.company1
        )
        
        self.admin_company1 = UserProfile.objects.create(
            email=f'admin1{unique_id1}@example.com',
            full_name='Admin Company 1',
            role='admin',
            company=self.company1
        )
        
        self.employee_company2 = UserProfile.objects.create(
            email=f'employee2{unique_id2}@example.com',
            full_name='Employee Company 2',
            role='employee',
            company=self.company2
        )
    
    def test_super_admin_sees_all_companies(self):
        """
        Property 8: Super admins should see all companies
        """
        from .views import CompanyViewSet
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/api/companies/')
        request.user = self.super_admin
        
        viewset = CompanyViewSet()
        viewset.request = request
        queryset = viewset.get_queryset()
        
        # Super admin should see both companies
        self.assertEqual(queryset.count(), 2)
        self.assertIn(self.company1, queryset)
        self.assertIn(self.company2, queryset)
    
    def test_regular_user_sees_only_own_company(self):
        """
        Property 8: Regular users should see only their own company
        """
        from .views import CompanyViewSet
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/api/companies/')
        request.user = self.employee_company2
        
        viewset = CompanyViewSet()
        viewset.request = request
        queryset = viewset.get_queryset()
        
        # Employee should see only their company
        self.assertEqual(queryset.count(), 1)
        self.assertIn(self.company2, queryset)
        self.assertNotIn(self.company1, queryset)
    
    def test_user_without_company_sees_nothing(self):
        """
        Property 8: Users without a company should see no companies
        """
        from .views import CompanyViewSet
        from django.test import RequestFactory
        
        unique_id = str(uuid.uuid4())[:8]
        user_no_company = UserProfile.objects.create(
            email=f'nocompany{unique_id}@example.com',
            full_name='No Company User',
            role='employee',
            company=None
        )
        
        factory = RequestFactory()
        request = factory.get('/api/companies/')
        request.user = user_no_company
        
        viewset = CompanyViewSet()
        viewset.request = request
        queryset = viewset.get_queryset()
        
        # User without company should see nothing
        self.assertEqual(queryset.count(), 0)


class CompanyReferentialIntegrityTest(TestCase):
    """
    Property 6: Referential Integrity Protection
    
    For any entity with foreign key relationships, when the referenced entity
    is deleted, the Django backend should either cascade delete dependent entities
    or prevent deletion with appropriate error messages.
    
    Validates: Requirements 3.2
    """
    
    def setUp(self):
        """Set up test fixtures"""
        unique_suffix = str(uuid.uuid4())[:8]
        self.company = Company.objects.create(
            name='Test Company',
            registration_number=f'REG{unique_suffix}',
            tax_id=f'TAX{unique_suffix}',
            address='Test Address',
            contact_email='test@company.com',
            contact_phone='1234567890'
        )
    
    def test_deleting_company_cascades_to_users(self):
        """
        Property 6: Deleting a company should cascade delete associated users
        """
        # Create user associated with company
        user = UserProfile.objects.create(
            email='user@example.com',
            full_name='Test User',
            role='employee',
            company=self.company
        )
        
        user_id = user.id
        
        # Delete company
        self.company.delete()
        
        # User should be deleted (CASCADE)
        self.assertFalse(UserProfile.objects.filter(id=user_id).exists())
    
    def test_company_deletion_with_no_dependencies(self):
        """
        Property 6: Company without dependencies can be deleted
        """
        company_id = self.company.id
        
        # Delete company
        self.company.delete()
        
        # Company should be deleted
        self.assertFalse(Company.objects.filter(id=company_id).exists())
