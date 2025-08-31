"""
WSGI config for inventory_app project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

from core.config import settings as app_settings

os.environ.setdefault("DJANGO_ENV", app_settings.django_env)
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", app_settings.django_settings_module
)

# Database migrations should be run separately before launching the application.
application = get_wsgi_application()
