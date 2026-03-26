"""
URL configuration for staff app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'staff'

router = DefaultRouter()
router.register(r'', views.StaffViewSet, basename='staff')

urlpatterns = [
    path('', include(router.urls)),
]
