# item_manager_app.py
# Consolidated backend logic based on canvas content ('indents_page_pdf')

import streamlit as st
from sqlalchemy import create_engine, text, func, inspect, select, MetaData, Table
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError, SQLAlchemyError
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple, Set
from datetime import datetime, date, timedelta
import re # Import regular expressions for parsing departments
# Note: fpdf is NOT imported here anymore, as generation is moved to the page script

# ─────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────
TX_RECEIVING       = "RECEIVING"
TX_ADJUSTMENT      = "ADJUSTMENT"
TX_WASTAGE         = "WASTAGE"
TX_INDENT_FULFILL  = "INDENT_FULFILL"
TX_SALE            = "SALE" # Assuming future use

STATUS_SUBMITTED   = "Submitted"
STATUS_PROCESSING  = "Processing"
STATUS_COMPLETED   = "Completed"
STATUS_CANCELLED   = "Cancelled"
ALL_INDENT_STATUSES = [
    STATUS_SUBMITTED, STATUS_PROCESSING,
    STATUS_COMPLETED, STATUS_CANCELLED
]

# ─────────────────────────────────────────────────────────
# DB CONNECTION (Using structure from canvas 'indents_page_pdf')
# ─────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Connecting to database…")
def connect_db():
    """Establishes a connection to the database using credentials from secrets."""
    try:
        if "database" not in st.secrets:
            st.error("Database configuration missing in secrets.toml!")
            st.info("Ensure `.streamlit/secrets.toml` has [database] section with keys: engine, user, password, host, port, dbname.")
            return None
        db = st.secrets["database"]
        required_keys = ["engine", "user", "password", "host", "port", "dbname"]
        if not all(key in db for key in required_keys):
            missing = [k for k in required_keys if k not in db]
            st.error(f"Missing keys in database secrets: {', '.join(missing)}")
            st.info("Expected keys: engine, user, password, host, port, dbname.")
            return None

        connection_url = f"{db['engine']}://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['dbname']}"
        engine = create_engine(connection_url, pool_pre_ping=True)

        # Test connection
        with engine.connect() as connection:
            # Connection successful, return engine
            return engine

    except OperationalError as e:
        st.error(f"Database connection failed: Check host, port, credentials.\nError: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during DB connection: {e}")
        return None

# ─────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────
# This function is NOT cached with @st.cache_data, so engine param remains 'engine'
def fetch_data(engine, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Fetches data using a SQL query and returns a Pandas DataFrame."""
    if engine is None:
        st.error("Database engine not available for fetch_data.")
        return pd.DataFrame()
    try:
        with engine.connect() as connection:
            result = connection.execute(text(query), params or {})
            # Use mappings().all() for list of dicts, easier to work with
            df = pd.DataFrame(result.mappings().all())
            return df
    except (ProgrammingError, OperationalError, SQLAlchemyError) as e:
        st.error(f"Database query error: {e}\nQuery: {query}\nParams: {params}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An unexpected error occurred during data fetch: {e}")
        return pd.DataFrame()

# ─────────────────────────────────────────────────────────
# ITEM MASTER FUNCTIONS (Using _engine convention for cached functions)
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching item data...") # Cache for 5 minutes
def get_all_items_with_stock(_engine, include_inactive=False) -> pd.DataFrame:
    """Fetches all items, optionally including inactive ones."""
    if _engine is None: return pd.DataFrame()
    query = "SELECT item_id, name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active FROM items"
    if not include_inactive:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name;"
    return fetch_data(_engine, query)

# Not cached, keep 'engine'
def get_item_details(engine, item_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a single item."""
    if engine is None: return None
    query = "SELECT item_id, name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active FROM items WHERE item_id = :item_id;"
    df = fetch_data(engine, query, {"item_id": item_id})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

# Not cached, keep 'engine'
def add_new_item(engine, details: Dict[str, Any]) -> Tuple[bool, str]:
    """Adds a new item to the database."""
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
    # Prepare params safely using .get() with defaults
    params = {
        "name": details.get("name", "").strip(),
        "unit": details.get("unit", "").strip(),
        "category": details.get("category", "Uncategorized").strip(),
        "sub_category": details.get("sub_category", "General").strip(),
        "permitted_departments": details.get("permitted_departments"), # Keep as provided (string expected)
        "reorder_point": details.get("reorder_point", 0.0), # Default to float
        "current_stock": details.get("current_stock", 0.0), # Default to float
        "notes": details.get("notes", "").strip() or None,
        "is_active": details.get("is_active", True)
    }
    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                result = connection.execute(query, params)
                new_id = result.scalar_one_or_none()
        if new_id:
            get_all_items_with_stock.clear() # Clear cache on success
            get_distinct_departments_from_items.clear() # Clear dept cache
            return True, f"Item '{params['name']}' added with ID {new_id}."
        else:
            return False, "Failed to add item (no ID returned)."
    except IntegrityError:
        return False, f"Item name '{params['name']}' already exists. Choose a unique name."
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error adding item: {e}") # Log error
        return False, f"Database error adding item."

# Not cached, keep 'engine'
def update_item_details(engine, item_id: int, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """Updates details for an existing item."""
    if engine is None: return False, "Database engine not available."
    if not item_id or not updates:
        return False, "Invalid item ID or no updates provided."

    set_clauses = []
    params = {"item_id": item_id}
    # Define allowed fields for update via this function
    allowed_fields = ["name", "unit", "category", "sub_category", "permitted_departments", "reorder_point", "notes"]

    for key, value in updates.items():
        if key in allowed_fields:
            set_clauses.append(f"{key} = :{key}")
            # Handle data types and stripping
            if isinstance(value, str):
                params[key] = value.strip()
            elif key == "reorder_point" and value is not None:
                 try:
                     params[key] = float(value)
                 except (ValueError, TypeError):
                      return False, f"Invalid numeric value for reorder_point: {value}"
            else:
                 params[key] = value # Assume other types are okay (e.g., None)

    if not set_clauses:
        return False, "No valid fields provided for update."

    query = text(f"UPDATE items SET {', '.join(set_clauses)} WHERE item_id = :item_id;")

    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                result = connection.execute(query, params)
        if result.rowcount > 0:
            get_all_items_with_stock.clear() # Clear cache on success
            get_item_details.clear() # Potentially clear specific item cache if added
            get_distinct_departments_from_items.clear() # Clear dept cache
            return True, f"Item ID {item_id} updated successfully."
        else:
            # Check if item exists to give better feedback
            existing_item = get_item_details(engine, item_id)
            if existing_item is None:
                 return False, f"Update failed: Item ID {item_id} not found."
            else:
                 return False, f"Item ID {item_id} found, but no changes were made (values might be the same)."
    except IntegrityError:
        return False, f"Update failed: Potential duplicate name '{updates.get('name')}'. Choose a unique name."
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error updating item {item_id}: {e}") # Log error
        return False, f"Database error updating item."

# Not cached, keep 'engine'
def deactivate_item(engine, item_id: int) -> bool:
    """Sets the is_active flag to FALSE for an item."""
    if engine is None: return False
    query = text("UPDATE items SET is_active = FALSE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"item_id": item_id})
        if result.rowcount > 0:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear() # Clear dept cache
            return True
        return False
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error deactivating item {item_id}: {e}")
        return False

# Not cached, keep 'engine'
def reactivate_item(engine, item_id: int) -> bool:
    """Sets the is_active flag to TRUE for an item."""
    if engine is None: return False
    query = text("UPDATE items SET is_active = TRUE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"item_id": item_id})
        if result.rowcount > 0:
            get_all_items_with_stock.clear()
            get_distinct_departments_from_items.clear() # Clear dept cache
            return True
        return False
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error reactivating item {item_id}: {e}")
        return False

# ─────────────────────────────────────────────────────────
# DEPARTMENT HELPER FUNCTION
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching department list...") # Cache for 5 minutes
def get_distinct_departments_from_items(_engine) -> List[str]:
    """
    Fetches distinct, non-empty department names from the permitted_departments
    column of active items. Assumes comma-separated strings.
    """
    if _engine is None: return []
    # Query to select the column containing comma-separated strings
    query = text("""
        SELECT permitted_departments
        FROM items
        WHERE is_active = TRUE
          AND permitted_departments IS NOT NULL
          AND permitted_departments <> ''
          AND permitted_departments <> ' ';
    """)
    departments_set: Set[str] = set()
    try:
        # Use _engine here
        with _engine.connect() as connection:
            result = connection.execute(query)
            # Fetch all rows, each row contains one string (potentially comma-separated)
            rows = result.fetchall()

        # Process each comma-separated string
        for row in rows:
            permitted_str = row[0] # Access the first (and only) column in the row
            if permitted_str: # Check if the string is not None or empty
                # Split the string by comma, strip whitespace from each part,
                # filter out any resulting empty strings, and add to the set
                departments = {dept.strip() for dept in permitted_str.split(',') if dept.strip()}
                departments_set.update(departments)

        return sorted(list(departments_set))

    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error fetching distinct departments: {e}")
        return []

# ─────────────────────────────────────────────────────────
# SUPPLIER MASTER FUNCTIONS (Using _engine convention)
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching supplier data...")
def get_all_suppliers(_engine, include_inactive=False) -> pd.DataFrame:
    """Fetches all suppliers, optionally including inactive ones."""
    if _engine is None: return pd.DataFrame()
    query = "SELECT supplier_id, name, contact_person, phone, email, address, notes, is_active FROM suppliers"
    if not include_inactive:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name;"
    return fetch_data(_engine, query)

# Not cached, keep 'engine'
def get_supplier_details(engine, supplier_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a single supplier."""
    if engine is None: return None
    query = "SELECT supplier_id, name, contact_person, phone, email, address, notes, is_active FROM suppliers WHERE supplier_id = :supplier_id;"
    df = fetch_data(engine, query, {"supplier_id": supplier_id})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

# Not cached, keep 'engine'
def add_supplier(engine, details: Dict[str, Any]) -> Tuple[bool, str]:
    """Adds a new supplier."""
    if engine is None: return False, "Database engine not available."
    if not details.get("name"):
        return False, "Supplier name is required."

    query = text("""
        INSERT INTO suppliers (name, contact_person, phone, email, address, notes, is_active)
        VALUES (:name, :contact_person, :phone, :email, :address, :notes, :is_active)
        RETURNING supplier_id;
    """)
    params = {
        "name": details.get("name", "").strip(),
        "contact_person": details.get("contact_person", "").strip() or None,
        "phone": details.get("phone", "").strip() or None,
        "email": details.get("email", "").strip() or None,
        "address": details.get("address", "").strip() or None,
        "notes": details.get("notes", "").strip() or None,
        "is_active": details.get("is_active", True)
    }
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, params)
                new_id = result.scalar_one_or_none()
        if new_id:
            get_all_suppliers.clear()
            return True, f"Supplier '{params['name']}' added with ID {new_id}."
        else:
            return False, "Failed to add supplier."
    except IntegrityError:
        return False, f"Supplier name '{params['name']}' already exists."
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error adding supplier: {e}") # Log error
        return False, f"Database error adding supplier."

# Not cached, keep 'engine'
def update_supplier(engine, supplier_id: int, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """Updates an existing supplier."""
    if engine is None: return False, "Database engine not available."
    if not supplier_id or not updates:
        return False, "Invalid supplier ID or no updates."

    set_clauses = []
    params = {"supplier_id": supplier_id}
    allowed = ["name", "contact_person", "phone", "email", "address", "notes"]

    for key, value in updates.items():
        if key in allowed:
            set_clauses.append(f"{key} = :{key}")
            # Handle empty strings -> None for optional fields if desired, or just strip
            params[key] = value.strip() if isinstance(value, str) else value
            if key != "name" and params[key] == "":
                 params[key] = None # Set optional fields to NULL if submitted empty

    if not set_clauses:
        return False, "No valid fields to update."

    query = text(f"UPDATE suppliers SET {', '.join(set_clauses)} WHERE supplier_id = :supplier_id;")

    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, params)
        if result.rowcount > 0:
            get_all_suppliers.clear()
            return True, f"Supplier ID {supplier_id} updated."
        else:
            # Check if supplier exists
            existing = get_supplier_details(engine, supplier_id)
            if existing is None:
                 return False, f"Update failed: Supplier ID {supplier_id} not found."
            else:
                 return False, f"Supplier ID {supplier_id} found, but no changes were made."
    except IntegrityError:
        return False, f"Update failed: Potential duplicate name '{updates.get('name')}'. Choose a unique name."
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error updating supplier {supplier_id}: {e}") # Log error
        return False, f"Database error updating supplier."

# Not cached, keep 'engine'
def deactivate_supplier(engine, supplier_id: int) -> bool:
    """Sets is_active to FALSE for a supplier."""
    if engine is None: return False
    query = text("UPDATE suppliers SET is_active = FALSE WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"supplier_id": supplier_id})
        if result.rowcount > 0:
            get_all_suppliers.clear()
            return True
        return False
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error deactivating supplier {supplier_id}: {e}")
        return False

# Not cached, keep 'engine'
def reactivate_supplier(engine, supplier_id: int) -> bool:
    """Sets is_active to TRUE for a supplier."""
    if engine is None: return False
    query = text("UPDATE suppliers SET is_active = TRUE WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"supplier_id": supplier_id})
        if result.rowcount > 0:
            get_all_suppliers.clear()
            return True
        return False
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error reactivating supplier {supplier_id}: {e}")
        return False


# ─────────────────────────────────────────────────────────
# STOCK TRANSACTION FUNCTIONS
# ─────────────────────────────────────────────────────────
# Not cached, keep 'engine'
def record_stock_transaction(
    engine,
    item_id: int,
    quantity_change: float,
    transaction_type: str,
    user_id: Optional[str] = "System", # Default user
    related_mrn: Optional[str] = None,
    related_po_id: Optional[int] = None,
    notes: Optional[str] = None
) -> bool:
    """Records a stock transaction and updates the item's current stock."""
    if engine is None: return False
    if not item_id or quantity_change == 0:
        st.warning("Item ID missing or quantity change is zero. No transaction recorded.")
        return False

    # Ensure notes is either a string or None
    notes_cleaned = str(notes).strip() if notes is not None else None
    user_id_cleaned = str(user_id).strip() if user_id is not None else "System"
    related_mrn_cleaned = str(related_mrn).strip() if related_mrn is not None else None

    stock_update_query = text("""
        UPDATE items
        SET current_stock = COALESCE(current_stock, 0) + :quantity_change -- Handle NULL stock
        WHERE item_id = :item_id;
    """)

    transaction_insert_query = text("""
        INSERT INTO stock_transactions
            (item_id, quantity_change, transaction_type, user_id, related_mrn, related_po_id, notes, transaction_date)
        VALUES
            (:item_id, :quantity_change, :transaction_type, :user_id, :related_mrn, :related_po_id, :notes, NOW()); -- Use NOW() for timestamp
    """)

    params = {
        "item_id": item_id,
        "quantity_change": quantity_change,
        "transaction_type": transaction_type,
        "user_id": user_id_cleaned,
        "related_mrn": related_mrn_cleaned,
        "related_po_id": related_po_id, # Assumes integer or None
        "notes": notes_cleaned
    }

    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                # 1. Update current stock
                upd_result = connection.execute(stock_update_query, {"item_id": item_id, "quantity_change": quantity_change})
                if upd_result.rowcount == 0:
                     raise Exception(f"Failed to update stock for item ID {item_id} (item might not exist).")
                # 2. Insert transaction record
                connection.execute(transaction_insert_query, params)
        # Clear relevant caches outside transaction
        get_all_items_with_stock.clear() # Clear item cache as stock changed
        get_stock_transactions.clear() # Clear transaction history cache
        return True
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error recording stock transaction: {e}")
        return False

@st.cache_data(ttl=120, show_spinner="Fetching transaction history...") # Cache history for 2 minutes
def get_stock_transactions(
    _engine,
    item_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[date] = None, # Keep original type hint here
    end_date: Optional[date] = None,   # Keep original type hint here
    related_mrn: Optional[str] = None
) -> pd.DataFrame:
    """Fetches stock transaction history with optional filters."""
    if _engine is None: return pd.DataFrame()
    query = """
        SELECT
            st.transaction_id,
            st.transaction_date,
            i.name AS item_name, -- Join with items to get name
            st.transaction_type,
            st.quantity_change,
            st.user_id,
            st.notes,
            st.related_mrn,
            st.related_po_id,
            st.item_id -- Include item_id for potential joins later
        FROM stock_transactions st
        JOIN items i ON st.item_id = i.item_id -- Join added
        WHERE 1=1
    """
    params = {}

    if item_id:
        query += " AND st.item_id = :item_id"
        params['item_id'] = item_id
    if transaction_type:
        query += " AND st.transaction_type = :transaction_type"
        params['transaction_type'] = transaction_type
    if user_id:
        query += " AND st.user_id ILIKE :user_id" # Case-insensitive search for user
        params['user_id'] = f"%{user_id}%"
    if related_mrn:
        query += " AND st.related_mrn ILIKE :related_mrn" # Case-insensitive search
        params['related_mrn'] = f"%{related_mrn}%"
    if start_date:
        # Ensure comparison is done correctly (>= start of the day)
        query += " AND st.transaction_date >= :start_date"
        params['start_date'] = start_date
    if end_date:
        # Adjust end_date to include the whole day (< start of the next day)
        effective_end_date = end_date + timedelta(days=1)
        query += " AND st.transaction_date < :end_date"
        params['end_date'] = effective_end_date

    query += " ORDER BY st.transaction_date DESC, st.transaction_id DESC;"

    df = fetch_data(_engine, query, params)
    # Keep datetime objects for potential further processing, format only at display time
    # if not df.empty:
    #     if 'transaction_date' in df.columns:
    #         df['transaction_date'] = pd.to_datetime(df['transaction_date']) # Ensure datetime type

    return df

# ─────────────────────────────────────────────────────────
# INDENT FUNCTIONS
# ─────────────────────────────────────────────────────────
# Not cached, keep 'engine'
def generate_mrn(engine) -> Optional[str]:
    """Generates a new Material Request Number (MRN) using a sequence."""
    if engine is None: return None
    try:
        with engine.connect() as connection:
            # Assuming sequence name is 'mrn_seq'
            result = connection.execute(text("SELECT nextval('mrn_seq');"))
            seq_num = result.scalar_one()
            # Format: MRN-YYYYMM-SequenceNumber (padded)
            mrn = f"MRN-{datetime.now().strftime('%Y%m')}-{seq_num:05d}"
            return mrn
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error generating MRN: Sequence 'mrn_seq' might not exist or other DB error. {e}")
        return None

# Not cached, keep 'engine'
def create_indent(engine, indent_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Creates a new indent record and its associated items."""
    if engine is None: return False, "Database engine not available."
    required_header = ["mrn", "requested_by", "department", "date_required"]

    # Validate header data presence and non-emptiness for strings
    missing_or_empty = []
    for k in required_header:
        value = indent_data.get(k)
        if value is None or (isinstance(value, str) and not value.strip()):
             missing_or_empty.append(k)
    if missing_or_empty:
        return False, f"Missing or empty required indent header fields: {', '.join(missing_or_empty)}"

    if not items_data:
        return False, "Indent must contain at least one item."

    # Validate item data (basic check)
    for i, item in enumerate(items_data):
        if not item.get('item_id') or not item.get('requested_qty') or item['requested_qty'] <= 0:
            return False, f"Invalid data in item row {i+1}: {item}. Ensure item ID and positive quantity are present."

    indent_query = text("""
        INSERT INTO indents (mrn, requested_by, department, date_required, notes, status, date_submitted)
        VALUES (:mrn, :requested_by, :department, :date_required, :notes, :status, NOW()) -- Add date_submitted
        RETURNING indent_id;
    """)
    item_query = text("""
        INSERT INTO indent_items (indent_id, item_id, requested_qty, notes)
        VALUES (:indent_id, :item_id, :requested_qty, :notes);
    """)

    indent_params = {
        "mrn": indent_data["mrn"].strip(), # Ensure stripped
        "requested_by": indent_data["requested_by"].strip(), # Ensure stripped
        "department": indent_data["department"], # Assuming already validated/selected
        "date_required": indent_data["date_required"], # Assume date object
        "notes": indent_data.get("notes", "").strip() or None,
        "status": indent_data.get("status", STATUS_SUBMITTED) # Default status
    }

    try:
        with engine.connect() as connection:
            with connection.begin(): # Transaction for header and items
                # 1. Insert indent header
                result = connection.execute(indent_query, indent_params)
                new_indent_id = result.scalar_one_or_none()

                if not new_indent_id:
                    # Rollback is automatic on exception
                    raise Exception("Failed to retrieve indent_id after insertion.")

                # 2. Insert indent items
                item_params_list = [
                    {
                        "indent_id": new_indent_id,
                        "item_id": item['item_id'],
                        "requested_qty": float(item['requested_qty']), # Ensure float
                        "notes": item.get('notes', "").strip() or None
                    }
                    for item in items_data
                ]
                connection.execute(item_query, item_params_list)

        # Clear relevant caches outside transaction
        get_indents.clear() # Clear indent list cache
        return True, f"Indent {indent_data['mrn']} created successfully."

    except IntegrityError as e:
        # Check for specific constraints if possible (e.g., unique MRN)
        if "indents_mrn_key" in str(e):
             error_msg = f"Failed to create indent: MRN '{indent_params['mrn']}' already exists."
        elif "indent_items_item_id_fkey" in str(e):
             error_msg = "Failed to create indent: One or more selected Item IDs are invalid."
        else:
             error_msg = f"Database integrity error creating indent. Check MRN uniqueness and Item IDs."
        st.error(error_msg + f" Details: {e}") # Log detailed error
        return False, error_msg
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error creating indent: {e}") # Log error
        return False, f"Database error creating indent."


@st.cache_data(ttl=120, show_spinner="Fetching indent list...") # Cache indent list for 2 minutes
def get_indents(
    _engine,
    mrn_filter: Optional[str] = None,
    dept_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    date_start_str: Optional[str] = None, # Accept string dates for caching key stability
    date_end_str: Optional[str] = None
) -> pd.DataFrame:
    """Fetches indent records with optional filters, accepting dates as strings."""
    if _engine is None: return pd.DataFrame()

    # --- Convert date strings to date objects internally for query ---
    date_start_filter = None
    if date_start_str:
        try:
            date_start_filter = datetime.strptime(date_start_str, '%Y-%m-%d').date()
        except ValueError:
            st.warning(f"Invalid start date format received: {date_start_str}. Ignoring filter.")

    date_end_filter = None
    if date_end_str:
        try:
            date_end_filter = datetime.strptime(date_end_str, '%Y-%m-%d').date()
        except ValueError:
            st.warning(f"Invalid end date format received: {date_end_str}. Ignoring filter.")
    # --- End Date Conversion ---

    query = """
        SELECT
            i.indent_id, i.mrn, i.requested_by, i.department, i.date_required,
            i.date_submitted, i.status, i.notes AS indent_notes,
            COUNT(ii.indent_item_id) AS item_count
        FROM indents i
        LEFT JOIN indent_items ii ON i.indent_id = ii.indent_id
        WHERE 1=1
    """
    params = {}

    if mrn_filter:
        query += " AND i.mrn ILIKE :mrn"
        params['mrn'] = f"%{mrn_filter}%"
    if dept_filter:
        query += " AND i.department = :department"
        params['department'] = dept_filter
    if status_filter:
        query += " AND i.status = :status"
        params['status'] = status_filter

    # Use the converted date objects for filtering
    if date_start_filter:
        query += " AND i.date_submitted >= :date_from"
        params['date_from'] = date_start_filter
    if date_end_filter:
        # Adjust end_date for timestamp comparison (< start of next day)
        effective_date_to = date_end_filter + timedelta(days=1)
        query += " AND i.date_submitted < :date_to"
        params['date_to'] = effective_date_to

    query += """
        GROUP BY
            i.indent_id, i.mrn, i.requested_by, i.department, i.date_required,
            i.date_submitted, i.status, i.notes
        ORDER BY i.date_submitted DESC, i.indent_id DESC
    """

    df = fetch_data(_engine, query, params)

    # Convert relevant columns to appropriate types *after* fetching
    if not df.empty:
        for col in ['date_required', 'date_submitted']:
             if col in df.columns:
                 df[col] = pd.to_datetime(df[col], errors='coerce')
        # item_count should be numeric
        if 'item_count' in df.columns:
             df['item_count'] = pd.to_numeric(df['item_count'], errors='coerce').fillna(0).astype(int)

    return df


# --- NEW FUNCTION TO GET DETAILS FOR PDF ---
# Not cached, keep 'engine'
def get_indent_details_for_pdf(engine, mrn: str) -> Tuple[Optional[Dict], Optional[List[Dict]]]:
    """
    Fetches header and item details for a specific indent MRN, suitable for PDF generation.

    Returns:
        A tuple containing:
        - dict: Indent header data (or None if not found).
        - list[dict]: List of indent item data (or None if not found).
    """
    if engine is None or not mrn:
        return None, None

    header_data = None
    items_data = None

    try:
        with engine.connect() as connection:
            # 1. Fetch Indent Header Details
            header_query = text("""
                SELECT
                    ind.indent_id, ind.mrn, ind.department, ind.requested_by,
                    ind.date_submitted, ind.date_required, ind.status, ind.notes
                FROM indents ind
                WHERE ind.mrn = :mrn;
            """)
            header_result = connection.execute(header_query, {"mrn": mrn}).mappings().first() # Use mappings().first()

            if not header_result:
                st.error(f"Indent with MRN '{mrn}' not found.")
                return None, None

            header_data = dict(header_result) # Convert MappingResult to dict

            # Convert dates to desired string format right after fetching
            if header_data.get('date_submitted'):
                header_data['date_submitted'] = pd.to_datetime(header_data['date_submitted']).strftime('%Y-%m-%d %H:%M')
            if header_data.get('date_required'):
                 header_data['date_required'] = pd.to_datetime(header_data['date_required']).strftime('%Y-%m-%d')


            # 2. Fetch Indent Items (join with items table for name and unit)
            items_query = text("""
                SELECT
                    ii.item_id,
                    i.name AS item_name,
                    i.unit AS item_unit,
                    ii.requested_qty,
                    ii.notes AS item_notes
                FROM indent_items ii
                JOIN items i ON ii.item_id = i.item_id
                JOIN indents ind ON ii.indent_id = ind.indent_id
                WHERE ind.mrn = :mrn
                ORDER BY i.name;
            """)
            items_result = connection.execute(items_query, {"mrn": mrn}).mappings().all()
            items_data = [dict(row) for row in items_result] # Convert list of MappingResults

        return header_data, items_data

    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error fetching details for indent {mrn}: {e}")
        return None, None


# ─────────────────────────────────────────────────────────
# DASHBOARD UI (Main App Page)
# ─────────────────────────────────────────────────────────
def run_dashboard():
    """Defines the UI for the main dashboard page."""
    st.set_page_config(page_title="Inv Manager", page_icon="🍲", layout="wide")
    st.title("🍲 Restaurant Inventory Dashboard")
    st.caption(f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # --- Database Connection ---
    engine = connect_db()
    if not engine:
        st.warning("Database connection failed. Dashboard data cannot be loaded.")
        st.stop() # Stop execution if no DB connection
    else:
        # Indicate successful connection (optional)
        # st.sidebar.success("DB connected")
        pass

    # --- Fetch data for KPIs (use _engine for cached functions) ---
    items_df = get_all_items_with_stock(engine, include_inactive=False) # Pass engine directly
    suppliers_df = get_all_suppliers(engine, include_inactive=False) # Pass engine directly

    total_active_items = len(items_df)
    total_active_suppliers = len(suppliers_df)

    # --- Calculate Low Stock ---
    low_stock_df = pd.DataFrame()
    low_stock_count = 0
    if not items_df.empty and 'current_stock' in items_df.columns and 'reorder_point' in items_df.columns:
        try:
            # Ensure columns are numeric, coercing errors and filling NaNs
            items_df['current_stock_num'] = pd.to_numeric(items_df['current_stock'], errors='coerce').fillna(0)
            items_df['reorder_point_num'] = pd.to_numeric(items_df['reorder_point'], errors='coerce').fillna(0)

            # Define the mask for low stock items
            mask = (
                items_df['current_stock_num'].notna() &
                items_df['reorder_point_num'].notna() &
                (items_df['reorder_point_num'] > 0) & # Only consider items with a defined reorder point > 0
                (items_df['current_stock_num'] <= items_df['reorder_point_num'])
            )
            # Select and copy the relevant columns for the low stock dataframe
            low_stock_df = items_df.loc[mask, ['name', 'unit', 'current_stock', 'reorder_point']].copy()
            low_stock_count = len(low_stock_df)
        except KeyError as e:
             st.error(f"Missing expected column for low-stock calculation: {e}")
        except Exception as e:
            st.error(f"Error calculating low stock items: {e}")

    # --- Display KPIs ---
    st.header("Key Metrics")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Active Items", total_active_items)
    kpi2.metric("Low Stock Items", low_stock_count, help="Items at or below reorder point (where reorder point > 0)")
    kpi3.metric("Active Suppliers", total_active_suppliers)

    st.divider()

    # --- Display Low Stock Table ---
    st.header("⚠️ Low Stock Items")
    if low_stock_count > 0:
        st.dataframe(
            low_stock_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                 "name": st.column_config.TextColumn("Item Name"),
                 "unit": st.column_config.TextColumn("Unit", width="small"),
                 "current_stock": st.column_config.NumberColumn("Current Stock", format="%.2f", width="small"),
                 "reorder_point": st.column_config.NumberColumn("Reorder Point", format="%.2f", width="small"),
            }
        )
    elif total_active_items > 0:
         st.info("No items are currently below their reorder point.")
    else: # No active items
         st.info("No active items found in the system.")


# --- Main execution check ---
if __name__ == "__main__":
    run_dashboard()
