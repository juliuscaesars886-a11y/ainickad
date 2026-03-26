"""
Simple Preservation Tests for Company Risk Fields Fix

These tests verify core preservation requirements without complex API interactions.
"""
import uuid
from django.test import TestCase
from authentication.models import UserProfile
from .models import Company


class SimplePreservationTest(TestCase):
    """
    Simple preservation tests that verify core requirements
    """
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a test company for admin user
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
    
    def test_settings_field_does_not_contain_risk_fields(self):
        """
        Test that risk_level and risk_category are NOT in settings JSON
        
        Validates: Requirement 3.6 - settings JSON preserves other data,
        risk fields are in model fields not JSON
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
        
        company = Company.objects.create(
            name='Settings Test Company',
            registration_number=f'REG{unique_suffix}',
            tax_id=f'TAX{unique_suffix}',
            address='789 Settings Street',
            contact_email=f'settings{unique_suffix}@example.com',
            contact_phone='+254766666666',
            risk_level='level_1',
            risk_category='private_limited',
            settings=settings_data
        )
        
        # Verify settings data is preserved
        self.assertEqual(company.settings['date_incorporated'], '2020-01-15')
        self.assertEqual(company.settings['shareholders'], ['John Doe', 'Jane Smith'])
        self.assertEqual(company.settings['shareCapital'], 1000000)
        self.assertEqual(company.settings['companyType'], 'Limited')
        self.assertEqual(company.settings['compliance_status'], 'compliant')
        
        # Verify risk fields are NOT in settings
        self.assertNotIn('risk_level', company.settings)
        self.assertNotIn('risk_category', company.settings)
        
        # Verify risk fields are in model fields
        self.assertEqual(company.risk_level, 'level_1')
        self.assertEqual(company.risk_category, 'private_limited')
    
    def test_all_company_fields_work_correctly(self):
        """
        Test that all company fields work correctly
        
        Validates: Requirement 3.1 - All other Company model fields continue to work
        """
        unique_suffix = str(uuid.uuid4())[:8]
        
        company = Company.objects.create(
            name='Complete Fields Company',
            registration_number=f'REG{unique_suffix}',
            tax_id=f'TAX{unique_suffix}',
            address='123 Complete Street, Nairobi',
            contact_email=f'complete{unique_suffix}@example.com',
            contact_phone='+254711222333',
            logo_url='https://example.com/logo.png',
            settings={
                'date_incorporated': '2021-05-20',
                'companyType': 'Private Limited'
            },
            is_active=True,
            risk_level='level_2',
            risk_category='private_limited'
        )
        
        # Verify all fields
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
    
    def test_registration_number_uniqueness(self):
        """
        Test that duplicate registration_number is prevented
        
        Validates: Requirement 3.2 - registration_number uniqueness validation
        """
        unique_suffix = str(uuid.uuid4())[:8]
        registration_number = f'REG{unique_suffix}'
        
        # Create first company
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
        with self.assertRaises(Exception):  # Will raise IntegrityError
            Company.objects.create(
                name='Second Company',
                registration_number=registration_number,  # Duplicate!
                tax_id=f'TAX{unique_suffix}2',
                address='456 Second Street',
                contact_email=f'second{unique_suffix}@example.com',
                contact_phone='+254733333333',
                risk_level='level_1',
                risk_category='retail_clients'
            )
    
    def test_tax_id_uniqueness(self):
        """
        Test that duplicate tax_id is prevented
        
        Validates: Requirement 3.3 - tax_id uniqueness validation
        """
        unique_suffix = str(uuid.uuid4())[:8]
        tax_id = f'TAX{unique_suffix}'
        
        # Create first company
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
        with self.assertRaises(Exception):  # Will raise IntegrityError
            Company.objects.create(
                name='Second Company',
                registration_number=f'REG{unique_suffix}2',
                tax_id=tax_id,  # Duplicate!
                address='456 Second Street',
                contact_email=f'second{unique_suffix}@example.com',
                contact_phone='+254755555555',
                risk_level='level_2',
                risk_category='financial_institutions'
            )
    
    def test_company_update_preserves_risk_fields(self):
        """
        Test that updating other fields doesn't affect risk fields
        
        Validates: Requirement 3.5 - Company updates work correctly
        """
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
        company.name = 'Updated Name'
        company.address = 'Updated Address'
        company.save()
        
        # Refresh from database
        company.refresh_from_db()
        
        # Verify updates
        self.assertEqual(company.name, 'Updated Name')
        self.assertEqual(company.address, 'Updated Address')
        
        # Verify risk fields unchanged
        self.assertEqual(company.risk_level, 'level_2')
        self.assertEqual(company.risk_category, 'retail_clients')
