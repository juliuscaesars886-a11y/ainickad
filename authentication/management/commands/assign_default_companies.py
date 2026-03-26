"""
Management command to assign default companies to users who don't have one.
This fixes the issue where existing users don't have companies assigned.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from authentication.models import UserProfile
from companies.models import Company


class Command(BaseCommand):
    help = 'Assign default companies to users who do not have a company assigned'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get users without companies
        users_without_company = UserProfile.objects.filter(company__isnull=True)
        
        if not users_without_company.exists():
            self.stdout.write(
                self.style.SUCCESS('All users already have companies assigned.')
            )
            return
        
        # Get the first available company
        default_company = Company.objects.filter(is_active=True).first()
        
        if not default_company:
            self.stdout.write(
                self.style.ERROR('No active companies found. Please create a company first.')
            )
            return
        
        self.stdout.write(f'Found {users_without_company.count()} users without companies')
        self.stdout.write(f'Default company: {default_company.name} (ID: {default_company.id})')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
            for user in users_without_company:
                self.stdout.write(f'Would assign {user.email} to {default_company.name}')
        else:
            with transaction.atomic():
                updated_count = users_without_company.update(company=default_company)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully assigned {updated_count} users to {default_company.name}'
                    )
                )
                
                # List the updated users
                for user in users_without_company:
                    self.stdout.write(f'Assigned {user.email} to {default_company.name}')