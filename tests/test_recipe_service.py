import pytest
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
    data = {
        "name": "Bread",
        "description": "desc",
        "is_active": True,
        "type": "FOOD",
        "default_yield_qty": 10,
        "default_yield_unit": "slice",
    }
    components = [
        {
            "component_kind": "ITEM",
            "component_id": item_id,
            "quantity": 2,
        }
    ]
    success, msg, rid = recipe_service.create_recipe(sqlite_engine, data, components)
    assert success and rid
    with sqlite_engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM recipe_components WHERE parent_recipe_id=:r"),
            {"r": rid},
        ).scalar_one()
        assert count == 1
        header = conn.execute(
            text(
                "SELECT type, default_yield_qty FROM recipes WHERE recipe_id=:r"
            ),
            {"r": rid},
        ).mappings().fetchone()
        assert header["type"] == "FOOD" and header["default_yield_qty"] == 10


def test_record_sale_reduces_stock(sqlite_engine):
    item_id = setup_items(sqlite_engine)
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO recipes (name, is_active, default_yield_unit) VALUES ('Toast', 1, 'kg')"
            )
        )
        recipe_id = conn.execute(text("SELECT recipe_id FROM recipes WHERE name='Toast'"))
        recipe_id = recipe_id.scalar_one()
        conn.execute(
            text(
                "INSERT INTO recipe_components (parent_recipe_id, component_kind, component_id, quantity, unit)"
                " VALUES (:r, 'ITEM', :i, 3, 'kg')"
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
    components = [
        {
            "component_kind": "ITEM",
            "component_id": item_id,
            "quantity": 4,
            "unit": "kg",
        }
    ]
    ok, _, rid = recipe_service.create_recipe(sqlite_engine, data, components)
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
            text(
                "SELECT COUNT(*) FROM recipe_components WHERE parent_recipe_id=:r"
            ),
            {"r": new_id},
        ).scalar_one()
        assert count == 1
        qty = conn.execute(
            text(
                "SELECT quantity FROM recipe_components WHERE parent_recipe_id=:r AND component_id=:i AND component_kind='ITEM'"
            ),
            {"r": new_id, "i": item_id},
        ).scalar_one()
        assert qty == 4


def test_cycle_detection(sqlite_engine):
    item_id = setup_items(sqlite_engine)
    data_a = {"name": "A", "is_active": True}
    comps_a = [
        {"component_kind": "ITEM", "component_id": item_id, "quantity": 1}
    ]
    ok, _, rid_a = recipe_service.create_recipe(sqlite_engine, data_a, comps_a)
    assert ok and rid_a

    data_b = {"name": "B", "is_active": True}
    comps_b = [
        {"component_kind": "RECIPE", "component_id": rid_a, "quantity": 1}
    ]
    ok, _, rid_b = recipe_service.create_recipe(sqlite_engine, data_b, comps_b)
    assert ok and rid_b

    comps_a.append({"component_kind": "RECIPE", "component_id": rid_b, "quantity": 1})
    ok, msg = recipe_service.update_recipe(sqlite_engine, rid_a, data_a, comps_a)
    assert not ok


def test_record_sale_nested_recipe_with_loss(sqlite_engine):
    item_id = setup_items(sqlite_engine)
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO recipes (name, is_active, default_yield_unit) VALUES ('PreMix', 1, 'kg')"
            )
        )
        premix_id = conn.execute(
            text("SELECT recipe_id FROM recipes WHERE name='PreMix'")
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO recipe_components (parent_recipe_id, component_kind, component_id, quantity, unit, loss_pct) "
                "VALUES (:r, 'ITEM', :i, 1, 'kg', 10)"
            ),
            {"r": premix_id, "i": item_id},
        )
        conn.execute(
            text(
                "INSERT INTO recipes (name, is_active, default_yield_unit) VALUES ('Bread', 1, 'kg')"
            )
        )
        bread_id = conn.execute(
            text("SELECT recipe_id FROM recipes WHERE name='Bread'")
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO recipe_components (parent_recipe_id, component_kind, component_id, quantity, unit, loss_pct) "
                "VALUES (:r, 'RECIPE', :c, 1, 'kg', 20)"
            ),
            {"r": bread_id, "c": premix_id},
        )

    ok, _ = recipe_service.record_sale(sqlite_engine, bread_id, 2, "tester")
    assert ok
    with sqlite_engine.connect() as conn:
        stock = conn.execute(
            text("SELECT current_stock FROM items WHERE item_id=:i"),
            {"i": item_id},
        ).scalar_one()
        expected = 20 - (2 * 1 / (1 - 0.2) / (1 - 0.1))
        assert stock == pytest.approx(expected)


def test_record_sale_fails_inactive_component(sqlite_engine):
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO items (name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active) "
                "VALUES ('Inactive', 'kg', 'c', 's', 'd', 0, 5, 'n', 0)"
            )
        )
        item_id = conn.execute(
            text("SELECT item_id FROM items WHERE name='Inactive'")
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO recipes (name, is_active, default_yield_unit) VALUES ('Bread', 1, 'kg')"
            )
        )
        recipe_id = conn.execute(
            text("SELECT recipe_id FROM recipes WHERE name='Bread'")
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO recipe_components (parent_recipe_id, component_kind, component_id, quantity, unit) "
                "VALUES (:r, 'ITEM', :i, 1, 'kg')"
            ),
            {"r": recipe_id, "i": item_id},
        )

    ok, msg = recipe_service.record_sale(sqlite_engine, recipe_id, 1, "tester")
    assert not ok


def test_record_sale_fails_unit_mismatch(sqlite_engine):
    item_id = setup_items(sqlite_engine)
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO recipes (name, is_active, default_yield_unit) VALUES ('Bread', 1, 'kg')"
            )
        )
        recipe_id = conn.execute(
            text("SELECT recipe_id FROM recipes WHERE name='Bread'")
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO recipe_components (parent_recipe_id, component_kind, component_id, quantity, unit) "
                "VALUES (:r, 'ITEM', :i, 1, 'g')"
            ),
            {"r": recipe_id, "i": item_id},
        )

    ok, msg = recipe_service.record_sale(sqlite_engine, recipe_id, 1, "tester")
    assert not ok


def test_record_sale_fails_missing_unit(sqlite_engine):
    item_id = setup_items(sqlite_engine)
    with sqlite_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO recipes (name, is_active, default_yield_unit) VALUES ('Bread', 1, 'kg')"
            )
        )
        recipe_id = conn.execute(
            text("SELECT recipe_id FROM recipes WHERE name='Bread'")
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO recipe_components (parent_recipe_id, component_kind, component_id, quantity, unit) "
                "VALUES (:r, 'ITEM', :i, 1, :u)"
            ),
            {"r": recipe_id, "i": item_id, "u": None},
        )

    ok, msg = recipe_service.record_sale(sqlite_engine, recipe_id, 1, "tester")
    assert not ok

