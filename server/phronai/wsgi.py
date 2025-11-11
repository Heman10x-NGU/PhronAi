"""
PHRONAI WSGI Configuration
For backwards compatibility with non-async deployments.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "phronai.settings")

application = get_wsgi_application()
