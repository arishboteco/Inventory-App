# app/services/item_service.py
import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple, Set
import re # For get_distinct_departments_from_items

from sqlalchemy import text # For direct SQL execution
from sqlalchemy.exc import IntegrityError, SQLAlchemyError # For error handling

# Import fetch_data from database_utils
from app.db.database_utils import fetch_data

# ─────────────────────────────────────────────────────────
# ITEM MASTER FUNCTIONS
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching item data...")
def get_all_items_with_stock(_engine, include_inactive=False) -> pd.DataFrame:
    if _engine is None: return pd.DataFrame()
    query = "SELECT item_id, name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active FROM items"
    if not include_inactive:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name;"
    return fetch_data(_engine, query)

def get_item_details(engine, item_id: int) -> Optional[Dict[str, Any]]:
    if engine is None: return None
    query = "SELECT item_id, name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active FROM items WHERE item_id = :item_id;"
    df = fetch_data(engine, query, {"item_id": item_id})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def add_new_item(engine, details: Dict[str, Any]) -> Tuple[bool, str]:
    if engine is None: return False, "Database engine not available."
    required = ["name", "unit"]
    if not all(details.get(k) for k in required):
        missing = [k for k in required if not details.get(k)]
        return False, f"Missing required fields: {', '.join(missing)}"
    query = text("""
        INSERT INTO items (name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active)
        VALUES (:name, :unit, :category, :sub_category, :permitted_departments, :reorder_point, :current_stock, :notes, :is_active)
        RETURNING item_id;
    """)
    params = {
        "name": details.get("name", "").strip(), "unit": details.get("unit", "").strip(),
        "category": details.get("category", "Uncategorized").strip(),
        "sub_category": details.get("sub_category", "General").strip(),
        "permitted_departments": details.get("permitted_departments"),
        "reorder_point": details.get("reorder_point", 0.0),
        "current_stock": details.get("current_stock", 0.0),
        "notes": details.get("notes", "").strip() or None,
        "is_active": details.get("is_active", True)
    }
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, params)
                new_id = result.scalar_one_or_none()
        if new_id:
            get_all_items_with_stock.clear() # Clear relevant caches within this service
            get_distinct_departments_from_items.clear()
            return True, f"Item '{params['name']}' added with ID {new_id}."
        else: return False, "Failed to add item (no ID returned)."
    except IntegrityError: return False, f"Item name '{params['name']}' already exists."
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error adding item: {e}"); return False, "Database error adding item."

def update_item_details(engine, item_id: int, updates: Dict[str, Any]) -> Tuple[bool, str]:
    if engine is None: return False, "Database engine not available."
    if not item_id or not updates: return False, "Invalid item ID or no updates provided."
    set_clauses = []
    params = {"item_id": item_id}
    allowed_fields = ["name", "unit", "category", "sub_category", "permitted_departments", "reorder_point", "notes"]
    for key, value in updates.items():
        if key in allowed_fields:
            set_clauses.append(f"{key} = :{key}")
            if isinstance(value, str): params[key] = value.strip()
            elif key == "reorder_point" and value is not None:
                 try: params[key] = float(value)
                 except (ValueError, TypeError): return False, f"Invalid numeric value for reorder_point: {value}"
            else: params[key] = value
    if not set_clauses: return False, "No valid fields provided for update."
    query = text(f"UPDATE items SET {', '.join(set_clauses)} WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(query, params)
        if result.rowcount > 0:
            get_all_items_with_stock.clear()
            # get_item_details.clear() # If get_item_details itself were cached, clear it here.
            get_distinct_departments_from_items.clear()
            return True, f"Item ID {item_id} updated."
        else:
            existing_item = get_item_details(engine, item_id) # Call within service
            if existing_item is None: return False, f"Update failed: Item ID {item_id} not found."
            else: return False, f"Item ID {item_id} found, but no changes were made."
    except IntegrityError: return False, f"Update failed: Potential duplicate name '{updates.get('name')}'."
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error updating item {item_id}: {e}"); return False, "Database error updating item."

def deactivate_item(engine, item_id: int) -> bool:
    if engine is None: return False
    query = text("UPDATE items SET is_active = FALSE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(query, {"item_id": item_id})
        if result.rowcount > 0:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear()
            return True
        return False
    except (SQLAlchemyError, Exception) as e: st.error(f"Error deactivating item {item_id}: {e}"); return False

def reactivate_item(engine, item_id: int) -> bool:
    if engine is None: return False
    query = text("UPDATE items SET is_active = TRUE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(query, {"item_id": item_id})
        if result.rowcount > 0:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear()
            return True
        return False
    except (SQLAlchemyError, Exception) as e: st.error(f"Error reactivating item {item_id}: {e}"); return False

# ─────────────────────────────────────────────────────────
# DEPARTMENT HELPER FUNCTION
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching department list...")
def get_distinct_departments_from_items(_engine) -> List[str]:
    if _engine is None: return []
    query = text("""
        SELECT permitted_departments FROM items
        WHERE is_active = TRUE AND permitted_departments IS NOT NULL AND permitted_departments <> '' AND permitted_departments <> ' ';
    """)
    departments_set: Set[str] = set()
    try:
        # This function directly executes SQL, not using fetch_data, which is fine.
        with _engine.connect() as connection:
            result = connection.execute(query)
            rows = result.fetchall()
        for row in rows:
            permitted_str = row[0]
            if permitted_str:
                departments = {dept.strip() for dept in permitted_str.split(',') if dept.strip()}
                departments_set.update(departments)
        return sorted(list(departments_set))
    except (SQLAlchemyError, Exception) as e: st.error(f"Error fetching distinct departments: {e}"); return []