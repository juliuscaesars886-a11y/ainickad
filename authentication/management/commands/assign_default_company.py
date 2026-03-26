"""
Management command to assign default company to all users without a company.
This is useful for fixing existing users who don't have a company assigned.

Usage:
    python manage.py assign_default_company
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from authentication.models import UserProfile
from companies.models import Company
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Assign default company to all users without a company'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-if-missing',
            action='store_true',
            help='Create a default company if none exists',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting company assignment...'))

        # Get all users without a company
        users_without_company = UserProfile.objects.filter(company__isnull=True)
        count = users_without_company.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('All users already have a company assigned!'))
            return

        self.stdout.write(f'Found {count} users without a company')

        # Get or create default company
        default_company = Company.objects.filter(is_active=True).first()

        if not default_company:
            if options['create_if_missing']:
                self.stdout.write('Creating default company...')
                default_company = Company.objects.create(
                    name='Default Company',
                    registration_number='DEFAULT-001',
                    tax_id='TAX-DEFAULT-001',
                    address='Default Address',
                    contact_email='admin@company.com',
                    contact_phone='+254700000000',
                    risk_level='level_2',
                    risk_category='general_business',
                    is_active=True
                )
                self.stdout.write(self.style.SUCCESS(f'Created company: {default_company.name}'))
            else:
                self.stdout.write(self.style.ERROR('No active company found. Use --create-if-missing to create one.'))
                return

        # Assign company to all users
        updated_count = 0
        for user in users_without_company:
            user.company = default_company
            user.save(update_fields=['company'])
            updated_count += 1

            # Also update Staff record if it exists
            try:
                if hasattr(user, 'staff'):
                    user.staff.company = default_company
                    user.staff.save(update_fields=['company'])
            except Exception as e:
                logger.warning(f"Could not update Staff record for {user.email}: {e}")

            self.stdout.write(f'  ✓ {user.email} -> {default_company.name}')

        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully assigned company to {updated_count} users!')
        )
