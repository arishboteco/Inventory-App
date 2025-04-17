# item_manager_app.py
import streamlit as st
from sqlalchemy import create_engine, text, exc as sqlalchemy_exc
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple # Ensure these are imported
from datetime import datetime, date, timedelta
import math
import time # Added for dummy MRN generation if needed, and maybe other uses

# --- Constants ---
# Define standard transaction types for consistency
TX_RECEIVING = "RECEIVING"
TX_ADJUSTMENT = "ADJUSTMENT"
TX_WASTAGE = "WASTAGE"
TX_INDENT_FULFILL = "INDENT_FULFILL" # Added for indent fulfillment
TX_SALE = "SALE" # For potential future use

# --- Constants for Indent Statuses ---
STATUS_SUBMITTED = "Submitted"
STATUS_PROCESSING = "Processing"
STATUS_COMPLETED = "Completed"
STATUS_CANCELLED = "Cancelled"
ALL_INDENT_STATUSES = [STATUS_SUBMITTED, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_CANCELLED]


# --- Database Connection ---
@st.cache_resource(show_spinner="Connecting to database...")
def connect_db():
    """Connects to the DB using secrets. Returns SQLAlchemy engine or None."""
    try:
        if "database" not in st.secrets:
            st.error("Database configuration missing in Streamlit secrets (secrets.toml)!")
            return None
        db_secrets = st.secrets["database"]
        required_keys = ["engine", "user", "password", "host", "port", "dbname"]
        if not all(key in db_secrets for key in required_keys):
            st.error(f"Database secrets are missing required keys: {required_keys}")
            return None
        db_url = (
            f"{db_secrets['engine']}://{db_secrets['user']}:{db_secrets['password']}"
            f"@{db_secrets['host']}:{db_secrets['port']}/{db_secrets['dbname']}"
        )
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1")) # Test connection
        return engine
    except OperationalError as oe:
        st.error(f"Database connection error: {oe}. Check connection details, firewall, or DB status.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during database connection: {e}")
        return None

# --- Helper Function for Data Fetching (Error Handling) ---
def fetch_data(engine, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Fetches data using SQLAlchemy, handles errors, returns DataFrame."""
    try:
        with engine.connect() as connection:
            # Ensure parameters are passed correctly
            result = connection.execute(text(query), parameters=params if params else {})
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"Database error executing query: {db_err}")
    except Exception as e:
        st.error(f"An unexpected error occurred fetching data: {e}")
    return pd.DataFrame() # Return empty DataFrame on error

# --- Item Management Functions ---
@st.cache_data(ttl=600, show_spinner="Fetching items...") # Cache for 10 minutes
def get_all_items_with_stock(_engine, include_inactive=False, department: Optional[str] = None) -> pd.DataFrame:
    """
    Fetches items joined with their calculated current stock.
    Optionally filters by department based on 'permitted_departments' column.
    """
    params = {}
    where_conditions = []
    if not include_inactive:
        where_conditions.append("i.is_active = TRUE")
    if department:
        where_conditions.append("(i.permitted_departments = 'All' OR i.permitted_departments ILIKE :dept_pattern)")
        params["dept_pattern"] = f'%{department}%' # Use ILIKE for case-insensitivity

    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    stock_query = """
        SELECT item_id, SUM(quantity_change) AS calculated_stock
        FROM stock_transactions GROUP BY item_id
    """
    items_query = f"""
        SELECT i.*, COALESCE(s.calculated_stock, 0) AS current_stock
        FROM items i LEFT JOIN ({stock_query}) s ON i.item_id = s.item_id
        {where_clause} ORDER BY i.name;
    """
    return fetch_data(_engine, items_query, params)

# Function to get details for a single item
def get_item_details(engine, item_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a single item by its ID."""
    query = "SELECT * FROM items WHERE item_id = :id;"
    df = fetch_data(engine, query, {"id": item_id})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

# Function to add a new item
def add_new_item(engine, name: str, unit: str, category: str, sub_category: str,
                 permitted_departments: str, reorder_point: float, notes: str) -> bool:
    """Adds a new item to the database."""
    sql = text("""
        INSERT INTO items (name, unit, category, sub_category, permitted_departments, reorder_point, notes, is_active)
        VALUES (:name, :unit, :category, :sub_category, :permitted_departments, :reorder_point, :notes, TRUE)
        ON CONFLICT (name) DO NOTHING;
    """)
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(sql, parameters={
                    "name": name, "unit": unit, "category": category, "sub_category": sub_category,
                    "permitted_departments": permitted_departments, "reorder_point": reorder_point, "notes": notes
                })
            get_all_items_with_stock.clear()
            return result.rowcount > 0
    except IntegrityError: st.error(f"Item name '{name}' might already exist."); return False
    except Exception as e: st.error(f"Error adding item: {e}"); return False

# Function to update existing item details
def update_item_details(engine, item_id: int, details: Dict[str, Any]) -> bool:
    """Updates details for an existing item."""
    sql = text("""
        UPDATE items SET
        name = :name, unit = :unit, category = :category, sub_category = :sub_category,
        permitted_departments = :permitted_departments, reorder_point = :reorder_point, notes = :notes
        WHERE item_id = :item_id;
    """)
    params = details.copy(); params["item_id"] = item_id
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(sql, parameters=params)
            get_all_items_with_stock.clear(); return result.rowcount > 0
    except IntegrityError: st.error(f"Update failed: Name '{details.get('name')}' might exist."); return False
    except Exception as e: st.error(f"Error updating item: {e}"); return False

# Function to deactivate an item (soft delete)
def deactivate_item(engine, item_id: int) -> bool:
    """Sets the is_active flag to FALSE for an item."""
    sql = text("UPDATE items SET is_active = FALSE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(sql, parameters={"item_id": item_id})
            get_all_items_with_stock.clear(); return result.rowcount > 0
    except Exception as e: st.error(f"Error deactivating item: {e}"); return False

# Function to reactivate an item
def reactivate_item(engine, item_id: int) -> bool:
    """Sets the is_active flag to TRUE for an item."""
    sql = text("UPDATE items SET is_active = TRUE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(sql, parameters={"item_id": item_id})
            get_all_items_with_stock.clear(); return result.rowcount > 0
    except Exception as e: st.error(f"Error reactivating item: {e}"); return False


# --- Supplier Management Functions ---
@st.cache_data(ttl=600, show_spinner="Fetching suppliers...")
def get_all_suppliers(_engine, include_inactive=False) -> pd.DataFrame:
    """Fetches all suppliers."""
    query = f"SELECT * FROM suppliers {'WHERE is_active = TRUE' if not include_inactive else ''} ORDER BY name;"
    return fetch_data(_engine, query)

def get_supplier_details(engine, supplier_id: int) -> Optional[Dict[str, Any]]:
    query = "SELECT * FROM suppliers WHERE supplier_id = :id;"
    df = fetch_data(engine, query, {"id": supplier_id})
    return df.iloc[0].to_dict() if not df.empty else None

def add_supplier(engine, name: str, contact: str, phone: str, email: str, address: str, notes: str) -> bool:
    sql = text("""INSERT INTO suppliers (name, contact_person, phone, email, address, notes, is_active)
                  VALUES (:name, :contact, :phone, :email, :address, :notes, TRUE) ON CONFLICT (name) DO NOTHING;""")
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(sql, parameters={"name": name, "contact": contact, "phone": phone, "email": email, "address": address, "notes": notes})
            get_all_suppliers.clear(); return result.rowcount > 0
    except IntegrityError: st.error(f"Supplier name '{name}' might already exist."); return False
    except Exception as e: st.error(f"Error adding supplier: {e}"); return False

def update_supplier(engine, supplier_id: int, details: Dict[str, Any]) -> bool:
    sql = text("""UPDATE suppliers SET name = :name, contact_person = :contact_person, phone = :phone, email = :email, address = :address, notes = :notes
                  WHERE supplier_id = :supplier_id;""")
    params = details.copy(); params["supplier_id"] = supplier_id
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(sql, parameters=params)
            get_all_suppliers.clear(); return result.rowcount > 0
    except IntegrityError: st.error(f"Update failed: Name '{details.get('name')}' might exist."); return False
    except Exception as e: st.error(f"Error updating supplier: {e}"); return False

def deactivate_supplier(engine, supplier_id: int) -> bool:
    sql = text("UPDATE suppliers SET is_active = FALSE WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(sql, parameters={"supplier_id": supplier_id})
            get_all_suppliers.clear(); return result.rowcount > 0
    except Exception as e: st.error(f"Error deactivating supplier: {e}"); return False

def reactivate_supplier(engine, supplier_id: int) -> bool:
    sql = text("UPDATE suppliers SET is_active = TRUE WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            with connection.begin(): result = connection.execute(sql, parameters={"supplier_id": supplier_id})
            get_all_suppliers.clear(); return result.rowcount > 0
    except Exception as e: st.error(f"Error reactivating supplier: {e}"); return False


# --- Stock Transaction Functions ---
def record_stock_transaction(engine, item_id: int, quantity_change: float, transaction_type: str,
                             user_id: Optional[str] = None, related_mrn: Optional[str] = None,
                             related_po_id: Optional[int] = None, notes: Optional[str] = None) -> bool:
    """Records a single stock movement transaction."""
    sql = text("""
        INSERT INTO stock_transactions
        (item_id, quantity_change, transaction_type, transaction_date, user_id, related_mrn, related_po_id, notes)
        VALUES (:item_id, :quantity_change, :transaction_type, CURRENT_TIMESTAMP, :user_id, :related_mrn, :related_po_id, :notes);
    """)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(sql, parameters={
                    "item_id": item_id, "quantity_change": quantity_change, "transaction_type": transaction_type,
                    "user_id": user_id, "related_mrn": related_mrn, "related_po_id": related_po_id, "notes": notes
                })
            get_all_items_with_stock.clear() # Clear item cache as stock level changed
            get_stock_transactions.clear() # Clear transaction history cache
            return True
    except IntegrityError as ie: st.error(f"DB integrity error: {ie}. Ensure item ID exists."); return False
    except Exception as e: st.error(f"Error recording transaction: {e}"); return False

@st.cache_data(ttl=300, show_spinner="Fetching transaction history...")
def get_stock_transactions(_engine, item_id: Optional[int] = None,
                           start_date: Optional[date] = None, end_date: Optional[date] = None,
                           limit: int = 1000) -> pd.DataFrame:
    """Fetches stock transaction history with optional filters."""
    params = {"limit": limit}; conditions = []
    if item_id: conditions.append("st.item_id = :item_id"); params["item_id"] = item_id
    if start_date: conditions.append("st.transaction_date >= :start_date"); params["start_date"] = start_date
    if end_date: end_date_inclusive = end_date + timedelta(days=1); conditions.append("st.transaction_date < :end_date"); params["end_date"] = end_date_inclusive
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"""SELECT st.transaction_id, st.transaction_date, i.name AS item_name, st.quantity_change,
                       st.transaction_type, st.user_id, st.related_mrn, st.related_po_id, st.notes
                FROM stock_transactions st JOIN items i ON st.item_id = i.item_id
                {where_clause} ORDER BY st.transaction_date DESC, st.transaction_id DESC LIMIT :limit;"""
    return fetch_data(_engine, query, params)

# --- Indent Management Functions ---
def generate_mrn(engine) -> Optional[str]:
    """Generates a unique Material Request Number (MRN) using the 'mrn_seq' sequence."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT nextval('mrn_seq');"))
            seq_val = result.scalar_one_or_none()
            if seq_val is not None: return f"MRN-{seq_val:04d}"
            else: st.error("Failed to fetch next value from mrn_seq sequence."); return None
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"DB error generating MRN: {db_err}. Ensure 'mrn_seq' sequence exists."); return None
    except Exception as e: st.error(f"Error generating MRN: {e}"); return None

def create_indent(engine, indent_details: Dict[str, Any], item_list: List[Dict[str, Any]]) -> bool:
    """Creates a new indent record (header and items) within a transaction."""
    if not indent_details or not item_list: st.error("Indent details or item list empty."); return False
    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                # Insert header
                sql_insert_indent = text("""
                    INSERT INTO indents (mrn, requested_by, department, date_required, status, date_submitted, notes)
                    VALUES (:mrn, :requested_by, :department, :date_required, :status, CURRENT_TIMESTAMP, :notes)
                    RETURNING indent_id; """)
                result = connection.execute(sql_insert_indent, parameters=indent_details)
                new_indent_id = result.scalar_one_or_none()
                if new_indent_id is None: raise Exception("Failed to retrieve indent_id after insert.")
                # Insert items
                sql_insert_item = text("""INSERT INTO indent_items (indent_id, item_id, requested_qty, notes)
                                          VALUES (:indent_id, :item_id, :requested_qty, :notes);""")
                item_params = [{"indent_id": new_indent_id, "item_id": item.get("item_id"),
                                "requested_qty": item.get("requested_qty"), "notes": item.get("notes")} for item in item_list]
                connection.execute(sql_insert_item, parameters=item_params)
            # Transaction commits automatically here
            # Clear relevant caches if needed (e.g., if get_indents exists and is cached)
            # get_indents.clear() # Uncomment when get_indents is implemented and cached
            return True
    except IntegrityError as ie: st.error(f"DB integrity error: {ie}. Check item IDs."); return False
    except Exception as e: st.error(f"Error creating indent: {e}"); return False

# --- NEW FUNCTION: Get Indents ---
@st.cache_data(ttl=120, show_spinner="Fetching indents...") # Cache for 2 minutes
def get_indents(_engine,
                mrn_filter: Optional[str] = None,
                dept_filter: Optional[List[str]] = None,
                status_filter: Optional[List[str]] = None,
                date_start_filter: Optional[date] = None,
                date_end_filter: Optional[date] = None,
                limit: int = 500) -> pd.DataFrame:
    """
    Fetches indent header data from the 'indents' table with optional filters.
    """
    params = {"limit": limit}
    conditions = []
    # Build WHERE clause based on provided filters
    if mrn_filter and mrn_filter.strip():
        conditions.append("ind.mrn ILIKE :mrn_pattern")
        params["mrn_pattern"] = f'%{mrn_filter.strip()}%'
    if dept_filter:
        conditions.append("ind.department = ANY(:dept_list)")
        params["dept_list"] = dept_filter
    if status_filter:
        conditions.append("ind.status = ANY(:status_list)")
        params["status_list"] = status_filter
    if date_start_filter:
        conditions.append("ind.date_submitted >= :date_start")
        params["date_start"] = date_start_filter
    if date_end_filter:
        end_date_inclusive = date_end_filter + timedelta(days=1)
        conditions.append("ind.date_submitted < :date_end")
        params["date_end"] = end_date_inclusive

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"""
        SELECT ind.indent_id, ind.mrn, ind.requested_by, ind.department,
               ind.date_required, ind.date_submitted, ind.status, ind.notes
        FROM indents ind {where_clause}
        ORDER BY ind.date_submitted DESC, ind.indent_id DESC LIMIT :limit;
    """
    try:
        # Assuming fetch_data is defined elsewhere in the file
        return fetch_data(_engine, query, params)
    except NameError: st.error("fetch_data function not found."); return pd.DataFrame()
    except Exception as e: st.error(f"Error fetching indents: {e}"); return pd.DataFrame()


# --- Main Application (Dashboard) ---
st.set_page_config(page_title="Inv. Manager", page_icon="🍲", layout="wide")
st.title("🍲 Restaurant Inventory Dashboard")
st.caption(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

engine = connect_db()
if not engine:
    st.error("Application cannot start without DB connection.")
    st.stop()
else:
    st.sidebar.success("Connected to Database")
    all_items_df = get_all_items_with_stock(engine, include_inactive=False)
    total_active_items = len(all_items_df) if not all_items_df.empty else 0
    low_stock_df = pd.DataFrame(); low_stock_count = 0
    if not all_items_df.empty and 'current_stock' in all_items_df.columns and 'reorder_point' in all_items_df.columns:
        try:
            current_stock_numeric = pd.to_numeric(all_items_df['current_stock'], errors='coerce')
            reorder_point_numeric = pd.to_numeric(all_items_df['reorder_point'], errors='coerce')
            is_low = ((current_stock_numeric <= reorder_point_numeric) & (reorder_point_numeric > 0) &
                      (reorder_point_numeric.notna()) & (current_stock_numeric.notna()))
            low_stock_df = all_items_df[is_low]; low_stock_count = len(low_stock_df)
        except Exception as e: st.error(f"Error calculating low stock: {e}")

    col1, col2 = st.columns(2)
    with col1: st.metric("Total Active Items", total_active_items)
    with col2: st.metric("Items Low on Stock", low_stock_count)
    st.divider()
    st.subheader("⚠️ Low Stock Items")
    if low_stock_df.empty: st.info("No active items are low on stock.")
    else:
        st.warning("The following items need attention:")
        st.dataframe(low_stock_df, use_container_width=True, hide_index=True,
                     column_config={ "item_id": "ID", "name": "Item Name", "unit": "Unit", "category": "Category",
                                     "sub_category": "Sub-Category", "permitted_departments": None,
                                     "reorder_point": st.column_config.NumberColumn("Reorder Lvl", width="small"),
                                     "current_stock": st.column_config.NumberColumn("Current Stock", width="small"),
                                     "notes": None, "is_active": None, },
                     column_order=[c for c in ["item_id", "name", "current_stock", "reorder_point", "unit", "category", "sub_category"] if c in low_stock_df.columns])
    st.divider()
    st.markdown("*(Dashboard elements can be added here)*")
