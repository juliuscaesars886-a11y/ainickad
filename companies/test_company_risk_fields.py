"""
Bug Condition Exploration Test for Company Risk Fields

This test demonstrates the bug where creating companies with risk_level and 
risk_category fields fails with a NOT NULL constraint violation.

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

The test encodes the expected behavior - it will validate the fix when it passes 
after implementation.
"""
import uuid
from hypothesis import given, strategies as st, settings as hypothesis_settings
from hypothesis.extra.django import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from authentication.models import UserProfile
from .models import Company


# Strategy for generating valid company names
company_name_strategy = st.text(
    min_size=3,
    max_size=50,
    alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 '
).filter(lambda x: x.strip() != '')

# Strategy for generating valid risk levels
risk_level_strategy = st.sampled_from(['level_1', 'level_2', 'level_3'])

# Strategy for generating valid risk categories
risk_category_strategy = st.sampled_from([
    'private_limited',
    'retail_clients',
    'financial_institutions',
    'cash_intensive'
])

# Strategy for generating valid email addresses
# Using a simpler strategy to avoid slow generation
# Only use lowercase letters and numbers for the local part
email_strategy = st.text(
    min_size=5,
    max_size=20,
    alphabet='abcdefghijklmnopqrstuvwxyz0123456789'
).map(lambda x: f'{x}@example.com')

# Strategy for generating valid phone numbers
phone_strategy = st.text(
    min_size=10,
    max_size=20,
    alphabet=st.characters(whitelist_categories=('Nd',))
).map(lambda x: f'+254{x[:9]}')

# Strategy for generating valid addresses
address_strategy = st.text(
    min_size=10,
    max_size=100,
    alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ,'
).filter(lambda x: x.strip() != '')


class CompanyRiskFieldsBugExplorationTest(TestCase):
    """
    Property 1: Fault Condition - Company Creation with Risk Fields Fails on Unfixed Code
    
    CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists
    
    For any POST request to /api/companies/ with risk_level and risk_category in the 
    request body, the unfixed code will fail with psycopg.errors.NotNullViolation 
    because the serializer pops these fields and stores them in the JSON settings 
    field instead of passing them to the model, causing the ORM to send NULL values 
    to the database columns which have NOT NULL constraints.
    
    After the fix is implemented, this test will pass, confirming that risk_level 
    and risk_category are properly stored in their respective database columns.
    
    Validates: Requirements 2.1, 2.2, 2.3
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
            contact_phone='+254700000000'
        )
        
        self.super_admin = UserProfile.objects.create(
            email=f'superadmin{unique_suffix}@example.com',
            full_name='Super Admin',
            role='super_admin',
            company=self.test_company
        )
        
        # Authenticate as super admin
        self.client.force_authenticate(user=self.super_admin)
    
    @hypothesis_settings(max_examples=20, deadline=None)
    @given(
        name=company_name_strategy,
        risk_level=risk_level_strategy,
        risk_category=risk_category_strategy,
        contact_email=email_strategy,
        contact_phone=phone_strategy,
        address=address_strategy
    )
    def test_company_creation_with_risk_fields(
        self, name, risk_level, risk_category, contact_email, contact_phone, address
    ):
        """
        Property 1: Company creation with risk_level and risk_category should succeed
        
        EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS with psycopg.errors.NotNullViolation
        EXPECTED OUTCOME ON FIXED CODE: Test PASSES with 201 Created response
        
        This test encodes the expected behavior after the fix:
        - Response status code should be 201 (Created)
        - Response should contain company ID
        - company.risk_level should match input value
        - company.risk_category should match input value
        - 'risk_level' should NOT be in company.settings (should be in model field)
        - 'risk_category' should NOT be in company.settings (should be in model field)
        """
        # Generate unique identifiers
        unique_suffix = str(uuid.uuid4())[:8]
        registration_number = f'REG{unique_suffix}'
        tax_id = f'TAX{unique_suffix}'
        
        # Prepare request data
        company_data = {
            'name': name,
            'registration_number': registration_number,
            'tax_id': tax_id,
            'address': address,
            'contact_email': contact_email,
            'contact_phone': contact_phone,
            'risk_level': risk_level,
            'risk_category': risk_category
        }
        
        # Make POST request to create company
        response = self.client.post('/api/companies/', company_data, format='json')
        
        # ASSERTION 1: Response status code should be 201 (Created)
        # ON UNFIXED CODE: This will fail with 500 Internal Server Error
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"Expected 201 Created, got {response.status_code}. "
            f"Response data: {response.data if hasattr(response, 'data') else 'N/A'}"
        )
        
        # ASSERTION 2: Response should contain company ID
        self.assertIn('id', response.data)
        company_id = response.data['id']
        
        # Retrieve the created company from database
        company = Company.objects.get(id=company_id)
        
        # ASSERTION 3: company.risk_level should match input value
        # ON UNFIXED CODE: This field doesn't exist on the model
        self.assertEqual(
            company.risk_level,
            risk_level,
            f"Expected risk_level={risk_level}, got {company.risk_level}"
        )
        
        # ASSERTION 4: company.risk_category should match input value
        # ON UNFIXED CODE: This field doesn't exist on the model
        self.assertEqual(
            company.risk_category,
            risk_category,
            f"Expected risk_category={risk_category}, got {company.risk_category}"
        )
        
        # ASSERTION 5: 'risk_level' should NOT be in company.settings
        # (should be in model field, not JSON)
        self.assertNotIn(
            'risk_level',
            company.settings,
            "risk_level should be stored in model field, not in settings JSON"
        )
        
        # ASSERTION 6: 'risk_category' should NOT be in company.settings
        # (should be in model field, not JSON)
        self.assertNotIn(
            'risk_category',
            company.settings,
            "risk_category should be stored in model field, not in settings JSON"
        )
    
    def test_company_creation_level_1_private_limited(self):
        """
        Specific test case: Level 1 risk with private_limited category
        
        EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS with NOT NULL violation
        """
        unique_suffix = str(uuid.uuid4())[:8]
        
        company_data = {
            'name': 'Acme Corporation',
            'registration_number': f'REG{unique_suffix}',
            'tax_id': f'TAX{unique_suffix}',
            'address': '123 Main Street, Nairobi',
            'contact_email': f'info{unique_suffix}@acme.com',
            'contact_phone': '+254700111222',
            'risk_level': 'level_1',
            'risk_category': 'private_limited'
        }
        
        response = self.client.post('/api/companies/', company_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        
        company = Company.objects.get(id=response.data['id'])
        self.assertEqual(company.risk_level, 'level_1')
        self.assertEqual(company.risk_category, 'private_limited')
        self.assertNotIn('risk_level', company.settings)
        self.assertNotIn('risk_category', company.settings)
    
    def test_company_creation_level_2_retail_clients(self):
        """
        Specific test case: Level 2 risk with retail_clients category
        
        EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS with NOT NULL violation
        """
        unique_suffix = str(uuid.uuid4())[:8]
        
        company_data = {
            'name': 'Beta Retail Ltd',
            'registration_number': f'REG{unique_suffix}',
            'tax_id': f'TAX{unique_suffix}',
            'address': '456 Oak Avenue, Mombasa',
            'contact_email': f'contact{unique_suffix}@beta.com',
            'contact_phone': '+254711333444',
            'risk_level': 'level_2',
            'risk_category': 'retail_clients'
        }
        
        response = self.client.post('/api/companies/', company_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        
        company = Company.objects.get(id=response.data['id'])
        self.assertEqual(company.risk_level, 'level_2')
        self.assertEqual(company.risk_category, 'retail_clients')
        self.assertNotIn('risk_level', company.settings)
        self.assertNotIn('risk_category', company.settings)
    
    def test_company_creation_level_3_cash_intensive(self):
        """
        Specific test case: Level 3 risk with cash_intensive category
        
        EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS with NOT NULL violation
        """
        unique_suffix = str(uuid.uuid4())[:8]
        
        company_data = {
            'name': 'Gamma Cash Services',
            'registration_number': f'REG{unique_suffix}',
            'tax_id': f'TAX{unique_suffix}',
            'address': '789 Pine Road, Kisumu',
            'contact_email': f'hello{unique_suffix}@gamma.com',
            'contact_phone': '+254722555666',
            'risk_level': 'level_3',
            'risk_category': 'cash_intensive'
        }
        
        response = self.client.post('/api/companies/', company_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        
        company = Company.objects.get(id=response.data['id'])
        self.assertEqual(company.risk_level, 'level_3')
        self.assertEqual(company.risk_category, 'cash_intensive')
        self.assertNotIn('risk_level', company.settings)
        self.assertNotIn('risk_category', company.settings)
    
    def test_company_creation_financial_institutions(self):
        """
        Specific test case: Financial institutions risk category
        
        EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS with NOT NULL violation
        """
        unique_suffix = str(uuid.uuid4())[:8]
        
        company_data = {
            'name': 'Delta Financial Group',
            'registration_number': f'REG{unique_suffix}',
            'tax_id': f'TAX{unique_suffix}',
            'address': '101 Finance Street, Nairobi',
            'contact_email': f'info{unique_suffix}@delta.com',
            'contact_phone': '+254733777888',
            'risk_level': 'level_2',
            'risk_category': 'financial_institutions'
        }
        
        response = self.client.post('/api/companies/', company_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        
        company = Company.objects.get(id=response.data['id'])
        self.assertEqual(company.risk_level, 'level_2')
        self.assertEqual(company.risk_category, 'financial_institutions')
        self.assertNotIn('risk_level', company.settings)
        self.assertNotIn('risk_category', company.settings)
