import pytest
from django.db import connection

from inventory.models import Item
from inventory.services import item_service


@pytest.fixture(autouse=True)
def clear_items():
    Item.objects.all().delete()
    item_service.suggest_category_and_units.clear()


def setup_module(module):
    with connection.schema_editor() as editor:
        editor.create_model(Item)
    item_service.suggest_category_and_units.clear()


def teardown_module(module):
    with connection.schema_editor() as editor:
        editor.delete_model(Item)


def test_suggest_from_similar_item():
    Item.objects.create(
        name="Whole Milk",
        base_unit="ltr",
        purchase_unit="carton",
        category="Dairy",
        sub_category="General",
        permitted_departments=None,
        reorder_point=0,
        notes=None,
        is_active=True,
    )
    base, purchase, category = item_service.suggest_category_and_units("Skim Milk")
    assert base == "ltr"
    assert purchase == "carton"
    assert category == "Dairy"


def test_suggest_returns_none_if_no_match():
    base, purchase, category = item_service.suggest_category_and_units("Widget")
    assert base is None and purchase is None and category is None

