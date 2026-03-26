"""
URL configuration for workflows app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'workflows'

router = DefaultRouter()
router.register(r'tasks', views.TaskViewSet, basename='task')
router.register(r'requests', views.RequestViewSet, basename='request')
router.register(r'approvals', views.ApprovalViewSet, basename='approval')
router.register(r'leave-balance', views.LeaveBalanceViewSet, basename='leave-balance')

urlpatterns = [
    path('', include(router.urls)),
]
