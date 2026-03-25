"""Backward-compatibility alias for inventory_app.settings.prod.

Render's dashboard environment variable DJANGO_SETTINGS_MODULE may point
here. Do not delete this file without updating the Render env var to
``inventory_app.settings.prod``.
"""

from .prod import *  # noqa
