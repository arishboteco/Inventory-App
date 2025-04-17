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

# --- Database Connection ---
@st.cache_resource(show_spinner="Connecting to database...")
def connect_db():
    """Connects to the DB using secrets. Returns SQLAlchemy engine or None."""
    try:
        # Check if secrets for database exist
        if "database" not in st.secrets:
            st.error("Database configuration missing in Streamlit secrets (secrets.toml)!")
            return None

        db_secrets = st.secrets["database"]
        required_keys = ["engine", "user", "password", "host", "port", "dbname"]

        # Validate required keys are present
        if not all(key in db_secrets for key in required_keys):
            st.error(f"Database secrets are missing required keys: {required_keys}")
            return None

        # Construct database URL
        db_url = (
            f"{db_secrets['engine']}://{db_secrets['user']}:{db_secrets['password']}"
            f"@{db_secrets['host']}:{db_secrets['port']}/{db_secrets['dbname']}"
        )

        # Create and test engine connection
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1")) # Test connection
        # print("DB Connection Successful") # Keep console log minimal for production
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
            return pd.read_sql(text(query), connection, params=params if params else {})
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
    # Base WHERE clause conditions
    where_conditions = []
    if not include_inactive:
        where_conditions.append("i.is_active = TRUE")

    # Add department filter if provided
    if department:
        # Uses simple LIKE matching - assumes department names don't clash as substrings
        # e.g., '%Kitchen%' will match 'Kitchen' or 'Kitchen,Bar' or 'Bar,Kitchen'
        where_conditions.append("(i.permitted_departments = 'All' OR i.permitted_departments LIKE :dept_pattern)")
        params["dept_pattern"] = f'%{department}%'

    # Combine WHERE conditions
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    # SQL query to calculate stock by summing transactions for each item
    stock_query = """
        SELECT
            item_id,
            SUM(quantity_change) AS calculated_stock
        FROM stock_transactions
        GROUP BY item_id
    """
    # Main query to get items and join with calculated stock
    items_query = f"""
        SELECT
            i.*,
            COALESCE(s.calculated_stock, 0) AS current_stock
        FROM items i
        LEFT JOIN ({stock_query}) s ON i.item_id = s.item_id
        {where_clause}
        ORDER BY i.name;
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
            with connection.begin(): # Use transaction
                result = connection.execute(sql, parameters={
                    "name": name, "unit": unit, "category": category, "sub_category": sub_category,
                    "permitted_departments": permitted_departments, "reorder_point": reorder_point, "notes": notes
                })
            # Clear cache for item list after adding
            get_all_items_with_stock.clear()
            return result.rowcount > 0 # Returns true if a row was inserted
    except IntegrityError: # Handles potential duplicate name if ON CONFLICT fails somehow
        st.error(f"Item name '{name}' might already exist.")
        return False
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"Database error adding item: {db_err}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred adding item: {e}")
        return False

# Function to update existing item details
def update_item_details(engine, item_id: int, details: Dict[str, Any]) -> bool:
    """Updates details for an existing item."""
    sql = text("""
        UPDATE items SET
        name = :name, unit = :unit, category = :category, sub_category = :sub_category,
        permitted_departments = :permitted_departments, reorder_point = :reorder_point, notes = :notes
        WHERE item_id = :item_id;
    """)
    params = details.copy()
    params["item_id"] = item_id
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(sql, parameters=params)
            get_all_items_with_stock.clear() # Clear cache
            return result.rowcount > 0
    except IntegrityError: # Handles potential duplicate name if trying to rename
        st.error(f"Could not update: Item name '{details.get('name')}' might already exist.")
        return False
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"Database error updating item: {db_err}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred updating item: {e}")
        return False

# Function to deactivate an item (soft delete)
def deactivate_item(engine, item_id: int) -> bool:
    """Sets the is_active flag to FALSE for an item."""
    sql = text("UPDATE items SET is_active = FALSE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(sql, parameters={"item_id": item_id})
            get_all_items_with_stock.clear() # Clear cache
            return result.rowcount > 0
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"Database error deactivating item: {db_err}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred deactivating item: {e}")
        return False

# Function to reactivate an item
def reactivate_item(engine, item_id: int) -> bool:
    """Sets the is_active flag to TRUE for an item."""
    sql = text("UPDATE items SET is_active = TRUE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(sql, parameters={"item_id": item_id})
            get_all_items_with_stock.clear() # Clear cache
            return result.rowcount > 0
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"Database error reactivating item: {db_err}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred reactivating item: {e}")
        return False


# --- Supplier Management Functions ---
@st.cache_data(ttl=600, show_spinner="Fetching suppliers...")
def get_all_suppliers(_engine, include_inactive=False) -> pd.DataFrame:
    """Fetches all suppliers."""
    query = f"""
        SELECT * FROM suppliers
        {"" if include_inactive else "WHERE is_active = TRUE"}
        ORDER BY name;
    """
    return fetch_data(_engine, query)

def get_supplier_details(engine, supplier_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a single supplier by its ID."""
    query = "SELECT * FROM suppliers WHERE supplier_id = :id;"
    df = fetch_data(engine, query, {"id": supplier_id})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def add_supplier(engine, name: str, contact: str, phone: str, email: str, address: str, notes: str) -> bool:
    """Adds a new supplier."""
    sql = text("""
        INSERT INTO suppliers (name, contact_person, phone, email, address, notes, is_active)
        VALUES (:name, :contact, :phone, :email, :address, :notes, TRUE)
        ON CONFLICT (name) DO NOTHING;
    """)
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(sql, parameters={
                    "name": name, "contact": contact, "phone": phone,
                    "email": email, "address": address, "notes": notes
                })
            get_all_suppliers.clear()
            return result.rowcount > 0
    except IntegrityError:
        st.error(f"Supplier name '{name}' might already exist.")
        return False
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"Database error adding supplier: {db_err}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred adding supplier: {e}")
        return False

def update_supplier(engine, supplier_id: int, details: Dict[str, Any]) -> bool:
    """Updates details for an existing supplier."""
    sql = text("""
        UPDATE suppliers SET
        name = :name, contact_person = :contact_person, phone = :phone, email = :email,
        address = :address, notes = :notes
        WHERE supplier_id = :supplier_id;
    """)
    params = details.copy()
    params["supplier_id"] = supplier_id
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(sql, parameters=params)
            get_all_suppliers.clear()
            return result.rowcount > 0
    except IntegrityError:
        st.error(f"Could not update: Supplier name '{details.get('name')}' might already exist.")
        return False
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"Database error updating supplier: {db_err}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred updating supplier: {e}")
        return False

def deactivate_supplier(engine, supplier_id: int) -> bool:
    """Sets the is_active flag to FALSE for a supplier."""
    sql = text("UPDATE suppliers SET is_active = FALSE WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(sql, parameters={"supplier_id": supplier_id})
            get_all_suppliers.clear()
            return result.rowcount > 0
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"Database error deactivating supplier: {db_err}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred deactivating supplier: {e}")
        return False

def reactivate_supplier(engine, supplier_id: int) -> bool:
    """Sets the is_active flag to TRUE for a supplier."""
    sql = text("UPDATE suppliers SET is_active = TRUE WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(sql, parameters={"supplier_id": supplier_id})
            get_all_suppliers.clear()
            return result.rowcount > 0
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"Database error reactivating supplier: {db_err}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred reactivating supplier: {e}")
        return False


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
            # Clear item cache as stock level changed
            get_all_items_with_stock.clear()
            # Clear transaction history cache if it exists
            # get_stock_transactions.clear() # Need to define this function first
            return True
    except IntegrityError as ie: # Catch FK violation if item_id doesn't exist
         st.error(f"Database integrity error recording transaction: {ie}. Ensure item ID {item_id} exists.")
         return False
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"Database error recording transaction: {db_err}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred recording transaction: {e}")
        return False

@st.cache_data(ttl=300, show_spinner="Fetching transaction history...") # Cache for 5 mins
def get_stock_transactions(_engine, item_id: Optional[int] = None,
                           start_date: Optional[date] = None, end_date: Optional[date] = None,
                           limit: int = 1000) -> pd.DataFrame:
    """Fetches stock transaction history with optional filters."""
    params = {"limit": limit}
    conditions = []
    if item_id:
        conditions.append("st.item_id = :item_id")
        params["item_id"] = item_id
    if start_date:
        conditions.append("st.transaction_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        # Add 1 day to end_date to include the whole day
        end_date_inclusive = end_date + timedelta(days=1)
        conditions.append("st.transaction_date < :end_date")
        params["end_date"] = end_date_inclusive

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            st.transaction_id,
            st.transaction_date,
            i.name AS item_name,
            st.quantity_change,
            st.transaction_type,
            st.user_id,
            st.related_mrn,
            st.related_po_id,
            st.notes
        FROM stock_transactions st
        JOIN items i ON st.item_id = i.item_id
        {where_clause}
        ORDER BY st.transaction_date DESC, st.transaction_id DESC
        LIMIT :limit;
    """
    return fetch_data(_engine, query, params)

# --- Indent Management Functions ---

# Function to generate a unique MRN using the database sequence
def generate_mrn(engine) -> Optional[str]:
    """
    Generates a unique Material Request Number (MRN) using the 'mrn_seq' sequence.
    Returns MRN string (e.g., 'MRN-123') or None on error.
    Requires 'mrn_seq' sequence to exist in the database:
    CREATE SEQUENCE IF NOT EXISTS mrn_seq START 1;
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT nextval('mrn_seq');"))
            seq_val = result.scalar_one_or_none()
            if seq_val is not None:
                return f"MRN-{seq_val:04d}" # Format as MRN-0001, MRN-0002 etc.
            else:
                st.error("Failed to fetch next value from mrn_seq sequence.")
                return None
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"Database error generating MRN: {db_err}")
        # Could indicate the sequence doesn't exist
        st.warning("Ensure the 'mrn_seq' sequence exists in your database.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred generating MRN: {e}")
        return None

# Function to create a new indent record (header and items)
def create_indent(engine, indent_details: Dict[str, Any], item_list: List[Dict[str, Any]]) -> bool:
    """
    Creates a new indent record in the database within a transaction.
    Inserts into 'indents' table and then related items into 'indent_items'.

    Args:
        engine: SQLAlchemy engine instance.
        indent_details: Dict containing header info (mrn, requested_by, department,
                          date_required, status, notes).
        item_list: List of dicts, each containing item info (item_id, requested_qty, notes).

    Returns:
        True if successful, False otherwise.
    """
    if not indent_details or not item_list:
        st.error("Indent details or item list cannot be empty.")
        return False

    try:
        with engine.connect() as connection:
            with connection.begin(): # Start a transaction
                # 1. Insert into indents table
                sql_insert_indent = text("""
                    INSERT INTO indents (mrn, requested_by, department, date_required, status, date_submitted, notes)
                    VALUES (:mrn, :requested_by, :department, :date_required, :status, CURRENT_TIMESTAMP, :notes)
                    RETURNING indent_id;
                """)
                result = connection.execute(sql_insert_indent, parameters=indent_details)
                new_indent_id = result.scalar_one_or_none()

                if new_indent_id is None:
                    st.error("Failed to retrieve indent_id after inserting indent header.")
                    # Transaction will be rolled back automatically here
                    return False

                # 2. Insert into indent_items table
                sql_insert_item = text("""
                    INSERT INTO indent_items (indent_id, item_id, requested_qty, notes)
                    VALUES (:indent_id, :item_id, :requested_qty, :notes);
                """)

                # Prepare list of parameter dictionaries for executemany
                item_params = [
                    {
                        "indent_id": new_indent_id,
                        "item_id": item.get("item_id"),
                        "requested_qty": item.get("requested_qty"),
                        "notes": item.get("notes", None) # Allow optional notes per item
                    }
                    for item in item_list
                ]

                connection.execute(sql_insert_item, parameters=item_params)

            # Transaction commits automatically if no exception occurred
            # print(f"Successfully created indent ID: {new_indent_id} with {len(item_list)} items.") # Debug log
            # Optionally clear caches if indent lists are cached elsewhere
            # get_indents.clear() # Assuming we create a get_indents function later
            return True

    except IntegrityError as ie:
        # Handles errors like non-existent item_id (FK violation)
        st.error(f"Database integrity error: {ie}")
        st.warning("Please ensure all selected items exist and data is correct.")
        return False
    except (OperationalError, ProgrammingError) as db_err:
        st.error(f"Database error creating indent: {db_err}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred creating indent: {e}")
        return False


# --- Main Application (Dashboard) ---
st.set_page_config(
    page_title="Restaurant Inventory Manager",
    page_icon="🍲", # You can use emojis or provide a path to a .ico file
    layout="wide" # Options: "centered" or "wide"
)

st.title("🍲 Restaurant Inventory Dashboard")
st.caption(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- Connect to Database ---
engine = connect_db()

# --- Main App Logic ---
if not engine:
    st.error("Application cannot start without a database connection. Please check secrets.toml and database status.")
    st.stop() # Halt execution if no DB connection
else:
    st.sidebar.success("Connected to Database")

    # Fetch data needed for the dashboard
    # Use the internal _engine variable for cached functions
    all_items_df = get_all_items_with_stock(engine, include_inactive=False) # Only active items for dashboard KPIs

    # --- Calculate KPIs ---
    total_active_items = len(all_items_df) if not all_items_df.empty else 0

    # Low stock calculation (REVISED LOGIC)
    low_stock_df = pd.DataFrame() # Initialize as empty
    low_stock_count = 0
    # Check if DataFrame is valid and required columns exist BEFORE attempting filtering/conversion
    if not all_items_df.empty and 'current_stock' in all_items_df.columns and 'reorder_point' in all_items_df.columns:
        try:
            # Create boolean masks applying pd.to_numeric safely
            # Only apply to_numeric to the columns involved in the comparison
            current_stock_numeric = pd.to_numeric(all_items_df['current_stock'], errors='coerce')
            reorder_point_numeric = pd.to_numeric(all_items_df['reorder_point'], errors='coerce')

            is_low = (
                (current_stock_numeric <= reorder_point_numeric) &
                (reorder_point_numeric > 0) &
                (reorder_point_numeric.notna()) &
                (current_stock_numeric.notna())
            )
            # Filter the original DataFrame using the boolean mask
            low_stock_df = all_items_df[is_low]
            low_stock_count = len(low_stock_df)

        except TypeError as te:
             # This catch block is a safeguard, the error should ideally be prevented by the initial checks
             st.error(f"Error during low stock calculation: Could not convert stock/reorder columns. {te}")
        except Exception as e:
             st.error(f"Unexpected error during low stock calculation: {e}")


    # --- Display KPIs ---
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Active Items", total_active_items)
    with col2:
        # Use the calculated low_stock_count
        st.metric("Items Low on Stock", low_stock_count)

    st.divider()

    # --- Display Low Stock Items ---
    st.subheader("⚠️ Low Stock Items")
    if low_stock_df.empty:
        st.info("No active items are currently at or below their reorder point.")
    else:
        st.warning("The following active items need attention:")
        st.dataframe(
            low_stock_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "item_id": "ID", "name": "Item Name", "unit": "Unit",
                "category": "Category", "sub_category": "Sub-Category",
                "permitted_departments": None, # Hide less relevant columns for this view
                "reorder_point": st.column_config.NumberColumn("Reorder Lvl", width="small"), # Removed %d format for flexibility
                "current_stock": st.column_config.NumberColumn("Current Stock", width="small"),
                "notes": None, "is_active": None,
            },
            # Ensure column order only includes columns present in the dataframe
            column_order=[col for col in ["item_id", "name", "current_stock", "reorder_point", "unit", "category", "sub_category"] if col in low_stock_df.columns]
        )

    # --- Placeholder for other dashboard elements ---
    st.divider()
    st.markdown("*(More dashboard elements like charts or recent activity can be added here later)*")


# Note: The page files (pages/1_Items.py, pages/2_Suppliers.py, etc.) should
# import functions from this file (e.g., `from item_manager_app import connect_db, ...`)
