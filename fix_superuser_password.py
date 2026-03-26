#!/usr/bin/env python
"""Fix superuser password - ensures it is properly hashed."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "governance_hub.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def fix_superuser_password():
    # Strip whitespace and newlines from environment variables
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "superadmin@ainick.com").strip()
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Superadmin@098").strip()
    
    print("="*60)
    print("FIXING SUPERUSER PASSWORD")
    print("="*60)
    print(f"Email: {email}")
    print(f"Password: {password}")
    print(f"Password length: {len(password)}")
    
    try:
        user = User.objects.get(email=email)
        print(f"Found user: {user.email}")
        print(f"  Current role: {user.role}")
        print(f"  Current password: {user.password[:50]}...")
        
        user.set_password(password)
        user.role = "super_admin"
        user.is_active = True
        user.save()
        
        print("Password updated successfully!")
        print(f"  New password hash: {user.password[:50]}...")
        print(f"  Role: {user.role}")
        print(f"  Is Staff: {user.is_staff}")
        print(f"  Is Superuser: {user.is_superuser}")
        
        if user.check_password(password):
            print("Password verification: SUCCESS")
            print(f"Login credentials:")
            print(f"  Email: {email}")
            print(f"  Password: {password}")
        else:
            print("Password verification: FAILED")
        
    except User.DoesNotExist:
        print(f"User not found: {email}")
        print("Creating new superuser...")
        
        user = User.objects.create_superuser(email=email, password=password)
        print(f"Superuser created: {email}")
        print(f"  Role: {user.role}")
        print(f"  Is Staff: {user.is_staff}")
        print(f"  Is Superuser: {user.is_superuser}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("="*60)

if __name__ == "__main__":
    fix_superuser_password()
