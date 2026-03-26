"""
Error Handlers for AI Assistant

Provides centralized error handling functions for all response handlers.
Each error handler logs the error with appropriate severity and returns
a user-friendly error message.

Error Types:
- Permission errors: User lacks permission to access requested data
- Math errors: Invalid mathematical expressions or evaluation failures
- Database errors: Database query failures or connection issues
- Memory errors: Session or persistent memory operation failures
- Classification errors: Message classification failures
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def handle_permission_error(
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    error: Optional[Exception] = None
) -> str:
    """
    Handle permission denied scenarios.
    
    Args:
        user_id: ID of the user who was denied access
        resource_type: Type of resource that was denied (e.g., "company data", "financial data")
        error: Optional exception that was raised
    
    Returns:
        User-friendly error message
    """
    # Log the permission error
    log_msg = f"Permission denied for user {user_id}"
    if resource_type:
        log_msg += f" accessing {resource_type}"
    if error:
        log_msg += f": {error}"
    
    logger.warning(log_msg, exc_info=error is not None)
    
    # Return user-friendly message
    if resource_type:
        return (
            f"You don't have permission to access {resource_type}. "
            "Please contact your administrator if you believe this is an error."
        )
    else:
        return (
            "You don't have permission to access this information. "
            "Please contact your administrator if you believe this is an error."
        )


def handle_math_error(
    expression: str,
    error: Exception
) -> str:
    """
    Handle math evaluation errors.
    
    Args:
        expression: The mathematical expression that failed
        error: The exception that was raised
    
    Returns:
        User-friendly error message with guidance
    """
    # Log the math error
    logger.warning(
        f"Math evaluation error for expression '{expression}': {error}",
        exc_info=True
    )
    
    # Determine error type and provide specific guidance
    error_msg = str(error).lower()
    
    if 'division by zero' in error_msg or 'zerodivision' in error_msg:
        return (
            "**Math Error**: Cannot divide by zero.\n\n"
            "Please check your expression and try again."
        )
    elif 'invalid' in error_msg or 'syntax' in error_msg:
        return (
            "**Math Error**: Invalid expression syntax.\n\n"
            "I can calculate expressions with:\n"
            "- Basic operators: +, -, *, /, %\n"
            "- Exponentiation: **\n"
            "- Parentheses for grouping\n\n"
            "Example: \"(5 + 3) * 2\" or \"100 / 3\""
        )
    elif 'disallowed' in error_msg or 'dangerous' in error_msg:
        return (
            "**Math Error**: Expression contains disallowed operations.\n\n"
            "For security reasons, I can only evaluate basic arithmetic expressions. "
            "Function calls, imports, and code execution are not allowed."
        )
    else:
        return (
            "**Math Error**: I couldn't evaluate that expression.\n\n"
            "I can calculate expressions with:\n"
            "- Basic operators: +, -, *, /, %\n"
            "- Exponentiation: **\n"
            "- Parentheses for grouping\n\n"
            "Example: \"(5 + 3) * 2\" or \"100 / 3\""
        )


def handle_database_error(
    operation: str,
    model_name: Optional[str] = None,
    error: Exception = None
) -> str:
    """
    Handle database query failures.
    
    Args:
        operation: Description of the database operation that failed
        model_name: Name of the Django model being queried
        error: The exception that was raised
    
    Returns:
        User-friendly error message
    """
    # Log the database error with high severity
    log_msg = f"Database error during {operation}"
    if model_name:
        log_msg += f" on {model_name}"
    if error:
        log_msg += f": {error}"
    
    logger.error(log_msg, exc_info=error is not None)
    
    # Return user-friendly message
    if model_name:
        return (
            f"I encountered an error retrieving {model_name.lower()} information. "
            "Please try again in a moment. If the problem persists, contact support."
        )
    else:
        return (
            "I encountered a database error. "
            "Please try again in a moment. If the problem persists, contact support."
        )


def handle_memory_error(
    operation: str,
    user_id: Optional[int] = None,
    error: Exception = None
) -> str:
    """
    Handle memory operation failures (session or persistent memory).
    
    Args:
        operation: Description of the memory operation that failed
        user_id: ID of the user whose memory operation failed
        error: The exception that was raised
    
    Returns:
        User-friendly error message (or None to continue gracefully)
    """
    # Log the memory error
    log_msg = f"Memory error during {operation}"
    if user_id:
        log_msg += f" for user {user_id}"
    if error:
        log_msg += f": {error}"
    
    logger.warning(log_msg, exc_info=error is not None)
    
    # Memory errors should not block the user - return None to continue gracefully
    # The calling code should check for None and continue without memory features
    return None


def handle_classification_error(
    message: str,
    error: Exception
) -> str:
    """
    Handle classification failures.
    
    Args:
        message: The user message that failed to classify
        error: The exception that was raised
    
    Returns:
        User-friendly error message with suggestions
    """
    # Log the classification error
    logger.error(
        f"Classification error for message '{message[:100]}...': {error}",
        exc_info=True
    )
    
    # Return user-friendly message with suggestions
    return (
        "I'm having trouble understanding your question. Could you try rephrasing it?\n\n"
        "**Here are some examples of what I can help with**:\n"
        "- \"What are the annual return requirements?\"\n"
        "- \"Show me my companies\"\n"
        "- \"How do I add a director?\"\n"
        "- \"What are the tax deadlines?\"\n"
        "- \"Calculate 50000 * 0.15\"\n\n"
        "What would you like to know?"
    )


def handle_knowledge_base_error(
    filename: str,
    error: Exception
) -> str:
    """
    Handle knowledge base file reading errors.
    
    Args:
        filename: Name of the knowledge base file that failed to load
        error: The exception that was raised
    
    Returns:
        User-friendly error message
    """
    # Log the knowledge base error
    logger.error(
        f"Knowledge base error reading file '{filename}': {error}",
        exc_info=True
    )
    
    # Return user-friendly message
    return (
        "I'm having trouble accessing my knowledge base. "
        "Please try again in a moment. If the problem persists, contact support."
    )


def handle_generic_error(
    operation: str,
    error: Exception
) -> str:
    """
    Handle generic errors that don't fit other categories.
    
    Args:
        operation: Description of the operation that failed
        error: The exception that was raised
    
    Returns:
        User-friendly error message
    """
    # Log the generic error
    logger.error(
        f"Error during {operation}: {error}",
        exc_info=True
    )
    
    # Return user-friendly message
    return (
        "I encountered an unexpected error. "
        "Please try again in a moment. If the problem persists, contact support."
    )
