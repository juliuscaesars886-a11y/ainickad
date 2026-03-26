"""
Preservation Property Tests for Company Risk Fields Fix

These tests verify that existing company operations remain unchanged after the fix.
They test operations that do NOT involve creating companies with risk fields.

Property 2: Preservation - Existing Company Operations Unchanged

IMPORTANT: These tests should PASS on both unfixed and fixed code, confirming
that the fix does not introduce regressions.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""
import uuid
from hypothesis import given, strategies as st, settings as hypothesis_settings
from hypothesis.extra.django import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from authentication.models import UserProfile
from .models import Company, Director


# Strategies for generating test data
company_name_strategy = st.text(
    min_size=3,
    max_size=50,
    alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 '
).filter(lambda x: x.strip() != '')

email_strategy = st.text(
    min_size=5,
    max_size=20,
    alphabet='abcdefghijklmnopqrstuvwxyz0123456789'
).map(lambda x: f'{x}@example.com')

phone_strategy = st.text(
    min_size=9,
    max_size=9,
    alphabet='0123456789'
).map(lambda x: f'+254{x}')

address_strategy = st.text(
    min_size=10,
    max_size=100,
    alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ,'
).filter(lambda x: x.strip() != '')


class CompanyPreservationTest(TestCase):
    """
    Property 2: Preservation - Existing Company Operations Unchanged
    
    These tests verify that operations NOT involving company creation with risk
    fields continue to work exactly as before the fix.
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        
        # Create a super admin user for authentication
        unique_suffix = str(uuid.uuid4())[:8]
        self.test_company = Company.objects.create(
            name='Test Admin Company',
            registration_number=f'ADMIN{unique_suffix}',
            tax_id=f'TAXADMIN{unique_suffix}',
            address='Admin Address',
            contact_email=f'admin{unique_suffix}@example.com',
            contact_phone='+254700000000',
            risk_level='level_2',
            risk_category='private_limited'
        )
        
        self.super_admin = UserProfile.objects.create(
            email=f'superadmin{unique_suffix}@example.com',
            full_name='Super Admin',
            role='super_admin',
            company=self.test_company
        )
        
        # Authenticate as super admin
        self.client.force_authenticate(user=self.super_admin)
    
    def test_company_retrieval_basic(self):
        """
        Test that GET /api/companies/ returns companies correctly
        
        Validates: Requirement 3.4 - Company retrieval continues to work
        """
        # Create a test company
        unique_suffix = str(uuid.uuid4())[:8]
        company = Company.objects.create(
            name='Test Retrieval Company',
            registration_number=f'REG{unique_suffix}',
            tax_id=f'TAX{unique_suffix}',
            address='123 Test Street',
            contact_email=f'test{unique_suffix}@example.com',
            contact_phone='+254711111111',
            risk_level='level_1',
            risk_category='retail_clients'
        )
        
        # Retrieve companies
        response = self.client.get('/api/companies/')
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        
        # Find our company in the results
        company_found = False
        for result_company in response.data['results']:
            if result_company['id'] == company.id:
                company_found = True
                self.assertEqual(result_company['name'], 'Test Retrieval Company')
                self.assertEqual(result_company['registration_number'], f'REG{unique_suffix}')
                break
        
        self.assertTrue(company_found, "Created company should be in the results")
    
    def test_registration_number_uniqueness_validation(self):
        """
        Test that duplicate registration_number raises ValidationError
        
        Validates: Requirement 3.2 - registration_number uniqueness validation
        """
        # Create first company
        unique_suffix = str(uuid.uuid4())[:8]
        registration_number = f'REG{unique_suffix}'
        
        Company.objects.create(
            name='First Company',
            registration_number=registration_number,
            tax_id=f'TAX{unique_suffix}1',
            address='123 First Street',
            contact_email=f'first{unique_suffix}@example.com',
            contact_phone='+254722222222',
            risk_level='level_2',
            risk_category='private_limited'
        )
        
        # Try to create second company with same registration_number
        company_data = {
            'name': 'Second Company',
            'registration_number': registration_number,  # Duplicate!
            'tax_id': f'TAX{unique_suffix}2',
            'address': '456 Second Street',
            'contact_email': f'second{unique_suffix}@example.com',
            'contact_phone': '+254733333333',
            'risk_level': 'level_1',
            'risk_category': 'retail_clients'
        }
        
        response = self.client.post('/api/companies/', company_data, format='json')
        
        # Should fail with 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('registration_number', response.data['detail'])
    
    def test_tax_id_uniqueness_validation(self):
        """
        Test that duplicate tax_id raises ValidationError
        
        Validates: Requirement 3.3 - tax_id uniqueness validation
        """
        # Create first company
        unique_suffix = str(uuid.uuid4())[:8]
        tax_id = f'TAX{unique_suffix}'
        
        Company.objects.create(
            name='First Company',
            registration_number=f'REG{unique_suffix}1',
            tax_id=tax_id,
            address='123 First Street',
            contact_email=f'first{unique_suffix}@example.com',
            contact_phone='+254744444444',
            risk_level='level_3',
            risk_category='cash_intensive'
        )
        
        # Try to create second company with same tax_id
        company_data = {
            'name': 'Second Company',
            'registration_number': f'REG{unique_suffix}2',
            'tax_id': tax_id,  # Duplicate!
            'address': '456 Second Street',
            'contact_email': f'second{unique_suffix}@example.com',
            'contact_phone': '+254755555555',
            'risk_level': 'level_2',
            'risk_category': 'financial_institutions'
        }
        
        response = self.client.post('/api/companies/', company_data, format='json')
        
        # Should fail with 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tax_id', response.data['detail'])
    
    def test_settings_field_preservation(self):
        """
        Test that other settings data is stored correctly in JSON field
        
        Validates: Requirement 3.6 - settings JSON field preserves other data
        """
        unique_suffix = str(uuid.uuid4())[:8]
        
        # Create company with settings data
        settings_data = {
            'date_incorporated': '2020-01-15',
            'shareholders': ['John Doe', 'Jane Smith'],
            'shareCapital': 1000000,
            'companyType': 'Limited',
            'compliance_status': 'compliant'
        }
        
        company_data = {
            'name': 'Settings Test Company',
            'registration_number': f'REG{unique_suffix}',
            'tax_id': f'TAX{unique_suffix}',
            'address': '789 Settings Street',
            'contact_email': f'settings{unique_suffix}@example.com',
            'contact_phone': '+254766666666',
            'risk_level': 'level_1',
            'risk_category': 'private_limited',
            'settings': settings_data
        }
        
        response = self.client.post('/api/companies/', company_data, format='json')
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Retrieve company and verify settings
        company = Company.objects.get(id=response.data['id'])
        self.assertEqual(company.settings['date_incorporated'], '2020-01-15')
        self.assertEqual(company.settings['shareholders'], ['John Doe', 'Jane Smith'])
        self.assertEqual(company.settings['shareCapital'], 1000000)
        self.assertEqual(company.settings['companyType'], 'Limited')
        self.assertEqual(company.settings['compliance_status'], 'compliant')
        
        # Verify risk fields are NOT in settings
        self.assertNotIn('risk_level', company.settings)
        self.assertNotIn('risk_category', company.settings)
    
    def test_company_update_preservation(self):
        """
        Test that PUT/PATCH updates work correctly
        
        Validates: Requirement 3.5 - Company updates continue to work
        """
        # Create a company
        unique_suffix = str(uuid.uuid4())[:8]
        company = Company.objects.create(
            name='Original Name',
            registration_number=f'REG{unique_suffix}',
            tax_id=f'TAX{unique_suffix}',
            address='Original Address',
            contact_email=f'original{unique_suffix}@example.com',
            contact_phone='+254777777777',
            risk_level='level_2',
            risk_category='retail_clients'
        )
        
        # Update the company
        update_data = {
            'name': 'Updated Name',
            'address': 'Updated Address'
        }
        
        response = self.client.patch(f'/api/companies/{company.id}/', update_data, format='json')
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify updates
        company.refresh_from_db()
        self.assertEqual(company.name, 'Updated Name')
        self.assertEqual(company.address, 'Updated Address')
        
        # Verify other fields unchanged
        self.assertEqual(company.registration_number, f'REG{unique_suffix}')
        self.assertEqual(company.tax_id, f'TAX{unique_suffix}')
        self.assertEqual(company.risk_level, 'level_2')
        self.assertEqual(company.risk_category, 'retail_clients')
    
    def test_director_operations_preservation(self):
        """
        Test that Director model operations are unaffected
        
        Validates: Requirement 3.1 - Director operations remain unchanged
        """
        # Create a company
        unique_suffix = str(uuid.uuid4())[:8]
        company = Company.objects.create(
            name='Director Test Company',
            registration_number=f'REG{unique_suffix}',
            tax_id=f'TAX{unique_suffix}',
            address='Director Test Address',
            contact_email=f'director{unique_suffix}@example.com',
            contact_phone='+254788888888',
            risk_level='level_3',
            risk_category='financial_institutions'
        )
        
        # Create a director
        director_data = {
            'company': company.id,
            'full_name': 'John Director',
            'id_number': f'ID{unique_suffix}',
            'email': f'john{unique_suffix}@example.com',
            'phone': '+254799999999',
            'address': 'Director Address',
            'appointment_date': '2020-01-01'
        }
        
        response = self.client.post('/api/directors/', director_data, format='json')
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['full_name'], 'John Director')
        self.assertEqual(response.data['company'], company.id)
        
        # Verify director was created
        director = Director.objects.get(id=response.data['id'])
        self.assertEqual(director.full_name, 'John Director')
        self.assertEqual(director.company.id, company.id)
    
    @hypothesis_settings(max_examples=10, deadline=None)
    @given(
        name=company_name_strategy,
        contact_email=email_strategy,
        contact_phone=phone_strategy,
        address=address_strategy
    )
    def test_company_retrieval_property(self, name, contact_email, contact_phone, address):
        """
        Property test: Company retrieval returns all expected fields
        
        Validates: Requirement 3.4 - CompanyListSerializer returns expected fields
        """
        # Create a company
        unique_suffix = str(uuid.uuid4())[:8]
        company = Company.objects.create(
            name=name,
            registration_number=f'REG{unique_suffix}',
            tax_id=f'TAX{unique_suffix}',
            address=address,
            contact_email=contact_email,
            contact_phone=contact_phone,
            risk_level='level_1',
            risk_category='private_limited'
        )
        
        # Retrieve companies
        response = self.client.get('/api/companies/')
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        
        # Find our company
        company_found = False
        for result_company in response.data['results']:
            if result_company['id'] == company.id:
                company_found = True
                self.assertEqual(result_company['name'], name)
                self.assertEqual(result_company['registration_number'], f'REG{unique_suffix}')
                self.assertEqual(result_company['address'], address)
                break
        
        self.assertTrue(company_found)
    
    @hypothesis_settings(max_examples=10, deadline=None)
    @given(
        name=company_name_strategy,
        address=address_strategy
    )
    def test_company_update_property(self, name, address):
        """
        Property test: Company updates work correctly without affecting other fields
        
        Validates: Requirement 3.5 - CompanyUpdateSerializer works correctly
        """
        # Create a company
        unique_suffix = str(uuid.uuid4())[:8]
        original_reg = f'REG{unique_suffix}'
        original_tax = f'TAX{unique_suffix}'
        
        company = Company.objects.create(
            name='Original',
            registration_number=original_reg,
            tax_id=original_tax,
            address='Original Address',
            contact_email=f'test{unique_suffix}@example.com',
            contact_phone='+254700000001',
            risk_level='level_2',
            risk_category='retail_clients'
        )
        
        # Update the company
        update_data = {
            'name': name,
            'address': address
        }
        
        response = self.client.patch(f'/api/companies/{company.id}/', update_data, format='json')
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify updates
        company.refresh_from_db()
        self.assertEqual(company.name, name)
        self.assertEqual(company.address, address)
        
        # Verify other fields unchanged
        self.assertEqual(company.registration_number, original_reg)
        self.assertEqual(company.tax_id, original_tax)
        self.assertEqual(company.risk_level, 'level_2')
        self.assertEqual(company.risk_category, 'retail_clients')


class CompanyOtherFieldsPreservationTest(TestCase):
    """
    Additional preservation tests for other company fields
    
    Validates: Requirement 3.1 - All other Company model fields continue to work
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        
        # Create a super admin user for authentication
        unique_suffix = str(uuid.uuid4())[:8]
        self.test_company = Company.objects.create(
            name='Test Admin Company',
            registration_number=f'ADMIN{unique_suffix}',
            tax_id=f'TAXADMIN{unique_suffix}',
            address='Admin Address',
            contact_email=f'admin{unique_suffix}@example.com',
            contact_phone='+254700000000',
            risk_level='level_2',
            risk_category='private_limited'
        )
        
        self.super_admin = UserProfile.objects.create(
            email=f'superadmin{unique_suffix}@example.com',
            full_name='Super Admin',
            role='super_admin',
            company=self.test_company
        )
        
        # Authenticate as super admin
        self.client.force_authenticate(user=self.super_admin)
    
    def test_all_company_fields_preserved(self):
        """
        Test that all company fields (name, registration_number, tax_id, address,
        contact_email, contact_phone, logo_url, settings, is_active) work correctly
        
        Validates: Requirement 3.1 - All other Company model fields continue to work
        """
        unique_suffix = str(uuid.uuid4())[:8]
        
        company_data = {
            'name': 'Complete Fields Company',
            'registration_number': f'REG{unique_suffix}',
            'tax_id': f'TAX{unique_suffix}',
            'address': '123 Complete Street, Nairobi',
            'contact_email': f'complete{unique_suffix}@example.com',
            'contact_phone': '+254711222333',
            'logo_url': 'https://example.com/logo.png',
            'settings': {
                'date_incorporated': '2021-05-20',
                'companyType': 'Private Limited'
            },
            'is_active': True,
            'risk_level': 'level_2',
            'risk_category': 'private_limited'
        }
        
        response = self.client.post('/api/companies/', company_data, format='json')
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify all fields
        company = Company.objects.get(id=response.data['id'])
        self.assertEqual(company.name, 'Complete Fields Company')
        self.assertEqual(company.registration_number, f'REG{unique_suffix}')
        self.assertEqual(company.tax_id, f'TAX{unique_suffix}')
        self.assertEqual(company.address, '123 Complete Street, Nairobi')
        self.assertEqual(company.contact_email, f'complete{unique_suffix}@example.com')
        self.assertEqual(company.contact_phone, '+254711222333')
        self.assertEqual(company.logo_url, 'https://example.com/logo.png')
        self.assertEqual(company.settings['date_incorporated'], '2021-05-20')
        self.assertEqual(company.settings['companyType'], 'Private Limited')
        self.assertTrue(company.is_active)
        self.assertEqual(company.risk_level, 'level_2')
        self.assertEqual(company.risk_category, 'private_limited')
