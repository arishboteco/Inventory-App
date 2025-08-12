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


def test_suggest_category_and_units(sqlite_engine):
    """Database-backed suggestions should return units and category."""
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO items (
                    name, base_unit, purchase_unit, category, sub_category,
                    permitted_departments, reorder_point, current_stock, notes, is_active
                ) VALUES (
                    'Fresh Milk', 'L', 'case', 'Dairy', 'General', 'Kitchen', 0, 0, '', 1
                )
                """
            )
        )

    base, purchase, category = item_service.suggest_category_and_units(
        sqlite_engine, "Whole Milk"
    )
    assert (base, purchase, category) == ("L", "case", "Dairy")


def test_add_items_bulk_inserts_rows(sqlite_engine):
    items = [
        {
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
        },
        {
            "name": "Gadget",
            "base_unit": "pcs",
            "purchase_unit": "each",
            "category": "cat",
            "sub_category": "sub",
            "permitted_departments": "dept2",
            "reorder_point": 2,
            "current_stock": 0,
            "notes": "n",
            "is_active": True,
        },
    ]
    inserted, errors = item_service.add_items_bulk(sqlite_engine, items)
    assert inserted == 2
    assert errors == []
    with sqlite_engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM items WHERE name IN ('Widget','Gadget')")
        ).scalar_one()
        assert count == 2


def test_add_items_bulk_validation_failure(sqlite_engine):
    items = [
        {"name": "Widget", "base_unit": "pcs"},
        {"name": "", "base_unit": "pcs"},
    ]
    inserted, errors = item_service.add_items_bulk(sqlite_engine, items)
    assert inserted == 0
    assert errors
    with sqlite_engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM items")).scalar_one()
        assert count == 0


def test_remove_items_bulk_marks_inactive(sqlite_engine):
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO items (
                    name, base_unit, purchase_unit, category, sub_category,
                    permitted_departments, reorder_point, current_stock, notes, is_active
                ) VALUES
                    ('Widget', 'pcs', 'box', 'cat', 'sub', 'dept', 1, 0, 'n', 1),
                    ('Gadget', 'pcs', 'each', 'cat', 'sub', 'dept2', 2, 0, 'n', 1)
                """
            )
        )
        ids = conn.execute(text("SELECT item_id FROM items"))
        item_ids = [row[0] for row in ids.fetchall()]
    removed, errors = item_service.remove_items_bulk(sqlite_engine, item_ids)
    assert removed == len(item_ids)
    assert errors == []
    with sqlite_engine.connect() as conn:
        inactive = conn.execute(
            text("SELECT COUNT(*) FROM items WHERE is_active = 0")
        ).scalar_one()
        assert inactive == len(item_ids)


def test_remove_items_bulk_requires_ids(sqlite_engine):
    removed, errors = item_service.remove_items_bulk(sqlite_engine, [])
    assert removed == 0
    assert errors

