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


def test_archive_and_reactivate_recipe(sqlite_engine):
    item_id = setup_items(sqlite_engine)
    data = {"name": "Cake", "description": "sponge"}
    ingredients = [{"item_id": item_id, "quantity": 1}]
    success, _, rid = recipe_service.create_recipe(sqlite_engine, data, ingredients)
    assert success and rid

    success, _ = recipe_service.archive_recipe(sqlite_engine, rid)
    assert success
    with sqlite_engine.connect() as conn:
        active = conn.execute(
            text("SELECT is_active FROM recipes WHERE recipe_id=:r"), {"r": rid}
        ).scalar_one()
        assert active == 0

    success, _ = recipe_service.reactivate_recipe(sqlite_engine, rid)
    assert success
    with sqlite_engine.connect() as conn:
        active = conn.execute(
            text("SELECT is_active FROM recipes WHERE recipe_id=:r"), {"r": rid}
        ).scalar_one()
        assert active == 1


def test_list_recipes_search_and_filter(sqlite_engine):
    item_id = setup_items(sqlite_engine)
    recipe_service.create_recipe(
        sqlite_engine,
        {"name": "Apple Pie", "description": "Sweet"},
        [{"item_id": item_id, "quantity": 1}],
    )
    recipe_service.create_recipe(
        sqlite_engine,
        {"name": "Banana Bread", "description": "Sweet bread"},
        [{"item_id": item_id, "quantity": 1}],
    )
    _, _, rid = recipe_service.create_recipe(
        sqlite_engine,
        {"name": "Carrot Soup", "description": "Healthy"},
        [{"item_id": item_id, "quantity": 1}],
    )
    recipe_service.archive_recipe(sqlite_engine, rid)

    df = recipe_service.list_recipes(sqlite_engine, search_text="Bread")
    assert list(df["name"]) == ["Banana Bread"]

    df_active = recipe_service.list_recipes(sqlite_engine)
    assert len(df_active) == 2

    df_all = recipe_service.list_recipes(sqlite_engine, include_inactive=True)
    assert len(df_all) == 3

    df_soup = recipe_service.list_recipes(
        sqlite_engine, search_text="Soup", include_inactive=True
    )
    assert list(df_soup["name"]) == ["Carrot Soup"]

