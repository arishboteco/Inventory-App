import os
import sys
import django

import pytest

from inventory.models import Item, Category

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory_app.settings")
django.setup()


@pytest.fixture
def item_factory():
    def create_item(**kwargs):
        category = kwargs.pop("category", "Cat")
        if isinstance(category, str):
            category = Category.objects.create(name=category)
        sub_category = kwargs.pop("sub_category", None)
        if isinstance(sub_category, str) or sub_category is None:
            sub_category = Category.objects.create(name=sub_category or "Sub", parent=category)
        defaults = {
            "name": "Item",
            "base_unit": "kg",
            "purchase_unit": "g",
            "category": category,
            "sub_category": sub_category,
        }
        defaults.update(kwargs)
        return Item.objects.create(**defaults)

    return create_item
