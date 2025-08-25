"""Core application configuration."""

from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _create_admin_user(sender, **kwargs):
    """Ensure a default ``admin`` superuser exists."""

    from django.contrib.auth import get_user_model

    User = get_user_model()
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", email="", password="admin")


class CoreConfig(AppConfig):
    """Configuration for the core app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):  # pragma: no cover - executed via Django startup
        """Connect signal handlers when the app is ready."""

        post_migrate.connect(
            _create_admin_user, dispatch_uid="core.create_admin_user"
        )
