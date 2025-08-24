from pydantic import BaseModel

from inventory.services.ui_service import autofill_component_meta


def test_autofill_component_meta_populates_unit_and_category():
    rows = [
        {
            "component": "Flour (1) | kg | Baking | 10.00",
            "unit": None,
            "category": None,
        },
        {"component": "Unknown", "unit": None, "category": None},
    ]
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {"base_unit": "kg", "category": "Baking"}
    }
    result = autofill_component_meta(rows, choice_map)
    assert result[0]["unit"] == "kg"
    assert result[0]["category"] == "Baking"
    assert result[1]["unit"] is None and result[1]["category"] is None


class RowModel(BaseModel):
    component: str
    unit: str | None = None
    category: str | None = None


def test_autofill_component_meta_accepts_models():
    rows = [
        RowModel(component="Flour (1) | kg | Baking | 10.00"),
        RowModel(component="Unknown"),
    ]
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {"base_unit": "kg", "category": "Baking"}
    }
    result = autofill_component_meta(rows, choice_map)
    assert result[0]["unit"] == "kg"
    assert result[0]["category"] == "Baking"
    assert result[1]["unit"] is None and result[1]["category"] is None
