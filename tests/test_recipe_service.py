"""Tests for the recipe_service module."""

import pytest
from sqlalchemy import text

from inventory.services import recipe_service


def _create_item(conn, name="Flour", base_unit="kg", purchase_unit="bag", stock=20):
    conn.execute(
        text(
            """
            INSERT INTO items (
                name, base_unit, purchase_unit, category, sub_category, permitted_departments,
                reorder_point, current_stock, notes, is_active
            ) VALUES (:n, :bu, :pu, 'cat', 'sub', 'dept', 0, :s, 'n', 1)
            """
        ),
        {"n": name, "bu": base_unit, "pu": purchase_unit, "s": stock},
    )
    return conn.execute(
        text("SELECT item_id FROM items WHERE name=:n"), {"n": name}
    ).scalar_one()


def test_create_and_update_components(sqlite_engine):
    """Components should retain provided units and loss percentages."""
    with sqlite_engine.begin() as conn:
        item_id = _create_item(conn)

    data = {
        "name": "Bread",
        "is_active": True,
        "default_yield_unit": "kg",
    }
    components = [
        {
            "component_kind": "ITEM",
            "component_id": item_id,
            "quantity": 2,
            "unit": "kg",
            "loss_pct": 5,
        }
    ]

    ok, _, rid = recipe_service.create_recipe(sqlite_engine, data, components)
    assert ok and rid

    with sqlite_engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT quantity, unit, loss_pct
                FROM recipe_components
                WHERE parent_recipe_id=:r
                """
            ),
            {"r": rid},
        ).mappings().fetchone()
        assert row["unit"] == "kg" and row["loss_pct"] == 5

    # update component quantity and loss percentage
    components[0]["quantity"] = 3
    components[0]["loss_pct"] = 10
    ok, _ = recipe_service.update_recipe(sqlite_engine, rid, data, components)
    assert ok

    with sqlite_engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT quantity, loss_pct
                FROM recipe_components
                WHERE parent_recipe_id=:r
                """
            ),
            {"r": rid},
        ).mappings().fetchone()
        assert row["quantity"] == 3 and row["loss_pct"] == 10


def test_nested_recipes_and_cycle_prevention(sqlite_engine):
    """Nested recipes are allowed but cycles are rejected."""
    with sqlite_engine.begin() as conn:
        item_id = _create_item(conn)

    dough_data = {
        "name": "Dough",
        "is_active": True,
        "default_yield_unit": "kg",
    }
    dough_components = [
        {
            "component_kind": "ITEM",
            "component_id": item_id,
            "quantity": 1,
            "unit": "kg",
        }
    ]
    ok, _, dough_id = recipe_service.create_recipe(
        sqlite_engine, dough_data, dough_components
    )
    assert ok and dough_id

    bread_data = {
        "name": "Bread",
        "is_active": True,
        "default_yield_unit": "kg",
    }
    bread_components = [
        {
            "component_kind": "RECIPE",
            "component_id": dough_id,
            "quantity": 1,
            "unit": "kg",
        }
    ]
    ok, _, bread_id = recipe_service.create_recipe(
        sqlite_engine, bread_data, bread_components
    )
    assert ok and bread_id

    # attempt to introduce cycle: dough uses bread
    dough_components.append(
        {
            "component_kind": "RECIPE",
            "component_id": bread_id,
            "quantity": 1,
            "unit": "kg",
        }
    )
    ok, _ = recipe_service.update_recipe(
        sqlite_engine, dough_id, dough_data, dough_components
    )
    assert not ok


def test_record_sale_reduces_nested_stock(sqlite_engine):
    """record_sale should consume stock through nested components."""
    with sqlite_engine.begin() as conn:
        item_id = _create_item(conn)

        # premix recipe -> item
        conn.execute(
            text(
                "INSERT INTO recipes (name, is_active, default_yield_unit)"
                " VALUES ('PreMix', 1, 'kg')"
            )
        )
        premix_id = conn.execute(
            text("SELECT recipe_id FROM recipes WHERE name='PreMix'")
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO recipe_components (parent_recipe_id, component_kind,"
                " component_id, quantity, unit, loss_pct)"
                " VALUES (:r, 'ITEM', :i, 1, 'kg', 10)"
            ),
            {"r": premix_id, "i": item_id},
        )

        # bread recipe -> premix
        conn.execute(
            text(
                "INSERT INTO recipes (name, is_active, default_yield_unit)"
                " VALUES ('Bread', 1, 'kg')"
            )
        )
        bread_id = conn.execute(
            text("SELECT recipe_id FROM recipes WHERE name='Bread'")
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO recipe_components (parent_recipe_id, component_kind,"
                " component_id, quantity, unit, loss_pct)"
                " VALUES (:r, 'RECIPE', :c, 1, 'kg', 20)"
            ),
            {"r": bread_id, "c": premix_id},
        )

    ok, msg = recipe_service.record_sale(sqlite_engine, bread_id, 2, "tester")
    assert ok, msg

    with sqlite_engine.connect() as conn:
        stock = conn.execute(
            text("SELECT current_stock FROM items WHERE item_id=:i"),
            {"i": item_id},
        ).scalar_one()
        expected = 20 - (2 * 1 / (1 - 0.2) / (1 - 0.1))
        assert stock == pytest.approx(expected)


def test_recipe_metadata_fields(sqlite_engine):
    """Metadata like yield units, tags and type should persist."""
    with sqlite_engine.begin() as conn:
        item_id = _create_item(conn)

    data = {
        "name": "Salad",
        "description": "Fresh",
        "is_active": True,
        "type": "FOOD",
        "default_yield_qty": 4,
        "default_yield_unit": "plate",
        "tags": "vegan,healthy",
    }
    components = [
        {
            "component_kind": "ITEM",
            "component_id": item_id,
            "quantity": 1,
            "unit": "kg",
        }
    ]

    ok, _, rid = recipe_service.create_recipe(sqlite_engine, data, components)
    assert ok and rid

    with sqlite_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT type, default_yield_unit, tags FROM recipes WHERE recipe_id=:r"
            ),
            {"r": rid},
        ).mappings().fetchone()
        assert row["type"] == "FOOD"
        assert row["default_yield_unit"] == "plate"
        assert row["tags"] == "vegan,healthy"

