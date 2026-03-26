"""
Authentication views for Governance Hub
"""
import logging
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import UserProfile
from .serializers import (
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    LoginSerializer,
    RegisterSerializer,
    ChangePasswordSerializer
)

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
@require_http_methods(["GET"])
def get_csrf_token(request):
    """
    API endpoint to get CSRF token.
    This endpoint ensures the CSRF cookie is set in the response.
    
    GET: Returns CSRF token for the client to use in POST requests
    """
    token = get_token(request)
    return JsonResponse({
        'csrfToken': token,
        'message': 'CSRF token generated successfully'
    })


@extend_schema(
    request=LoginSerializer,
    responses={200: UserProfileSerializer},
    description="Login with email and password"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Login with email and password.
    Creates a session for the authenticated user and returns an authentication token.
    """
    serializer = LoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    try:
        # Use Django's authenticate function with custom backend
        user_profile = authenticate(request, username=email, password=password)
        
        if not user_profile:
            return Response(
                {'error': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if user is active
        if not user_profile.is_active:
            return Response(
                {'error': 'Account is inactive'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # CRITICAL: Ensure user has a company assigned (for existing users who might not have one)
        # This is essential for request creation and task assignment
        if not user_profile.company:
            from companies.models import Company
            
            # Try to get the first active company
            default_company = Company.objects.filter(is_active=True).first()
            
            # If no active company exists, create one
            if not default_company:
                logger.info("No active company found. Creating default company...")
                default_company = Company.objects.create(
                    name='Default Company',
                    registration_number='DEFAULT-001',
                    tax_id='TAX-DEFAULT-001',
                    address='Default Address',
                    contact_email='admin@company.com',
                    contact_phone='+254700000000',
                    risk_level='level_2',
                    risk_category='general_business',
                    is_active=True
                )
                logger.info(f"Default company created: {default_company.name}")
            
            # Assign the company to the user
            user_profile.company = default_company
            user_profile.save(update_fields=['company'])
            logger.info(f"Assigned company to user {user_profile.email}: {default_company.name}")
            
            # If user has a Staff record, also update that
            try:
                if hasattr(user_profile, 'staff'):
                    user_profile.staff.company = default_company
                    user_profile.staff.save(update_fields=['company'])
                    logger.info(f"Also updated Staff record for {user_profile.email}")
            except Exception as e:
                logger.warning(f"Could not update Staff record for {user_profile.email}: {e}")
        
        # Create session
        login(request, user_profile)
        
        # Generate or get authentication token
        token, created = Token.objects.get_or_create(user=user_profile)
        
        logger.info(f"User logged in: {user_profile.email}")
        
        response_serializer = UserProfileSerializer(user_profile)
        return Response(
            {
                'message': 'Login successful',
                'user': response_serializer.data,
                'token': token.key
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Login failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    responses={200: {'message': 'Logout successful'}},
    description="Logout current user"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout current user and destroy session.
    Also clears AI assistant session memory.
    """
    try:
        user_id = request.user.id
        logger.info(f"User logged out: {request.user.email}")
        
        # Clear AI assistant session memory
        try:
            from communications.memory_helpers import clear_session_memory
            clear_session_memory(user_id)
            logger.debug(f"Cleared session memory for user {user_id}")
        except Exception as mem_error:
            # Don't fail logout if memory clearing fails
            logger.warning(f"Failed to clear session memory for user {user_id}: {mem_error}")
        
        logout(request)
        return Response(
            {'message': 'Logout successful'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response(
            {'error': 'Logout failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    request=RegisterSerializer,
    responses={201: UserProfileSerializer},
    description="Register a new user"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    Register a new user account.
    """
    serializer = RegisterSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Check if user already exists
        if UserProfile.objects.filter(email=serializer.validated_data['email']).exists():
            return Response(
                {'error': 'User with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the first available company to assign to the user
        from companies.models import Company
        default_company = Company.objects.filter(is_active=True).first()
        
        # If no company exists, create a default one
        if not default_company:
            logger.info("No active company found. Creating default company...")
            default_company = Company.objects.create(
                name='Default Company',
                registration_number='DEFAULT-001',
                tax_id='TAX-DEFAULT-001',
                address='Default Address',
                contact_email='admin@company.com',
                contact_phone='+254700000000',
                risk_level='level_2',
                risk_category='general_business',
                is_active=True
            )
            logger.info(f"Default company created: {default_company.name}")
        
        # Create user
        user_profile = UserProfile.objects.create(
            email=serializer.validated_data['email'],
            full_name=serializer.validated_data.get('full_name', ''),
            role=serializer.validated_data.get('role', 'staff'),
            company=default_company,  # Assign default company
            is_active=True
        )
        
        # Set password
        user_profile.set_password(serializer.validated_data['password'])
        user_profile.temp_password = serializer.validated_data['password']
        user_profile.save()
        
        logger.info(f"New user registered: {user_profile.email} (assigned to company: {default_company.name if default_company else 'None'})")
        
        response_serializer = UserProfileSerializer(user_profile)
        return Response(
            {
                'message': 'Registration successful',
                'user': response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return Response(
            {'error': 'Registration failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class CurrentUserView(generics.RetrieveUpdateAPIView):
    """
    Get or update the current authenticated user's profile.
    
    GET: Returns the current user's profile
    PATCH: Updates the current user's profile (limited fields)
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return UserProfileUpdateSerializer
        return UserProfileSerializer
    
    def get_object(self):
        """Return the current authenticated user"""
        return self.request.user
    
    @extend_schema(
        responses={200: UserProfileSerializer},
        description="Get current user profile"
    )
    def get(self, request, *args, **kwargs):
        """Get current user profile"""
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        request=UserProfileUpdateSerializer,
        responses={200: UserProfileSerializer},
        description="Update current user profile"
    )
    def patch(self, request, *args, **kwargs):
        """Update current user profile"""
        response = super().patch(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_200_OK:
            logger.info(f"User profile updated: {request.user.email}")
        
        return response


class ProfilesListView(generics.ListAPIView):
    """
    List all user profiles (for messaging, staff lists, etc.)
    
    GET: Returns a list of all active user profiles
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.filter(is_active=True).order_by('full_name')
    
    @extend_schema(
        responses={200: UserProfileSerializer(many=True)},
        description="Get list of all user profiles"
    )
    def get(self, request, *args, **kwargs):
        """Get list of all user profiles"""
        return super().get(request, *args, **kwargs)


class ProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a user profile.
    
    GET: Returns a specific user profile
    PATCH: Updates a specific user profile
    DELETE: Deletes a specific user profile (admin only)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    lookup_field = 'id'
    
    @extend_schema(
        responses={200: UserProfileSerializer},
        description="Get a specific user profile"
    )
    def get(self, request, *args, **kwargs):
        """Get a specific user profile"""
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        request=UserProfileUpdateSerializer,
        responses={200: UserProfileSerializer},
        description="Update a specific user profile"
    )
    def patch(self, request, *args, **kwargs):
        """Update a specific user profile"""
        return super().patch(request, *args, **kwargs)
    
    @extend_schema(
        responses={204: None},
        description="Delete a specific user profile (admin only)"
    )
    def delete(self, request, *args, **kwargs):
        """Delete a specific user profile (admin only)"""
        if not request.user.is_super_admin:
            return Response(
                {'error': 'Only super admins can delete user profiles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_profile = self.get_object()
        logger.info(f"User profile deleted: {user_profile.email} by {request.user.email}")
        return super().delete(request, *args, **kwargs)




@extend_schema(
    request=ChangePasswordSerializer,
    responses={200: {'message': 'Password changed successfully'}},
    description="Change user password. Super admins can change any user's password."
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """
    Change user password.
    Super admins can change any user's password by providing user_id.
    Regular users can only change their own password.
    """
    serializer = ChangePasswordSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user_id = serializer.validated_data.get('user_id')
        new_password = serializer.validated_data['new_password']
        
        # Determine which user's password to change
        if user_id:
            # Super admin changing another user's password
            if not request.user.is_super_admin:
                return Response(
                    {'error': 'Only super admins can change other users\' passwords'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            try:
                target_user = UserProfile.objects.get(id=user_id)
            except UserProfile.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # User changing their own password
            target_user = request.user
        
        # Set the new password
        target_user.set_password(new_password)
        target_user.save()
        
        logger.info(f"Password changed for user: {target_user.email} by {request.user.email}")
        
        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Password change error: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Password change failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

