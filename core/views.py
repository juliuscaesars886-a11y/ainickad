from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from core.validation_rules import get_validation_rules


class ValidationRulesView(APIView):
    """
    API endpoint for retrieving centralized validation rules.
    
    GET /api/validation-rules/
    Returns all validation rules (email, password, phone, tax ID) with version.
    
    The frontend fetches these rules on app initialization and caches them
    in localStorage. Version is used for cache invalidation.
    
    This endpoint is publicly accessible (no authentication required) because
    validation rules are needed before user authentication.
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        Retrieve all validation rules.
        
        Returns:
            JSON response containing validation rules and version
        """
        rules = get_validation_rules()
        return Response(rules, status=status.HTTP_200_OK)
