# app/services/item_service.py
import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple, Set
import re 
from datetime import datetime, date, timedelta
import traceback # For detailed error logging

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.database_utils import fetch_data # This function takes 'engine'

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
    return fetch_data(_engine, query) # Pass _engine to fetch_data

def get_item_details(engine, item_id: int) -> Optional[Dict[str, Any]]:
    # This function is not cached, so 'engine' is the correct param name
    if engine is None: return None
    query = "SELECT item_id, name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active FROM items WHERE item_id = :item_id;"
    df = fetch_data(engine, query, {"item_id": item_id}) # Pass 'engine'
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def add_new_item(engine, details: Dict[str, Any]) -> Tuple[bool, str]:
    # Not cached
    if engine is None: return False, "Database engine not available."
    required = ["name", "unit"]
    if not all(details.get(k) for k in required):
        missing = [k for k in required if not details.get(k)]
        return False, f"Missing required fields: {', '.join(missing)}"
    
    notes_value_from_details = details.get("notes")
    cleaned_notes_for_db = notes_value_from_details.strip() if isinstance(notes_value_from_details, str) else None
    if cleaned_notes_for_db == "":
        cleaned_notes_for_db = None

    params = {
        "name": details.get("name", "").strip(),
        "unit": details.get("unit", "").strip(),
        "category": (details.get("category") or "Uncategorized").strip(),
        "sub_category": (details.get("sub_category") or "General").strip(),
        "permitted_departments": details.get("permitted_departments"),
        "reorder_point": details.get("reorder_point", 0.0),
        "current_stock": details.get("current_stock", 0.0),
        "notes": cleaned_notes_for_db,
        "is_active": details.get("is_active", True)
    }
    query = text("""
        INSERT INTO items (name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active)
        VALUES (:name, :unit, :category, :sub_category, :permitted_departments, :reorder_point, :current_stock, :notes, :is_active)
        RETURNING item_id;
    """)
    try:
        with engine.connect() as connection: # Uses 'engine'
            with connection.begin():
                result = connection.execute(query, params)
                new_id = result.scalar_one_or_none()
        if new_id:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear()
            return True, f"Item '{params['name']}' added with ID {new_id}."
        else: return False, "Failed to add item (no ID returned)."
    except IntegrityError: return False, f"Item name '{params['name']}' already exists. Choose a unique name."
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error adding item: {e}"); return False, "Database error adding item."

def update_item_details(engine, item_id: int, updates: Dict[str, Any]) -> Tuple[bool, str]:
    # Not cached
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
        with engine.connect() as connection: # Uses 'engine'
            with connection.begin(): result = connection.execute(query, params)
        if result.rowcount > 0:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear()
            # If get_item_details were cached, you'd clear it here too, perhaps with specific args if it's parameterized
            return True, f"Item ID {item_id} updated."
        else:
            existing_item = get_item_details(engine, item_id) # Uses 'engine'
            if existing_item is None: return False, f"Update failed: Item ID {item_id} not found."
            else: return False, f"Item ID {item_id} found, but no changes were made."
    except IntegrityError: return False, f"Update failed: Potential duplicate name '{updates.get('name')}'."
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error updating item {item_id}: {e}"); return False, "Database error updating item."

def deactivate_item(engine, item_id: int) -> bool:
    # Not cached
    if engine is None: return False
    query = text("UPDATE items SET is_active = FALSE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection: # Uses 'engine'
            with connection.begin(): result = connection.execute(query, {"item_id": item_id})
        if result.rowcount > 0:
            get_all_items_with_stock.clear(); get_distinct_departments_from_items.clear(); return True
        return False
    except (SQLAlchemyError, Exception) as e: st.error(f"Error deactivating item {item_id}: {e}"); return False

def reactivate_item(engine, item_id: int) -> bool:
    # Not cached
    if engine is None: return False
    query = text("UPDATE items SET is_active = TRUE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection: # Uses 'engine'
            with connection.begin(): result = connection.execute(query, {"item_id": item_id})
        if result.rowcount > 0:
            get_all_items_with_stock.clear(); get_distinct_departments_from_items.clear(); return True
        return False
    except (SQLAlchemyError, Exception) as e: st.error(f"Error reactivating item {item_id}: {e}"); return False

@st.cache_data(ttl=300, show_spinner="Fetching department list...")
def get_distinct_departments_from_items(_engine) -> List[str]: # Correctly uses _engine
    if _engine is None: return []
    query = text("""
        SELECT permitted_departments FROM items
        WHERE is_active = TRUE AND permitted_departments IS NOT NULL AND permitted_departments <> '' AND permitted_departments <> ' ';
    """)
    departments_set: Set[str] = set()
    try:
        with _engine.connect() as connection: # Uses _engine
            result = connection.execute(query)
            rows = result.fetchall()
        for row in rows:
            permitted_str = row[0]
            if permitted_str:
                departments = {dept.strip() for dept in permitted_str.split(',') if dept.strip()}
                departments_set.update(departments)
        return sorted(list(departments_set))
    except (SQLAlchemyError, Exception) as e: st.error(f"Error fetching distinct departments: {e}"); return []

# ─────────────────────────────────────────────────────────
# NEW FUNCTIONS FOR ITEM HISTORY & SUGGESTIONS
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_item_order_history_details(_engine, item_id: int, department_name: Optional[str] = None) -> Dict[str, Any]: # Parameter is _engine
    if _engine is None or item_id is None: # Check _engine
        return {"last_ordered_date": None, "median_quantity": None}
    params = {"item_id": item_id}
    date_query_conditions = ["ii.item_id = :item_id"]
    qty_query_conditions = ["ii.item_id = :item_id"]
    if department_name:
        date_query_conditions.append("ind.department = :department_name")
        qty_query_conditions.append("ind.department = :department_name")
        params["department_name"] = department_name
    date_where_clause = " AND ".join(date_query_conditions)
    qty_where_clause = " AND ".join(qty_query_conditions)
    last_ordered_date_query = text(f"SELECT MAX(ind.date_submitted) AS last_ordered_date FROM indent_items ii JOIN indents ind ON ii.indent_id = ind.indent_id WHERE {date_where_clause};")
    median_quantity_query = text(f"SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY ii.requested_qty) AS median_quantity FROM indent_items ii JOIN indents ind ON ii.indent_id = ind.indent_id WHERE {qty_where_clause};")
    last_date_str = None; median_qty_val = None
    try:
        with _engine.connect() as connection: # Use _engine
            date_result = connection.execute(last_ordered_date_query, params).scalar_one_or_none()
            if date_result: last_date_str = pd.to_datetime(date_result).strftime("%d-%b-%Y") if pd.notna(date_result) else None
            qty_result = connection.execute(median_quantity_query, params).scalar_one_or_none()
            if qty_result is not None: median_qty_val = float(qty_result)
    except Exception as e:
        print(f"Warning: Could not fetch full order history for item {item_id}, dept {department_name}: {type(e).__name__} - {e}")
        # print(traceback.format_exc()) # Keep for detailed debugging if needed by user
    return {"last_ordered_date": last_date_str, "median_quantity": median_qty_val}

@st.cache_data(ttl=3600, show_spinner="Analyzing item suggestions...")
def get_suggested_items_for_department(_engine, department_name: str, top_n: int = 5, days_recency: int = 90) -> List[Dict[str, Any]]: # Parameter is _engine
    if _engine is None or not department_name: return [] # Check _engine
    cutoff_date_val = datetime.now() - timedelta(days=days_recency)
    query = text("""
        SELECT i.item_id, i.name AS item_name, i.unit, COUNT(ii.item_id) as order_frequency
        FROM indent_items ii JOIN items i ON ii.item_id = i.item_id JOIN indents ind ON ii.indent_id = ind.indent_id
        WHERE ind.department = :department_name AND ind.date_submitted >= :cutoff_date AND i.is_active = TRUE
        GROUP BY i.item_id, i.name, i.unit ORDER BY order_frequency DESC, i.name ASC LIMIT :top_n;
    """)
    params = {"department_name": department_name, "cutoff_date": cutoff_date_val, "top_n": top_n}
    try:
        with _engine.connect() as connection: # Use _engine
            result = connection.execute(query, params).mappings().all()
            return [dict(row) for row in result]
    except Exception as e:
        st.warning(f"Could not fetch suggested items for {department_name}. Error: {type(e).__name__} - {e}")
        print(f"ERROR in get_suggested_items_for_department for dept '{department_name}':")
        print(traceback.format_exc()) # This will print the full stack trace to the console
        return []