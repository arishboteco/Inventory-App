"""Core application configuration."""

from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _create_master_user(sender, **kwargs):
    """Ensure a default superuser exists.

    This creates a ``master`` user with password ``admin`` so the
    application always has a default login available. The function is
    attached to Django's ``post_migrate`` signal so it runs after the
    database schema has been created.
    """

    from django.contrib.auth import get_user_model

    User = get_user_model()
    if not User.objects.filter(username="master").exists():
        User.objects.create_superuser("master", email="", password="admin")


class CoreConfig(AppConfig):
    """Configuration for the core app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):  # pragma: no cover - executed via Django startup
        """Connect signal handlers when the app is ready."""

        post_migrate.connect(
            _create_master_user, dispatch_uid="core.create_master_user"
        )
