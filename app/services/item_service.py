# app/services/item_service.py
from datetime import datetime, timedelta
import traceback
from typing import Any, Optional, Dict, List, Tuple, Set

import pandas as pd
import streamlit as st  # Only for type hinting @st.cache_data
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.engine import Engine

from app.core.logging import get_logger
from app.db.database_utils import fetch_data

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
    query = (
        "SELECT item_id, name, purchase_unit, base_unit, conversion_factor, "
        "category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active FROM items"
    )
    if not include_inactive:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name;"
    return fetch_data(_engine, query)


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
        "SELECT item_id, name, purchase_unit, base_unit, conversion_factor, "
        "category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active "
        "FROM items WHERE item_id = :item_id;"
    )
    df = fetch_data(engine, query, {"item_id": item_id})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None


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
    required = ["name", "purchase_unit"]
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

    params = {
        "name": details["name"].strip(),
        "purchase_unit": details["purchase_unit"].strip(),
        "base_unit": details.get("base_unit"),
        "conversion_factor": details.get("conversion_factor"),
        "category": (details.get("category", "").strip() or "Uncategorized"),
        "sub_category": (details.get("sub_category", "").strip() or "General"),
        "permitted_departments": cleaned_permitted_departments,
        "reorder_point": details.get("reorder_point", 0.0),
        "current_stock": details.get("current_stock", 0.0),
        "notes": cleaned_notes_for_db,
        "is_active": details.get("is_active", True),
    }
    query = text(
        """
        INSERT INTO items (name, purchase_unit, base_unit, conversion_factor, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active)
        VALUES (:name, :purchase_unit, :base_unit, :conversion_factor, :category, :sub_category, :permitted_departments, :reorder_point, :current_stock, :notes, :is_active)
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
        "purchase_unit",
        "base_unit",
        "conversion_factor",
        "category",
        "sub_category",
        "permitted_departments",
        "reorder_point",
        "notes",
    ]

    if "name" in updates and not updates["name"].strip():
        return False, "Item Name cannot be empty."

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
            elif key in ["reorder_point", "conversion_factor"] and current_val is not None:
                try:
                    params[key] = float(current_val)
                except (ValueError, TypeError):
                    return (
                        False,
                        f"Invalid numeric value for {key}: {current_val}",
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
        SELECT i.item_id, i.name AS item_name, i.purchase_unit, COUNT(ii.item_id) as order_frequency
        FROM indent_items ii JOIN items i ON ii.item_id = i.item_id JOIN indents ind ON ii.indent_id = ind.indent_id
        WHERE ind.department = :department_name AND ind.date_submitted >= :cutoff_date AND i.is_active = TRUE
        GROUP BY i.item_id, i.name, i.purchase_unit ORDER BY order_frequency DESC, i.name ASC LIMIT :top_n;
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
