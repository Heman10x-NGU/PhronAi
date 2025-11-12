"""
PHRONAI URL Configuration
"""

from django.contrib import admin
from django.urls import path
from django.http import JsonResponse


def health_check(request):
    """Simple health check endpoint."""
    return JsonResponse({
        "status": "healthy",
        "service": "phronai",
        "version": "1.0.0"
    })


def readiness_check(request):
    """Kubernetes readiness probe."""
    # TODO: Add DB and Redis connectivity checks
    return JsonResponse({
        "ready": True,
        "checks": {
            "database": True,
            "redis": True
        }
    })


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health"),
    path("health/ready/", readiness_check, name="readiness"),
]
