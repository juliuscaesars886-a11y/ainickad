"""
Admin configuration for authentication app
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms
from .models import UserProfile


class UserProfileCreationForm(forms.ModelForm):
    """Form for creating new users in admin"""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = UserProfile
        fields = ('email', 'full_name', 'role', 'company')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserProfileChangeForm(forms.ModelForm):
    """Form for updating users in admin"""
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Raw passwords are not stored, so there is no way to see this "
            "user's password, but you can change the password using "
            "<a href=\"../password/\">this form</a>."
        ),
    )

    class Meta:
        model = UserProfile
        fields = ('email', 'password', 'full_name', 'role', 'company', 'is_active', 'avatar_url')


@admin.register(UserProfile)
class UserProfileAdmin(BaseUserAdmin):
    """Admin interface for UserProfile model"""

    form = UserProfileChangeForm
    add_form = UserProfileCreationForm

    list_display = ['email', 'full_name', 'role', 'company', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['email', 'full_name']
    ordering = ['-created_at']
    filter_horizontal = ()

    # Defined BEFORE fieldsets to avoid declaration order issues
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_login']

    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal Info', {
            'fields': ('full_name', 'avatar_url')
        }),
        ('Permissions', {
            'fields': ('role', 'company', 'is_active')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'company', 'password1', 'password2'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Return readonly fields.
        'id' is already in readonly_fields so we don't append it again
        to avoid Django raising a duplicate field error.
        """
        return self.readonly_fields
