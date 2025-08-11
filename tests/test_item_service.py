from sqlalchemy import text

from app.services import item_service


def test_add_new_item_inserts_row(sqlite_engine):
    details = {
        "name": "Widget",
        "base_unit": "pcs",
        "purchase_unit": "box",
        "category": "cat",
        "sub_category": "sub",
        "permitted_departments": "dept",
        "reorder_point": 1,
        "current_stock": 0,
        "notes": "n",
        "is_active": True,
    }
    success, msg = item_service.add_new_item(sqlite_engine, details)
    assert success

    with sqlite_engine.connect() as conn:
        row = conn.execute(text("SELECT name FROM items WHERE name='Widget'"))
        assert row.fetchone() is not None


def test_get_all_items_with_stock_includes_unit(sqlite_engine):
    """The service should provide a 'unit' column mirroring 'base_unit'."""
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO items (
                    name, base_unit, purchase_unit, category, sub_category,
                    permitted_departments, reorder_point, current_stock, notes, is_active
                ) VALUES (
                    'Widget', 'pcs', 'box', 'cat', 'sub', 'dept', 1, 5, 'n', 1
                )
                """
            )
        )
    df = item_service.get_all_items_with_stock(sqlite_engine, include_inactive=True)
    assert "unit" in df.columns
    assert df.loc[df["name"] == "Widget", "unit"].iloc[0] == "pcs"


def test_get_item_details_includes_unit(sqlite_engine):
    """The detailed item lookup should include a 'unit' key."""
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO items (
                    name, base_unit, purchase_unit, category, sub_category,
                    permitted_departments, reorder_point, current_stock, notes, is_active
                ) VALUES (
                    'Widget', 'pcs', 'box', 'cat', 'sub', 'dept', 1, 5, 'n', 1
                )
                """
            )
        )
        item_id = conn.execute(
            text("SELECT item_id FROM items WHERE name='Widget'")
        ).scalar_one()
    details = item_service.get_item_details(sqlite_engine, item_id)
    assert details["unit"] == "pcs"

