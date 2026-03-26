#!/usr/bin/env python
"""
Script to fix company assignment issues.
This script should be run after deploying the backend fixes.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'governance_hub.settings')
django.setup()

from django.core.management import call_command
from companies.models import Company
from authentication.models import UserProfile


def main():
    print("🔧 Fixing company assignment issues...")
    
    # Step 1: Create default company if none exists
    print("\n📋 Step 1: Ensuring default company exists...")
    if not Company.objects.exists():
        print("No companies found. Creating default company...")
        call_command('create_default_company')
    else:
        print(f"✅ Found {Company.objects.count()} companies")
    
    # Step 2: Assign companies to users without them
    print("\n👥 Step 2: Assigning companies to users...")
    users_without_company = UserProfile.objects.filter(company__isnull=True)
    
    if users_without_company.exists():
        print(f"Found {users_without_company.count()} users without companies")
        call_command('assign_default_companies')
    else:
        print("✅ All users already have companies assigned")
    
    # Step 3: Verify the fix
    print("\n✅ Step 3: Verification...")
    total_users = UserProfile.objects.count()
    users_with_company = UserProfile.objects.filter(company__isnull=False).count()
    
    print(f"Total users: {total_users}")
    print(f"Users with companies: {users_with_company}")
    
    if total_users == users_with_company:
        print("🎉 SUCCESS: All users now have companies assigned!")
    else:
        print(f"⚠️  WARNING: {total_users - users_with_company} users still don't have companies")
    
    print("\n🚀 Company assignment fix completed!")


if __name__ == '__main__':
    main()