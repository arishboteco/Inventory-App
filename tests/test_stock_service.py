from sqlalchemy import text

from app.services import stock_service


def test_record_stock_transaction_updates_stock_and_logs(sqlite_engine):
    # Insert a sample item with initial stock 10
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, purchase_unit, base_unit, conversion_factor, "
                "category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active) "
                "VALUES ('Sample', 'box', 'each', 1, 'cat', 'sub', 'dept', 0, 10, 'n', 1)"
            )
        )
        item_id = conn.execute(text("SELECT item_id FROM items LIMIT 1")).scalar_one()

    success = stock_service.record_stock_transaction(
        item_id=item_id,
        quantity_change=5,
        transaction_type="RECEIVING",
        user_id="tester",
        db_engine_param=sqlite_engine,
    )
    assert success

    with sqlite_engine.connect() as conn:
        current = conn.execute(text("SELECT current_stock FROM items WHERE item_id=:i"), {"i": item_id}).scalar_one()
        assert current == 15
        count = conn.execute(text("SELECT COUNT(*) FROM stock_transactions WHERE item_id=:i"), {"i": item_id}).scalar_one()
        assert count == 1

