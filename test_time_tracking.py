#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'governance_hub.settings')
django.setup()

from workflows.models import Task
from communications.models import Notification
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# Get users
admin_user = User.objects.get(email='fcs.isaac@ainick.com')
staff_user = User.objects.get(email='samuelresearchafrica@gmail.com')

print('=== TESTING TIME TRACKING SYSTEM ===')

# Create a test task with time tracking
task = Task.objects.create(
    title='Time Tracking Test Task',
    description='This task will test the time tracking and report generation system',
    assignee=staff_user,
    creator=admin_user,
    company=admin_user.company,
    priority='medium',
    due_date=timezone.now() + timezone.timedelta(days=1)
)

print(f'Task created: {task.title}')
print(f'Task ID: {task.id}')
print(f'Initial time spent: {task.time_spent_formatted}')

# Simulate starting the task
task.status = 'in_progress'
task.started_at = timezone.now()
task.save()
print(f'Task started at: {task.started_at}')

# Simulate adding time (e.g., 2 hours and 30 minutes = 9000 seconds)
task.add_time_spent(9000)
print(f'Added 9000 seconds (2h 30m)')
print(f'Total time spent: {task.time_spent_formatted}')

# Simulate completion
task.status = 'completed'
task.completed_at = timezone.now()
if not task.metadata:
    task.metadata = {}
task.metadata['completion_notes'] = 'Task completed successfully with time tracking'
task.metadata['pending_approval'] = True
task.save()
print(f'Task completed at: {task.completed_at}')

# Simulate approval
task.status = 'approved'
task.metadata['pending_approval'] = False
task.metadata['approved_by'] = str(admin_user.id)
task.metadata['approved_at'] = timezone.now().isoformat()
task.save()
print(f'Task approved')

print('\n=== TASK SUMMARY ===')
print(f'Title: {task.title}')
print(f'Status: {task.status}')
print(f'Started: {task.started_at}')
print(f'Completed: {task.completed_at}')
print(f'Total Time: {task.time_spent_formatted}')
print(f'Approved: {task.metadata.get("approved_at")}')

print('\n=== TESTING COMPLETE ===')
print('You can now test the frontend:')
print('1. Login as staff user and start a task')
print('2. Use the timer to track time')
print('3. Complete the task')
print('4. Login as admin and approve the task')
print('5. Download the timestamp report')