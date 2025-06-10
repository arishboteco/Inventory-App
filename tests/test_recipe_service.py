from sqlalchemy import text

from app.services import recipe_service


def setup_items(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active)"
                " VALUES ('Flour', 'kg', 'cat', 'sub', 'dept', 0, 20, 'n', 1)"
            )
        )
        item_id = conn.execute(text("SELECT item_id FROM items WHERE name='Flour'"))
        return item_id.scalar_one()


def test_create_recipe_inserts_rows(sqlite_engine):
    item_id = setup_items(sqlite_engine)
    data = {"name": "Bread", "description": "desc", "is_active": True}
    ingredients = [{"item_id": item_id, "quantity": 2}]
    success, msg, rid = recipe_service.create_recipe(sqlite_engine, data, ingredients)
    assert success and rid
    with sqlite_engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM recipe_items WHERE recipe_id=:r"), {"r": rid}
        ).scalar_one()
        assert count == 1


def test_record_sale_reduces_stock(sqlite_engine):
    item_id = setup_items(sqlite_engine)
    with sqlite_engine.begin() as conn:
        conn.execute(text("INSERT INTO recipes (name, is_active) VALUES ('Toast', 1)"))
        recipe_id = conn.execute(text("SELECT recipe_id FROM recipes WHERE name='Toast'"))
        recipe_id = recipe_id.scalar_one()
        conn.execute(
            text(
                "INSERT INTO recipe_items (recipe_id, item_id, quantity) VALUES (:r, :i, 3)"
            ),
            {"r": recipe_id, "i": item_id},
        )
    ok, _ = recipe_service.record_sale(sqlite_engine, recipe_id, 1, "tester")
    assert ok
    with sqlite_engine.connect() as conn:
        stock = conn.execute(
            text("SELECT current_stock FROM items WHERE item_id=:i"), {"i": item_id}
        ).scalar_one()
        assert stock == 17


def test_clone_recipe_duplicates_rows(sqlite_engine):
    item_id = setup_items(sqlite_engine)
    data = {"name": "Pie", "description": "sweet", "is_active": True}
    ingredients = [{"item_id": item_id, "quantity": 4}]
    ok, _, rid = recipe_service.create_recipe(sqlite_engine, data, ingredients)
    assert ok and rid

    ok, msg, new_id = recipe_service.clone_recipe(
        sqlite_engine, rid, "Pie Copy", data["description"]
    )
    assert ok and new_id and new_id != rid

    with sqlite_engine.connect() as conn:
        header = conn.execute(
            text("SELECT description FROM recipes WHERE recipe_id=:r"), {"r": new_id}
        ).mappings().fetchone()
        assert header["description"] == "sweet"
        count = conn.execute(
            text("SELECT COUNT(*) FROM recipe_items WHERE recipe_id=:r"), {"r": new_id}
        ).scalar_one()
        assert count == 1
        qty = conn.execute(
            text(
                "SELECT quantity FROM recipe_items WHERE recipe_id=:r AND item_id=:i"
            ),
            {"r": new_id, "i": item_id},
        ).scalar_one()
        assert qty == 4
