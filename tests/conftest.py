import os
import sys

import django
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory_app.settings")
django.setup()

from inventory.models import Item  # noqa: E402


@pytest.fixture
def item_factory():
    def create_item(**kwargs):
        defaults = {
            "name": "Item",
            "base_unit": "kg",
            "purchase_unit": "g",
            "category_id": 1,
            "is_active": True,
        }
        defaults.update(kwargs)
        return Item.objects.create(**defaults)

    return create_item


@pytest.fixture(autouse=True)
def logged_in_client(client, db):
    """Log in the default admin user for tests that require authentication."""

    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(username="admin")
    if not user.has_usable_password():
        user.set_password("admin")
        user.save()
    client.force_login(user)
    yield
    client.logout()
