"""
ASGI config for inventory_app project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

from core.config import settings as app_settings

os.environ.setdefault("DJANGO_ENV", app_settings.django_env)
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", app_settings.django_settings_module
)

application = get_asgi_application()
