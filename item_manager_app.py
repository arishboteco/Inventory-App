import streamlit as st
from sqlalchemy import create_engine, text, exc as sqlalchemy_exc
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta
import math

# --- Constants ---
# Define standard transaction types for consistency
TX_RECEIVING = "RECEIVING"
TX_ADJUSTMENT = "ADJUSTMENT"
TX_WASTAGE = "WASTAGE"
TX_INDENT_FULFILL = "INDENT_FULFILL"
TX_SALE = "SALE"

# --- Database Connection ---
# This function will be called by the main app and pages
@st.cache_resource(show_spinner="Connecting to database...")
def connect_db():
    """Connects to the DB. Returns SQLAlchemy engine or None."""
    try:
        if "database" not in st.secrets: st.error("DB config missing!"); return None
        db_secrets = st.secrets["database"]; required_keys = ["engine", "user", "password", "host", "port", "dbname"]
        if not all(key in db_secrets for key in required_keys): st.error("DB secrets missing keys."); return None
        db_url = (f"{db_secrets['engine']}://{db_secrets['user']}:{db_secrets['password']}"
                  f"@{db_secrets['host']}:{db_secrets['port']}/{db_secrets['dbname']}")
        engine = create_engine(db_url, pool_pre_ping=True)
        # Test connection once
        with engine.connect() as connection: connection.execute(text("SELECT 1"))
        print("DB Connection Successful") # Optional: Log success to console
        return engine
    except Exception as e:
        print(f"DB Connection Error: {e}") # Log error to console
        st.error(f"DB connection failed: {e}")
        return None

# --- Database Interaction Functions ---
# All functions that interact with the database are kept here
# They will be imported by the page scripts

# --- Item Functions ---
@st.cache_data(ttl=600)
def get_all_items_with_stock(_engine, include_inactive: bool = False) -> pd.DataFrame:
    """Fetches items and calculates stock, optionally including inactive."""
    if not _engine: st.error("DB connection unavailable."); return pd.DataFrame()
    items_query_sql = """SELECT item_id, name, unit, category, sub_category, permitted_departments, reorder_point, notes, is_active FROM items"""
    if not include_inactive: items_query_sql += " WHERE is_active = TRUE"
    items_query_sql += " ORDER BY category, sub_category, name;"
    items_query = text(items_query_sql)
    stock_query = text("""SELECT item_id, SUM(quantity_change) AS calculated_stock FROM stock_transactions GROUP BY item_id;""")
    expected_cols = ["item_id", "name", "unit", "category", "sub_category", "permitted_departments", "reorder_point", "notes", "is_active", "current_stock"]
    try:
        with _engine.connect() as connection:
            items_df = pd.read_sql(items_query, connection)
            stock_levels_df = pd.read_sql(stock_query, connection)
            if items_df.empty: return pd.DataFrame(columns=expected_cols)
            items_df['item_id'] = items_df['item_id'].astype(int)
            if not stock_levels_df.empty:
                 stock_levels_df['item_id'] = stock_levels_df['item_id'].astype(int)
                 stock_levels_df['calculated_stock'] = pd.to_numeric(stock_levels_df['calculated_stock'], errors='coerce').fillna(0)
            else: stock_levels_df = pd.DataFrame(columns=['item_id', 'calculated_stock'])
            combined_df = pd.merge(items_df, stock_levels_df, on='item_id', how='left')
            combined_df['calculated_stock'] = combined_df['calculated_stock'].fillna(0)
            combined_df.rename(columns={'calculated_stock': 'current_stock'}, inplace=True)
            if 'reorder_point' in combined_df.columns: combined_df['reorder_point'] = pd.to_numeric(combined_df['reorder_point'], errors='coerce').fillna(0)
            if 'current_stock' in combined_df.columns: combined_df['current_stock'] = pd.to_numeric(combined_df['current_stock'], errors='coerce').fillna(0)
            for col in expected_cols:
                if col not in combined_df.columns:
                    if col == 'is_active': combined_df[col] = True
                    elif col in ['reorder_point', 'current_stock']: combined_df[col] = 0
                    else: combined_df[col] = None
            return combined_df[expected_cols]
    except ProgrammingError as e: st.error(f"DB query failed (items/transactions tables?). Error: {e}"); return pd.DataFrame(columns=expected_cols)
    except Exception as e: st.error(f"Failed to fetch items/stock: {e}"); st.exception(e); return pd.DataFrame(columns=expected_cols)

def get_item_details(engine, item_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a specific item_id."""
    if not engine or item_id is None: return None
    query = text("SELECT * FROM items WHERE item_id = :id")
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"id": item_id}); row = result.fetchone()
            return row._mapping if row else None
    except Exception as e: st.error(f"Failed to fetch item details {item_id}: {e}"); return None

def add_new_item(engine, item_details: Dict[str, Any]) -> bool:
    """Inserts a new item."""
    if not engine: return False
    insert_query = text("""INSERT INTO items (name, unit, category, sub_category, permitted_departments, reorder_point, notes, current_stock, is_active) VALUES (:name, :unit, :category, :sub_category, :permitted_departments, :reorder_point, :notes, 0, TRUE)""")
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(insert_query, item_details)
        return True
    except IntegrityError as e: st.error(f"Failed to add: Duplicate name? Error: {e}"); return False
    except Exception as e: st.error(f"Failed to add item: {e}"); st.exception(e); return False

def update_item_details(engine, item_id: int, updated_details: Dict[str, Any]) -> bool:
    """Updates an existing item (excluding current_stock)."""
    if not engine or item_id is None: return False
    update_parts = []; params = {"item_id": item_id}; editable_fields = ['name', 'unit', 'category', 'sub_category', 'permitted_departments', 'reorder_point', 'notes']
    for key, value in updated_details.items():
        if key in editable_fields: update_parts.append(f"{key} = :{key}"); params[key] = value if value != "" else None # Store empty strings as NULL for optional text fields
    if not update_parts: st.warning("No changes detected."); return False
    update_query = text(f"UPDATE items SET {', '.join(update_parts)} WHERE item_id = :item_id")
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(update_query, params)
        return True
    except IntegrityError as e: st.error(f"Failed to update: Duplicate name? Error: {e}"); return False
    except Exception as e: st.error(f"Failed to update item {item_id}: {e}"); st.exception(e); return False

def deactivate_item(engine, item_id: int) -> bool:
    """Sets the item's is_active flag to FALSE."""
    if not engine or item_id is None: return False
    deactivate_query = text("UPDATE items SET is_active = FALSE WHERE item_id = :item_id"); params = {"item_id": item_id}
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(deactivate_query, params)
        return True
    except Exception as e: st.error(f"Failed to deactivate item {item_id}: {e}"); st.exception(e); return False

def reactivate_item(engine, item_id: int) -> bool:
    """Sets the item's is_active flag to TRUE."""
    if not engine or item_id is None: return False
    reactivate_query = text("UPDATE items SET is_active = TRUE WHERE supplier_id = :id"); params = {"id": item_id}
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(reactivate_query, params)
        return True
    except Exception as e: st.error(f"Failed to reactivate item {item_id}: {e}"); st.exception(e); return False

# --- Stock Transaction Functions ---
def record_stock_transaction(engine, item_id: int, quantity_change: float, transaction_type: str, user_id: str, notes: Optional[str] = None, related_mrn: Optional[str] = None, related_po_id: Optional[int] = None) -> bool:
    """Records a single stock movement."""
    if not engine: st.error("DB connection unavailable."); return False
    if not all([item_id, quantity_change is not None, transaction_type, user_id]): st.error("Missing required fields for stock transaction."); return False
    if math.isclose(quantity_change, 0): st.warning("Quantity change cannot be zero."); return False
    insert_query = text("""INSERT INTO stock_transactions (item_id, quantity_change, transaction_type, user_id, notes, related_mrn, related_po_id) VALUES (:item_id, :quantity_change, :transaction_type, :user_id, :notes, :related_mrn, :related_po_id)""")
    params = {"item_id": item_id, "quantity_change": quantity_change, "transaction_type": transaction_type, "user_id": user_id, "notes": notes, "related_mrn": related_mrn, "related_po_id": related_po_id}
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(insert_query, params)
        return True
    except Exception as e: st.error(f"Failed to record stock transaction: {e}"); st.exception(e); return False

@st.cache_data(ttl=60)
def get_stock_transactions(_engine, item_id: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> pd.DataFrame:
    """Fetches stock transaction history, optionally filtered."""
    if not _engine: st.error("DB connection unavailable."); return pd.DataFrame()
    base_query = """SELECT t.transaction_date, i.name AS item_name, t.transaction_type, t.quantity_change, t.user_id, t.notes, t.related_mrn FROM stock_transactions t JOIN items i ON t.item_id = i.item_id"""
    params = {}; conditions = []
    if item_id: conditions.append("t.item_id = :item_id"); params["item_id"] = item_id
    if start_date: conditions.append("t.transaction_date >= :start_date"); params["start_date"] = start_date
    if end_date: conditions.append("t.transaction_date < :end_date_plus_one"); params["end_date_plus_one"] = end_date + timedelta(days=1)
    query_string = base_query + (" WHERE " + " AND ".join(conditions) if conditions else "") + " ORDER BY t.transaction_date DESC;"
    try:
        with _engine.connect() as connection:
            df = pd.read_sql(text(query_string), connection, params=params)
            if 'transaction_date' in df.columns: df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.strftime('%Y-%m-%d %H:%M:%S')
            if 'quantity_change' in df.columns: df['quantity_change'] = pd.to_numeric(df['quantity_change'], errors='coerce').fillna(0)
            return df
    except ProgrammingError as e: st.error(f"DB query failed. Tables exist? Error: {e}"); return pd.DataFrame()
    except Exception as e: st.error(f"Failed to fetch stock transactions: {e}"); st.exception(e); return pd.DataFrame()

# --- Supplier Database Functions ---
@st.cache_data(ttl=600)
def get_all_suppliers(_engine, include_inactive: bool = False) -> pd.DataFrame:
    """Fetches all suppliers, optionally including inactive ones."""
    if not _engine: st.error("DB connection unavailable."); return pd.DataFrame()
    query_sql = "SELECT supplier_id, name, contact_person, phone, email, address, notes, is_active FROM suppliers"
    if not include_inactive: query_sql += " WHERE is_active = TRUE"
    query_sql += " ORDER BY name;"
    query = text(query_sql)
    try:
        with _engine.connect() as connection: df = pd.read_sql(query, connection)
        return df
    except ProgrammingError as e: st.error(f"DB query failed. Does 'suppliers' table exist? Error: {e}"); return pd.DataFrame()
    except Exception as e: st.error(f"Failed to fetch suppliers: {e}"); st.exception(e); return pd.DataFrame()

def get_supplier_details(engine, supplier_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a specific supplier_id."""
    if not engine or supplier_id is None: return None
    query = text("SELECT * FROM suppliers WHERE supplier_id = :id")
    try:
        with engine.connect() as connection: result = connection.execute(query, {"id": supplier_id}); row = result.fetchone()
        return row._mapping if row else None
    except Exception as e: st.error(f"Failed to fetch supplier details {supplier_id}: {e}"); return None

def add_supplier(engine, supplier_details: Dict[str, Any]) -> bool:
    """Inserts a new supplier."""
    if not engine: return False
    if not supplier_details.get("name"): st.error("Supplier Name is required."); return False
    supplier_details.setdefault("is_active", True)
    insert_query = text("""INSERT INTO suppliers (name, contact_person, phone, email, address, notes, is_active) VALUES (:name, :contact_person, :phone, :email, :address, :notes, :is_active)""")
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(insert_query, supplier_details)
        return True
    except IntegrityError as e: st.error(f"Failed to add supplier: Duplicate name? Error: {e}"); return False
    except Exception as e: st.error(f"Failed to add supplier: {e}"); st.exception(e); return False

def update_supplier(engine, supplier_id: int, updated_details: Dict[str, Any]) -> bool:
    """Updates an existing supplier."""
    if not engine or supplier_id is None: return False
    update_parts = []; params = {"supplier_id": supplier_id}; editable_fields = ['name', 'contact_person', 'phone', 'email', 'address', 'notes']
    for key, value in updated_details.items():
        if key in editable_fields: update_parts.append(f"{key} = :{key}"); params[key] = value if value else None # Store empty string as NULL
    if not update_parts: st.warning("No changes detected."); return False
    update_query = text(f"UPDATE suppliers SET {', '.join(update_parts)} WHERE supplier_id = :supplier_id")
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(update_query, params)
        return True
    except IntegrityError as e: st.error(f"Failed to update supplier: Duplicate name? Error: {e}"); return False
    except Exception as e: st.error(f"Failed to update supplier {supplier_id}: {e}"); st.exception(e); return False

def deactivate_supplier(engine, supplier_id: int) -> bool:
    """Sets the supplier's is_active flag to FALSE."""
    if not engine or supplier_id is None: return False
    deactivate_query = text("UPDATE suppliers SET is_active = FALSE WHERE supplier_id = :id"); params = {"id": supplier_id}
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(deactivate_query, params)
        return True
    except Exception as e: st.error(f"Failed to deactivate supplier {supplier_id}: {e}"); st.exception(e); return False

def reactivate_supplier(engine, supplier_id: int) -> bool:
    """Sets the supplier's is_active flag to TRUE."""
    if not engine or supplier_id is None: return False
    reactivate_query = text("UPDATE suppliers SET is_active = TRUE WHERE supplier_id = :id"); params = {"id": supplier_id}
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(reactivate_query, params)
        return True
    except Exception as e: st.error(f"Failed to reactivate supplier {supplier_id}: {e}"); st.exception(e); return False
# --- End of DB Functions ---


# --- Main App Execution ---
# Set page config first
st.set_page_config(
    page_title="Boteco Inventory Manager",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded" # Keep sidebar open
)

# Display Title on the main page
st.title("Boteco Inventory Manager 🛒")
st.write("Welcome! Use the sidebar to navigate between sections.")

# Attempt to connect to the database - needed for pages potentially
db_engine = connect_db()

if not db_engine:
    st.error("Database connection failed. Please check secrets and configuration.")
    st.stop()

# The rest of the UI is now handled by files in the 'pages/' directory
# Streamlit automatically creates navigation from those files.

