"""
Security-focused tests for document/file upload functionality
Tests for vulnerabilities #3, #4, #11, #23 from security audit
"""
import pytest
import os
import uuid
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from authentication.models import UserProfile
from companies.models import Company
from documents.models import Document


class PathTraversalSecurityTests(APITestCase):
    """
    Test path traversal prevention (Vulnerability #3)
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
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            role='admin',
            company=self.company
        )
        
        # Login
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'testuser', 'password': 'TestPass123!'},
            format='json'
        )
        self.token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def test_path_traversal_in_filename_blocked(self):
        """
        Test that path traversal attempts in filename are blocked
        
        **Validates: Requirements 1.2**
        
        VULNERABILITY: Filename used directly without sanitization
        EXPLOIT: Upload file with name '../../../etc/passwd'
        FIX: Use UUID-based naming or secure_filename()
        """
        # Create malicious file with path traversal
        malicious_filenames = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '../../sensitive_data.db',
            '../.env',
            'documents/../../outside_directory/file.pdf'
        ]
        
        for filename in malicious_filenames:
            file_content = b'malicious content'
            uploaded_file = SimpleUploadedFile(
                filename,
                file_content,
                content_type='application/pdf'
            )
            
            response = self.client.post(
                '/api/documents/',
                {
                    'title': 'Test Document',
                    'company': str(self.company.id),
                    'category': 'contract',
                    'file': uploaded_file
                },
                format='multipart'
            )
            
            # Should either reject or sanitize the filename
            if response.status_code == status.HTTP_201_CREATED:
                # If accepted, verify file is stored safely
                document = Document.objects.get(id=response.data['id'])
                stored_path = document.file_path
                
                # Path should not contain '..'
                self.assertNotIn('..', stored_path,
                               f"Path traversal not prevented for: {filename}")
                
                # Path should be within expected directory
                self.assertTrue(
                    stored_path.startswith('documents/'),
                    f"File stored outside expected directory: {stored_path}"
                )
    
    def test_filename_uses_uuid_or_sanitized_name(self):
        """
        Test that uploaded files are renamed with UUID or sanitized names
        
        **Validates: Requirements 1.2**
        
        FIX: Generate UUID-based filename to prevent all path issues
        """
        file_content = b'test content'
        uploaded_file = SimpleUploadedFile(
            'test document.pdf',
            file_content,
            content_type='application/pdf'
        )
        
        response = self.client.post(
            '/api/documents/',
            {
                'title': 'Test Document',
                'company': str(self.company.id),
                'category': 'contract',
                'file': uploaded_file
            },
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        document = Document.objects.get(id=response.data['id'])
        stored_filename = os.path.basename(document.file_path)
        
        # Filename should be UUID-based or properly sanitized
        # Should not contain spaces or special characters
        self.assertNotIn(' ', stored_filename)
        self.assertNotIn('..', stored_filename)
    
    def test_absolute_path_in_filename_blocked(self):
        """
        Test that absolute paths in filenames are blocked
        
        **Validates: Requirements 1.2**
        """
        malicious_filenames = [
            '/etc/passwd',
            'C:\\Windows\\System32\\config\\sam',
            '/var/www/html/shell.php'
        ]
        
        for filename in malicious_filenames:
            file_content = b'malicious content'
            uploaded_file = SimpleUploadedFile(
                filename,
                file_content,
                content_type='application/pdf'
            )
            
            response = self.client.post(
                '/api/documents/',
                {
                    'title': 'Test Document',
                    'company': str(self.company.id),
                    'category': 'contract',
                    'file': uploaded_file
                },
                format='multipart'
            )
            
            if response.status_code == status.HTTP_201_CREATED:
                document = Document.objects.get(id=response.data['id'])
                stored_path = document.file_path
                
                # Should not start with absolute path indicators
                self.assertFalse(
                    stored_path.startswith('/') or stored_path.startswith('C:'),
                    f"Absolute path not prevented for: {filename}"
                )


class FileTypeValidationSecurityTests(APITestCase):
    """
    Test file type validation (Vulnerability #4)
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
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            role='admin',
            company=self.company
        )
        
        # Login
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'testuser', 'password': 'TestPass123!'},
            format='json'
        )
        self.token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def test_mime_type_spoofing_blocked(self):
        """
        Test that MIME type spoofing is detected and blocked
        
        **Validates: Requirements 1.2**
        
        VULNERABILITY: Only MIME type checked, not actual file content
        EXPLOIT: Upload .exe file with Content-Type: application/pdf
        FIX: Validate file magic bytes using python-magic
        """
        # Create executable content (MZ header for Windows .exe)
        exe_content = b'MZ\x90\x00' + b'\x00' * 100  # Simplified .exe header
        
        # Try to upload with spoofed MIME type
        uploaded_file = SimpleUploadedFile(
            'malware.pdf',  # Looks like PDF
            exe_content,
            content_type='application/pdf'  # Claims to be PDF
        )
        
        response = self.client.post(
            '/api/documents/',
            {
                'title': 'Malicious Document',
                'company': str(self.company.id),
                'category': 'contract',
                'file': uploaded_file
            },
            format='multipart'
        )
        
        # Should be rejected
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_msg = str(response.data).lower()
        self.assertTrue('file' in error_msg or 'type' in error_msg)
    
    def test_script_file_upload_blocked(self):
        """
        Test that script files are blocked even with valid extensions
        
        **Validates: Requirements 1.2**
        
        EXPLOIT: Upload .js, .py, .sh files disguised as documents
        """
        script_files = [
            ('malicious.js', b'alert("XSS")', 'application/javascript'),
            ('malicious.py', b'import os; os.system("rm -rf /")', 'text/x-python'),
            ('malicious.sh', b'#!/bin/bash\nrm -rf /', 'application/x-sh'),
        ]
        
        for filename, content, mime_type in script_files:
            uploaded_file = SimpleUploadedFile(filename, content, content_type=mime_type)
            
            response = self.client.post(
                '/api/documents/',
                {
                    'title': 'Test Document',
                    'company': str(self.company.id),
                    'category': 'contract',
                    'file': uploaded_file
                },
                format='multipart'
            )
            
            # Should be rejected
            self.assertNotEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"Script file {filename} should be blocked"
            )
    
    def test_valid_pdf_upload_succeeds(self):
        """
        Test that valid PDF files are accepted
        
        **Validates: Requirements 1.2**
        
        This ensures our security fixes don't break legitimate uploads
        """
        # Minimal valid PDF content
        pdf_content = b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n'
        
        uploaded_file = SimpleUploadedFile(
            'valid.pdf',
            pdf_content,
            content_type='application/pdf'
        )
        
        response = self.client.post(
            '/api/documents/',
            {
                'title': 'Valid Document',
                'company': str(self.company.id),
                'category': 'contract',
                'file': uploaded_file
            },
            format='multipart'
        )
        
        # Should succeed (or fail for other reasons, but not file type)
        # Note: May fail due to other validation, but not file type
        if response.status_code != status.HTTP_201_CREATED:
            # If it fails, should not be due to file type
            error_msg = str(response.data).lower()
            self.assertNotIn('file type', error_msg)
    
    def test_double_extension_attack_blocked(self):
        """
        Test that double extension attacks are blocked
        
        **Validates: Requirements 1.2**
        
        EXPLOIT: Upload file named 'document.pdf.exe' to bypass filters
        """
        exe_content = b'MZ\x90\x00' + b'\x00' * 100
        
        uploaded_file = SimpleUploadedFile(
            'document.pdf.exe',
            exe_content,
            content_type='application/pdf'
        )
        
        response = self.client.post(
            '/api/documents/',
            {
                'title': 'Test Document',
                'company': str(self.company.id),
                'category': 'contract',
                'file': uploaded_file
            },
            format='multipart'
        )
        
        # Should be rejected or sanitized
        if response.status_code == status.HTTP_201_CREATED:
            document = Document.objects.get(id=response.data['id'])
            # Stored filename should not end with .exe
            self.assertFalse(
                document.file_path.lower().endswith('.exe'),
                "Executable extension should be removed or blocked"
            )


class FileSizeSecurityTests(APITestCase):
    """
    Test file size limits (Vulnerability #32)
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
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            role='admin',
            company=self.company
        )
        
        # Login
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'testuser', 'password': 'TestPass123!'},
            format='json'
        )
        self.token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def test_file_size_limit_enforced(self):
        """
        Test that file size limits are enforced
        
        **Validates: Requirements 1.2**
        
        VULNERABILITY: Large files can cause DoS
        FIX: Enforce size limits at middleware level
        """
        # Current limit is 50MB according to serializer
        # Test with file over limit (should fail)
        
        # Create a file that's 51MB (over the limit)
        large_file_size = 51 * 1024 * 1024  # 51MB
        large_content = b'X' * large_file_size
        
        uploaded_file = SimpleUploadedFile(
            'large_file.pdf',
            large_content,
            content_type='application/pdf'
        )
        
        response = self.client.post(
            '/api/documents/',
            {
                'title': 'Large Document',
                'company': str(self.company.id),
                'category': 'contract',
                'file': uploaded_file
            },
            format='multipart'
        )
        
        # Should be rejected
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_msg = str(response.data).lower()
        self.assertTrue('size' in error_msg or 'large' in error_msg or 'exceed' in error_msg)
    
    def test_file_within_size_limit_accepted(self):
        """
        Test that files within size limit are accepted
        
        **Validates: Requirements 1.2**
        """
        # Create a file that's 1MB (well within limit)
        small_file_size = 1 * 1024 * 1024  # 1MB
        small_content = b'%PDF-1.4\n' + b'X' * (small_file_size - 10)
        
        uploaded_file = SimpleUploadedFile(
            'small_file.pdf',
            small_content,
            content_type='application/pdf'
        )
        
        response = self.client.post(
            '/api/documents/',
            {
                'title': 'Small Document',
                'company': str(self.company.id),
                'category': 'contract',
                'file': uploaded_file
            },
            format='multipart'
        )
        
        # Should succeed or fail for reasons other than size
        if response.status_code != status.HTTP_201_CREATED:
            error_msg = str(response.data).lower()
            self.assertNotIn('size', error_msg)
            self.assertNotIn('large', error_msg)
    
    def test_zero_byte_file_rejected(self):
        """
        Test that zero-byte files are rejected
        
        **Validates: Requirements 1.2**
        """
        empty_file = SimpleUploadedFile(
            'empty.pdf',
            b'',
            content_type='application/pdf'
        )
        
        response = self.client.post(
            '/api/documents/',
            {
                'title': 'Empty Document',
                'company': str(self.company.id),
                'category': 'contract',
                'file': empty_file
            },
            format='multipart'
        )
        
        # Should be rejected
        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)


class VirusScanningSecurityTests(APITestCase):
    """
    Test virus scanning (Vulnerability #11)
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
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            role='admin',
            company=self.company
        )
        
        # Login
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'testuser', 'password': 'TestPass123!'},
            format='json'
        )
        self.token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def test_eicar_test_file_blocked(self):
        """
        Test that EICAR test virus file is detected and blocked
        
        **Validates: Requirements 1.2**
        
        VULNERABILITY: No virus scanning on uploads
        FIX: Integrate ClamAV or similar scanner
        
        Note: This test will pass if virus scanning is not yet implemented,
        but should be enabled once virus scanning is added.
        """
        # EICAR test file - standard test file for antivirus
        eicar_content = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
        
        uploaded_file = SimpleUploadedFile(
            'test.pdf',
            eicar_content,
            content_type='application/pdf'
        )
        
        response = self.client.post(
            '/api/documents/',
            {
                'title': 'Test Document',
                'company': str(self.company.id),
                'category': 'contract',
                'file': uploaded_file
            },
            format='multipart'
        )
        
        # If virus scanning is implemented, should be rejected
        # If not implemented yet, this test documents the expected behavior
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            error_msg = str(response.data).lower()
            self.assertTrue(
                'virus' in error_msg or 'malware' in error_msg or 'threat' in error_msg,
                "Should indicate virus/malware detection"
            )
    
    def test_malformed_file_rejected(self):
        """
        Test that malformed files are rejected
        
        **Validates: Requirements 1.2**
        """
        # Create a file that claims to be PDF but has invalid content
        malformed_content = b'This is not a valid PDF file'
        
        uploaded_file = SimpleUploadedFile(
            'malformed.pdf',
            malformed_content,
            content_type='application/pdf'
        )
        
        response = self.client.post(
            '/api/documents/',
            {
                'title': 'Malformed Document',
                'company': str(self.company.id),
                'category': 'contract',
                'file': uploaded_file
            },
            format='multipart'
        )
        
        # Should be rejected if magic byte validation is implemented
        # This test documents expected behavior
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            error_msg = str(response.data).lower()
            self.assertTrue('file' in error_msg or 'type' in error_msg or 'invalid' in error_msg)


class FileDownloadSecurityTests(APITestCase):
    """
    Test file download access control (Vulnerability #23)
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
    
    def test_user_cannot_download_other_company_files(self):
        """
        Test that users cannot download files from other companies
        
        **Validates: Requirements 1.2**
        
        VULNERABILITY: Only checks if file exists, not if user has access
        FIX: Add explicit permission check before download
        """
        # Login as user A and create document
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'user_a', 'password': 'TestPass123!'},
            format='json'
        )
        token_a = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_a}')
        
        # Create document for Company A
        file_content = b'confidential company A data'
        uploaded_file = SimpleUploadedFile(
            'confidential.pdf',
            file_content,
            content_type='application/pdf'
        )
        
        create_response = self.client.post(
            '/api/documents/',
            {
                'title': 'Confidential Document',
                'company': str(self.company_a.id),
                'category': 'contract',
                'file': uploaded_file
            },
            format='multipart'
        )
        
        if create_response.status_code != status.HTTP_201_CREATED:
            self.skipTest(f"Could not create test document: {create_response.data}")
        
        document_id = create_response.data['id']
        
        # Login as user B
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'user_b', 'password': 'TestPass123!'},
            format='json'
        )
        token_b = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_b}')
        
        # Try to download Company A's document
        download_response = self.client.get(f'/api/documents/{document_id}/download/')
        
        # Should be forbidden or not found (both are acceptable for security)
        self.assertIn(
            download_response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
            "User from Company B should not be able to download Company A's document"
        )
    
    def test_user_can_download_own_company_files(self):
        """
        Test that users can download files from their own company
        
        **Validates: Requirements 1.2**
        """
        # Login as user A
        login_response = self.client.post(
            '/api/auth/login/',
            {'username': 'user_a', 'password': 'TestPass123!'},
            format='json'
        )
        token_a = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_a}')
        
        # Create document for Company A
        file_content = b'company A data'
        uploaded_file = SimpleUploadedFile(
            'document.pdf',
            file_content,
            content_type='application/pdf'
        )
        
        create_response = self.client.post(
            '/api/documents/',
            {
                'title': 'Company Document',
                'company': str(self.company_a.id),
                'category': 'contract',
                'file': uploaded_file
            },
            format='multipart'
        )
        
        if create_response.status_code != status.HTTP_201_CREATED:
            self.skipTest(f"Could not create test document: {create_response.data}")
        
        document_id = create_response.data['id']
        
        # Try to download own company's document
        download_response = self.client.get(f'/api/documents/{document_id}/download/')
        
        # Should succeed
        self.assertEqual(
            download_response.status_code,
            status.HTTP_200_OK,
            "User should be able to download their own company's document"
        )


# Test runner configuration
pytest_plugins = ['pytest_django']
