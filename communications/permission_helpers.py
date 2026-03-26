"""
Permission scoping helpers for AI Assistant.

This module provides permission-based data filtering to ensure users only access
data within their permission scope:
- Superadmin: All data across all accounts
- Company Admin: Only their company's data
- Staff: Only data assigned to or created by them

Security-critical: Always defaults to most restrictive permissions on errors.
"""
import logging
from enum import Enum
from typing import Optional
from django.db.models import Q, QuerySet

logger = logging.getLogger(__name__)


class PermissionScope(Enum):
    """
    User permission scopes for data access control.
    
    Defines three levels of data visibility:
    - SUPERADMIN: Access to all data across all accounts
    - COMPANY_ADMIN: Access to data within user's company only
    - STAFF: Access to data assigned to or created by the user only
    """
    SUPERADMIN = "superadmin"
    COMPANY_ADMIN = "company_admin"
    STAFF = "staff"


def get_permission_scope(user_id: int) -> PermissionScope:
    """
    Determine user's permission scope based on their role.
    
    Args:
        user_id: The ID of the user to check permissions for
        
    Returns:
        PermissionScope enum value indicating the user's access level
        
    Permission mapping:
    - Superadmin/is_superuser → SUPERADMIN (all data)
    - Admin/company_admin role → COMPANY_ADMIN (company data only)
    - Other roles → STAFF (assigned/created data only)
    
    Security: Defaults to STAFF (most restrictive) on any error.
    """
    try:
        from authentication.models import UserProfile
        
        user = UserProfile.objects.get(id=user_id)
        
        # Check for superadmin access
        if user.is_superuser or user.role == 'super_admin':
            return PermissionScope.SUPERADMIN
        
        # Check for company admin access
        if user.role in ['admin', 'company_admin']:
            return PermissionScope.COMPANY_ADMIN
        
        # Default to staff access
        return PermissionScope.STAFF
    
    except UserProfile.DoesNotExist:
        logger.error(f"User with ID {user_id} does not exist")
        return PermissionScope.STAFF  # Most restrictive default
    
    except Exception as e:
        logger.error(f"Error determining permission scope for user {user_id}: {e}")
        return PermissionScope.STAFF  # Most restrictive default


def apply_permission_filter(
    queryset: QuerySet,
    user_id: int,
    permission_scope: PermissionScope
) -> QuerySet:
    """
    Apply permission-based filtering to a Django queryset.
    
    Args:
        queryset: The Django queryset to filter
        user_id: The ID of the user requesting data
        permission_scope: The user's permission scope
        
    Returns:
        Filtered queryset based on permission scope
        
    Filtering rules:
    - SUPERADMIN: No filtering (returns queryset as-is)
    - COMPANY_ADMIN: Filters by user's company (checks 'company' or 'company_id' field)
    - STAFF: Filters by assigned_to or created_by fields
    
    Security: Returns empty queryset on any error to prevent data leakage.
    """
    try:
        from authentication.models import UserProfile
        
        # Superadmin sees all data
        if permission_scope == PermissionScope.SUPERADMIN:
            return queryset
        
        # Get user for filtering
        user = UserProfile.objects.get(id=user_id)
        
        # Company admin sees only their company's data
        if permission_scope == PermissionScope.COMPANY_ADMIN:
            # Check if model has company field
            if hasattr(queryset.model, 'company'):
                return queryset.filter(company=user.company)
            elif hasattr(queryset.model, 'company_id'):
                return queryset.filter(company_id=user.company_id)
            else:
                # Model doesn't have company field, return as-is
                logger.warning(
                    f"Model {queryset.model.__name__} has no company field, "
                    f"cannot apply company filtering"
                )
                return queryset
        
        # Staff sees only data assigned to or created by them
        if permission_scope == PermissionScope.STAFF:
            filters = Q()
            
            # Check for assigned_to field
            if hasattr(queryset.model, 'assigned_to'):
                filters |= Q(assigned_to=user)
            
            # Check for created_by field
            if hasattr(queryset.model, 'created_by'):
                filters |= Q(created_by=user)
            
            # If model has neither field, log warning and return empty queryset
            if not filters:
                logger.warning(
                    f"Model {queryset.model.__name__} has no assigned_to or created_by field, "
                    f"returning empty queryset for staff user"
                )
                return queryset.none()
            
            return queryset.filter(filters)
        
        # Unknown permission scope, return empty queryset
        logger.error(f"Unknown permission scope: {permission_scope}")
        return queryset.none()
    
    except UserProfile.DoesNotExist:
        logger.error(f"User with ID {user_id} does not exist")
        return queryset.none()  # Return empty queryset on error
    
    except Exception as e:
        logger.error(
            f"Error applying permission filter for user {user_id}: {e}",
            exc_info=True
        )
        return queryset.none()  # Return empty queryset on error
