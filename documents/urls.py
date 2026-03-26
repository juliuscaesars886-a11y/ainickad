"""
URL configuration for documents app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, TemplateViewSet

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'templates', TemplateViewSet, basename='template')

urlpatterns = [
    path('', include(router.urls)),
]
