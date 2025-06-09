from sqlalchemy import text

from app.services import item_service


def test_add_new_item_inserts_row(sqlite_engine):
    details = {
        "name": "Widget",
        "unit": "pcs",
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
