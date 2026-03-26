"""
Centralized validation rules for the Governance Hub application.

This module defines all validation patterns and rules that are shared between
frontend and backend. The backend serves these rules via API, and the frontend
fetches and caches them for client-side validation.

Version is used for cache invalidation - increment when rules change.
"""

import re

# API version for cache invalidation
VERSION = "1.0.0"

# Email validation pattern
EMAIL_PATTERN = {
    "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "message": "Invalid email address"
}

# Password validation rules
PASSWORD_RULES = {
    "min_length": 8,
    "uppercase": True,
    "lowercase": True,
    "number": True,
    "special": True,
    "message": "Password must be at least 8 characters with uppercase, lowercase, number, and special character"
}

# Phone number validation pattern
PHONE_PATTERN = {
    "pattern": r"^[\+]?[0-9\s\-\(\)]{7,}$",
    "message": "Invalid phone number format"
}

# Tax ID validation patterns by country
TAX_ID_PATTERN = {
    "patterns": {
        "KE": r"^[0-9]{10}$",  # Kenya: 10 digits
        "UG": r"^[0-9]{14}$",  # Uganda: 14 digits
        "TZ": r"^[0-9]{9}$",   # Tanzania: 9 digits
        "RW": r"^[0-9]{9}$",   # Rwanda: 9 digits
        "ZA": r"^[0-9]{10}$",  # South Africa: 10 digits
    },
    "message": "Invalid tax ID format for the specified country"
}


def validate_email(email: str) -> tuple[bool, str]:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    pattern = EMAIL_PATTERN["pattern"]
    if not re.match(pattern, email):
        return False, EMAIL_PATTERN["message"]
    
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password against rules.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    rules = PASSWORD_RULES
    
    if len(password) < rules["min_length"]:
        return False, f"Password must be at least {rules['min_length']} characters"
    
    if rules["uppercase"] and not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if rules["lowercase"] and not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if rules["number"] and not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number"
    
    if rules["special"] and not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        return False, "Password must contain at least one special character"
    
    return True, ""


def validate_phone(phone: str) -> tuple[bool, str]:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return True, ""  # Phone is optional
    
    pattern = PHONE_PATTERN["pattern"]
    if not re.match(pattern, phone):
        return False, PHONE_PATTERN["message"]
    
    return True, ""


def validate_tax_id(tax_id: str, country: str) -> tuple[bool, str]:
    """
    Validate tax ID format for a specific country.
    
    Args:
        tax_id: Tax ID to validate
        country: Country code (e.g., 'KE', 'UG')
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not tax_id:
        return False, "Tax ID is required"
    
    if country not in TAX_ID_PATTERN["patterns"]:
        return False, f"Unsupported country code: {country}"
    
    pattern = TAX_ID_PATTERN["patterns"][country]
    if not re.match(pattern, tax_id):
        return False, TAX_ID_PATTERN["message"]
    
    return True, ""


def get_validation_rules() -> dict:
    """
    Get all validation rules as a dictionary.
    
    Returns:
        Dictionary containing all validation rules and version
    """
    return {
        "version": VERSION,
        "email": EMAIL_PATTERN,
        "password": PASSWORD_RULES,
        "phone": PHONE_PATTERN,
        "taxId": TAX_ID_PATTERN,
    }
