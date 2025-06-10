from sqlalchemy import text

from app.services import recipe_service
from app.services import item_service


def test_create_recipe_inserts_rows(sqlite_engine):
    # Insert a sample item for recipe ingredients
    item_service.add_new_item(
        sqlite_engine,
        {
            "name": "Flour",
            "unit": "kg",
            "category": "Food",
            "sub_category": "Base",
            "permitted_departments": "Kitchen",
            "reorder_point": 0,
            "current_stock": 0,
            "notes": "",
            "is_active": True,
        },
    )
    with sqlite_engine.connect() as conn:
        item_id = conn.execute(
            text("SELECT item_id FROM items WHERE name='Flour'")
        ).scalar_one()
    ok, msg = recipe_service.create_recipe(
        sqlite_engine,
        {"name": "Cake", "description": "Tasty"},
        [{"item_id": item_id, "quantity": 1}],
    )
    assert ok
    with sqlite_engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM recipes WHERE name='Cake'"))
        assert count.scalar_one() == 1
        count_items = conn.execute(text("SELECT COUNT(*) FROM recipe_items WHERE recipe_id=1"))
        assert count_items.scalar_one() == 1
