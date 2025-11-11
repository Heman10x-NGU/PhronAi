"""
PHRONAI ASGI Configuration

This module configures Django Channels for WebSocket support.
It routes HTTP requests to Django and WebSocket requests to our agent consumers.
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "phronai.settings")

# Initialize Django ASGI application early to populate the registry
django_asgi_app = get_asgi_application()

# Import routing after Django setup
from agent.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        # HTTP requests go to Django
        "http": django_asgi_app,
        # WebSocket requests go to our agent consumers
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            )
        ),
    }
)
