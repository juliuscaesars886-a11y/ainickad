"""
Management command to create demo user profiles for testing
"""
from django.core.management.base import BaseCommand
from authentication.models import UserProfile
from companies.models import Company


class Command(BaseCommand):
    help = 'Creates demo user profiles for testing'

    def handle(self, *args, **options):
        # Create a demo company first
        company, company_created = Company.objects.get_or_create(
            name='Demo Company',
            defaults={
                'registration_number': 'DEMO001',
                'tax_id': 'TAX001',
                'contact_email': 'demo@company.com',
                'contact_phone': '+254700000000',
                'address': 'Nairobi, Kenya',
            }
        )
        
        if company_created:
            self.stdout.write(self.style.SUCCESS(f'Created company: {company.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Company already exists: {company.name}'))

        demo_users = [
            {
                'email': 'superadmin@ainick.com',
                'full_name': 'Super Admin',
                'role': 'super_admin',
                'company': None,  # Super admin has no company
            },
            {
                'email': 'admin@ainick.com',
                'full_name': 'Admin User',
                'role': 'admin',
                'company': company,
            },
            {
                'email': 'accountant@ainick.com',
                'full_name': 'Demo Accountant',
                'role': 'accountant',
                'company': company,
            },
            {
                'email': 'employee@ainick.com',
                'full_name': 'Demo Employee',
                'role': 'employee',
                'company': company,
            },
        ]

        for user_data in demo_users:
            # Create or update profile
            profile, created = UserProfile.objects.get_or_create(
                email=user_data['email'],
                defaults={
                    'full_name': user_data['full_name'],
                    'role': user_data['role'],
                    'company': user_data['company'],
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'Created profile: {profile.email} ({profile.get_role_display()})'
                ))
            else:
                # Update existing profile
                profile.full_name = user_data['full_name']
                profile.role = user_data['role']
                profile.company = user_data['company']
                profile.save()
                self.stdout.write(self.style.WARNING(
                    f'Updated profile: {profile.email} ({profile.get_role_display()})'
                ))

        self.stdout.write(self.style.SUCCESS('\n✅ Demo user profiles created successfully!'))
        self.stdout.write(self.style.SUCCESS('\nNote: These are profiles only. Users must sign up through Supabase Auth.'))
        self.stdout.write(self.style.SUCCESS('After signing up with these emails, the profiles will be linked automatically.'))
