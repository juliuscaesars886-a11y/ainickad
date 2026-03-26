#!/usr/bin/env python3
"""
Test script to verify the report download endpoint works correctly
"""
import requests
import os
import sys

# Add the Django project to the path
sys.path.append('ainick-backend-repo')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ainick_backend.settings')

import django
django.setup()

from workflows.models import Task
from authentication.models import UserProfile

def test_report_download():
    # Get an approved task
    approved_task = Task.objects.filter(status='approved').first()
    if not approved_task:
        print("No approved tasks found")
        return False
    
    print(f"Testing report download for task: {approved_task.title} (ID: {approved_task.id})")
    
    # Get a user token for authentication
    user = UserProfile.objects.filter(role='admin').first()
    if not user:
        user = UserProfile.objects.first()
    
    if not user:
        print("No users found")
        return False
    
    print(f"Using user: {user.email}")
    
    # Test the endpoint directly
    url = f'http://localhost:8000/api/tasks/{approved_task.id}/generate_report/'
    
    # Create a session and login
    session = requests.Session()
    
    # Get CSRF token
    csrf_response = session.get('http://localhost:8000/api/auth/csrf-token/')
    if csrf_response.status_code == 200:
        csrf_data = csrf_response.json()
        csrf_token = csrf_data.get('csrfToken')
        print(f"Got CSRF token: {csrf_token[:20]}...")
    else:
        print("Failed to get CSRF token")
        return False
    
    # Login
    login_data = {
        'email': user.email,
        'password': 'admin123'  # Assuming this is the password
    }
    login_headers = {
        'X-CSRFToken': csrf_token,
        'Content-Type': 'application/json'
    }
    
    login_response = session.post(
        'http://localhost:8000/api/auth/login/',
        json=login_data,
        headers=login_headers
    )
    
    if login_response.status_code == 200:
        login_result = login_response.json()
        token = login_result.get('access_token')
        print(f"Login successful, got token: {token[:20]}...")
    else:
        print(f"Login failed: {login_response.status_code} - {login_response.text}")
        return False
    
    # Test report download with Token authentication
    report_headers = {
        'Authorization': f'Token {token}',
        'X-CSRFToken': csrf_token
    }
    
    report_response = session.get(url, headers=report_headers)
    
    print(f"Report download response: {report_response.status_code}")
    if report_response.status_code == 200:
        print("✅ Report download successful!")
        print(f"Content-Type: {report_response.headers.get('Content-Type')}")
        print(f"Content-Disposition: {report_response.headers.get('Content-Disposition')}")
        
        # Check if it's CSV content
        content = report_response.text
        lines = content.split('\n')
        print(f"CSV has {len(lines)} lines")
        if len(lines) > 0:
            print(f"Header: {lines[0]}")
        if len(lines) > 1:
            print(f"Data: {lines[1]}")
        
        return True
    else:
        print(f"❌ Report download failed: {report_response.text}")
        return False

if __name__ == '__main__':
    success = test_report_download()
    sys.exit(0 if success else 1)