"""
Health check endpoint for Railway/Kubernetes.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    """
    Simple health check endpoint.
    Returns 200 OK if the server is running.
    """
    return JsonResponse({
        "status": "healthy",
        "service": "phronai-api",
        "version": "1.0.0",
    })
