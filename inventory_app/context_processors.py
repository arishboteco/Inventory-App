from django.conf import settings

from core.config import settings as app_settings


def app_version(request):
    """Expose a cache-busting version for static assets."""
    version = getattr(settings, "STATIC_VERSION", app_settings.static_version)
    return {"STATIC_VERSION": version}


def site_config(request):
    """Expose SiteConfig singleton to every template (currency symbol, business name)."""
    from inventory.models.site_config import SiteConfig

    return {"site_config": SiteConfig.get()}
