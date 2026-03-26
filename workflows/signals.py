"""
Signals for workflows app
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from staff.models import Staff
from workflows.models import LeaveBalance


@receiver(post_save, sender=Staff)
def create_leave_balance(sender, instance, created, **kwargs):
    """
    Create LeaveBalance when a new Staff member is created
    """
    if created:
        LeaveBalance.objects.get_or_create(
            staff=instance,
            company=instance.company,
            defaults={
                'annual_leave_entitlement': 20,
                'maternity_leave_entitlement': 90,
                'paternity_leave_entitlement': 14,
                'sick_leave_entitlement': 10,
                'emergency_leave_entitlement': 3,
            }
        )
