"""
Tag Along - Root URL Configuration
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'ok', 'service': 'tag-along-api'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/health/', health_check, name='health-check'),
    path('api/v1/auth/', include('apps.users.urls')),
    path('api/v1/groups/', include('apps.groups.urls')),
    path('api/v1/trips/', include('apps.trips.urls')),
    path('api/v1/expenses/', include('apps.expenses.urls')),
    path('api/v1/locations/', include('apps.locations.urls')),
    path('api/v1/ai/', include('apps.ai_services.urls')),
]

# API documentation
if settings.DEBUG:
    try:
        from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
        urlpatterns += [
            path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
            path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        ]
    except ImportError:
        pass

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
