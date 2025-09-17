from pydantic import BaseModel

from inventory.constants import PLACEHOLDER_SELECT_COMPONENT
from inventory.services.recipe_service import build_items_from_editor


def test_build_items_autofill_and_validation():
    rows = [
        {
            "item": "Flour (1) | kg | Baking | 10.00",  # label; irrelevant
            "quantity": 2,
            "unit": None,
            "loss_pct": 0,
            "sort_order": 1,
            "notes": None,
        },
        {
            "item": "Dough | kg | tag",  # sub-recipe label
            "quantity": 1,
            "unit": None,
            "loss_pct": 0,
            "sort_order": 2,
            "notes": None,
        },
    ]
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {
            "id": 1,
            "unit_id": 19,
            "category": "Baking",
            "name": "Flour",
        },
        "Dough | kg | tag": {
            "id": 2,
            "unit_id": 19,  # Assuming kg maps to unit_id 19
            "category": "Sub-recipe",
            "name": "Dough",
        },
    }
    items, errs = build_items_from_editor(rows, choice_map)
    assert not errs
    assert items[0]["unit"] == "KG" and items[0]["item_id"] == 1
    assert items[1]["unit"] == "KG" and items[1]["item_id"] == 2


def test_build_items_detects_unit_mismatch():
    rows = [
        {
            "item": "Flour (1) | kg | Baking | 10.00",
            "quantity": 1,
            "unit": "g",  # wrong unit
            "loss_pct": 0,
            "sort_order": 1,
            "notes": None,
        }
    ]
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {
            "id": 1,
            "unit_id": 19,
            "category": "Baking",
            "name": "Flour",
        }
    }
    items, errs = build_items_from_editor(rows, choice_map)
    assert errs and "Unit mismatch" in errs[0]
    assert not items


def test_build_items_rejects_wrong_unit():
    rows = [
        {
            "item": "Flour (1) | kg | Baking | 10.00",
            "quantity": 3,
            "unit": "bag",  # wrong unit
            "loss_pct": 0,
            "sort_order": 1,
            "notes": None,
        }
    ]
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {
            "id": 1,
            "unit_id": 19,
            "category": "Baking",
            "name": "Flour",
        }
    }
    items, errs = build_items_from_editor(rows, choice_map)
    assert errs  # Should have error about unit mismatch
    assert "Unit mismatch" in errs[0]


def test_build_items_skips_placeholder():
    rows = [
        {
            "item": PLACEHOLDER_SELECT_COMPONENT,
            "quantity": 1,
            "unit": None,
            "loss_pct": 0,
            "sort_order": 1,
            "notes": None,
        }
    ]
    items, errs = build_items_from_editor(rows, {})
    assert not items
    assert not errs


class ItemRow(BaseModel):
    item: str
    quantity: float
    unit: str | None = None
    loss_pct: float = 0
    sort_order: int = 1
    notes: str | None = None


def test_build_items_from_editor_accepts_models():
    rows = [
        ItemRow(item="Flour (1) | kg | Baking | 10.00", quantity=2),
        ItemRow(item=PLACEHOLDER_SELECT_COMPONENT, quantity=1),
    ]
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {
            "id": 1,
            "unit_id": 19,
            "category": "Baking",
            "name": "Flour",
        }
    }
    items, errs = build_items_from_editor(rows, choice_map)
    assert not errs
    assert items[0]["unit"] == "KG"
    assert items[0]["item_id"] == 1
