"""
WSGI config for inventory_app project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.db.utils import OperationalError

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory_app.settings")

try:
    call_command("migrate", interactive=False)
except OperationalError:
    # Database may be unavailable when the server starts; continue without failing.
    pass

application = get_wsgi_application()
