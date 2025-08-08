import pandas as pd
from app.services import recipe_service

def test_build_components_autofill_and_validation():
    df = pd.DataFrame([
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
    ])
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {
            "kind": "ITEM",
            "id": 1,
            "unit": "kg",
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
    comps, errs = recipe_service.build_components_from_editor(df, choice_map)
    assert not errs
    assert comps[0]["unit"] == "kg" and comps[0]["component_id"] == 1
    assert comps[1]["unit"] == "kg" and comps[1]["component_id"] == 2

def test_build_components_detects_unit_mismatch():
    df = pd.DataFrame([
        {
            "component": "Flour (1) | kg | Baking | 10.00",
            "quantity": 1,
            "unit": "g",  # wrong unit
            "loss_pct": 0,
            "sort_order": 1,
            "notes": None,
        }
    ])
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {
            "kind": "ITEM",
            "id": 1,
            "unit": "kg",
            "category": "Baking",
            "name": "Flour",
        }
    }
    comps, errs = recipe_service.build_components_from_editor(df, choice_map)
    assert errs and "Unit mismatch" in errs[0]
    assert not comps
