"""
Serializers for workflows app
"""
from rest_framework import serializers
from .models import Task, Request, Approval, LeaveBalance


class TaskListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing tasks (minimal fields)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    creator_name = serializers.CharField(source='creator.full_name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.full_name', read_only=True)
    is_completed = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    is_urgent = serializers.ReadOnlyField()
    time_spent_formatted = serializers.ReadOnlyField()
    due_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'company', 'company_name', 'creator', 'creator_name',
            'assignee', 'assignee_name', 'due_date', 'due_time', 'priority', 'status',
            'is_completed', 'is_overdue', 'is_urgent', 'started_at', 
            'total_time_seconds', 'time_spent_formatted', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_due_time(self, obj):
        """Extract time from due_date"""
        if obj.due_date:
            return obj.due_date.strftime('%H:%M')
        return None


class TaskDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for task details (all fields)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    creator_name = serializers.CharField(source='creator.full_name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.full_name', read_only=True)
    is_completed = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    is_urgent = serializers.ReadOnlyField()
    time_spent_formatted = serializers.ReadOnlyField()
    due_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'company', 'company_name',
            'creator', 'creator_name', 'assignee', 'assignee_name',
            'due_date', 'due_time', 'priority', 'status', 'tags', 'completed_at',
            'started_at', 'total_time_seconds', 'time_spent_formatted',
            'metadata', 'is_completed', 'is_overdue', 'is_urgent',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creator', 'completed_at', 'started_at', 'total_time_seconds', 'created_at', 'updated_at']
    
    def get_due_time(self, obj):
        """Extract time from due_date"""
        if obj.due_date:
            return obj.due_date.strftime('%H:%M')
        return None


class TaskCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating tasks
    """
    due_time = serializers.TimeField(required=False, allow_null=True, write_only=True)
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'company', 'assignee', 'due_date',
            'due_time', 'priority', 'tags', 'metadata'
        ]
    
    def validate_title(self, value):
        """Validate title is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value
    
    def validate_due_date(self, value):
        """Validate due date is not in the past (allow today)"""
        from django.utils import timezone
        from datetime import datetime, time
        
        # Get today's date at midnight
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # If value is a date object, convert to datetime at midnight
        if isinstance(value, datetime):
            value_start = value.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # If it's a date object, convert to datetime
            value_start = timezone.make_aware(datetime.combine(value, time.min))
        
        # Only reject dates that are strictly in the past (before today)
        if value_start < today_start:
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value
    
    def create(self, validated_data):
        """Create task, combining due_date and due_time"""
        from django.utils import timezone
        from datetime import datetime, time
        
        # Extract due_time if provided
        due_time = validated_data.pop('due_time', None)
        due_date = validated_data.get('due_date')
        
        # If due_time is provided, combine it with due_date
        if due_time and due_date:
            if isinstance(due_date, datetime):
                # If due_date is already a datetime, replace the time
                due_date = due_date.replace(hour=due_time.hour, minute=due_time.minute, second=due_time.second)
            else:
                # If due_date is a date, convert to datetime with the specified time
                due_date = timezone.make_aware(datetime.combine(due_date, due_time))
            validated_data['due_date'] = due_date
        
        return super().create(validated_data)


class TaskUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating tasks
    """
    due_time = serializers.TimeField(required=False, allow_null=True, write_only=True)
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'assignee', 'due_date', 'due_time', 'priority',
            'status', 'tags', 'metadata'
        ]
    
    def update(self, instance, validated_data):
        """Update task, combining due_date and due_time if provided"""
        from django.utils import timezone
        from datetime import datetime, time
        
        # Extract due_time if provided
        due_time = validated_data.pop('due_time', None)
        
        # If due_time is provided, combine it with due_date
        if due_time:
            due_date = validated_data.get('due_date', instance.due_date)
            if due_date:
                if isinstance(due_date, datetime):
                    # If due_date is already a datetime, replace the time
                    due_date = due_date.replace(hour=due_time.hour, minute=due_time.minute, second=due_time.second)
                else:
                    # If due_date is a date, convert to datetime with the specified time
                    due_date = timezone.make_aware(datetime.combine(due_date, due_time))
                validated_data['due_date'] = due_date
        
        return super().update(instance, validated_data)



class ApprovalSerializer(serializers.ModelSerializer):
    """
    Serializer for approval details
    """
    approver_name = serializers.CharField(source='approver.full_name', read_only=True)
    is_pending = serializers.ReadOnlyField()
    is_approved = serializers.ReadOnlyField()
    is_rejected = serializers.ReadOnlyField()
    
    class Meta:
        model = Approval
        fields = [
            'id', 'request', 'approver', 'approver_name', 'step_number',
            'status', 'comments', 'approved_at', 'is_pending', 'is_approved',
            'is_rejected', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'request', 'approver', 'approved_at', 'created_at', 'updated_at']


class RequestListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing requests (minimal fields)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    requester_name = serializers.CharField(source='requester.full_name', read_only=True)
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    is_pending = serializers.ReadOnlyField()
    is_approved = serializers.ReadOnlyField()
    is_rejected = serializers.ReadOnlyField()
    
    class Meta:
        model = Request
        fields = [
            'id', 'request_type', 'request_type_display', 'company', 'company_name',
            'requester', 'requester_name', 'status', 'data', 'submission_date',
            'is_pending', 'is_approved', 'is_rejected', 'created_at', 'metadata'
        ]
        read_only_fields = ['id', 'submission_date', 'created_at']


class RequestDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for request details (all fields with approvals)
    """
    company_name = serializers.CharField(source='company.name', read_only=True)
    requester_name = serializers.CharField(source='requester.full_name', read_only=True)
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    approvals = ApprovalSerializer(many=True, read_only=True)
    is_pending = serializers.ReadOnlyField()
    is_approved = serializers.ReadOnlyField()
    is_rejected = serializers.ReadOnlyField()
    
    class Meta:
        model = Request
        fields = [
            'id', 'request_type', 'request_type_display', 'company', 'company_name',
            'requester', 'requester_name', 'status', 'data', 'submission_date',
            'completion_date', 'approvals', 'is_pending', 'is_approved',
            'is_rejected', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'requester', 'submission_date', 'completion_date',
            'created_at', 'updated_at'
        ]


class RequestCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating requests
    """
    class Meta:
        model = Request
        fields = ['request_type', 'company', 'data', 'metadata']
    
    def validate_data(self, value):
        """Validate data is not empty"""
        if not value:
            raise serializers.ValidationError("Request data cannot be empty.")
        return value


class RequestUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating requests
    """
    class Meta:
        model = Request
        fields = ['data', 'metadata']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """
    Serializer for leave balance details
    """
    staff_name = serializers.CharField(source='staff.user.full_name', read_only=True)
    staff_email = serializers.CharField(source='staff.user.email', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    # Calculated fields from model properties
    annual_remaining = serializers.ReadOnlyField()
    sick_remaining = serializers.ReadOnlyField()
    maternity_remaining = serializers.ReadOnlyField()
    paternity_remaining = serializers.ReadOnlyField()
    emergency_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'staff', 'staff_name', 'staff_email', 'company', 'company_name',
            'annual_entitlement', 'annual_used', 'annual_remaining',
            'sick_entitlement', 'sick_used', 'sick_remaining',
            'maternity_entitlement', 'maternity_used', 'maternity_remaining',
            'paternity_entitlement', 'paternity_used', 'paternity_remaining',
            'emergency_entitlement', 'emergency_used', 'emergency_remaining',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
