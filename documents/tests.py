"""
Tests for documents app
"""
import pytest
import io
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from authentication.models import UserProfile
from companies.models import Company
from .models import Document


@pytest.fixture
def api_client():
    """Create API client"""
    return APIClient()


@pytest.fixture
def company(db):
    """Create test company"""
    return Company.objects.create(
        name='Test Company',
        registration_number='REG001',
        tax_id='TAX001',
        address='123 Test St'
    )


@pytest.fixture
def admin_user(db, company):
    """Create admin user"""
    return UserProfile.objects.create(
        email='admin@test.com',
        full_name='Test Admin',
        role='admin',
        company=company
    )


@pytest.fixture
def employee_user(db, company):
    """Create employee user"""
    return UserProfile.objects.create(
        email='employee@test.com',
        full_name='Test Employee',
        role='employee',
        company=company
    )


@pytest.mark.django_db
class TestDocumentAPI:
    """Test Document API endpoints"""
    
    def test_upload_document(self, api_client, admin_user, company):
        """Test uploading a document"""
        api_client.force_authenticate(user=admin_user)
        
        # Create a test file
        file_content = b'Test file content'
        test_file = SimpleUploadedFile(
            'test_document.pdf',
            file_content,
            content_type='application/pdf'
        )
        
        data = {
            'title': 'Test Document',
            'description': 'A test document',
            'category': 'contract',
            'company': str(company.id),
            'file': test_file
        }
        
        response = api_client.post('/api/documents/', data, format='multipart')
        assert response.status_code == 201
        assert response.data['title'] == 'Test Document'
        assert response.data['file_name'] == 'test_document.pdf'
        assert response.data['category'] == 'contract'
    
    def test_list_documents(self, api_client, admin_user, company):
        """Test listing documents"""
        api_client.force_authenticate(user=admin_user)
        
        # Create test document
        Document.objects.create(
            title='Test Doc',
            category='invoice',
            file_path='documents/test.pdf',
            file_name='test.pdf',
            file_size=1024,
            mime_type='application/pdf',
            company=company,
            uploaded_by=admin_user
        )
        
        response = api_client.get('/api/documents/')
        assert response.status_code == 200
        assert len(response.data['results']) == 1
    
    def test_get_document_details(self, api_client, admin_user, company):
        """Test getting document details"""
        api_client.force_authenticate(user=admin_user)
        
        document = Document.objects.create(
            title='Test Doc',
            description='Test description',
            category='invoice',
            file_path='documents/test.pdf',
            file_name='test.pdf',
            file_size=1024,
            mime_type='application/pdf',
            company=company,
            uploaded_by=admin_user
        )
        
        response = api_client.get(f'/api/documents/{document.id}/')
        assert response.status_code == 200
        assert response.data['title'] == 'Test Doc'
        assert response.data['description'] == 'Test description'
    
    def test_update_document_metadata(self, api_client, admin_user, company):
        """Test updating document metadata"""
        api_client.force_authenticate(user=admin_user)
        
        document = Document.objects.create(
            title='Old Title',
            category='invoice',
            file_path='documents/test.pdf',
            file_name='test.pdf',
            file_size=1024,
            mime_type='application/pdf',
            company=company,
            uploaded_by=admin_user
        )
        
        data = {
            'title': 'New Title',
            'description': 'Updated description'
        }
        
        response = api_client.patch(f'/api/documents/{document.id}/', data, format='json')
        assert response.status_code == 200
        assert response.data['title'] == 'New Title'
        assert response.data['description'] == 'Updated description'
    
    def test_delete_document(self, api_client, admin_user, company):
        """Test deleting a document"""
        api_client.force_authenticate(user=admin_user)
        
        document = Document.objects.create(
            title='Test Doc',
            category='invoice',
            file_path='documents/test.pdf',
            file_name='test.pdf',
            file_size=1024,
            mime_type='application/pdf',
            company=company,
            uploaded_by=admin_user
        )
        
        response = api_client.delete(f'/api/documents/{document.id}/')
        assert response.status_code == 204
        assert not Document.objects.filter(id=document.id).exists()
    
    def test_company_based_filtering(self, api_client, admin_user, company):
        """Test that users only see documents from their company"""
        api_client.force_authenticate(user=admin_user)
        
        # Create document for user's company
        Document.objects.create(
            title='My Company Doc',
            category='invoice',
            file_path='documents/test1.pdf',
            file_name='test1.pdf',
            file_size=1024,
            mime_type='application/pdf',
            company=company,
            uploaded_by=admin_user
        )
        
        # Create document for another company
        other_company = Company.objects.create(
            name='Other Company',
            registration_number='REG002',
            tax_id='TAX002',
            address='456 Other St'
        )
        Document.objects.create(
            title='Other Company Doc',
            category='invoice',
            file_path='documents/test2.pdf',
            file_name='test2.pdf',
            file_size=1024,
            mime_type='application/pdf',
            company=other_company,
            uploaded_by=admin_user
        )
        
        response = api_client.get('/api/documents/')
        assert response.status_code == 200
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['title'] == 'My Company Doc'
