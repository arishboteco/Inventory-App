import pytest
from inventory.models import Item, Recipe, RecipeComponent
from inventory.services import recipe_service

@pytest.mark.django_db
def test_create_and_update_components():
    """Components should retain provided units and loss percentages."""
    item = Item.objects.create(name="Flour", base_unit="kg", purchase_unit="bag", current_stock=20)

    data = {
        "name": "Bread",
        "is_active": True,
        "default_yield_unit": "kg",
    }
    components = [
        {
            "component_kind": "ITEM",
            "component_id": item.pk,
            "quantity": 2,
            "unit": "kg",
            "loss_pct": 5,
        }
    ]

    ok, _, rid = recipe_service.create_recipe(data, components)
    assert ok and rid

    component = RecipeComponent.objects.get(parent_recipe_id=rid)
    assert component.unit == "kg"
    assert component.loss_pct == 5

    # update component quantity and loss percentage
    components[0]["quantity"] = 3
    components[0]["loss_pct"] = 10
    ok, _ = recipe_service.update_recipe(rid, data, components)
    assert ok

    component.refresh_from_db()
    assert component.quantity == 3
    assert component.loss_pct == 10

@pytest.mark.django_db
def test_nested_recipes_and_cycle_prevention():
    """Nested recipes are allowed but cycles are rejected."""
    item = Item.objects.create(name="Flour", base_unit="kg")

    dough_data = {
        "name": "Dough",
        "is_active": True,
        "default_yield_unit": "kg",
    }
    dough_components = [
        {"component_kind": "ITEM", "component_id": item.pk, "quantity": 1, "unit": "kg"}
    ]
    ok, _, dough_id = recipe_service.create_recipe(dough_data, dough_components)
    assert ok and dough_id

    bread_data = {
        "name": "Bread",
        "is_active": True,
        "default_yield_unit": "kg",
    }
    bread_components = [
        {"component_kind": "RECIPE", "component_id": dough_id, "quantity": 1, "unit": "kg"}
    ]
    ok, _, bread_id = recipe_service.create_recipe(bread_data, bread_components)
    assert ok and bread_id

    # attempt to introduce cycle: dough uses bread
    dough_components.append(
        {"component_kind": "RECIPE", "component_id": bread_id, "quantity": 1, "unit": "kg"}
    )
    ok, _ = recipe_service.update_recipe(dough_id, dough_data, dough_components)
    assert not ok

@pytest.mark.django_db
def test_record_sale_reduces_nested_stock():
    """record_sale should consume stock through nested components."""
    item = Item.objects.create(name="Flour", base_unit="kg", current_stock=20)

    premix_data = {"name": "PreMix", "is_active": True, "default_yield_unit": "kg"}
    premix_components = [
        {"component_kind": "ITEM", "component_id": item.pk, "quantity": 1, "unit": "kg", "loss_pct": 10}
    ]
    ok, _, premix_id = recipe_service.create_recipe(premix_data, premix_components)
    assert ok

    bread_data = {"name": "Bread", "is_active": True, "default_yield_unit": "kg"}
    bread_components = [
        {"component_kind": "RECIPE", "component_id": premix_id, "quantity": 1, "unit": "kg", "loss_pct": 20}
    ]
    ok, _, bread_id = recipe_service.create_recipe(bread_data, bread_components)
    assert ok

    ok, msg = recipe_service.record_sale(bread_id, 2, "tester")
    assert ok, msg

    item.refresh_from_db()
    expected = 20 - (2 / (1 - 0.2) / (1 - 0.1))
    assert item.current_stock == pytest.approx(expected)

@pytest.mark.django_db
def test_recipe_metadata_fields():
    """Metadata like yield units, tags and type should persist."""
    item = Item.objects.create(name="Lettuce", base_unit="kg")

    data = {
        "name": "Salad",
        "description": "Fresh",
        "is_active": True,
        "type": "FOOD",
        "default_yield_qty": 4,
        "default_yield_unit": "plate",
        "tags": "vegan,healthy",
    }
    components = [{"component_kind": "ITEM", "component_id": item.pk, "quantity": 1, "unit": "kg"}]

    ok, _, rid = recipe_service.create_recipe(data, components)
    assert ok and rid

    recipe = Recipe.objects.get(pk=rid)
    assert recipe.type == "FOOD"
    assert recipe.default_yield_unit == "plate"
    assert recipe.tags == "vegan,healthy"
