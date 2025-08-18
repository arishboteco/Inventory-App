import pandas as pd
from app.ui.helpers import autofill_component_meta


def test_autofill_component_meta_populates_unit_and_category():
    df = pd.DataFrame(
        {
            "component": ["Flour (1) | kg | Baking | 10.00", "Unknown"],
            "unit": [None, None],
            "category": [None, None],
        }
    )
    choice_map = {
        "Flour (1) | kg | Baking | 10.00": {"base_unit": "kg", "category": "Baking"}
    }
    result = autofill_component_meta(df, choice_map)
    assert result.loc[0, "unit"] == "kg"
    assert result.loc[0, "category"] == "Baking"
    assert pd.isna(result.loc[1, "unit"]) and pd.isna(result.loc[1, "category"])
