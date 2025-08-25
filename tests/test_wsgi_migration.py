from unittest.mock import patch
import sys


def test_wsgi_runs_migrate():
    sys.modules.pop("inventory_app.wsgi", None)
    with patch("django.core.management.call_command") as call, patch(
        "django.core.wsgi.get_wsgi_application"
    ):
        import inventory_app.wsgi  # noqa: F401

    call.assert_called_with("migrate", interactive=False)
