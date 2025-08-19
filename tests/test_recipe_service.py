"""Tests for the recipe_service module."""

import pytest
from django.db import connection

from inventory.models import (
    Item,
    Recipe,
    RecipeComponent,
    StockTransaction,
    SaleTransaction,
)
from inventory.services.recipe_service import (
    create_recipe,
    update_recipe,
    record_sale,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module", autouse=True)
def create_tables(django_db_blocker):
    with django_db_blocker.unblock():
        with connection.schema_editor() as editor:
            editor.create_model(SaleTransaction)
    yield
    with django_db_blocker.unblock():
        with connection.schema_editor() as editor:
            editor.delete_model(SaleTransaction)


def _create_item(name="Flour", base_unit="kg", purchase_unit="bag", stock=20):
    item = Item.objects.create(
        name=name,
        base_unit=base_unit,
        purchase_unit=purchase_unit,
        category="cat",
        sub_category="sub",
        permitted_departments="dept",
        reorder_point=0,
        current_stock=stock,
        notes="n",
        is_active=True,
    )
    return item.item_id


@pytest.mark.django_db
def test_create_and_update_components():
    """Components should retain provided units and loss percentages."""
    item_id = _create_item()

    data = {
        "name": "Bread",
        "is_active": True,
        "default_yield_unit": "kg",
    }
    components = [
        {
            "component_kind": "ITEM",
            "component_id": item_id,
            "quantity": 2,
            "unit": "kg",
            "loss_pct": 5,
        }
    ]

    ok, _, rid = create_recipe(data, components)
    assert ok and rid

    row = RecipeComponent.objects.get(parent_recipe_id=rid)
    assert row.unit == "kg" and row.loss_pct == 5

    components[0]["quantity"] = 3
    components[0]["loss_pct"] = 10
    ok, _ = update_recipe(rid, data, components)
    assert ok

    row = RecipeComponent.objects.get(parent_recipe_id=rid)
    assert row.quantity == 3 and row.loss_pct == 10


@pytest.mark.django_db
def test_nested_recipes_and_cycle_prevention():
    """Nested recipes are allowed but cycles are rejected."""
    item_id = _create_item()

    dough_data = {
        "name": "Dough",
        "is_active": True,
        "default_yield_unit": "kg",
    }
    dough_components = [
        {
            "component_kind": "ITEM",
            "component_id": item_id,
            "quantity": 1,
            "unit": "kg",
        }
    ]
    ok, _, dough_id = create_recipe(dough_data, dough_components)
    assert ok and dough_id

    bread_data = {
        "name": "BreadCycle",
        "is_active": True,
        "default_yield_unit": "kg",
    }
    bread_components = [
        {
            "component_kind": "RECIPE",
            "component_id": dough_id,
            "quantity": 1,
            "unit": "kg",
        }
    ]
    ok, _, bread_id = create_recipe(bread_data, bread_components)
    assert ok and bread_id

    dough_components.append(
        {
            "component_kind": "RECIPE",
            "component_id": bread_id,
            "quantity": 1,
            "unit": "kg",
        }
    )
    ok, _ = update_recipe(dough_id, dough_data, dough_components)
    assert not ok


@pytest.mark.django_db
def test_record_sale_reduces_nested_stock():
    """record_sale should consume stock through nested components."""
    item_id = _create_item()

    premix = Recipe.objects.create(name="PreMix", is_active=True, default_yield_unit="kg")
    RecipeComponent.objects.create(
        parent_recipe=premix,
        component_kind="ITEM",
        component_id=item_id,
        quantity=1,
        unit="kg",
        loss_pct=10,
    )

    bread = Recipe.objects.create(name="BreadSale", is_active=True, default_yield_unit="kg")
    RecipeComponent.objects.create(
        parent_recipe=bread,
        component_kind="RECIPE",
        component_id=premix.recipe_id,
        quantity=1,
        unit="kg",
        loss_pct=20,
    )

    ok, msg = record_sale(bread.recipe_id, 2, "tester")
    assert ok, msg

    item = Item.objects.get(pk=item_id)
    expected = 20 - (2 * 1 / (1 - 0.2) / (1 - 0.1))
    assert item.current_stock == pytest.approx(expected)


@pytest.mark.django_db
def test_recipe_metadata_fields():
    """Metadata like yield units, tags and type should persist."""
    item_id = _create_item()

    data = {
        "name": "Salad",
        "description": "Fresh",
        "is_active": True,
        "type": "FOOD",
        "default_yield_qty": 4,
        "default_yield_unit": "plate",
        "tags": "vegan,healthy",
    }
    components = [
        {
            "component_kind": "ITEM",
            "component_id": item_id,
            "quantity": 1,
            "unit": "kg",
        }
    ]

    ok, _, rid = create_recipe(data, components)
    assert ok and rid

    recipe = Recipe.objects.get(pk=rid)
    assert recipe.type == "FOOD"
    assert recipe.default_yield_unit == "plate"
    assert recipe.tags == "vegan,healthy"
