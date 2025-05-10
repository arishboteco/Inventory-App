# app/item_manager_app.py

import sys
import os

# Add the project root (INVENTORY-APP) to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
# Only import sqlalchemy components needed by functions *remaining* in this file
from sqlalchemy import text, func # inspect, select, MetaData, Table (if used by remaining functions)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError # Keep if used by remaining functions

import pandas as pd
from typing import Any, Optional, Dict, List, Tuple, Set
from datetime import datetime, date, timedelta
import re

# --- Import from our new/refactored modules ---
from app.core.constants import (
    TX_RECEIVING, TX_ADJUSTMENT, TX_WASTAGE, TX_INDENT_FULFILL, TX_SALE,
    STATUS_SUBMITTED, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_CANCELLED,
    ALL_INDENT_STATUSES
)
from app.db.database_utils import connect_db, fetch_data # <-- IMPORTING MOVED FUNCTIONS

# ─────────────────────────────────────────────────────────
# ITEM MASTER FUNCTIONS (Temporarily here, will move to item_service.py)
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching item data...")
def get_all_items_with_stock(_engine, include_inactive=False) -> pd.DataFrame:
    if _engine is None: return pd.DataFrame()
    query = "SELECT item_id, name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active FROM items"
    if not include_inactive:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name;"
    return fetch_data(_engine, query) # Uses imported fetch_data

def get_item_details(engine, item_id: int) -> Optional[Dict[str, Any]]:
    if engine is None: return None
    query = "SELECT item_id, name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active FROM items WHERE item_id = :item_id;"
    df = fetch_data(engine, query, {"item_id": item_id}) # Uses imported fetch_data
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
            get_all_items_with_stock.clear()
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
            # get_item_details.clear() # If it were cached
            get_distinct_departments_from_items.clear()
            return True, f"Item ID {item_id} updated."
        else:
            existing_item = get_item_details(engine, item_id)
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
            get_all_items_with_stock.clear(); get_distinct_departments_from_items.clear(); return True
        return False
    except (SQLAlchemyError, Exception) as e: st.error(f"Error deactivating item {item_id}: {e}"); return False

def reactivate_item(engine, item_id: int) -> bool:
    if engine is None: return False
    query = text("UPDATE items SET is_active = TRUE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(query, {"item_id": item_id})
        if result.rowcount > 0:
            get_all_items_with_stock.clear(); get_distinct_departments_from_items.clear(); return True
        return False
    except (SQLAlchemyError, Exception) as e: st.error(f"Error reactivating item {item_id}: {e}"); return False

# ─────────────────────────────────────────────────────────
# DEPARTMENT HELPER FUNCTION (Temporarily here)
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

# ─────────────────────────────────────────────────────────
# SUPPLIER MASTER FUNCTIONS (Temporarily here, will move to supplier_service.py)
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching supplier data...")
def get_all_suppliers(_engine, include_inactive=False) -> pd.DataFrame:
    if _engine is None: return pd.DataFrame()
    query = "SELECT supplier_id, name, contact_person, phone, email, address, notes, is_active FROM suppliers"
    if not include_inactive: query += " WHERE is_active = TRUE"
    query += " ORDER BY name;"
    return fetch_data(_engine, query) # Uses imported fetch_data

def get_supplier_details(engine, supplier_id: int) -> Optional[Dict[str, Any]]:
    if engine is None: return None
    query = "SELECT supplier_id, name, contact_person, phone, email, address, notes, is_active FROM suppliers WHERE supplier_id = :supplier_id;"
    df = fetch_data(engine, query, {"supplier_id": supplier_id}) # Uses imported fetch_data
    if not df.empty: return df.iloc[0].to_dict()
    return None

def add_supplier(engine, details: Dict[str, Any]) -> Tuple[bool, str]:
    if engine is None: return False, "Database engine not available."
    if not details.get("name"): return False, "Supplier name is required."
    query = text("""
        INSERT INTO suppliers (name, contact_person, phone, email, address, notes, is_active)
        VALUES (:name, :contact_person, :phone, :email, :address, :notes, :is_active) RETURNING supplier_id;
    """)
    params = {
        "name": details.get("name", "").strip(),
        "contact_person": (details.get("contact_person") or "").strip() or None,
        "phone": (details.get("phone") or "").strip() or None,
        "email": (details.get("email") or "").strip() or None,
        "address": (details.get("address") or "").strip() or None,
        "notes": (details.get("notes") or "").strip() or None,
        "is_active": details.get("is_active", True)
    }
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(query, params); new_id = result.scalar_one_or_none()
        if new_id: get_all_suppliers.clear(); return True, f"Supplier '{params['name']}' added with ID {new_id}."
        else: return False, "Failed to add supplier."
    except IntegrityError: return False, f"Supplier name '{params['name']}' already exists."
    except (SQLAlchemyError, Exception) as e: st.error(f"Database error adding supplier: {e}"); return False, "Database error adding supplier."

def update_supplier(engine, supplier_id: int, updates: Dict[str, Any]) -> Tuple[bool, str]:
    if engine is None: return False, "Database engine not available."
    if not supplier_id or not updates: return False, "Invalid supplier ID or no updates."
    set_clauses = []; params = {"supplier_id": supplier_id}
    allowed = ["name", "contact_person", "phone", "email", "address", "notes"]
    for key, value in updates.items():
        if key in allowed:
            set_clauses.append(f"{key} = :{key}")
            params[key] = value.strip() if isinstance(value, str) else value
            if key != "name" and params[key] == "": params[key] = None
    if not set_clauses: return False, "No valid fields to update."
    query = text(f"UPDATE suppliers SET {', '.join(set_clauses)} WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(query, params)
        if result.rowcount > 0: get_all_suppliers.clear(); return True, f"Supplier ID {supplier_id} updated."
        else:
            existing = get_supplier_details(engine, supplier_id)
            if existing is None: return False, f"Update failed: Supplier ID {supplier_id} not found."
            else: return False, f"Supplier ID {supplier_id} found, but no changes were made."
    except IntegrityError: return False, f"Update failed: Potential duplicate name '{updates.get('name')}'."
    except (SQLAlchemyError, Exception) as e: st.error(f"Database error updating supplier {supplier_id}: {e}"); return False, "Database error updating supplier."

def deactivate_supplier(engine, supplier_id: int) -> bool:
    if engine is None: return False
    query = text("UPDATE suppliers SET is_active = FALSE WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(query, {"supplier_id": supplier_id})
        if result.rowcount > 0: get_all_suppliers.clear(); return True
        return False
    except (SQLAlchemyError, Exception) as e: st.error(f"Error deactivating supplier {supplier_id}: {e}"); return False

def reactivate_supplier(engine, supplier_id: int) -> bool:
    if engine is None: return False
    query = text("UPDATE suppliers SET is_active = TRUE WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(query, {"supplier_id": supplier_id})
        if result.rowcount > 0: get_all_suppliers.clear(); return True
        return False
    except (SQLAlchemyError, Exception) as e: st.error(f"Error reactivating supplier {supplier_id}: {e}"); return False

# ─────────────────────────────────────────────────────────
# STOCK TRANSACTION FUNCTIONS (Temporarily here, will move to stock_service.py)
# ─────────────────────────────────────────────────────────
def record_stock_transaction(
    engine, item_id: int, quantity_change: float, transaction_type: str,
    user_id: Optional[str] = "System", related_mrn: Optional[str] = None,
    related_po_id: Optional[int] = None, notes: Optional[str] = None
) -> bool:
    if engine is None: return False
    if not item_id or quantity_change == 0: st.warning("Item ID or qty change is zero."); return False
    notes_cleaned = str(notes).strip() if notes is not None else None
    user_id_cleaned = str(user_id).strip() if user_id is not None else "System"
    related_mrn_cleaned = str(related_mrn).strip() if related_mrn is not None else None
    stock_update_query = text("UPDATE items SET current_stock = COALESCE(current_stock, 0) + :quantity_change WHERE item_id = :item_id;")
    transaction_insert_query = text("""
        INSERT INTO stock_transactions (item_id, quantity_change, transaction_type, user_id, related_mrn, related_po_id, notes, transaction_date)
        VALUES (:item_id, :quantity_change, :transaction_type, :user_id, :related_mrn, :related_po_id, :notes, NOW());
    """)
    params = {"item_id": item_id, "quantity_change": quantity_change, "transaction_type": transaction_type,
              "user_id": user_id_cleaned, "related_mrn": related_mrn_cleaned, "related_po_id": related_po_id, "notes": notes_cleaned}
    try:
        with engine.connect() as connection:
            with connection.begin():
                upd_result = connection.execute(stock_update_query, {"item_id": item_id, "quantity_change": quantity_change})
                if upd_result.rowcount == 0: raise Exception(f"Failed to update stock for item {item_id}.")
                connection.execute(transaction_insert_query, params)
        get_all_items_with_stock.clear(); get_stock_transactions.clear(); return True
    except (SQLAlchemyError, Exception) as e: st.error(f"DB error in stock transaction: {e}"); return False

@st.cache_data(ttl=120, show_spinner="Fetching transaction history...")
def get_stock_transactions(
    _engine, item_id: Optional[int] = None, transaction_type: Optional[str] = None,
    user_id: Optional[str] = None, start_date: Optional[date] = None,
    end_date: Optional[date] = None, related_mrn: Optional[str] = None
) -> pd.DataFrame:
    if _engine is None: return pd.DataFrame()
    query = """
        SELECT st.transaction_id, st.transaction_date, i.name AS item_name, st.transaction_type,
               st.quantity_change, st.user_id, st.notes, st.related_mrn, st.related_po_id, st.item_id
        FROM stock_transactions st JOIN items i ON st.item_id = i.item_id WHERE 1=1
    """
    params = {}
    if item_id: query += " AND st.item_id = :item_id"; params['item_id'] = item_id
    if transaction_type: query += " AND st.transaction_type = :transaction_type"; params['transaction_type'] = transaction_type
    if user_id: query += " AND st.user_id ILIKE :user_id"; params['user_id'] = f"%{user_id}%"
    if related_mrn: query += " AND st.related_mrn ILIKE :related_mrn"; params['related_mrn'] = f"%{related_mrn}%"
    if start_date: query += " AND st.transaction_date >= :start_date"; params['start_date'] = start_date
    if end_date:
        effective_end_date = end_date + timedelta(days=1)
        query += " AND st.transaction_date < :end_date"; params['end_date'] = effective_end_date
    query += " ORDER BY st.transaction_date DESC, st.transaction_id DESC;"
    return fetch_data(_engine, query, params) # Uses imported fetch_data

# ─────────────────────────────────────────────────────────
# INDENT FUNCTIONS (Temporarily here, will move to indent_service.py)
# ─────────────────────────────────────────────────────────
def generate_mrn(engine) -> Optional[str]:
    if engine is None: return None
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT nextval('mrn_seq');"))
            seq_num = result.scalar_one()
            return f"MRN-{datetime.now().strftime('%Y%m')}-{seq_num:05d}"
    except (SQLAlchemyError, Exception) as e: st.error(f"Error generating MRN: {e}"); return None

def create_indent(engine, indent_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Tuple[bool, str]:
    if engine is None: return False, "DB engine unavailable."
    required_header = ["mrn", "requested_by", "department", "date_required"]
    missing = [k for k in required_header if not indent_data.get(k) or (isinstance(indent_data.get(k), str) and not indent_data.get(k).strip())]
    if missing: return False, f"Missing indent header fields: {', '.join(missing)}"
    if not items_data: return False, "Indent must have items."
    for i, item in enumerate(items_data):
        if not item.get('item_id') or not item.get('requested_qty') or item['requested_qty'] <= 0:
            return False, f"Invalid data in item row {i+1}."
    indent_query = text("INSERT INTO indents (mrn, requested_by, department, date_required, notes, status, date_submitted) VALUES (:mrn, :requested_by, :department, :date_required, :notes, :status, NOW()) RETURNING indent_id;")
    item_query = text("INSERT INTO indent_items (indent_id, item_id, requested_qty, notes) VALUES (:indent_id, :item_id, :requested_qty, :notes);")
    notes_val = indent_data.get("notes")
    cleaned_notes = notes_val.strip() if isinstance(notes_val, str) else None
    indent_params = {"mrn": indent_data["mrn"].strip(), "requested_by": indent_data["requested_by"].strip(),
                     "department": indent_data["department"], "date_required": indent_data["date_required"],
                     "notes": cleaned_notes, "status": indent_data.get("status", STATUS_SUBMITTED)}
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(indent_query, indent_params)
                new_indent_id = result.scalar_one_or_none()
                if not new_indent_id: raise Exception("Failed to get indent_id.")
                item_params_list = [{"indent_id": new_indent_id, "item_id": item['item_id'],
                                     "requested_qty": float(item['requested_qty']),
                                     "notes": (item.get('notes') or "").strip() or None} for item in items_data]
                connection.execute(item_query, item_params_list)
        get_indents.clear(); return True, f"Indent {indent_data['mrn']} created."
    except IntegrityError as e:
        msg = "DB integrity error."
        if "indents_mrn_key" in str(e): msg = f"MRN '{indent_params['mrn']}' exists."
        elif "indent_items_item_id_fkey" in str(e): msg = "Invalid Item ID."
        st.error(f"{msg} Details: {e}"); return False, msg
    except (SQLAlchemyError, Exception) as e: st.error(f"DB error creating indent: {e}"); return False, "DB error."

@st.cache_data(ttl=120, show_spinner="Fetching indent list...")
def get_indents(
    _engine, mrn_filter: Optional[str] = None, dept_filter: Optional[str] = None,
    status_filter: Optional[str] = None, date_start_str: Optional[str] = None,
    date_end_str: Optional[str] = None
) -> pd.DataFrame:
    if _engine is None: return pd.DataFrame()
    date_start_filter, date_end_filter = None, None # Initialize
    if date_start_str: # CORRECTED SYNTAX FOR TRY-EXCEPT
        try:
            date_start_filter = datetime.strptime(date_start_str, '%Y-%m-%d').date()
        except ValueError:
            st.warning(f"Invalid start date format: {date_start_str}. Ignoring.")
    if date_end_str: # CORRECTED SYNTAX FOR TRY-EXCEPT
        try:
            date_end_filter = datetime.strptime(date_end_str, '%Y-%m-%d').date()
        except ValueError:
            st.warning(f"Invalid end date format: {date_end_str}. Ignoring.")
    query = """
        SELECT i.indent_id, i.mrn, i.requested_by, i.department, i.date_required,
               i.date_submitted, i.status, i.notes AS indent_notes, COUNT(ii.indent_item_id) AS item_count
        FROM indents i LEFT JOIN indent_items ii ON i.indent_id = ii.indent_id WHERE 1=1
    """
    params = {}
    if mrn_filter: query += " AND i.mrn ILIKE :mrn"; params['mrn'] = f"%{mrn_filter}%"
    if dept_filter: query += " AND i.department = :department"; params['department'] = dept_filter
    if status_filter: query += " AND i.status = :status"; params['status'] = status_filter
    if date_start_filter: query += " AND i.date_submitted >= :date_from"; params['date_from'] = date_start_filter
    if date_end_filter:
        effective_date_to = date_end_filter + timedelta(days=1)
        query += " AND i.date_submitted < :date_to"; params['date_to'] = effective_date_to
    query += " GROUP BY i.indent_id, i.mrn, i.requested_by, i.department, i.date_required, i.date_submitted, i.status, i.notes ORDER BY i.date_submitted DESC, i.indent_id DESC" # Added missing GROUP BY fields
    df = fetch_data(_engine, query, params) # Uses imported fetch_data
    if not df.empty:
        for col in ['date_required', 'date_submitted']:
             if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce')
        if 'item_count' in df.columns: df['item_count'] = pd.to_numeric(df['item_count'], errors='coerce').fillna(0).astype(int)
    return df

def get_indent_details_for_pdf(engine, mrn: str) -> Tuple[Optional[Dict], Optional[List[Dict]]]:
    if engine is None or not mrn: return None, None
    header_data, items_data = None, None
    try:
        with engine.connect() as connection:
            header_query = text("SELECT ind.indent_id, ind.mrn, ind.department, ind.requested_by, ind.date_submitted, ind.date_required, ind.status, ind.notes FROM indents ind WHERE ind.mrn = :mrn;")
            header_result = connection.execute(header_query, {"mrn": mrn}).mappings().first()
            if not header_result: st.error(f"Indent '{mrn}' not found."); return None, None
            header_data = dict(header_result)
            if header_data.get('date_submitted'): header_data['date_submitted'] = pd.to_datetime(header_data['date_submitted']).strftime('%Y-%m-%d %H:%M')
            if header_data.get('date_required'): header_data['date_required'] = pd.to_datetime(header_data['date_required']).strftime('%Y-%m-%d')
            items_query = text("SELECT ii.item_id, i.name AS item_name, i.unit AS item_unit, ii.requested_qty, ii.notes AS item_notes FROM indent_items ii JOIN items i ON ii.item_id = i.item_id JOIN indents ind ON ii.indent_id = ind.indent_id WHERE ind.mrn = :mrn ORDER BY i.name;")
            items_result = connection.execute(items_query, {"mrn": mrn}).mappings().all()
            items_data = [dict(row) for row in items_result]
        return header_data, items_data
    except (SQLAlchemyError, Exception) as e: st.error(f"DB error fetching indent details for {mrn}: {e}"); return None, None

# ─────────────────────────────────────────────────────────
# DASHBOARD UI (Main App Page)
# ─────────────────────────────────────────────────────────
def run_dashboard():
    st.set_page_config(page_title="Inv Manager", page_icon="🍲", layout="wide")
    st.title("🍲 Restaurant Inventory Dashboard")
    st.caption(f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    engine = connect_db() # Uses imported connect_db
    if not engine:
        st.warning("Database connection failed. Dashboard data cannot be loaded."); st.stop()

    items_df = get_all_items_with_stock(engine, include_inactive=False)
    suppliers_df = get_all_suppliers(engine, include_inactive=False)
    total_active_items = len(items_df)
    total_active_suppliers = len(suppliers_df)
    low_stock_df = pd.DataFrame(); low_stock_count = 0
    if not items_df.empty and 'current_stock' in items_df.columns and 'reorder_point' in items_df.columns:
        try:
            items_df['current_stock_num'] = pd.to_numeric(items_df['current_stock'], errors='coerce').fillna(0)
            items_df['reorder_point_num'] = pd.to_numeric(items_df['reorder_point'], errors='coerce').fillna(0)
            mask = (items_df['current_stock_num'].notna() & items_df['reorder_point_num'].notna() &
                    (items_df['reorder_point_num'] > 0) &
                    (items_df['current_stock_num'] <= items_df['reorder_point_num']))
            low_stock_df = items_df.loc[mask, ['name', 'unit', 'current_stock', 'reorder_point']].copy()
            low_stock_count = len(low_stock_df)
        except KeyError as e: st.error(f"Missing column for low-stock calc: {e}")
        except Exception as e: st.error(f"Error calculating low stock: {e}")

    st.header("Key Metrics")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Active Items", total_active_items)
    kpi2.metric("Low Stock Items", low_stock_count, help="Items at or below reorder point (reorder > 0)")
    kpi3.metric("Active Suppliers", total_active_suppliers)
    st.divider()
    st.header("⚠️ Low Stock Items")
    if low_stock_count > 0:
        st.dataframe(low_stock_df, use_container_width=True, hide_index=True,
            column_config={"name": "Item Name", "unit": st.column_config.TextColumn(width="small"),
                           "current_stock": st.column_config.NumberColumn(format="%.2f", width="small"),
                           "reorder_point": st.column_config.NumberColumn(format="%.2f", width="small")})
    elif total_active_items > 0: st.info("No items currently below reorder point.")
    else: st.info("No active items in the system.")

if __name__ == "__main__":
    run_dashboard()