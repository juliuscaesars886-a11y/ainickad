"""
Authentication middleware for role-based access control

DEPLOYMENT: Force redeploy to apply staff approvals access fix
"""
import logging
from django.http import JsonResponse
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status
from .models import UserProfile

logger = logging.getLogger(__name__)


class RoleBasedAccessMiddleware(MiddlewareMixin):
    """
    Middleware to enforce role-based access control on API endpoints
    """
    
    # Define role hierarchy (higher index = higher privilege)
    ROLE_HIERARCHY = {
        'staff': 0,
        'accountant': 1,
        'admin': 2,
        'super_admin': 3
    }
    
    # Define minimum required role for each page
    PAGE_ROLE_REQUIREMENTS = {
        '/': 'staff',
        '/companies': 'staff',
        '/documents': 'staff',
        '/staff': 'admin',
        '/user-management': 'super_admin',
        '/assistant': 'staff',
        '/settings': 'admin',
        '/accounting': 'accountant',
        '/templates': 'staff',
        '/annual-returns': 'admin',
        '/tasks': 'staff',
        '/approvals': 'staff',  # Changed from 'admin' to 'staff' - staff can see approvals for their own requests
        '/notifications': 'staff',
        '/messages': 'staff',
        '/requests': 'staff'
    }
    
    # Define role-based page access permissions (must match frontend roleManager.ts)
    ROLE_PERMISSIONS = {
        'super_admin': [
            '/', '/companies', '/documents', '/staff', '/user-management',
            '/assistant', '/settings', '/accounting', '/templates',
            '/annual-returns', '/tasks', '/approvals', '/notifications', '/messages'
        ],
        'admin': [
            '/', '/companies', '/documents', '/staff', '/assistant',
            '/settings', '/accounting', '/templates', '/annual-returns',
            '/tasks', '/approvals', '/notifications', '/messages'
        ],
        'accountant': [
            '/', '/assistant', '/accounting', '/notifications', '/messages'
        ],
        'staff': [
            '/', '/companies', '/documents', '/templates', '/tasks',
            '/requests', '/approvals', '/assistant', '/notifications', '/messages'  # Added /approvals
        ]
    }
    
    # API endpoints that require role validation
    PROTECTED_API_PATTERNS = [
        'companies',
        'documents', 
        'staff',
        'user-management',
        'accounting',
        'templates',
        'annual-returns',
        'tasks',
        'approvals',
        'requests',
        'notifications',
        'messages'
    ]
    
    # Endpoints that bypass role checking (auth, public APIs)
    BYPASS_PATTERNS = [
        'auth',
        'csrf',
        'admin',
        'api-docs',
        'swagger',
        'redoc'
    ]

    def process_request(self, request):
        """
        Process incoming request and validate role-based access
        """
        # Skip validation for non-API requests
        if not request.path.startswith('/api/'):
            return None
            
        # Skip validation for bypass patterns
        for pattern in self.BYPASS_PATTERNS:
            if pattern in request.path:
                return None
        
        # Skip validation for unauthenticated requests (handled by DRF permissions)
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
            
        # Get the URL pattern name
        try:
            resolved = resolve(request.path)
            url_name = resolved.url_name
            namespace = resolved.namespace
        except:
            # If URL resolution fails, allow the request to proceed
            return None
        
        # Check if this is a protected API endpoint
        is_protected = any(pattern in request.path for pattern in self.PROTECTED_API_PATTERNS)
        
        if is_protected:
            # Validate user role access
            user_role = getattr(request.user, 'role', None)
            if not user_role:
                logger.warning(f"User {request.user.email} has no role assigned")
                return JsonResponse(
                    {'error': 'User role not found', 'code': 'NO_ROLE'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Map API endpoint to frontend page for permission checking
            page_path = self._map_api_to_page(request.path)
            
            if page_path:
                # Check if user has sufficient role level for this page
                if not self._has_sufficient_role(user_role, page_path):
                    logger.warning(
                        f"Access denied: User {request.user.email} ({user_role}) "
                        f"attempted to access {request.path} (mapped to {page_path})"
                    )
                    return JsonResponse(
                        {
                            'error': 'Access denied',
                            'code': 'INSUFFICIENT_PERMISSIONS',
                            'required_role': self.PAGE_ROLE_REQUIREMENTS.get(page_path, 'super_admin'),
                            'user_role': user_role
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
        
        # Log successful access for security monitoring
        if is_protected:
            logger.info(
                f"[SECURITY] API Access: {request.user.email} ({getattr(request.user, 'role', 'unknown')}) "
                f"-> {request.method} {request.path}"
            )
        
        return None
    
    def _map_api_to_page(self, api_path):
        """
        Map API endpoint to corresponding frontend page path
        """
        mapping = {
            '/api/companies': '/companies',
            '/api/documents': '/documents',
            '/api/staff': '/staff',
            '/api/user-management': '/user-management',
            '/api/accounting': '/accounting',
            '/api/templates': '/templates',
            '/api/annual-returns': '/annual-returns',
            '/api/tasks': '/tasks',
            '/api/approvals': '/approvals',
            '/api/requests': '/requests',
            '/api/notifications': '/notifications',
            '/api/messages': '/messages',
        }
        
        # Check for exact matches first
        for api_pattern, page_path in mapping.items():
            if api_path.startswith(api_pattern):
                return page_path
        
        return None
    
    def _get_required_role(self, page_path):
        """
        Get the minimum required role for a page
        """
        return self.PAGE_ROLE_REQUIREMENTS.get(page_path, 'super_admin')
    
    def _has_sufficient_role(self, user_role, page_path):
        """
        Check if user's role has sufficient privilege level for the page.
        Uses role hierarchy to allow higher roles to access lower role pages.
        """
        required_role = self.PAGE_ROLE_REQUIREMENTS.get(page_path)
        if not required_role:
            return True  # No requirement, allow access
        
        user_level = self.ROLE_HIERARCHY.get(user_role, -1)
        required_level = self.ROLE_HIERARCHY.get(required_role, -1)
        
        # User must have equal or higher privilege level
        return user_level >= required_level


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Middleware to enhance session security
    """
    
    # Session timeout in seconds (30 minutes)
    SESSION_TIMEOUT = 30 * 60
    
    def process_request(self, request):
        """
        Process request for session security validation
        """
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        # Skip session security checks for API requests (they use Token auth, not session auth)
        if request.path.startswith('/api/'):
            return None
        
        # Check session timeout
        if hasattr(request, 'session'):
            last_activity = request.session.get('last_activity')
            if last_activity:
                import time
                if time.time() - last_activity > self.SESSION_TIMEOUT:
                    logger.info(f"Session timeout for user {request.user.email}")
                    request.session.flush()
                    return JsonResponse(
                        {'error': 'Session expired', 'code': 'SESSION_TIMEOUT'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            
            # Update last activity
            import time
            request.session['last_activity'] = time.time()
        
        # Validate session integrity (only for non-API requests)
        stored_user_id = request.session.get('_auth_user_id')
        if stored_user_id and str(request.user.id) != str(stored_user_id):
            logger.error(
                f"Session integrity violation: stored_id={stored_user_id}, "
                f"current_id={request.user.id}, user={request.user.email}"
            )
            request.session.flush()
            return JsonResponse(
                {'error': 'Session integrity violation', 'code': 'SESSION_INVALID'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        return None


class SecurityLoggingMiddleware(MiddlewareMixin):
    """
    Middleware for security event logging
    """
    
    def process_request(self, request):
        """
        Log security-relevant events
        """
        # Log authentication attempts
        if request.path.startswith('/api/auth/'):
            logger.info(f"[SECURITY] Auth attempt: {request.method} {request.path} from {self._get_client_ip(request)}")
        
        # Log admin panel access
        if request.path.startswith('/admin/'):
            if hasattr(request, 'user') and request.user.is_authenticated:
                logger.info(f"[SECURITY] Admin access: {request.user.email} -> {request.path}")
        
        return None
    
    def process_response(self, request, response):
        """
        Log security-relevant responses
        """
        # Log failed authentication attempts
        if (request.path.startswith('/api/auth/') and 
            response.status_code in [401, 403]):
            logger.warning(
                f"[SECURITY] Auth failed: {request.method} {request.path} "
                f"-> {response.status_code} from {self._get_client_ip(request)}"
            )
        
        return response
    
    def _get_client_ip(self, request):
        """
        Get client IP address from request
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip