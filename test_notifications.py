#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'governance_hub.settings')
django.setup()

from workflows.models import Task
from communications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

# Get users
admin_user = User.objects.get(email='fcs.isaac@ainick.com')
staff_user = User.objects.get(email='samuelresearchafrica@gmail.com')

print('=== CREATING TEST TASK WITH NOTIFICATION ===')

# Create a test task
task = Task.objects.create(
    title='Test Notification Task',
    description='This task will test the notification system',
    assignee=staff_user,
    creator=admin_user,
    company=admin_user.company,
    priority='medium',
    due_date='2026-03-15'
)

# Create notification for task assignment
notification = Notification.objects.create(
    user=staff_user,
    notification_type='task_assigned',
    title='New Task Assigned',
    message=f'You have been assigned a new task: "{task.title}"',
    related_entity_type='task',
    related_entity_id=str(task.id),
    metadata={
        'task_id': str(task.id),
        'task_title': task.title,
        'assigned_by': admin_user.full_name,
        'link': '/tasks'
    }
)

print(f'Task created: {task.title}')
print(f'Task ID: {task.id}')
print(f'Assignee: {task.assignee.email}')
print(f'Notification created: {notification.title}')
print(f'Notification ID: {notification.id}')
print(f'Notification user: {notification.user.email}')

print('\n=== NOTIFICATION COUNTS ===')
total_notifications = Notification.objects.count()
staff_notifications = Notification.objects.filter(user=staff_user).count()
unread_staff_notifications = Notification.objects.filter(user=staff_user, is_read=False).count()

print(f'Total notifications: {total_notifications}')
print(f'Staff user notifications: {staff_notifications}')
print(f'Unread staff notifications: {unread_staff_notifications}')

print('\n=== TESTING TASK APPROVAL ERROR FIX ===')
# Test the UUID serialization fix
task.status = 'completed'
if not task.metadata:
    task.metadata = {}
task.metadata['completion_notes'] = 'Test completion'
task.metadata['pending_approval'] = True
task.save()

# Test approval
task.status = 'approved'
task.metadata['pending_approval'] = False
task.metadata['approved_by'] = str(admin_user.id)  # This should work now
task.save()

print('UUID serialization test passed!')
print(f'Task status: {task.status}')
print(f'Task metadata: {task.metadata}')