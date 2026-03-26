"""
URL configuration for communications app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import ai_chat

app_name = 'communications'

router = DefaultRouter()
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'notifications', views.NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('ai-chat/', ai_chat.ai_chat, name='ai-chat'),
]
