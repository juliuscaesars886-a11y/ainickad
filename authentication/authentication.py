"""
Admin configuration for authentication app
"""
from django.contrib import admin
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
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile model"""
    
    form = UserProfileChangeForm
    add_form = UserProfileCreationForm
    
    list_display = ['email', 'full_name', 'role', 'company', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['email', 'full_name']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'avatar_url')}),
        ('Permissions', {'fields': ('role', 'company', 'is_active')}),
        ('Metadata', {'fields': ('metadata',), 'classes': ('collapse',)}),
        ('Important dates', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'company', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    filter_horizontal = ()
    
    def get_readonly_fields(self, request, obj=None):
        """Make created_at and updated_at readonly"""
        if obj:  # editing an existing object
            return self.readonly_fields
        return self.readonly_fields
       
