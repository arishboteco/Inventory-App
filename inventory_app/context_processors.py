from django.conf import settings

from core.config import settings as app_settings


def _is_lightweight_partial(request):
    """Skip global context that table/card fragments do not render."""

    match = getattr(request, "resolver_match", None)
    url_name = getattr(match, "url_name", "") or ""
    path = getattr(request, "path", "") or ""
    return (
        request.headers.get("HX-Request")
        or url_name.endswith("_table")
        or url_name.endswith("_cards")
        or "/table/" in path
        or "/cards/" in path
    )


def app_version(request):
    """Expose a cache-busting version for static assets."""
    version = getattr(settings, "STATIC_VERSION", app_settings.static_version)
    return {"STATIC_VERSION": version}


def site_config(request):
    """Expose SiteConfig singleton to every template (currency symbol, business name)."""
    if _is_lightweight_partial(request):
        return {}

    from inventory.models.site_config import SiteConfig

    return {"site_config": SiteConfig.get()}
