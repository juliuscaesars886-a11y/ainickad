"""
Management command to create demo users for Django authentication
"""
from django.core.management.base import BaseCommand
from authentication.models import UserProfile


class Command(BaseCommand):
    help = 'Create demo users for Django authentication'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating demo users...'))
        
        users = [
            {
                'email': 'superadmin@ainick.com',
                'full_name': 'Super Admin',
                'role': 'super_admin',
                'password': 'SuperAdmin@123'
            },
            {
                'email': 'admin@ainick.com',
                'full_name': 'Admin User',
                'role': 'admin',
                'password': 'Admin@123'
            },
            {
                'email': 'accountant@ainick.com',
                'full_name': 'Accountant',
                'role': 'accountant',
                'password': 'Accountant@123'
            },
            {
                'email': 'staff@ainick.com',
                'full_name': 'Demo Staff',
                'role': 'staff',
                'password': 'Staff@123'
            },
        ]

        for user_data in users:
            password = user_data.pop('password')
            email = user_data['email']
            
            # Check if user already exists
            if UserProfile.objects.filter(email=email).exists():
                self.stdout.write(
                    self.style.WARNING(f'⚠ User already exists: {email}')
                )
                continue
            
            # Create user
            user = UserProfile.objects.create(**user_data, is_active=True)
            user.set_password(password)
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created user: {email} (role: {user.role})')
            )

        self.stdout.write(self.style.SUCCESS('\n✅ Demo users setup complete!'))
        self.stdout.write('\nDemo Credentials:')
        self.stdout.write('  Super Admin: superadmin@ainick.com / SuperAdmin@123')
        self.stdout.write('  Admin:       admin@ainick.com / Admin@123')
        self.stdout.write('  Accountant:  accountant@ainick.com / Accountant@123')
        self.stdout.write('  Staff:       staff@ainick.com / Staff@123')
