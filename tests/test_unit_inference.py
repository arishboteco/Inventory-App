import pytest
from django.db import connection

from inventory.models import (
    Item,
    StockTransaction,
    RecipeComponent,
    Recipe,
    IndentItem,
    PurchaseOrderItem,
)
from inventory.services import item_service
from django.db.utils import OperationalError

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_items(db):
    for model in (
        RecipeComponent,
        Recipe,
        IndentItem,
        PurchaseOrderItem,
        StockTransaction,
        Item,
    ):
        try:
            model.objects.all().delete()
        except OperationalError:
            pass
    item_service.suggest_category_and_units.clear()


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
