"""
Custom exception handlers and domain exceptions for Governance Hub API
"""
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


# Domain Exception Hierarchy
class DomainException(Exception):
    """Base exception for all domain-level errors.
    
    Domain exceptions represent business logic errors that should be caught
    and translated to appropriate HTTP responses by views.
    """
    pass


class BusinessLogicError(DomainException):
    """Raised when a business rule is violated.
    
    Example: Attempting to complete a task that's already completed.
    """
    pass


class ValidationError(DomainException):
    """Raised when data validation fails.
    
    Includes field-specific error messages for detailed error reporting.
    """
    def __init__(self, field_errors: dict = None, message: str = None):
        """Initialize ValidationError.
        
        Args:
            field_errors: Dictionary mapping field names to error messages
            message: Optional general error message
        """
        self.field_errors = field_errors or {}
        self.message = message or "Validation failed"
        super().__init__(self.message)


class PermissionError(DomainException):
    """Raised when a user lacks permission to perform an action.
    
    Example: Non-admin user attempting to delete another user.
    """
    pass


class ResourceNotFoundError(DomainException):
    """Raised when a requested resource doesn't exist.
    
    Example: Attempting to update a task that doesn't exist.
    """
    pass


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    
    This handler wraps Django REST Framework's default exception handler
    and adds additional logging and formatting for better error tracking.
    """
    # Call DRF's default exception handler first
    response = drf_exception_handler(exc, context)
    
    if response is not None:
        # Log the exception
        logger.error(
            f"API Exception: {exc.__class__.__name__} - {str(exc)}",
            extra={
                'status_code': response.status_code,
                'view': context.get('view'),
                'request': context.get('request'),
            }
        )
        
        # Customize the response format
        custom_response_data = {
            'error': True,
            'message': str(exc),
            'status_code': response.status_code,
        }
        
        # Add detail if available
        if hasattr(response, 'data') and isinstance(response.data, dict):
            if 'detail' in response.data:
                custom_response_data['detail'] = response.data['detail']
            else:
                custom_response_data['detail'] = response.data
        
        response.data = custom_response_data
    else:
        # Handle unexpected exceptions
        logger.exception(
            f"Unhandled Exception: {exc.__class__.__name__}",
            extra={
                'view': context.get('view'),
                'request': context.get('request'),
            }
        )
        
        # Return a generic error response
        response = Response(
            {
                'error': True,
                'message': 'An unexpected error occurred.',
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return response
