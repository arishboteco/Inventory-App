from sqlalchemy import text

from inventory.services import item_service


def test_suggest_from_similar_item(sqlite_engine):
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO items (
                    name, base_unit, purchase_unit, category, sub_category,
                    permitted_departments, reorder_point, current_stock, notes, is_active
                ) VALUES (
                    'Whole Milk', 'ltr', 'carton', 'Dairy', 'General', NULL, 0, 0, NULL, 1
                )
                """
            )
        )
    base, purchase, category = item_service.suggest_category_and_units(
        sqlite_engine, "Skim Milk"
    )
    assert base == "ltr"
    assert purchase == "carton"
    assert category == "Dairy"


def test_suggest_returns_none_if_no_match(sqlite_engine):
    base, purchase, category = item_service.suggest_category_and_units(
        sqlite_engine, "Widget"
    )
    assert base is None and purchase is None and category is None
