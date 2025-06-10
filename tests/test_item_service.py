from sqlalchemy import text

from app.services import item_service


def test_add_new_item_inserts_row(sqlite_engine):
    details = {
        "name": "Widget",
        "purchase_unit": "box",
        "base_unit": "each",
        "conversion_factor": 12,
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
        row = conn.execute(
            text(
                "SELECT purchase_unit, base_unit, conversion_factor "
                "FROM items WHERE name='Widget'"
            )
        )
        result = row.fetchone()
        assert result == ("box", "each", 12.0)


def test_update_item_details_updates_unit_fields(sqlite_engine):
    details = {
        "name": "Gadget",
        "purchase_unit": "bag",
        "base_unit": "g",
        "conversion_factor": 1000,
        "category": "c",
        "sub_category": "s",
        "reorder_point": 0,
        "current_stock": 0,
        "is_active": True,
    }
    success, _ = item_service.add_new_item(sqlite_engine, details)
    assert success
    with sqlite_engine.connect() as conn:
        item_id = conn.execute(
            text("SELECT item_id FROM items WHERE name='Gadget'")
        ).scalar_one()

    ok, _ = item_service.update_item_details(
        sqlite_engine,
        item_id,
        {"purchase_unit": "box", "conversion_factor": 500},
    )
    assert ok

    with sqlite_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT purchase_unit, conversion_factor FROM items "
                "WHERE item_id=:i"
            ),
            {"i": item_id},
        ).fetchone()
        assert row == ("box", 500.0)

