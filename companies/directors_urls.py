"""
URL configuration for directors
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'directors'

router = DefaultRouter()
router.register(r'', views.DirectorViewSet, basename='director')

urlpatterns = [
    path('', include(router.urls)),
]
