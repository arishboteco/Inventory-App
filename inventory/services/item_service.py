"""Database-backed item service utilities for the Django app.

This module extracts a subset of the legacy Streamlit service functions and
makes them available for the Django codebase.  Any Streamlit-specific caching is
replaced with :func:`functools.lru_cache` so that callers can clear caches after
mutating operations.
"""
from __future__ import annotations

import logging
import re
import traceback
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from inventory.unit_inference import infer_units

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _fetch_df(
    engine: Engine, query: str, params: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """Execute ``query`` and return the results as a :class:`pandas.DataFrame`."""
    if engine is None:
        logger.error("Database engine not available")
        return pd.DataFrame()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return pd.DataFrame(result.mappings().all())
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error("Error fetching data: %s\n%s", e, traceback.format_exc())
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Cached lookup helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def get_all_items_with_stock(
    _engine: Engine, include_inactive: bool = False
) -> pd.DataFrame:
    """Return all items with their current stock.

    A convenience ``unit`` column mirroring ``base_unit`` is included so that
    callers can use a single field for display purposes.
    """
    if _engine is None:
        logger.error("ERROR [item_service.get_all_items_with_stock]: Database engine not available.")
        return pd.DataFrame()
    query = (
        "SELECT item_id, name, base_unit, purchase_unit, category, sub_category, "
        "permitted_departments, reorder_point, current_stock, notes, is_active FROM items"
    )
    if not include_inactive:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name;"
    df = _fetch_df(_engine, query)
    df["unit"] = df["base_unit"]
    return df


# expose a ``clear`` method like the legacy cache decorator
get_all_items_with_stock.clear = get_all_items_with_stock.cache_clear  # type: ignore[attr-defined]


@lru_cache(maxsize=None)
def suggest_category_and_units(
    _engine: Engine, item_name: str
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Guess base unit, purchase unit and category for ``item_name``.

    The first database row whose name contains any token from ``item_name`` is
    returned.  If no match is found ``(None, None, None)`` is returned so callers
    may fall back to heuristic inference.
    """
    if _engine is None or not item_name:
        return None, None, None
    tokens = [t for t in re.split(r"\W+", item_name.lower()) if t]
    if not tokens:
        return None, None, None
    query = text(
        "SELECT base_unit, purchase_unit, category FROM items "
        "WHERE lower(name) LIKE :pattern LIMIT 1"
    )
    with _engine.connect() as conn:
        for token in tokens:
            row = conn.execute(query, {"pattern": f"%{token}%"}).mappings().first()
            if row:
                return row["base_unit"], row["purchase_unit"], row["category"]
    return None, None, None


suggest_category_and_units.clear = (  # type: ignore[attr-defined]
    suggest_category_and_units.cache_clear
)


@lru_cache(maxsize=None)
def get_distinct_departments_from_items(_engine: Engine) -> List[str]:
    """Return a sorted list of unique department names from active items."""
    if _engine is None:
        logger.error(
            "ERROR [item_service.get_distinct_departments_from_items]: Database engine not available."
        )
        return []
    query = (
        "SELECT permitted_departments FROM items "
        "WHERE is_active = TRUE AND permitted_departments IS NOT NULL "
        "AND permitted_departments <> '' AND permitted_departments <> ' ';"
    )
    departments: Set[str] = set()
    try:
        with _engine.connect() as conn:
            result = conn.execute(text(query))
            for (permitted,) in result.fetchall():
                if permitted:
                    departments.update({d.strip() for d in permitted.split(",") if d.strip()})
        return sorted(departments)
    except Exception as e:  # pragma: no cover - defensive logging
        logger.error(
            "ERROR [item_service.get_distinct_departments_from_items]: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return []


get_distinct_departments_from_items.clear = (  # type: ignore[attr-defined]
    get_distinct_departments_from_items.cache_clear
)


# ---------------------------------------------------------------------------
# Mutating helpers
# ---------------------------------------------------------------------------

def add_new_item(engine: Engine, details: Dict[str, Any]) -> Tuple[bool, str]:
    """Insert a single item into the database."""
    if engine is None:
        return False, "Database engine not available."

    s_base, s_purchase, s_category = suggest_category_and_units(
        engine, details.get("name", "")
    )
    if s_base and not str(details.get("base_unit", "")).strip():
        details["base_unit"] = s_base
    if s_purchase and not str(details.get("purchase_unit", "")).strip():
        details["purchase_unit"] = s_purchase
    if s_category and not details.get("category"):
        details["category"] = s_category

    if (
        not details.get("base_unit")
        or not str(details.get("base_unit")).strip()
        or not details.get("purchase_unit")
        or not str(details.get("purchase_unit")).strip()
    ):
        inferred_base, inferred_purchase = infer_units(
            details.get("name", ""), details.get("category")
        )
        if not str(details.get("base_unit", "")).strip():
            details["base_unit"] = inferred_base
        if not str(details.get("purchase_unit", "")).strip() and inferred_purchase:
            details["purchase_unit"] = inferred_purchase

    required = ["name", "base_unit"]
    if not all(details.get(k) and str(details.get(k)).strip() for k in required):
        missing = [k for k in required if not details.get(k) or not str(details.get(k)).strip()]
        return False, f"Missing or empty required fields: {', '.join(missing)}"

    notes_val = details.get("notes")
    cleaned_notes = notes_val.strip() if isinstance(notes_val, str) else None
    if cleaned_notes == "":
        cleaned_notes = None

    permitted_val = details.get("permitted_departments")
    cleaned_permitted = (
        permitted_val.strip() if isinstance(permitted_val, str) and permitted_val.strip() else None
    )

    purchase_unit_val = details.get("purchase_unit")
    if isinstance(purchase_unit_val, str):
        purchase_unit_val = purchase_unit_val.strip() or None

    params = {
        "name": details["name"].strip(),
        "base_unit": details["base_unit"].strip(),
        "purchase_unit": purchase_unit_val,
        "category": (details.get("category", "").strip() or "Uncategorized"),
        "sub_category": (details.get("sub_category", "").strip() or "General"),
        "permitted_departments": cleaned_permitted,
        "reorder_point": details.get("reorder_point", 0.0),
        "current_stock": details.get("current_stock", 0.0),
        "notes": cleaned_notes,
        "is_active": details.get("is_active", True),
    }
    query = text(
        """
        INSERT INTO items (
            name, base_unit, purchase_unit, category, sub_category,
            permitted_departments, reorder_point, current_stock, notes, is_active
        ) VALUES (
            :name, :base_unit, :purchase_unit, :category, :sub_category,
            :permitted_departments, :reorder_point, :current_stock, :notes, :is_active
        ) RETURNING item_id;
        """
    )
    try:
        with engine.connect() as conn:
            with conn.begin():
                new_id = conn.execute(query, params).scalar_one_or_none()
        if new_id:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear()
            return True, f"Item '{params['name']}' added with ID {new_id}."
        return False, "Failed to add item (no ID returned)."
    except IntegrityError:
        return (
            False,
            f"Item name '{params['name']}' already exists. Choose a unique name.",
        )
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [item_service.add_new_item]: Database error adding item: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred while adding the item."


def add_items_bulk(engine: Engine, items: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
    """Insert multiple items in a single transaction."""
    if engine is None:
        return 0, ["Database engine not available."]
    if not items:
        return 0, ["No items provided."]

    processed: List[Dict[str, Any]] = []
    errors: List[str] = []
    for idx, details in enumerate(items):
        s_base, s_purchase, s_category = suggest_category_and_units(
            engine, details.get("name", "")
        )
        if s_base and not str(details.get("base_unit", "")).strip():
            details["base_unit"] = s_base
        if s_purchase and not str(details.get("purchase_unit", "")).strip():
            details["purchase_unit"] = s_purchase
        if s_category and not details.get("category"):
            details["category"] = s_category

        if (
            not details.get("base_unit")
            or not str(details.get("base_unit")).strip()
            or not details.get("purchase_unit")
            or not str(details.get("purchase_unit")).strip()
        ):
            inferred_base, inferred_purchase = infer_units(
                details.get("name", ""), details.get("category")
            )
            if not str(details.get("base_unit", "")).strip():
                details["base_unit"] = inferred_base
            if not str(details.get("purchase_unit", "")).strip() and inferred_purchase:
                details["purchase_unit"] = inferred_purchase

        required = ["name", "base_unit"]
        if not all(details.get(k) and str(details.get(k)).strip() for k in required):
            missing = [k for k in required if not details.get(k) or not str(details.get(k)).strip()]
            errors.append(f"Item {idx} missing required fields: {', '.join(missing)}")
            continue

        notes_val = details.get("notes")
        cleaned_notes = notes_val.strip() if isinstance(notes_val, str) else None
        if cleaned_notes == "":
            cleaned_notes = None

        permitted_val = details.get("permitted_departments")
        cleaned_permitted = (
            permitted_val.strip() if isinstance(permitted_val, str) and permitted_val.strip() else None
        )

        purchase_unit_val = details.get("purchase_unit")
        if isinstance(purchase_unit_val, str):
            purchase_unit_val = purchase_unit_val.strip() or None

        processed.append(
            {
                "name": details["name"].strip(),
                "base_unit": details["base_unit"].strip(),
                "purchase_unit": purchase_unit_val,
                "category": (details.get("category", "").strip() or "Uncategorized"),
                "sub_category": (details.get("sub_category", "").strip() or "General"),
                "permitted_departments": cleaned_permitted,
                "reorder_point": details.get("reorder_point", 0.0),
                "current_stock": details.get("current_stock", 0.0),
                "notes": cleaned_notes,
                "is_active": details.get("is_active", True),
            }
        )

    if errors:
        return 0, errors

    query = text(
        """
        INSERT INTO items (
            name, base_unit, purchase_unit, category, sub_category,
            permitted_departments, reorder_point, current_stock, notes, is_active
        ) VALUES (
            :name, :base_unit, :purchase_unit, :category, :sub_category,
            :permitted_departments, :reorder_point, :current_stock, :notes, :is_active
        );
        """
    )
    try:
        with engine.connect() as conn:
            with conn.begin():
                result = conn.execute(query, processed)
                inserted = result.rowcount or 0
        if inserted:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear()
        return inserted, []
    except IntegrityError as e:
        return 0, [str(e.orig) if hasattr(e, "orig") else str(e)]
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [item_service.add_items_bulk]: Database error adding items: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return 0, ["A database error occurred while adding items."]


def remove_items_bulk(engine: Engine, item_ids: List[int]) -> Tuple[int, List[str]]:
    """Mark multiple items inactive by ID."""
    if engine is None:
        return 0, ["Database engine not available."]
    if not item_ids:
        return 0, ["No item IDs provided."]

    query = text("UPDATE items SET is_active = FALSE WHERE item_id IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    try:
        with engine.connect() as conn:
            with conn.begin():
                result = conn.execute(query, {"ids": item_ids})
                affected = result.rowcount or 0
        if affected:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear()
        return affected, []
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [item_service.remove_items_bulk]: Database error removing items: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return 0, ["A database error occurred while removing items."]


# ---------------------------------------------------------------------------
# Non-cached detail lookup
# ---------------------------------------------------------------------------

def get_item_details(engine: Engine, item_id: int) -> Optional[Dict[str, Any]]:
    """Return the details for a single item."""
    if engine is None:
        logger.error(
            "ERROR [item_service.get_item_details]: Database engine not available."
        )
        return None
    query = (
        "SELECT item_id, name, base_unit, purchase_unit, category, sub_category, "
        "permitted_departments, reorder_point, current_stock, notes, is_active FROM items "
        "WHERE item_id = :item_id;"
    )
    df = _fetch_df(engine, query, {"item_id": item_id})
    if not df.empty:
        result = df.iloc[0].to_dict()
        result["unit"] = result.get("base_unit")
        return result
    return None
