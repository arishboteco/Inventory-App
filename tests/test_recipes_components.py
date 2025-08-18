from inventory.services.recipe_service import build_components_from_editor
from inventory.constants import PLACEHOLDER_SELECT_COMPONENT
from pydantic import BaseModel

def test_build_components_autofill_and_validation():
    rows = [
        {
            "component": "Flour (1) | kg | Baking | 10.00",  # label; irrelevant
            "quantity": 2,
            "unit": None,
            "loss_pct": 0,
            "sort_order": 1,
            "notes": None,
        },
        {
            "component": "Dough | kg | tag",  # sub-recipe label
            "quantity": 1,
            "unit": None,
            "loss_pct": 0,
            "sort_order": 2,
            "notes": None,
        },
    ]
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {
            "kind": "ITEM",
            "id": 1,
            "base_unit": "kg",
            "purchase_unit": "bag",
            "category": "Baking",
            "name": "Flour",
        },
        "Dough | kg | tag": {
            "kind": "RECIPE",
            "id": 2,
            "unit": "kg",
            "category": "Sub-recipe",
            "name": "Dough",
        },
    }
    comps, errs = build_components_from_editor(rows, choice_map)
    assert not errs
    assert comps[0]["unit"] == "kg" and comps[0]["component_id"] == 1
    assert comps[1]["unit"] == "kg" and comps[1]["component_id"] == 2

def test_build_components_detects_unit_mismatch():
    rows = [
        {
            "component": "Flour (1) | kg | Baking | 10.00",
            "quantity": 1,
            "unit": "g",  # wrong unit
            "loss_pct": 0,
            "sort_order": 1,
            "notes": None,
        }
    ]
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {
            "kind": "ITEM",
            "id": 1,
            "base_unit": "kg",
            "purchase_unit": "bag",
            "category": "Baking",
            "name": "Flour",
        }
    }
    comps, errs = build_components_from_editor(rows, choice_map)
    assert errs and "Unit mismatch" in errs[0]
    assert not comps


def test_build_components_allows_purchase_unit():
    rows = [
        {
            "component": "Flour (1) | kg | Baking | 10.00",
            "quantity": 3,
            "unit": "bag",  # purchase unit
            "loss_pct": 0,
            "sort_order": 1,
            "notes": None,
        }
    ]
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {
            "kind": "ITEM",
            "id": 1,
            "base_unit": "kg",
            "purchase_unit": "bag",
            "category": "Baking",
            "name": "Flour",
        }
    }
    comps, errs = build_components_from_editor(rows, choice_map)
    assert not errs
    assert comps and comps[0]["unit"] == "bag"


def test_build_components_skips_placeholder():
    rows = [
        {
            "component": PLACEHOLDER_SELECT_COMPONENT,
            "quantity": 1,
            "unit": None,
            "loss_pct": 0,
            "sort_order": 1,
            "notes": None,
        }
    ]
    comps, errs = build_components_from_editor(rows, {})
    assert not comps
    assert not errs


class ComponentRow(BaseModel):
    component: str
    quantity: float
    unit: str | None = None
    loss_pct: float = 0
    sort_order: int = 1
    notes: str | None = None


def test_build_components_from_editor_accepts_models():
    rows = [
        ComponentRow(component="Flour (1) | kg | Baking | 10.00", quantity=2),
        ComponentRow(component=PLACEHOLDER_SELECT_COMPONENT, quantity=1),
    ]
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {
            "kind": "ITEM",
            "id": 1,
            "base_unit": "kg",
            "purchase_unit": "bag",
            "category": "Baking",
            "name": "Flour",
        }
    }
    comps, errs = build_components_from_editor(rows, choice_map)
    assert not errs
    assert comps[0]["unit"] == "kg"
    assert comps[0]["component_id"] == 1
