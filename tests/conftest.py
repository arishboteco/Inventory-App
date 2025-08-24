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
