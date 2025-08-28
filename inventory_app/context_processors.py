import os
from django.conf import settings


def app_version(request):
    """Expose a cache-busting version for static assets.

    Reads STATIC_VERSION from settings or environment and falls back to 'dev'.
    """
    version = getattr(settings, "STATIC_VERSION", None) or os.environ.get("STATIC_VERSION", "dev")
    return {"STATIC_VERSION": version}

