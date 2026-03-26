"""
Signal handlers for automatic staff record creation.

This module ensures that every UserProfile automatically gets a corresponding
Staff record, maintaining data integrity and synchronization.
"""
import logging
import random
from datetime import datetime
from django.db.models.signals import post_save
from django.dispatch import receiver
from authentication.models import UserProfile
from .models import Staff

logger = logging.getLogger(__name__)


def generate_staff_number():
    """
    Generate unique staff number in format STF-YYYYMMDD-XXXX.
    
    Returns:
        str: Unique staff number
    """
    date_str = datetime.now().strftime('%Y%m%d')
    
    # Try up to 10 times to generate a unique number
    for _ in range(10):
        random_num = str(random.randint(0, 9999)).zfill(4)
        staff_number = f"STF-{date_str}-{random_num}"
        
        if not Staff.objects.filter(staff_number=staff_number).exists():
            return staff_number
    
    # Fallback: use timestamp for uniqueness
    timestamp = datetime.now().strftime('%H%M%S')
    return f"STF-{date_str}-{timestamp}"


def get_job_title_from_role(role):
    """
    Map user role to appropriate job title.
    
    Args:
        role (str): User role
        
    Returns:
        str: Job title
    """
    job_title_map = {
        'super_admin': 'Super Administrator',
        'admin': 'Administrator',
        'accountant': 'Accountant',
        'employee': 'Staff Member',
    }
    return job_title_map.get(role, 'Staff Member')


def parse_full_name(full_name):
    """
    Parse full name into first and last name.
    
    Args:
        full_name (str): Full name string
        
    Returns:
        tuple: (first_name, last_name)
    """
    if not full_name:
        return '', ''
    
    parts = full_name.strip().split()
    if len(parts) == 0:
        return '', ''
    elif len(parts) == 1:
        return parts[0], ''
    else:
        return parts[0], ' '.join(parts[1:])


@receiver(post_save, sender=UserProfile)
def create_staff_for_user(sender, instance, created, **kwargs):
    """
    Automatically create a Staff record when a UserProfile is created.
    
    This signal handler ensures every user has a corresponding staff record,
    maintaining data integrity across the system.
    
    Args:
        sender: The model class (UserProfile)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional keyword arguments
    """
    # Only create staff for new users
    if not created:
        return
    
    # Check if staff already exists (idempotency)
    if hasattr(instance, 'staff'):
        logger.info(f"Staff record already exists for user {instance.email}")
        return
    
    try:
        # Generate unique staff number
        staff_number = generate_staff_number()
        
        # Parse name
        first_name, last_name = parse_full_name(instance.full_name)
        
        # If no name provided, use email prefix
        if not first_name:
            first_name = instance.email.split('@')[0]
        
        # Determine job title from role
        job_title = get_job_title_from_role(instance.role)
        
        # Get company (required for staff)
        if not instance.company:
            logger.warning(
                f"User {instance.email} has no company assigned. "
                f"Staff creation may fail or require manual company assignment."
            )
        
        # Create staff record
        staff = Staff.objects.create(
            user=instance,
            staff_number=staff_number,
            company=instance.company,
            first_name=first_name,
            last_name=last_name,
            email=instance.email,
            job_title=job_title,
            department='General',
            employment_status='active',
            hire_date=instance.created_at.date(),
        )
        
        logger.info(
            f"Staff record created successfully: "
            f"{staff.staff_number} for user {instance.email}"
        )
        
    except Exception as e:
        logger.error(
            f"Failed to create staff for user {instance.email}: {str(e)}",
            exc_info=True
        )
        # Don't raise - allow user creation to succeed even if staff creation fails
        # This prevents blocking user registration due to staff creation issues
