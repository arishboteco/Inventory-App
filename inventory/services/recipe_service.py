"""Service layer for recipe management.

This module provides a light-weight port of the legacy Streamlit
``recipe_service``.  It operates directly on the ``recipes`` and
``recipe_components`` tables using SQLAlchemy connections so it can be used
from the Django app and in tests without depending on the legacy codebase.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger(__name__)

TX_SALE = "SALE"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _strip_or_none(val: Any) -> Optional[str]:
    """Return a stripped string or ``None``."""
    if isinstance(val, str):
        val = val.strip()
        return val or None
    return None


def _component_unit(conn: Connection, kind: str, cid: int, unit: Optional[str]) -> Optional[str]:
    """Validate and resolve a component's unit.

    For ``ITEM`` components the unit must match the item's ``base_unit``.
    For ``RECIPE`` components the unit must match the child recipe's
    ``default_yield_unit``.
    """

    if kind == "ITEM":
        row = conn.execute(
            text("SELECT base_unit FROM items WHERE item_id=:i"), {"i": cid}
        ).mappings().fetchone()
        if not row:
            raise ValueError(f"Item {cid} not found")
        base = row["base_unit"]
        if unit is None:
            return base
        if unit != base:
            raise ValueError("Unit mismatch for item component")
        return unit
    if kind == "RECIPE":
        row = conn.execute(
            text("SELECT default_yield_unit FROM recipes WHERE recipe_id=:r"),
            {"r": cid},
        ).mappings().fetchone()
        db_unit = row["default_yield_unit"] if row else None
        if unit is not None and db_unit and unit != db_unit:
            raise ValueError("Unit mismatch for recipe component")
        return unit if unit is not None else db_unit
    raise ValueError("Invalid component_kind")


def _has_path(conn: Connection, start: int, target: int) -> bool:
    """Return True if ``start`` recipe references ``target`` recursively."""
    if start == target:
        return True
    rows = conn.execute(
        text(
            "SELECT component_id FROM recipe_components "
            "WHERE parent_recipe_id=:r AND component_kind='RECIPE'"
        ),
        {"r": start},
    ).fetchall()
    for (cid,) in rows:
        if _has_path(conn, cid, target):
            return True
    return False


def _creates_cycle(conn: Connection, parent_id: int, child_id: int) -> bool:
    """Check whether linking ``parent_id`` -> ``child_id`` creates a cycle."""
    if parent_id == child_id:
        return True
    return _has_path(conn, child_id, parent_id)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def build_components_from_editor(
    df, choice_map: Dict[str, Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Convert a data-editor DataFrame into component payload.

    ``choice_map`` is expected to map the label from the UI to metadata about
    the component (kind, id, unit information etc.).
    """

    from inventory.constants import PLACEHOLDER_SELECT_COMPONENT

    components: List[Dict[str, Any]] = []
    errors: List[str] = []
    for idx, row in df.iterrows():
        label = row.get("component")
        if not label or label == PLACEHOLDER_SELECT_COMPONENT:
            continue
        meta = choice_map.get(label)
        if not meta:
            continue
        qty = row.get("quantity")
        if qty is None or float(qty) <= 0:
            errors.append(f"Quantity must be greater than 0 for {label}.")
            continue
        unit = row.get("unit") or meta.get("base_unit") or meta.get("unit")
        if meta["kind"] == "ITEM":
            base_unit = meta.get("base_unit")
            purchase_unit = meta.get("purchase_unit")
            allowed = {u for u in [base_unit, purchase_unit] if u}
            if unit not in allowed:
                if purchase_unit:
                    errors.append(
                        f"Unit mismatch for {meta.get('name')}. Use {base_unit} or {purchase_unit}."
                    )
                else:
                    errors.append(
                        f"Unit mismatch for {meta.get('name')}. Use {base_unit}."
                    )
                continue
        components.append(
            {
                "component_kind": meta["kind"],
                "component_id": meta["id"],
                "quantity": float(qty),
                "unit": unit,
                "loss_pct": float(row.get("loss_pct") or 0),
                "sort_order": int(row.get("sort_order") or idx + 1),
                "notes": row.get("notes") or None,
            }
        )
    return components, errors


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


def create_recipe(
    engine: Engine, data: Dict[str, Any], components: List[Dict[str, Any]]
) -> Tuple[bool, str, Optional[int]]:
    """Create a recipe and associated components."""
    if engine is None:
        return False, "Database engine not available.", None
    try:
        with engine.begin() as conn:
            fields = [
                "name",
                "description",
                "is_active",
                "type",
                "default_yield_qty",
                "default_yield_unit",
                "plating_notes",
                "tags",
            ]
            ins = text(
                f"INSERT INTO recipes ({', '.join(fields)}) "
                f"VALUES ({', '.join(':'+f for f in fields)})"
            )
            params = {f: data.get(f) for f in fields}
            result = conn.execute(ins, params)
            rid = result.lastrowid
            for comp in components:
                unit = _component_unit(
                    conn,
                    comp["component_kind"],
                    comp["component_id"],
                    comp.get("unit"),
                )
                if comp["component_kind"] == "RECIPE" and _creates_cycle(
                    conn, rid, comp["component_id"]
                ):
                    raise ValueError("Adding this component creates a cycle")
                conn.execute(
                    text(
                        """
                        INSERT INTO recipe_components
                        (parent_recipe_id, component_kind, component_id, quantity, unit, loss_pct, sort_order, notes)
                        VALUES
                        (:r, :k, :cid, :q, :u, :loss, :sort, :notes)
                        """
                    ),
                    {
                        "r": rid,
                        "k": comp["component_kind"],
                        "cid": comp["component_id"],
                        "q": comp["quantity"],
                        "u": unit,
                        "loss": comp.get("loss_pct") or 0,
                        "sort": comp.get("sort_order") or 0,
                        "notes": _strip_or_none(comp.get("notes")),
                    },
                )
        return True, "Recipe created.", rid
    except (IntegrityError, ValueError) as exc:
        logger.error("Error creating recipe: %s", exc)
        return False, str(exc), None
    except SQLAlchemyError as exc:  # pragma: no cover - defensive
        logger.error("DB error creating recipe: %s", exc)
        return False, "A database error occurred.", None


def update_recipe(
    engine: Engine,
    recipe_id: int,
    data: Dict[str, Any],
    components: List[Dict[str, Any]],
) -> Tuple[bool, str]:
    """Update a recipe and replace its components."""
    if engine is None:
        return False, "Database engine not available."
    try:
        with engine.begin() as conn:
            if data:
                fields = ", ".join(f"{k}=:{k}" for k in data.keys())
                conn.execute(
                    text(f"UPDATE recipes SET {fields} WHERE recipe_id=:rid"),
                    {**data, "rid": recipe_id},
                )
            conn.execute(
                text("DELETE FROM recipe_components WHERE parent_recipe_id=:r"),
                {"r": recipe_id},
            )
            for comp in components:
                unit = _component_unit(
                    conn,
                    comp["component_kind"],
                    comp["component_id"],
                    comp.get("unit"),
                )
                if comp["component_kind"] == "RECIPE" and _creates_cycle(
                    conn, recipe_id, comp["component_id"]
                ):
                    raise ValueError("Adding this component creates a cycle")
                conn.execute(
                    text(
                        """
                        INSERT INTO recipe_components
                        (parent_recipe_id, component_kind, component_id, quantity, unit, loss_pct, sort_order, notes)
                        VALUES
                        (:r, :k, :cid, :q, :u, :loss, :sort, :notes)
                        """
                    ),
                    {
                        "r": recipe_id,
                        "k": comp["component_kind"],
                        "cid": comp["component_id"],
                        "q": comp["quantity"],
                        "u": unit,
                        "loss": comp.get("loss_pct") or 0,
                        "sort": comp.get("sort_order") or 0,
                        "notes": _strip_or_none(comp.get("notes")),
                    },
                )
        return True, "Recipe updated."
    except (IntegrityError, ValueError) as exc:
        logger.error("Error updating recipe: %s", exc)
        return False, str(exc)
    except SQLAlchemyError as exc:  # pragma: no cover - defensive
        logger.error("DB error updating recipe: %s", exc)
        return False, "A database error occurred."


# ---------------------------------------------------------------------------
# Sale handling
# ---------------------------------------------------------------------------


def _expand_requirements(
    conn: Connection,
    recipe_id: int,
    multiplier: float,
    totals: Dict[int, float],
    visited: Set[int],
) -> None:
    if recipe_id in visited:
        raise ValueError("Circular reference detected during expansion")
    visited.add(recipe_id)
    rows = conn.execute(
        text(
            "SELECT component_kind, component_id, quantity, unit, loss_pct "
            "FROM recipe_components WHERE parent_recipe_id=:r"
        ),
        {"r": recipe_id},
    ).mappings().all()
    for row in rows:
        qty = multiplier * float(row["quantity"]) / (
            1 - float(row.get("loss_pct") or 0) / 100.0
        )
        if row["component_kind"] == "ITEM":
            item = conn.execute(
                text(
                    "SELECT base_unit, is_active FROM items WHERE item_id=:i"
                ),
                {"i": row["component_id"]},
            ).mappings().fetchone()
            if not item:
                raise ValueError(f"Item {row['component_id']} not found")
            if not item["is_active"]:
                raise ValueError("Inactive item component encountered")
            if item["base_unit"] != row["unit"]:
                raise ValueError("Unit mismatch for item component")
            totals[row["component_id"]] = totals.get(row["component_id"], 0) + qty
        elif row["component_kind"] == "RECIPE":
            sub = conn.execute(
                text(
                    "SELECT default_yield_unit, is_active FROM recipes WHERE recipe_id=:r"
                ),
                {"r": row["component_id"]},
            ).mappings().fetchone()
            if not sub:
                raise ValueError(f"Recipe {row['component_id']} not found")
            if not sub["is_active"]:
                raise ValueError("Inactive sub-recipe encountered")
            if not sub["default_yield_unit"]:
                raise ValueError("Missing unit for recipe component")
            if sub["default_yield_unit"] != row["unit"]:
                raise ValueError("Unit mismatch for recipe component")
            _expand_requirements(conn, row["component_id"], qty, totals, visited)
        else:
            raise ValueError("Invalid component_kind")
    visited.remove(recipe_id)


def _resolve_item_requirements(
    conn: Connection, recipe_id: int, quantity: float
) -> Dict[int, float]:
    totals: Dict[int, float] = {}
    _expand_requirements(conn, recipe_id, quantity, totals, set())
    return totals


def record_sale(
    engine: Engine,
    recipe_id: int,
    quantity: float,
    user_id: str,
    notes: Optional[str] = None,
) -> Tuple[bool, str]:
    """Record sale of a recipe and reduce ingredient stock."""
    if engine is None:
        return False, "Database engine not available."
    if not recipe_id or quantity <= 0:
        return False, "Invalid recipe or quantity."
    user_id_clean = user_id.strip() if user_id else "System"
    notes_clean = _strip_or_none(notes)
    sale_ins = text(
        "INSERT INTO sales_transactions (recipe_id, quantity, user_id, notes) "
        "VALUES (:r, :q, :u, :n);"
    )
    try:
        with engine.connect() as conn:
            with conn.begin():
                is_active = conn.execute(
                    text("SELECT is_active FROM recipes WHERE recipe_id=:r"),
                    {"r": recipe_id},
                ).scalar_one_or_none()
                if is_active is None:
                    return False, "Recipe not found."
                if not is_active:
                    return False, "Recipe is inactive."
                totals = _resolve_item_requirements(conn, recipe_id, quantity)
                conn.execute(
                    sale_ins,
                    {"r": recipe_id, "q": quantity, "u": user_id_clean, "n": notes_clean},
                )
                for iid, qty in totals.items():
                    conn.execute(
                        text(
                            "UPDATE items SET current_stock = COALESCE(current_stock,0) - :q WHERE item_id=:i"
                        ),
                        {"q": qty, "i": iid},
                    )
                    conn.execute(
                        text(
                            """
                            INSERT INTO stock_transactions
                            (item_id, quantity_change, transaction_type, user_id, notes, transaction_date)
                            VALUES (:i, :q, :t, :u, :n, NOW())
                            """
                        ),
                        {
                            "i": iid,
                            "q": -qty,
                            "t": TX_SALE,
                            "u": user_id_clean,
                            "n": f"Recipe {recipe_id} sale",
                        },
                    )
        return True, "Sale recorded."
    except ValueError as ve:
        logger.error("Error recording sale: %s", ve)
        return False, str(ve)
    except SQLAlchemyError as exc:  # pragma: no cover - defensive
        logger.error("DB error recording sale: %s", exc)
        return False, "A database error occurred during sale recording."
