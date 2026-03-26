"""
Management command to create a default company if none exists.
This ensures there's always at least one company for user assignment.
"""

from django.core.management.base import BaseCommand
from companies.models import Company


class Command(BaseCommand):
    help = 'Create a default company if no companies exist'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            default='Default Company',
            help='Name for the default company',
        )

    def handle(self, *args, **options):
        company_name = options['name']
        
        # Check if any companies exist
        if Company.objects.exists():
            self.stdout.write(
                self.style.SUCCESS(f'Companies already exist. Found {Company.objects.count()} companies.')
            )
            return
        
        # Create default company
        default_company = Company.objects.create(
            name=company_name,
            registration_number='DEFAULT-001',
            tax_id='TAX-DEFAULT-001',
            address='Default Address',
            contact_email='admin@company.com',
            contact_phone='+254700000000',
            risk_level='level_2',
            risk_category='general_business',
            settings={},
            is_active=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created default company: {default_company.name} (ID: {default_company.id})'
            )
        )