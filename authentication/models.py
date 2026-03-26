"""
Authentication models for Governance Hub
"""
import uuid
from django.db import models
from django.contrib.auth.hashers import make_password, check_password as django_check_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class UserProfileManager(BaseUserManager):
    """Manager for UserProfile model"""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a user with an email and password"""
        if not email:
            raise ValueError('Users must have an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('role', 'super_admin')
        extra_fields.setdefault('is_active', True)
        user = self.create_user(email, password, **extra_fields)
        return user


class UserProfile(AbstractBaseUser):
    """
    User profile with Django authentication.

    This model stores user information and handles authentication.
    """

    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
        ('accountant', 'Accountant'),
        ('staff', 'Staff'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    password = models.CharField(max_length=128, default='')
    temp_password = models.CharField(max_length=255, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='staff',
        db_index=True
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
        db_index=True
    )
    avatar_url = models.URLField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserProfileManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'user_profiles'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['company', 'role']),
        ]

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    # --- Role helpers ---

    @property
    def is_super_admin(self):
        return self.role == 'super_admin'

    @property
    def is_admin(self):
        return self.role in ['super_admin', 'admin']

    @property
    def is_accountant(self):
        return self.role in ['super_admin', 'admin', 'accountant']

    @property
    def can_approve(self):
        return self.role in ['super_admin', 'admin', 'accountant']

    # --- Django auth interface ---

    @property
    def is_authenticated(self):
        """Always True for authenticated users. Required by DRF."""
        return True

    @property
    def is_anonymous(self):
        """Always False for authenticated users. Required by DRF."""
        return False

    @property
    def is_staff(self):
        """Controls access to Django admin panel."""
        return self.role in ['super_admin', 'admin']

    @property
    def is_superuser(self):
        """Full permissions — only super_admin."""
        return self.role == 'super_admin'

    def has_perm(self, perm, obj=None):
        """Super admins have all permissions."""
        return self.is_superuser

    def has_module_perms(self, app_label):
        """Admins and super admins can view all apps in admin."""
        return self.is_staff

    # --- Password handling ---

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return django_check_password(raw_password, self.password)

