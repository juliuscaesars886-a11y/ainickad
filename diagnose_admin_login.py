#!/usr/bin/env python
"""
Comprehensive diagnostic script for Django admin login issues.
Run this on Render Shell: python diagnose_admin_login.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'governance_hub.settings')
django.setup()

from django.contrib.auth import get_user_model, authenticate
from django.db import connection

User = get_user_model()

def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def check_database_connection():
    print_header("1. DATABASE CONNECTION CHECK")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✅ Database connection: SUCCESS")
            print(f"   Database: {connection.settings_dict['NAME']}")
            return True
    except Exception as e:
        print(f"❌ Database connection: FAILED - {str(e)}")
        return False

def check_superuser():
    print_header("2. SUPERUSER CHECK")
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'superadmin@ainick.com')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Superadmin@098')
    
    print(f"Looking for: {email}\n")
    
    try:
        user = User.objects.get(email=email)
        print("✅ Superuser EXISTS\n")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role}")
        print(f"   Is Active: {user.is_active}")
        print(f"   Is Staff: {user.is_staff}")
        print(f"   Is Superuser: {user.is_superuser}")
        print(f"   Password Hash: {user.password[:50]}...")
        
        if user.password == '':
            print("\n❌ PROBLEM: Password is EMPTY!")
        elif not user.password.startswith('pbkdf2_'):
            print("\n❌ PROBLEM: Password NOT HASHED!")
        else:
            print("\n✅ Password is hashed")
            if user.check_password(password):
                print(f"✅ Password '{password}' is CORRECT")
            else:
                print(f"❌ Password '{password}' is WRONG")
        
        return user
    except User.DoesNotExist:
        print(f"❌ Superuser NOT FOUND: {email}")
        return None

def test_authentication():
    print_header("3. AUTHENTICATION TEST")
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'superadmin@ainick.com')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Superadmin@098')
    
    try:
        user = authenticate(username=email, password=password)
        if user:
            print(f"✅ Authentication SUCCESS for {email}")
        else:
            print(f"❌ Authentication FAILED for {email}")
    except Exception as e:
        print(f"❌ Authentication ERROR: {str(e)}")

def main():
    print("\n" + "="*70)
    print("  DJANGO ADMIN LOGIN DIAGNOSTIC")
    print("="*70)
    
    if not check_database_connection():
        return
    
    user = check_superuser()
    if user:
        test_authentication()
    
    print_header("RECOMMENDATION")
    if not user:
        print("Run: python fix_superuser_password.py")
    elif user.password == '' or not user.password.startswith('pbkdf2_'):
        print("Run: python fix_superuser_password.py")
    else:
        print("✅ Everything looks good!")
    
    print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    main()
