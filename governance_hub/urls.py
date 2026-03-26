"""
URL configuration for governance_hub project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.http import JsonResponse
from core.views import ValidationRulesView

# Health check view
def health_check(request):
    """Simple health check endpoint for deployment monitoring"""
    return JsonResponse({'status': 'healthy', 'service': 'ainick-backend'})

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Health check endpoint
    path('api/health/', health_check, name='health-check'),
    
    # Validation rules endpoint
    path('api/validation-rules/', ValidationRulesView.as_view(), name='validation-rules'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API endpoints
    path('api/auth/', include('authentication.urls')),
    path('api/companies/', include('companies.urls')),
    path('api/directors/', include('companies.directors_urls')),
    path('api/staff/', include('staff.urls')),
    path('api/', include('financial.urls')),  # Includes /api/invoices/ and /api/expenses/
    path('api/', include('documents.urls')),  # Includes /api/documents/
    path('api/', include('workflows.urls')),  # Includes /api/tasks/
    path('api/', include('communications.urls')),  # Includes /api/messages/ and /api/notifications/
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
