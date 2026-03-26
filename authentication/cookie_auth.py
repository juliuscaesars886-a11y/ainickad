"""
Cookie-based JWT Authentication

Custom authentication class that reads JWT tokens from httpOnly cookies
instead of the Authorization header.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads tokens from httpOnly cookies.
    
    This provides better security than localStorage by preventing XSS attacks
    from accessing the JWT tokens.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using JWT token from cookie.
        
        First tries to get token from cookie, then falls back to Authorization header
        for backward compatibility.
        """
        # Try to get token from cookie first
        raw_token = request.COOKIES.get('access_token')
        
        # Fall back to Authorization header if cookie not present
        if raw_token is None:
            header = self.get_header(request)
            if header is None:
                return None
            
            raw_token = self.get_raw_token(header)
        
        if raw_token is None:
            return None
        
        # Validate token
        validated_token = self.get_validated_token(raw_token)
        
        # Get user from token
        return self.get_user(validated_token), validated_token
