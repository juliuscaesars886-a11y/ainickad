#!/usr/bin/env python3
"""
Test the report generation endpoint
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ainick_backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from workflows.models import Task
from authentication.models import UserProfile

def test_report_generation():
    # Get an approved task
    approved_task = Task.objects.filter(status='approved').first()
    if not approved_task:
        print("❌ No approved tasks found")
        return False
    
    print(f"✅ Found approved task: {approved_task.title} (ID: {approved_task.id})")
    
    # Get a user
    user = UserProfile.objects.filter(role='admin').first()
    if not user:
        user = UserProfile.objects.first()
    
    if not user:
        print("❌ No users found")
        return False
    
    print(f"✅ Using user: {user.email}")
    
    # Create a test client
    client = Client()
    
    # Force login the user
    client.force_login(user)
    
    # Test the report endpoint
    url = f'/api/tasks/{approved_task.id}/generate_report/'
    response = client.get(url)
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Report generation successful!")
        print(f"Content-Type: {response.get('Content-Type')}")
        print(f"Content-Disposition: {response.get('Content-Disposition')}")
        
        # Check if it's CSV content
        content = response.content.decode('utf-8')
        lines = content.split('\n')
        print(f"CSV has {len(lines)} lines")
        if len(lines) > 0:
            print(f"Header: {lines[0]}")
        if len(lines) > 1:
            print(f"Data: {lines[1]}")
        
        return True
    else:
        print(f"❌ Report generation failed")
        print(f"Response content: {response.content.decode('utf-8')}")
        return False

if __name__ == '__main__':
    success = test_report_generation()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")