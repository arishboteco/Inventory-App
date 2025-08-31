#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import sys
import os

from core.config import settings as app_settings


def main():
    """Run administrative tasks."""
    # Ensure the expected settings module and environment are set
    os.environ.setdefault("DJANGO_ENV", app_settings.django_env)
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", app_settings.django_settings_module
    )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
