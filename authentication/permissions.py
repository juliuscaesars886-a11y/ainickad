"""
Custom permission classes for role-based access control
"""
from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission class that only allows super admins.
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated and has super_admin role"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            return request.user.profile.role == 'super_admin'
        except AttributeError:
            return False


class IsAdmin(permissions.BasePermission):
    """
    Permission class that allows super admins and admins.
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated and has admin or super_admin role"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            return request.user.profile.role in ['super_admin', 'admin']
        except AttributeError:
            return False


class IsAccountant(permissions.BasePermission):
    """
    Permission class that allows super admins, admins, and accountants.
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated and has accountant, admin, or super_admin role"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            return request.user.profile.role in ['super_admin', 'admin', 'accountant']
        except AttributeError:
            return False


class CanApprove(permissions.BasePermission):
    """
    Permission class that allows users who can approve requests.
    Typically super admins, admins, and accountants.
    """
    
    def has_permission(self, request, view):
        """Check if user is authenticated and can approve"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            return request.user.profile.can_approve
        except AttributeError:
            return False


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class that allows owners of an object or admins.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user is the owner or an admin"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            # Check if user is admin
            if request.user.profile.is_admin:
                return True
            
            # Check if user is the owner
            if hasattr(obj, 'user'):
                return obj.user == request.user
            elif hasattr(obj, 'created_by'):
                return obj.created_by == request.user
            elif hasattr(obj, 'owner'):
                return obj.owner == request.user
            
            return False
        except AttributeError:
            return False
