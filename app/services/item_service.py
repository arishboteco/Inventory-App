# app/services/item_service.py
from datetime import datetime, timedelta
import re
import traceback
from typing import Any, Optional, Dict, List, Tuple, Set

import pandas as pd
import streamlit as st  # Only for type hinting @st.cache_data
from sqlalchemy import text, bindparam
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.engine import Engine

from app.core.logging import get_logger
from app.db.database_utils import fetch_data
from app.core.unit_inference import infer_units

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────
# ITEM MASTER FUNCTIONS
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching item data...")
def get_all_items_with_stock(_engine: Engine, include_inactive=False) -> pd.DataFrame:
    """
    Fetches all items, optionally including inactive ones, with their current stock.
    This version does NOT select created_at or updated_at from the items table.
    Args:
        _engine: SQLAlchemy database engine instance.
        include_inactive: Flag to include inactive items.
    Returns:
        Pandas DataFrame of items.
    """
    if _engine is None:
        logger.error(
            "ERROR [item_service.get_all_items_with_stock]: Database engine not available."
        )
        return pd.DataFrame()
    # Include purchase_unit so UIs can offer both base and purchasing units
    query = (
        "SELECT item_id, name, base_unit, purchase_unit, category, sub_category, "
        "permitted_departments, reorder_point, current_stock, notes, is_active FROM items"
    )
    if not include_inactive:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name;"
    df = fetch_data(_engine, query)
    # Duplicate base_unit into a user-facing 'unit' column for convenience
    df["unit"] = df["base_unit"]
    return df


def get_item_details(engine: Engine, item_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches details for a specific item by its ID.
    This version does NOT select created_at or updated_at from the items table.
    (This function is NOT CACHED)
    Args:
        engine: SQLAlchemy database engine instance.
        item_id: The ID of the item to fetch.
    Returns:
        Dictionary of item details or None if not found.
    """
    if engine is None:
        logger.error(
            "ERROR [item_service.get_item_details]: Database engine not available."
        )
        return None
    query = (
        "SELECT item_id, name, base_unit, purchase_unit, category, sub_category, permitted_departments, "
        "reorder_point, current_stock, notes, is_active FROM items WHERE item_id = :item_id;"
    )
    df = fetch_data(engine, query, {"item_id": item_id})
    if not df.empty:
        result = df.iloc[0].to_dict()
        # Mirror base_unit into a 'unit' key for downstream consumers
        result["unit"] = result.get("base_unit")
        return result
    return None


@st.cache_data(ttl=300)
def get_category_dropdowns(engine: Engine) -> Dict[str, List[str]]:
    """Return mapping of parent categories to their sub-categories.

    Parameters
    ----------
    engine : Engine
        SQLAlchemy database engine instance.

    Returns
    -------
    Dict[str, List[str]]
        Dictionary where keys are top-level category names and values are
        sorted lists of sub-category names. Categories without children map to
        an empty list.
    """
    if engine is None:
        logger.error(
            "ERROR [item_service.get_category_dropdowns]: Database engine not available."
        )
        return {}

    query = (
        "SELECT id, name, parent_id FROM category ORDER BY name"
    )
    df = fetch_data(engine, query)
    if df.empty:
        return {}

    mapping: Dict[str, List[str]] = {}
    parents = df[df["parent_id"].isna()]
    for _, parent_row in parents.iterrows():
        parent_id = parent_row["id"]
        parent_name = parent_row["name"]
        children = (
            df[df["parent_id"] == parent_id]["name"].sort_values().tolist()
        )
        mapping[parent_name] = children
    return mapping


@st.cache_data(ttl=300)
def suggest_category_and_units(
    _engine: Engine, item_name: str
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Guess units and category for a new item based on existing entries.

    The database is queried for items whose names share at least one token
    with ``item_name``.  When a match is found, the matched row's
    ``base_unit``, ``purchase_unit`` and ``category`` are returned.  If no
    match exists the function returns ``(None, None, None)`` so callers can
    fall back to heuristic inference.
    """

    if _engine is None or not item_name:
        return None, None, None

    # Break the item name into alphanumeric tokens and search for the first
    # existing item that contains any of them.  This simple heuristic allows
    # users to benefit from previously entered items without maintaining a
    # separate lookup table.
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


def add_new_item(engine: Engine, details: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Adds a new item to the database.
    This version does NOT insert created_at or updated_at into the items table.
    It correctly handles None or empty strings for 'notes' and 'permitted_departments'.
    Args:
        engine: SQLAlchemy database engine instance.
        details: Dictionary containing item details.
    Returns:
        Tuple (success_status, message).
    """
    if engine is None:
        return False, "Database engine not available."

    # ------------------------------------------------------------------
    # Suggest units and category from similar existing items.
    # ------------------------------------------------------------------
    s_base, s_purchase, s_category = suggest_category_and_units(
        engine, details.get("name", "")
    )
    if s_base and (not details.get("base_unit") or not str(details.get("base_unit")).strip()):
        details["base_unit"] = s_base
    if s_purchase and (
        not details.get("purchase_unit") or not str(details.get("purchase_unit")).strip()
    ):
        details["purchase_unit"] = s_purchase
    if s_category and not details.get("category"):
        details["category"] = s_category

    # ------------------------------------------------------------------
    # Fallback to heuristic inference if still missing units.
    # ------------------------------------------------------------------
    if (
        not details.get("base_unit")
        or not str(details.get("base_unit")).strip()
        or not details.get("purchase_unit")
        or not str(details.get("purchase_unit")).strip()
    ):
        inferred_base, inferred_purchase = infer_units(
            details.get("name", ""), details.get("category")
        )
        if not details.get("base_unit") or not str(details.get("base_unit")).strip():
            details["base_unit"] = inferred_base
        if (
            (not details.get("purchase_unit") or not str(details.get("purchase_unit")).strip())
            and inferred_purchase
        ):
            details["purchase_unit"] = inferred_purchase

    required = ["name", "base_unit"]
    if not all(details.get(k) and str(details.get(k)).strip() for k in required):
        missing = [
            k for k in required if not details.get(k) or not str(details.get(k)).strip()
        ]
        return False, f"Missing or empty required fields: {', '.join(missing)}"

    # Robust handling for notes
    notes_value_from_details = details.get("notes")
    cleaned_notes_for_db = None
    if isinstance(notes_value_from_details, str):
        cleaned_notes_for_db = notes_value_from_details.strip()
        if not cleaned_notes_for_db:
            cleaned_notes_for_db = None

    # Robust handling for permitted_departments
    permitted_departments_value = details.get("permitted_departments")
    cleaned_permitted_departments = None
    if isinstance(permitted_departments_value, str):
        cleaned_permitted_departments = permitted_departments_value.strip()
        if not cleaned_permitted_departments:
            cleaned_permitted_departments = None

    purchase_unit_val = details.get("purchase_unit")
    if isinstance(purchase_unit_val, str):
        purchase_unit_val = purchase_unit_val.strip() or None

    params = {
        "name": details["name"].strip(),
        "base_unit": details["base_unit"].strip(),
        "purchase_unit": purchase_unit_val,
        "category": (details.get("category", "").strip() or "Uncategorized"),
        "sub_category": (details.get("sub_category", "").strip() or "General"),
        "permitted_departments": cleaned_permitted_departments,  # Use the cleaned value
        "reorder_point": details.get("reorder_point", 0.0),
        "current_stock": details.get("current_stock", 0.0),
        "notes": cleaned_notes_for_db,  # Use the cleaned value
        "is_active": details.get("is_active", True),
    }
    query = text(
        """
        INSERT INTO items (name, base_unit, purchase_unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active)
        VALUES (:name, :base_unit, :purchase_unit, :category, :sub_category, :permitted_departments, :reorder_point, :current_stock, :notes, :is_active)
        RETURNING item_id;
    """
    )  # No created_at, updated_at
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, params)
                new_id = result.scalar_one_or_none()
        if new_id:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear()
            return True, f"Item '{params['name']}' added with ID {new_id}."
        else:
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
    """Insert multiple items in one transaction.

    Args:
        engine: SQLAlchemy database engine instance.
        items: List of item detail dictionaries.

    Returns:
        Tuple of (number_of_items_inserted, list_of_error_messages).
    """
    if engine is None:
        return 0, ["Database engine not available."]
    if not items:
        return 0, ["No items provided."]

    processed: List[Dict[str, Any]] = []
    errors: List[str] = []

    for idx, details in enumerate(items):
        # Suggest details from similar existing items
        s_base, s_purchase, s_category = suggest_category_and_units(
            engine, details.get("name", "")
        )
        if s_base and (not details.get("base_unit") or not str(details.get("base_unit")).strip()):
            details["base_unit"] = s_base
        if s_purchase and (
            not details.get("purchase_unit") or not str(details.get("purchase_unit")).strip()
        ):
            details["purchase_unit"] = s_purchase
        if s_category and not details.get("category"):
            details["category"] = s_category

        # Infer units heuristically if still missing
        if (
            not details.get("base_unit")
            or not str(details.get("base_unit")).strip()
            or not details.get("purchase_unit")
            or not str(details.get("purchase_unit")).strip()
        ):
            inferred_base, inferred_purchase = infer_units(
                details.get("name", ""), details.get("category")
            )
            if not details.get("base_unit") or not str(details.get("base_unit")).strip():
                details["base_unit"] = inferred_base
            if (
                (not details.get("purchase_unit") or not str(details.get("purchase_unit")).strip())
                and inferred_purchase
            ):
                details["purchase_unit"] = inferred_purchase

        required = ["name", "base_unit"]
        if not all(details.get(k) and str(details.get(k)).strip() for k in required):
            missing = [
                k for k in required if not details.get(k) or not str(details.get(k)).strip()
            ]
            errors.append(
                f"Item {idx} missing required fields: {', '.join(missing)}"
            )
            continue

        notes_value = details.get("notes")
        cleaned_notes = None
        if isinstance(notes_value, str):
            cleaned_notes = notes_value.strip() or None

        permitted_val = details.get("permitted_departments")
        cleaned_permitted = None
        if isinstance(permitted_val, str):
            cleaned_permitted = permitted_val.strip() or None

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
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, processed)
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
    """Deactivate multiple items by ID in a single statement."""
    if engine is None:
        return 0, ["Database engine not available."]
    if not item_ids:
        return 0, ["No item IDs provided."]

    query = (
        text("UPDATE items SET is_active = FALSE WHERE item_id IN :ids")
        .bindparams(bindparam("ids", expanding=True))
    )

    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"ids": item_ids})
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


def update_item_details(
    engine: Engine, item_id: int, updates: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Updates details for an existing item.
    This version does NOT set an 'updated_at' column.
    Args:
        engine: SQLAlchemy database engine instance.
        item_id: The ID of the item to update.
        updates: Dictionary of fields to update.
    Returns:
        Tuple (success_status, message).
    """
    if engine is None:
        return False, "Database engine not available."
    if not item_id or not updates:
        return False, "Invalid item ID or no updates provided."

    set_clauses = []
    params = {"item_id": item_id}
    allowed_fields = [
        "name",
        "base_unit",
        "purchase_unit",
        "category",
        "sub_category",
        "permitted_departments",
        "reorder_point",
        "notes",
    ]

    if "name" in updates and not updates["name"].strip():
        return False, "Item Name cannot be empty."
    if "base_unit" in updates and not updates["base_unit"].strip():
        return False, "Base unit cannot be empty."

    for key, value in updates.items():
        if key in allowed_fields:
            set_clauses.append(f"{key} = :{key}")
            current_val = value
            if isinstance(current_val, str):
                current_val = current_val.strip()
                if key in ["category", "sub_category"] and not current_val:
                    params[key] = "Uncategorized" if key == "category" else "General"
                elif key in ["permitted_departments", "notes"] and not current_val:
                    params[key] = None
                else:
                    params[key] = current_val
            elif key == "reorder_point" and current_val is not None:
                try:
                    params[key] = float(current_val)
                except (ValueError, TypeError):
                    return (
                        False,
                        f"Invalid numeric value for reorder_point: {current_val}",
                    )
            else:
                params[key] = current_val

    if not set_clauses:
        return False, "No valid fields provided for update."
    query_str = f"UPDATE items SET {', '.join(set_clauses)} WHERE item_id = :item_id;"  # No updated_at = NOW()
    query = text(query_str)

    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, params)
        if result.rowcount > 0:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear()
            return True, f"Item ID {item_id} updated successfully."
        else:
            existing_item = get_item_details(engine, item_id)
            if existing_item is None:
                return False, f"Update failed: Item ID {item_id} not found."
            return (
                True,
                f"No changes detected for Item ID {item_id}. Update considered successful.",
            )
    except IntegrityError:
        return (
            False,
            f"Update failed: Potential duplicate name '{updates.get('name')}'.",
        )
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [item_service.update_item_details]: Database error updating item %s: %s\n%s",
            item_id,
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred while updating the item."


def deactivate_item(engine: Engine, item_id: int) -> Tuple[bool, str]:
    """
    Deactivates an item. This version does NOT set updated_at.
    Args:
        engine: SQLAlchemy database engine instance.
        item_id: The ID of the item to deactivate.
    Returns:
        Tuple (success_status, message).
    """
    if engine is None:
        return False, "Database engine not available."
    query = text(
        "UPDATE items SET is_active = FALSE WHERE item_id = :item_id;"
    )  # No updated_at = NOW()
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"item_id": item_id})
        if result.rowcount > 0:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear()
            return True, "Item deactivated successfully."
        return False, "Item not found or already inactive."
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [item_service.deactivate_item]: Error deactivating item %s: %s\n%s",
            item_id,
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred."


def reactivate_item(engine: Engine, item_id: int) -> Tuple[bool, str]:
    """
    Reactivates an item. This version does NOT set updated_at.
    Args:
        engine: SQLAlchemy database engine instance.
        item_id: The ID of the item to reactivate.
    Returns:
        Tuple (success_status, message).
    """
    if engine is None:
        return False, "Database engine not available."
    query = text(
        "UPDATE items SET is_active = TRUE WHERE item_id = :item_id;"
    )  # No updated_at = NOW()
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"item_id": item_id})
        if result.rowcount > 0:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear()
            return True, "Item reactivated successfully."
        return False, "Item not found or already active."
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [item_service.reactivate_item]: Error reactivating item %s: %s\n%s",
            item_id,
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred."


# ─────────────────────────────────────────────────────────
# DEPARTMENT & ITEM HISTORY/SUGGESTIONS FUNCTIONS
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching department list...")
def get_distinct_departments_from_items(_engine: Engine) -> List[str]:
    """
    Fetches a sorted list of unique, non-empty department names from active items.
    Args:
        _engine: SQLAlchemy database engine instance.
    Returns:
        List of distinct department names.
    """
    if _engine is None:
        logger.error(
            "ERROR [item_service.get_distinct_departments_from_items]: Database engine not available."
        )
        return []
    query = text(
        """
        SELECT permitted_departments FROM items
        WHERE is_active = TRUE AND permitted_departments IS NOT NULL AND permitted_departments <> '' AND permitted_departments <> ' ';
    """
    )
    departments_set: Set[str] = set()
    try:
        with _engine.connect() as connection:
            result = connection.execute(query)
            rows = result.fetchall()
        for row_tuple in rows:
            permitted_str = row_tuple[0]
            if permitted_str:
                departments = {
                    dept.strip() for dept in permitted_str.split(",") if dept.strip()
                }
                departments_set.update(departments)
        return sorted(list(departments_set))
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [item_service.get_distinct_departments_from_items]: Error fetching distinct departments: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return []


@st.cache_data(ttl=300)
def get_item_order_history_details(
    _engine: Engine, item_id: int, department_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetches last ordered date and median requested quantity for an item, optionally filtered by department.
    Args:
        _engine: SQLAlchemy database engine instance.
        item_id: The ID of the item.
        department_name: Optional department name to filter history.
    Returns:
        Dictionary with 'last_ordered_date' and 'median_quantity'.
    """
    if _engine is None or item_id is None:
        logger.error(
            "ERROR [item_service.get_item_order_history_details]: Database engine or item_id not available."
        )
        return {"last_ordered_date": None, "median_quantity": None}

    params: Dict[str, Any] = {"item_id": item_id}
    date_query_conditions = ["ii.item_id = :item_id"]
    qty_query_conditions = ["ii.item_id = :item_id"]

    if department_name:
        date_query_conditions.append("ind.department = :department_name")
        qty_query_conditions.append("ind.department = :department_name")
        params["department_name"] = department_name

    date_where_clause = " AND ".join(date_query_conditions)
    qty_where_clause = " AND ".join(qty_query_conditions)

    last_ordered_date_query = text(
        f"SELECT MAX(ind.date_submitted) AS last_ordered_date FROM indent_items ii JOIN indents ind ON ii.indent_id = ind.indent_id WHERE {date_where_clause};"
    )
    median_quantity_query = text(
        f"SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY ii.requested_qty) AS median_quantity FROM indent_items ii JOIN indents ind ON ii.indent_id = ind.indent_id WHERE {qty_where_clause};"
    )

    last_date_str: Optional[str] = None
    median_qty_val: Optional[float] = None

    try:
        with _engine.connect() as connection:
            date_result = connection.execute(
                last_ordered_date_query, params
            ).scalar_one_or_none()
            if date_result and pd.notna(date_result):
                last_date_str = pd.to_datetime(date_result).strftime("%d-%b-%Y")

            qty_result = connection.execute(
                median_quantity_query, params
            ).scalar_one_or_none()
            if qty_result is not None:
                median_qty_val = float(qty_result)
    except Exception as e:
        logger.warning(
            "WARNING [item_service.get_item_order_history_details]: Could not fetch full order history for item %s, dept %s: %s - %s",
            item_id,
            department_name,
            type(e).__name__,
            e,
        )
    return {"last_ordered_date": last_date_str, "median_quantity": median_qty_val}


@st.cache_data(ttl=3600, show_spinner="Analyzing item suggestions...")
def get_suggested_items_for_department(
    _engine: Engine, department_name: str, top_n: int = 5, days_recency: int = 90
) -> List[Dict[str, Any]]:
    """
    Suggests items for a department based on recent order frequency.
    Args:
        _engine: SQLAlchemy database engine instance.
        department_name: The name of the department.
        top_n: Number of suggestions to return.
        days_recency: How many days back to consider for recency.
    Returns:
        List of suggested item dictionaries.
    """
    if _engine is None or not department_name:
        logger.error(
            "ERROR [item_service.get_suggested_items_for_department]: Database engine or department_name not available."
        )
        return []

    cutoff_date_val = datetime.now() - timedelta(days=days_recency)
    query = text(
        """
        SELECT i.item_id, i.name AS item_name, i.base_unit, COUNT(ii.item_id) as order_frequency
        FROM indent_items ii JOIN items i ON ii.item_id = i.item_id JOIN indents ind ON ii.indent_id = ind.indent_id
        WHERE ind.department = :department_name AND ind.date_submitted >= :cutoff_date AND i.is_active = TRUE
        GROUP BY i.item_id, i.name, i.base_unit ORDER BY order_frequency DESC, i.name ASC LIMIT :top_n;
    """
    )
    params = {
        "department_name": department_name,
        "cutoff_date": cutoff_date_val,
        "top_n": top_n,
    }
    try:
        with _engine.connect() as connection:
            result = connection.execute(query, params).mappings().all()
            return [dict(row) for row in result]
    except Exception as e:
        logger.error(
            "ERROR [item_service.get_suggested_items_for_department]: Could not fetch suggested items for dept '%s'. Error: %s - %s\n%s",
            department_name,
            type(e).__name__,
            e,
            traceback.format_exc(),
        )
        return []
