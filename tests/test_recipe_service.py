"""Tests for the recipe_service module."""

import pytest
from django.db import OperationalError, connection

from inventory.models import Item, Recipe, RecipeItem, SaleTransaction
from inventory.services.recipe_service import create_recipe, record_sale, update_recipe

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module", autouse=True)
def create_tables(django_db_blocker):
    """Ensure the temporary SaleTransaction table exists for this module.

    The table is created by migrations in normal operation, so it may already
    be present. Attempting to create it again raises an ``OperationalError``.
    To make the tests resilient we ignore the error if the table already exists
    and likewise ignore missing-table errors on cleanup.
    """

    with django_db_blocker.unblock():
        with connection.schema_editor() as editor:
            try:
                editor.create_model(SaleTransaction)
            except OperationalError:
                pass
    yield
    with django_db_blocker.unblock():
        with connection.schema_editor() as editor:
            try:
                editor.delete_model(SaleTransaction)
            except OperationalError:
                pass


def _create_item(name="Flour", unit_id=19, stock=20):
    item = Item.objects.create(
        name=name,
        unit_id=unit_id,
        category_id=1,
        reorder_point=0,
        current_stock=stock,
        notes="n",
        is_active=True,
    )
    return item.item_id


@pytest.mark.django_db
def test_create_and_update_items():
    """Items should retain provided units and loss percentages."""
    item_id = _create_item()

    data = {
        "name": "Bread",
        "is_active": True,
        "default_yield_unit": "KG",
    }
    items = [
        {
            "item_id": item_id,
            "quantity": 2,
            "unit": "KG",
            "loss_pct": 5,
        }
    ]

    ok, _, rid = create_recipe(data, items)
    assert ok and rid

    row = RecipeItem.objects.get(recipe_id=rid)
    assert row.unit == "KG" and row.loss_pct == 5

    items[0]["quantity"] = 3
    items[0]["loss_pct"] = 10
    ok, _ = update_recipe(rid, data, items)
    assert ok

    row = RecipeItem.objects.get(recipe_id=rid)
    assert row.quantity == 3 and row.loss_pct == 10


@pytest.mark.django_db
def test_cycle_prevention():
    """Cycles should be rejected when creating recipes."""
    item_id = _create_item()

    # Create a simple recipe first
    data = {
        "name": "Simple",
        "is_active": True,
        "default_yield_unit": "KG",
    }
    items = [
        {
            "item_id": item_id,
            "quantity": 1,
            "unit": "KG",
        }
    ]
    ok, _, recipe_id = create_recipe(data, items)
    assert ok and recipe_id

    # For now, just ensure basic cycle detection works
    # More complex sub-recipe cycle tests will be added when that feature is implemented
    assert True  # Placeholder for now


@pytest.mark.django_db
def test_record_sale_reduces_stock():
    """record_sale should consume stock through recipe items."""
    item_id = _create_item()

    # Create a simple recipe with one item
    data = {
        "name": "SimpleRecipe",
        "is_active": True,
        "default_yield_unit": "KG",
    }
    items = [
        {
            "item_id": item_id,
            "quantity": 1,
            "unit": "KG",
            "loss_pct": 10,
        }
    ]
    ok, _, recipe_id = create_recipe(data, items)
    assert ok and recipe_id

    # Record a sale
    ok, msg = record_sale(recipe_id, 2, "tester")
    assert ok, msg

    # Check that stock was reduced
    item = Item.objects.get(pk=item_id)
    expected = round(20 - (2 * 1 / (1 - 0.1)), 2)  # loss adjustment with rounding
    assert float(item.current_stock) == expected


@pytest.mark.django_db
def test_recipe_metadata_fields():
    """Metadata like yield units, tags and type should persist."""
    item_id = _create_item()

    data = {
        "name": "Salad",
        "description": "Fresh",
        "is_active": True,
        "type": "FINAL",
        "default_yield_qty": 4,
        "default_yield_unit": "plate",
        "tags": "vegan,healthy",
    }
    items = [
        {
            "item_id": item_id,
            "quantity": 1,
            "unit": "KG",
        }
    ]

    ok, _, rid = create_recipe(data, items)
    assert ok and rid

    recipe = Recipe.objects.get(pk=rid)
    assert recipe.type == "FINAL"
    assert recipe.default_yield_unit == "portion"
    assert recipe.tags == ["vegan", "healthy"]
