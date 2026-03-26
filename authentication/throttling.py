"""
Rate limiting (throttling) classes for authentication endpoints

This module provides rate limiting to prevent brute force attacks on authentication endpoints.
"""
from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Rate limiter for login endpoint to prevent brute force attacks.
    
    Limits anonymous users to 5 login attempts per minute.
    This helps prevent credential stuffing and brute force attacks.
    
    Usage:
        Apply to login view using throttle_classes:
        
        class CustomTokenObtainPairView(TokenObtainPairView):
            throttle_classes = [LoginRateThrottle]
    
    Configuration:
        Rate: 5 attempts per minute (5/minute)
        Scope: 'login' (can be customized in settings.py)
    
    Validates: Requirement 2.8 from production-security-hardening spec
    """
    
    # Rate: 5 attempts per minute (reasonable for login attempts)
    rate = '5/minute'
    
    # Scope for this throttle (can be overridden in settings)
    scope = 'login'
