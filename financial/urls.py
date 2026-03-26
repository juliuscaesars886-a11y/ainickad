"""
URL configuration for financial app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'financial'

router = DefaultRouter()
router.register(r'invoices', views.InvoiceViewSet, basename='invoice')
router.register(r'expenses', views.ExpenseViewSet, basename='expense')
router.register(r'petty-cash', views.PettyCashRequestViewSet, basename='petty-cash')

urlpatterns = [
    path('', include(router.urls)),
]
