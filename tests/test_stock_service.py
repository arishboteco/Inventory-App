from sqlalchemy import text

from legacy_streamlit.services import stock_service


def test_record_stock_transaction_updates_stock_and_logs(sqlite_engine):
    # Insert a sample item with initial stock 10
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, base_unit, purchase_unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active) "
                "VALUES ('Sample', 'pcs', 'box', 'cat', 'sub', 'dept', 0, 10, 'n', 1)"
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


def test_record_stock_transactions_bulk(sqlite_engine):
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, base_unit, purchase_unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active) VALUES"
                " ('Item1', 'pcs', 'box', 'cat', 'sub', 'dept', 0, 10, 'n', 1),"
                " ('Item2', 'pcs', 'box', 'cat', 'sub', 'dept', 0, 10, 'n', 1)"
            )
        )
        ids = conn.execute(text("SELECT item_id FROM items ORDER BY item_id"))
        item1_id, item2_id = [row[0] for row in ids.fetchall()]

    transactions = [
        {"item_id": item1_id, "quantity_change": 5, "transaction_type": "RECEIVING", "user_id": "u1"},
        {"item_id": item2_id, "quantity_change": -3, "transaction_type": "ISSUE", "user_id": "u2"},
    ]
    assert stock_service.record_stock_transactions_bulk(sqlite_engine, transactions)

    with sqlite_engine.connect() as conn:
        stock1 = conn.execute(text("SELECT current_stock FROM items WHERE item_id=:i"), {"i": item1_id}).scalar_one()
        stock2 = conn.execute(text("SELECT current_stock FROM items WHERE item_id=:i"), {"i": item2_id}).scalar_one()
        assert stock1 == 15
        assert stock2 == 7
        count = conn.execute(text("SELECT COUNT(*) FROM stock_transactions"))
        assert count.scalar_one() == 2


def test_remove_stock_transactions_bulk(sqlite_engine):
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, base_unit, purchase_unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active) VALUES ('Item', 'pcs', 'box', 'cat', 'sub', 'dept', 0, 20, 'n', 1)"
            )
        )
        item_id = conn.execute(text("SELECT item_id FROM items LIMIT 1")).scalar_one()

    transactions = [
        {"item_id": item_id, "quantity_change": 5, "transaction_type": "RECEIVING"},
        {"item_id": item_id, "quantity_change": -2, "transaction_type": "ISSUE"},
    ]
    assert stock_service.record_stock_transactions_bulk(sqlite_engine, transactions)

    with sqlite_engine.connect() as conn:
        ids = conn.execute(
            text("SELECT transaction_id FROM stock_transactions ORDER BY transaction_id")
        ).fetchall()
        t_ids = [row[0] for row in ids]

    assert stock_service.remove_stock_transactions_bulk(sqlite_engine, t_ids)

    with sqlite_engine.connect() as conn:
        stock = conn.execute(
            text("SELECT current_stock FROM items WHERE item_id=:i"), {"i": item_id}
        ).scalar_one()
        assert stock == 20
        count = conn.execute(text("SELECT COUNT(*) FROM stock_transactions"))
        assert count.scalar_one() == 0


def test_record_stock_transactions_bulk_rollback_on_error(sqlite_engine):
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, base_unit, purchase_unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active) VALUES ('Item', 'pcs', 'box', 'cat', 'sub', 'dept', 0, 10, 'n', 1)"
            )
        )
        item_id = conn.execute(text("SELECT item_id FROM items LIMIT 1")).scalar_one()

    transactions = [
        {"item_id": item_id, "quantity_change": 5, "transaction_type": "RECEIVING"},
        {"item_id": 9999, "quantity_change": 3, "transaction_type": "RECEIVING"},
    ]
    assert not stock_service.record_stock_transactions_bulk(sqlite_engine, transactions)

    with sqlite_engine.connect() as conn:
        stock = conn.execute(text("SELECT current_stock FROM items WHERE item_id=:i"), {"i": item_id}).scalar_one()
        assert stock == 10
        count = conn.execute(text("SELECT COUNT(*) FROM stock_transactions"))
        assert count.scalar_one() == 0


def test_remove_stock_transactions_bulk_rollback_on_error(sqlite_engine):
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, base_unit, purchase_unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active) VALUES ('Item', 'pcs', 'box', 'cat', 'sub', 'dept', 0, 10, 'n', 1)"
            )
        )
        item_id = conn.execute(text("SELECT item_id FROM items LIMIT 1")).scalar_one()

    transactions = [
        {"item_id": item_id, "quantity_change": 5, "transaction_type": "RECEIVING"},
        {"item_id": item_id, "quantity_change": -2, "transaction_type": "ISSUE"},
    ]
    assert stock_service.record_stock_transactions_bulk(sqlite_engine, transactions)

    with sqlite_engine.connect() as conn:
        ids = conn.execute(
            text("SELECT transaction_id FROM stock_transactions ORDER BY transaction_id")
        ).fetchall()
        valid_id = ids[0][0]
        current_stock = conn.execute(
            text("SELECT current_stock FROM items WHERE item_id=:i"), {"i": item_id}
        ).scalar_one()

    assert not stock_service.remove_stock_transactions_bulk(
        sqlite_engine, [valid_id, 9999]
    )

    with sqlite_engine.connect() as conn:
        stock = conn.execute(
            text("SELECT current_stock FROM items WHERE item_id=:i"), {"i": item_id}
        ).scalar_one()
        assert stock == current_stock
        count = conn.execute(text("SELECT COUNT(*) FROM stock_transactions"))
        assert count.scalar_one() == 2

