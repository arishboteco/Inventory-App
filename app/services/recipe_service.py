"""Service layer for recipe management."""

from typing import Dict, List, Tuple, Any, Optional, Set
import traceback
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.engine import Engine, Connection

from app.core.logging import get_logger
from app.db.database_utils import fetch_data
from app.core.constants import TX_SALE
from . import stock_service

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────


def _strip_or_none(val: Any) -> Optional[str]:
    return val.strip() if isinstance(val, str) and val.strip() else None


def _component_unit(
    conn: Connection, kind: str, cid: int, unit: Optional[str]
) -> Optional[str]:
    if kind == "ITEM":
        db_unit = conn.execute(
            text("SELECT unit FROM items WHERE item_id=:i"), {"i": cid}
        ).scalar_one_or_none()
        if not db_unit:
            raise ValueError(f"Item {cid} not found")
        if unit is None:
            return db_unit
        if unit != db_unit:
            raise ValueError("Unit mismatch for item component")
        return unit
    elif kind == "RECIPE":
        db_unit = conn.execute(
            text("SELECT default_yield_unit FROM recipes WHERE recipe_id=:r"),
            {"r": cid},
        ).scalar_one_or_none()
        return unit if unit is not None else db_unit
    else:
        raise ValueError("Invalid component_kind")


def _creates_cycle(conn: Connection, parent_id: int, child_id: int) -> bool:
    if parent_id == child_id:
        return True
    query = text(
        """
        WITH RECURSIVE sub(id) AS (
            SELECT component_id FROM recipe_components
            WHERE parent_recipe_id=:c AND component_kind='RECIPE'
            UNION
            SELECT rc.component_id
            FROM recipe_components rc
            JOIN sub s ON rc.parent_recipe_id = s.id
            WHERE rc.component_kind='RECIPE'
        )
        SELECT 1 FROM sub WHERE id=:p LIMIT 1;
        """
    )
    res = conn.execute(query, {"c": child_id, "p": parent_id}).scalar_one_or_none()
    return res is not None


def build_components_from_editor(
    df: pd.DataFrame, choice_map: Dict[str, Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Convert a data-editor dataframe into component payload.

    Returns (components, errors).
    Automatically applies unit/category defaults and validates units.
    """
    components: List[Dict[str, Any]] = []
    errors: List[str] = []
    for idx, row in df.iterrows():
        label = row.get("component")
        if not label:
            continue
        meta = choice_map.get(label)
        if not meta:
            continue
        qty = row.get("quantity")
        if qty is None or float(qty) <= 0:
            errors.append(f"Quantity must be greater than 0 for {label}.")
            continue
        unit = row.get("unit") or meta.get("unit")
        if meta["kind"] == "ITEM":
            base_unit = meta.get("unit")
            if unit != base_unit:
                errors.append(
                    f"Unit mismatch for {meta.get('name')}. Use {base_unit}."
                )
                continue
            unit = base_unit
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


# ─────────────────────────────────────────────────────────
# RECIPE CRUD FUNCTIONS
# ─────────────────────────────────────────────────────────


def list_recipes(
    engine: Engine, include_inactive: bool = False, rtype: Optional[str] = None
) -> pd.DataFrame:
    """Return recipes with optional type filtering."""
    if engine is None:
        logger.error(
            "ERROR [recipe_service.list_recipes]: Database engine not available."
        )
        return pd.DataFrame()
    query = (
        "SELECT recipe_id, name, description, is_active, type, "
        "default_yield_qty, default_yield_unit, plating_notes, tags, version, "
        "effective_from, effective_to FROM recipes"
    )
    conditions = []
    params: Dict[str, Any] = {}
    if not include_inactive:
        conditions.append("is_active = TRUE")
    if rtype:
        conditions.append("type = :rtype")
        params["rtype"] = rtype
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY name;"
    return fetch_data(engine, query, params)


def get_recipe_components(engine: Engine, recipe_id: int) -> pd.DataFrame:
    """Return component breakdown (items or sub-recipes) for a recipe.

    Ensures that expected columns are always present even when the query
    returns no rows or the engine is unavailable.
    """

    columns = [
        "id",
        "parent_recipe_id",
        "component_kind",
        "component_id",
        "component_name",
        "quantity",
        "unit",
        "loss_pct",
        "sort_order",
        "notes",
    ]

    if engine is None:
        logger.error(
            "ERROR [recipe_service.get_recipe_components]: Database engine not available."
        )
        return pd.DataFrame(columns=columns)

    query = text(
        """
        SELECT rc.id, rc.parent_recipe_id, rc.component_kind, rc.component_id,
               COALESCE(i.name, r.name) AS component_name,
               rc.quantity, rc.unit, rc.loss_pct, rc.sort_order, rc.notes
        FROM recipe_components rc
        LEFT JOIN items i ON rc.component_kind='ITEM' AND rc.component_id=i.item_id
        LEFT JOIN recipes r ON rc.component_kind='RECIPE' AND rc.component_id=r.recipe_id
        WHERE rc.parent_recipe_id=:rid
        ORDER BY rc.sort_order;
        """
    )

    df = fetch_data(engine, query.text, {"rid": recipe_id})
    return df.reindex(columns=columns)


def create_recipe(
    engine: Engine,
    recipe_data: Dict[str, Any],
    components: List[Dict[str, Any]],
) -> Tuple[bool, str, Optional[int]]:
    """Create a recipe and its component rows."""
    if engine is None:
        return False, "Database engine not available.", None
    if not recipe_data.get("name") or not str(recipe_data.get("name")).strip():
        return False, "Recipe name is required.", None
    if not components:
        return False, "At least one component is required.", None

    clean = {
        "name": recipe_data["name"].strip(),
        "description": _strip_or_none(recipe_data.get("description")),
        "is_active": bool(recipe_data.get("is_active", True)),
        "type": _strip_or_none(recipe_data.get("type")),
        "default_yield_qty": recipe_data.get("default_yield_qty"),
        "default_yield_unit": _strip_or_none(recipe_data.get("default_yield_unit")),
        "plating_notes": _strip_or_none(recipe_data.get("plating_notes")),
        "tags": recipe_data.get("tags"),
        "version": recipe_data.get("version"),
        "effective_from": recipe_data.get("effective_from"),
        "effective_to": recipe_data.get("effective_to"),
    }

    insert_recipe_q = text(
        """
        INSERT INTO recipes (name, description, is_active, type, default_yield_qty, default_yield_unit,
                             plating_notes, tags, version, effective_from, effective_to)
        VALUES (:name, :description, :is_active, :type, :default_yield_qty, :default_yield_unit,
                :plating_notes, :tags, :version, :effective_from, :effective_to)
        RETURNING recipe_id;
        """
    )
    insert_comp_q = text(
        """
        INSERT INTO recipe_components (parent_recipe_id, component_kind, component_id, quantity,
                                      unit, loss_pct, sort_order, notes)
        VALUES (:parent_recipe_id, :component_kind, :component_id, :quantity,
                :unit, :loss_pct, :sort_order, :notes);
        """
    )

    try:
        with engine.connect() as conn:
            with conn.begin():
                rid = conn.execute(insert_recipe_q, clean).scalar_one_or_none()
                if not rid:
                    raise Exception("Failed to insert recipe header.")
                for idx, comp in enumerate(components, start=1):
                    kind = comp.get("component_kind")
                    cid = comp.get("component_id")
                    qty = comp.get("quantity")
                    if kind not in {"ITEM", "RECIPE"} or not cid or qty is None or qty <= 0:
                        raise ValueError("Invalid component data")
                    unit = _strip_or_none(comp.get("unit"))
                    unit = _component_unit(conn, kind, cid, unit)
                    loss_pct = float(comp.get("loss_pct", 0) or 0)
                    sort_order = comp.get("sort_order", idx)
                    notes = _strip_or_none(comp.get("notes"))
                    if kind == "RECIPE" and _creates_cycle(conn, rid, cid):
                        raise ValueError("Circular recipe reference detected")
                    conn.execute(
                        insert_comp_q,
                        {
                            "parent_recipe_id": rid,
                            "component_kind": kind,
                            "component_id": cid,
                            "quantity": float(qty),
                            "unit": unit,
                            "loss_pct": loss_pct,
                            "sort_order": sort_order,
                            "notes": notes,
                        },
                    )
        return True, f"Recipe '{clean['name']}' added.", rid
    except IntegrityError as ie:
        logger.error(
            "ERROR [recipe_service.create_recipe]: Integrity error: %s\n%s",
            ie,
            traceback.format_exc(),
        )
        msg = (
            "Recipe with this name already exists."
            if "unique" in str(ie).lower()
            else "Integrity error."
        )
        return False, msg, None
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [recipe_service.create_recipe]: DB error: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred.", None


def update_recipe(
    engine: Engine,
    recipe_id: int,
    recipe_data: Dict[str, Any],
    components: List[Dict[str, Any]],
) -> Tuple[bool, str]:
    """Update recipe details and components."""
    if engine is None:
        return False, "Database engine not available."
    if not recipe_id:
        return False, "Recipe ID required."
    if not recipe_data.get("name") or not str(recipe_data.get("name")).strip():
        return False, "Recipe name is required."
    if not components:
        return False, "At least one component is required."

    clean = {
        "name": recipe_data["name"].strip(),
        "description": _strip_or_none(recipe_data.get("description")),
        "is_active": bool(recipe_data.get("is_active", True)),
        "type": _strip_or_none(recipe_data.get("type")),
        "default_yield_qty": recipe_data.get("default_yield_qty"),
        "default_yield_unit": _strip_or_none(recipe_data.get("default_yield_unit")),
        "plating_notes": _strip_or_none(recipe_data.get("plating_notes")),
        "tags": recipe_data.get("tags"),
        "version": recipe_data.get("version"),
        "effective_from": recipe_data.get("effective_from"),
        "effective_to": recipe_data.get("effective_to"),
        "rid": recipe_id,
    }

    upd_q = text(
        """
        UPDATE recipes
        SET name=:name,
            description=:description,
            is_active=:is_active,
            type=:type,
            default_yield_qty=:default_yield_qty,
            default_yield_unit=:default_yield_unit,
            plating_notes=:plating_notes,
            tags=:tags,
            version=:version,
            effective_from=:effective_from,
            effective_to=:effective_to,
            updated_at=NOW()
        WHERE recipe_id=:rid;
        """
    )
    del_q = text("DELETE FROM recipe_components WHERE parent_recipe_id=:rid;")
    ins_q = text(
        """
        INSERT INTO recipe_components (parent_recipe_id, component_kind, component_id, quantity,
                                      unit, loss_pct, sort_order, notes)
        VALUES (:parent_recipe_id, :component_kind, :component_id, :quantity,
                :unit, :loss_pct, :sort_order, :notes);
        """
    )

    try:
        with engine.connect() as conn:
            with conn.begin():
                res = conn.execute(upd_q, clean)
                if res.rowcount == 0:
                    return False, "Recipe not found."
                conn.execute(del_q, {"rid": recipe_id})
                for idx, comp in enumerate(components, start=1):
                    kind = comp.get("component_kind")
                    cid = comp.get("component_id")
                    qty = comp.get("quantity")
                    if kind not in {"ITEM", "RECIPE"} or not cid or qty is None or qty <= 0:
                        raise ValueError("Invalid component data")
                    unit = _strip_or_none(comp.get("unit"))
                    unit = _component_unit(conn, kind, cid, unit)
                    loss_pct = float(comp.get("loss_pct", 0) or 0)
                    sort_order = comp.get("sort_order", idx)
                    notes = _strip_or_none(comp.get("notes"))
                    if kind == "RECIPE" and _creates_cycle(conn, recipe_id, cid):
                        raise ValueError("Circular recipe reference detected")
                    conn.execute(
                        ins_q,
                        {
                            "parent_recipe_id": recipe_id,
                            "component_kind": kind,
                            "component_id": cid,
                            "quantity": float(qty),
                            "unit": unit,
                            "loss_pct": loss_pct,
                            "sort_order": sort_order,
                            "notes": notes,
                        },
                    )
        return True, f"Recipe '{clean['name']}' updated."
    except IntegrityError as ie:
        logger.error(
            "ERROR [recipe_service.update_recipe]: Integrity error: %s\n%s",
            ie,
            traceback.format_exc(),
        )
        msg = (
            "Duplicate recipe name."
            if "unique" in str(ie).lower()
            else "Integrity error."
        )
        return False, msg
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [recipe_service.update_recipe]: DB error: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred."


def delete_recipe(engine: Engine, recipe_id: int) -> Tuple[bool, str]:
    """Delete a recipe."""
    if engine is None:
        return False, "Database engine not available."
    if not recipe_id:
        return False, "Recipe ID required."
    del_q = text("DELETE FROM recipes WHERE recipe_id=:rid;")
    try:
        with engine.begin() as conn:
            res = conn.execute(del_q, {"rid": recipe_id})
            if res.rowcount == 0:
                return False, "Recipe not found."
        return True, "Recipe deleted."
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [recipe_service.delete_recipe]: DB error: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred."


# ─────────────────────────────────────────────────────────
# CLONE RECIPE
# ─────────────────────────────────────────────────────────


def clone_recipe(
    engine: Engine,
    original_id: int,
    new_name: str,
    new_desc: Optional[str] = None,
) -> Tuple[bool, str, Optional[int]]:
    """Duplicate a recipe and its component rows."""

    if engine is None:
        return False, "Database engine not available.", None
    if not original_id:
        return False, "Original recipe ID required.", None
    if not new_name or not new_name.strip():
        return False, "New recipe name required.", None

    clean_name = new_name.strip()

    try:
        with engine.begin() as conn:
            header = conn.execute(
                text(
                    "SELECT description, is_active, type, default_yield_qty, default_yield_unit, "
                    "plating_notes, tags, version, effective_from, effective_to "
                    "FROM recipes WHERE recipe_id=:rid"
                ),
                {"rid": original_id},
            ).mappings().fetchone()

            if not header:
                return False, "Original recipe not found.", None

            desc = (
                new_desc.strip()
                if isinstance(new_desc, str) and new_desc.strip()
                else header["description"]
            )

            new_id = conn.execute(
                text(
                    """
                    INSERT INTO recipes (name, description, is_active, type, default_yield_qty, default_yield_unit,
                                         plating_notes, tags, version, effective_from, effective_to)
                    VALUES (:n, :d, :a, :t, :dyq, :dyu, :pn, :tags, :ver, :ef, :et)
                    RETURNING recipe_id;
                    """
                ),
                {
                    "n": clean_name,
                    "d": desc,
                    "a": header["is_active"],
                    "t": header["type"],
                    "dyq": header["default_yield_qty"],
                    "dyu": header["default_yield_unit"],
                    "pn": header["plating_notes"],
                    "tags": header["tags"],
                    "ver": header["version"],
                    "ef": header["effective_from"],
                    "et": header["effective_to"],
                },
            ).scalar_one_or_none()
            if not new_id:
                raise Exception("Failed to insert cloned recipe header.")

            comps = conn.execute(
                text(
                    "SELECT component_kind, component_id, quantity, unit, loss_pct, sort_order, notes "
                    "FROM recipe_components WHERE parent_recipe_id=:rid ORDER BY sort_order"
                ),
                {"rid": original_id},
            ).mappings().all()

            for row in comps:
                conn.execute(
                    text(
                        """
                        INSERT INTO recipe_components (parent_recipe_id, component_kind, component_id,
                                                       quantity, unit, loss_pct, sort_order, notes)
                        VALUES (:pr, :ck, :cid, :q, :u, :l, :s, :n);
                        """
                    ),
                    {
                        "pr": new_id,
                        "ck": row["component_kind"],
                        "cid": row["component_id"],
                        "q": row["quantity"],
                        "u": row["unit"],
                        "l": row["loss_pct"],
                        "s": row["sort_order"],
                        "n": row["notes"],
                    },
                )

        return True, f"Recipe '{clean_name}' cloned.", new_id
    except IntegrityError as ie:
        logger.error(
            "ERROR [recipe_service.clone_recipe]: Integrity error: %s\n%s",
            ie,
            traceback.format_exc(),
        )
        msg = (
            "Recipe with this name already exists."
            if "unique" in str(ie).lower()
            else "Integrity error."
        )
        return False, msg, None
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [recipe_service.clone_recipe]: DB error: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred.", None


# ─────────────────────────────────────────────────────────
# SALES RECORDING USING RECIPES
# ─────────────────────────────────────────────────────────


def _expand_requirements(
    conn: Connection,
    recipe_id: int,
    multiplier: float,
    totals: Dict[int, float],
    visited: Set[int],
) -> None:
    """Recursively accumulate item requirements for a recipe."""
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
        if row["unit"] is None:
            raise ValueError("Component unit missing")
        qty = multiplier * float(row["quantity"]) / (
            1 - float(row["loss_pct"] or 0) / 100.0
        )
        if row["component_kind"] == "ITEM":
            item = conn.execute(
                text("SELECT unit, is_active FROM items WHERE item_id=:i"),
                {"i": row["component_id"]},
            ).mappings().fetchone()
            if not item:
                raise ValueError(f"Item {row['component_id']} not found")
            if not item["is_active"]:
                raise ValueError("Inactive item component encountered")
            if item["unit"] != row["unit"]:
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
    """Return total item requirements for given recipe quantity."""
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
    sale_ins_q = text(
        "INSERT INTO sales_transactions (recipe_id, quantity, user_id, notes) VALUES (:r, :q, :u, :n);"
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
                    sale_ins_q,
                    {"r": recipe_id, "q": quantity, "u": user_id_clean, "n": notes_clean},
                )
                for iid, qty in totals.items():
                    ok = stock_service.record_stock_transaction(
                        item_id=iid,
                        quantity_change=-qty,
                        transaction_type=TX_SALE,
                        user_id=user_id_clean,
                        related_mrn=None,
                        related_po_id=None,
                        notes=f"Recipe {recipe_id} sale",  # type: ignore
                        db_engine_param=None,
                        db_connection_param=conn,
                    )
                    if not ok:
                        raise Exception(
                            f"Failed stock tx for item {iid} during sale."
                        )
        return True, "Sale recorded."
    except ValueError as ve:
        logger.error("ERROR [recipe_service.record_sale]: %s", ve)
        return False, str(ve)
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [recipe_service.record_sale]: Error recording sale: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred during sale recording."

