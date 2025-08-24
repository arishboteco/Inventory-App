from inventory.services.ui_service import build_component_options


def test_build_component_options_basic():
    items = [
        {
            "item_id": 1,
            "name": "Flour",
            "base_unit": "kg",
            "purchase_unit": "bag",
            "category": "Baking",
            "current_stock": 10,
        }
    ]
    recipes = [
        {
            "recipe_id": 10,
            "name": "Bread",
            "default_yield_unit": "loaf",
            "tags": ["baked"],
        }
    ]
    options, meta = build_component_options(items, recipes, placeholder="Choose")
    assert options == [
        "Choose",
        "Flour (1) | kg | Baking | 10.00",
        "Bread | loaf | baked",
    ]
    flour_label = "Flour (1) | kg | Baking | 10.00"
    bread_label = "Bread | loaf | baked"
    assert meta[flour_label] == {
        "kind": "ITEM",
        "id": 1,
        "base_unit": "kg",
        "purchase_unit": "bag",
        "category": "Baking",
        "name": "Flour",
    }
    assert meta[bread_label]["kind"] == "RECIPE"
    assert meta[bread_label]["id"] == 10
