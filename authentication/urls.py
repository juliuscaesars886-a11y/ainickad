"""
URL configuration for authentication app
"""
from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # CSRF token endpoint - MUST be first
    path('csrf-token/', views.get_csrf_token, name='csrf-token'),
    
    # Authentication endpoints
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('me/', views.CurrentUserView.as_view(), name='current-user'),
    path('profiles/', views.ProfilesListView.as_view(), name='profiles-list'),
    path('profiles/<str:id>/', views.ProfileDetailView.as_view(), name='profile-detail'),
    path('change-password/', views.change_password_view, name='change-password'),
]
