import streamlit as st
from sqlalchemy import create_engine, text, func, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError, SQLAlchemyError
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple, Set
from datetime import datetime, date, timedelta
import re # Import regular expressions for parsing departments

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
# DB CONNECTION
# ─────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Connecting to database…")
def connect_db():
    """Establishes a connection to the database using credentials from secrets."""
    try:
        if "database" not in st.secrets:
            st.error("Database configuration missing in secrets.toml!")
            return None
        db = st.secrets["database"]
        required_keys = ["engine", "user", "password", "host", "port", "dbname"]
        if not all(key in db for key in required_keys):
            missing = [k for k in required_keys if k not in db]
            st.error(f"Missing keys in database secrets: {', '.join(missing)}")
            return None

        connection_url = f"{db['engine']}://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['dbname']}"
        engine = create_engine(connection_url, pool_pre_ping=True)

        # Test connection
        with engine.connect() as connection:
            st.sidebar.success("DB connected") # Move success message here after testing
            return engine

    except OperationalError as e:
        st.error(f"Database connection failed: Check host, port, credentials.\n{e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during DB connection: {e}")
        return None

# ─────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────
def fetch_data(engine, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Fetches data using a SQL query and returns a Pandas DataFrame."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text(query), params or {})
            df = pd.DataFrame(result.mappings().all())
            return df
    except (ProgrammingError, OperationalError, SQLAlchemyError) as e:
        st.error(f"Database query error: {e}\nQuery: {query}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An unexpected error occurred during data fetch: {e}")
        return pd.DataFrame()

# ─────────────────────────────────────────────────────────
# ITEM MASTER FUNCTIONS
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300) # Cache for 5 minutes
def get_all_items_with_stock(engine, include_inactive=False) -> pd.DataFrame:
    """Fetches all items, optionally including inactive ones."""
    query = "SELECT item_id, name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active FROM items"
    if not include_inactive:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name;"
    return fetch_data(engine, query)

def get_item_details(engine, item_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a single item."""
    query = "SELECT item_id, name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active FROM items WHERE item_id = :item_id;"
    df = fetch_data(engine, query, {"item_id": item_id})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def add_new_item(engine, details: Dict[str, Any]) -> Tuple[bool, str]:
    """Adds a new item to the database."""
    required = ["name", "unit"]
    if not all(details.get(k) for k in required):
        return False, f"Missing required fields: {', '.join(k for k in required if not details.get(k))}"

    query = text("""
        INSERT INTO items (name, unit, category, sub_category, permitted_departments, reorder_point, current_stock, notes, is_active)
        VALUES (:name, :unit, :category, :sub_category, :permitted_departments, :reorder_point, :current_stock, :notes, :is_active)
        RETURNING item_id;
    """)
    params = {
        "name": details["name"].strip(),
        "unit": details["unit"].strip(),
        "category": details.get("category", "Uncategorized").strip(),
        "sub_category": details.get("sub_category", "General").strip(),
        "permitted_departments": details.get("permitted_departments"), # Keep as provided (string expected)
        "reorder_point": details.get("reorder_point", 0),
        "current_stock": details.get("current_stock", 0),
        "notes": details.get("notes"),
        "is_active": details.get("is_active", True)
    }
    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                result = connection.execute(query, params)
                new_id = result.scalar_one_or_none()
        if new_id:
            get_all_items_with_stock.clear() # Clear cache on success
            return True, f"Item '{params['name']}' added with ID {new_id}."
        else:
            return False, "Failed to add item (no ID returned)."
    except IntegrityError:
        return False, f"Item name '{params['name']}' already exists. Choose a unique name."
    except (SQLAlchemyError, Exception) as e:
        return False, f"Database error adding item: {e}"

def update_item_details(engine, item_id: int, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """Updates details for an existing item."""
    if not item_id or not updates:
        return False, "Invalid item ID or no updates provided."

    set_clauses = []
    params = {"item_id": item_id}
    allowed_fields = ["name", "unit", "category", "sub_category", "permitted_departments", "reorder_point", "notes"] # Exclude current_stock, is_active

    for key, value in updates.items():
        if key in allowed_fields:
            set_clauses.append(f"{key} = :{key}")
            params[key] = value.strip() if isinstance(value, str) else value

    if not set_clauses:
        return False, "No valid fields provided for update."

    query = text(f"UPDATE items SET {', '.join(set_clauses)} WHERE item_id = :item_id;")

    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                result = connection.execute(query, params)
        if result.rowcount > 0:
            get_all_items_with_stock.clear() # Clear cache on success
            return True, f"Item ID {item_id} updated successfully."
        else:
            # This could happen if the item_id doesn't exist, though usually caught earlier
            return False, f"Item ID {item_id} not found or no changes made."
    except IntegrityError:
        return False, f"Update failed: Potential duplicate name '{updates.get('name')}'. Choose a unique name."
    except (SQLAlchemyError, Exception) as e:
        return False, f"Database error updating item: {e}"

def deactivate_item(engine, item_id: int) -> bool:
    """Sets the is_active flag to FALSE for an item."""
    query = text("UPDATE items SET is_active = FALSE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"item_id": item_id})
        if result.rowcount > 0:
            get_all_items_with_stock.clear()
            return True
        return False
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error deactivating item {item_id}: {e}")
        return False

def reactivate_item(engine, item_id: int) -> bool:
    """Sets the is_active flag to TRUE for an item."""
    query = text("UPDATE items SET is_active = TRUE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(query, {"item_id": item_id})
        if result.rowcount > 0:
            get_all_items_with_stock.clear()
            return True
        return False
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error reactivating item {item_id}: {e}")
        return False

# ─────────────────────────────────────────────────────────
# DEPARTMENT HELPER FUNCTION (NEW)
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300) # Cache for 5 minutes
def get_distinct_departments_from_items(engine) -> List[str]:
    """
    Fetches distinct, non-empty department names from the permitted_departments
    column of active items. Assumes comma-separated strings.
    """
    query = text("""
        SELECT DISTINCT permitted_departments
        FROM items
        WHERE is_active = TRUE
          AND permitted_departments IS NOT NULL
          AND permitted_departments <> ''
          AND permitted_departments <> ' ';
    """)
    departments_set: Set[str] = set()
    try:
        with engine.connect() as connection:
            result = connection.execute(query)
            rows = result.fetchall() # Use fetchall to get all distinct strings

        for row in rows:
            permitted_str = row[0] # Assuming permitted_departments is the first column
            if permitted_str:
                # Split by comma, strip whitespace, filter out empty strings
                departments = [dept.strip() for dept in permitted_str.split(',') if dept.strip()]
                departments_set.update(departments)

        return sorted(list(departments_set))

    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error fetching distinct departments: {e}")
        return []

# ─────────────────────────────────────────────────────────
# SUPPLIER MASTER FUNCTIONS
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_all_suppliers(engine, include_inactive=False) -> pd.DataFrame:
    """Fetches all suppliers, optionally including inactive ones."""
    query = "SELECT supplier_id, name, contact_person, phone, email, address, notes, is_active FROM suppliers"
    if not include_inactive:
        query += " WHERE is_active = TRUE"
    query += " ORDER BY name;"
    return fetch_data(engine, query)

def get_supplier_details(engine, supplier_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a single supplier."""
    query = "SELECT supplier_id, name, contact_person, phone, email, address, notes, is_active FROM suppliers WHERE supplier_id = :supplier_id;"
    df = fetch_data(engine, query, {"supplier_id": supplier_id})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def add_supplier(engine, details: Dict[str, Any]) -> Tuple[bool, str]:
    """Adds a new supplier."""
    if not details.get("name"):
        return False, "Supplier name is required."

    query = text("""
        INSERT INTO suppliers (name, contact_person, phone, email, address, notes, is_active)
        VALUES (:name, :contact_person, :phone, :email, :address, :notes, :is_active)
        RETURNING supplier_id;
    """)
    params = {
        "name": details["name"].strip(),
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
        return False, f"Database error adding supplier: {e}"

def update_supplier(engine, supplier_id: int, updates: Dict[str, Any]) -> Tuple[bool, str]:
    """Updates an existing supplier."""
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
            return False, f"Supplier ID {supplier_id} not found or no changes."
    except IntegrityError:
        return False, f"Update failed: Potential duplicate name '{updates.get('name')}'. Choose a unique name."
    except (SQLAlchemyError, Exception) as e:
        return False, f"Database error updating supplier: {e}"

def deactivate_supplier(engine, supplier_id: int) -> bool:
    """Sets is_active to FALSE for a supplier."""
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

def reactivate_supplier(engine, supplier_id: int) -> bool:
    """Sets is_active to TRUE for a supplier."""
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
def record_stock_transaction(
    engine,
    item_id: int,
    quantity_change: float,
    transaction_type: str,
    user_id: Optional[str] = None,
    related_mrn: Optional[str] = None,
    related_po_id: Optional[int] = None,
    notes: Optional[str] = None
) -> bool:
    """Records a stock transaction and updates the item's current stock."""
    if not item_id or quantity_change == 0:
        st.warning("Item ID missing or quantity change is zero. No transaction recorded.")
        return False

    # Ensure notes is either a string or None
    notes = str(notes).strip() if notes is not None else None
    user_id = str(user_id).strip() if user_id is not None else None
    related_mrn = str(related_mrn).strip() if related_mrn is not None else None

    stock_update_query = text("""
        UPDATE items
        SET current_stock = current_stock + :quantity_change
        WHERE item_id = :item_id;
    """)

    transaction_insert_query = text("""
        INSERT INTO stock_transactions
            (item_id, quantity_change, transaction_type, user_id, related_mrn, related_po_id, notes)
        VALUES
            (:item_id, :quantity_change, :transaction_type, :user_id, :related_mrn, :related_po_id, :notes);
    """)

    params = {
        "item_id": item_id,
        "quantity_change": quantity_change,
        "transaction_type": transaction_type,
        "user_id": user_id,
        "related_mrn": related_mrn,
        "related_po_id": related_po_id,
        "notes": notes
    }

    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                # 1. Update current stock
                connection.execute(stock_update_query, {"item_id": item_id, "quantity_change": quantity_change})
                # 2. Insert transaction record
                connection.execute(transaction_insert_query, params)
        get_all_items_with_stock.clear() # Clear item cache as stock changed
        get_stock_transactions.clear() # Clear transaction history cache
        return True
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Database error recording stock transaction: {e}")
        return False

@st.cache_data(ttl=120) # Cache history for 2 minutes
def get_stock_transactions(
    engine,
    item_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    related_mrn: Optional[str] = None
) -> pd.DataFrame:
    """Fetches stock transaction history with optional filters."""
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
        query += " AND st.transaction_date >= :start_date"
        params['start_date'] = start_date
    if end_date:
        # Adjust end_date to include the whole day
        effective_end_date = end_date + timedelta(days=1)
        query += " AND st.transaction_date < :end_date"
        params['end_date'] = effective_end_date

    query += " ORDER BY st.transaction_date DESC, st.transaction_id DESC;"

    df = fetch_data(engine, query, params)
    if not df.empty:
        # Format date for better display, keep time component
         df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.strftime('%Y-%m-%d %H:%M:%S')
    return df

# ─────────────────────────────────────────────────────────
# INDENT FUNCTIONS
# ─────────────────────────────────────────────────────────
def generate_mrn(engine) -> Optional[str]:
    """Generates a new Material Request Number (MRN) using a sequence."""
    try:
        with engine.connect() as connection:
            # Assuming sequence name is 'mrn_seq'
            result = connection.execute(text("SELECT nextval('mrn_seq');"))
            seq_num = result.scalar_one()
            # Format: MRN-YYYYMM-SequenceNumber (padded)
            mrn = f"MRN-{datetime.now().strftime('%Y%m')}-{seq_num:05d}"
            return mrn
    except (SQLAlchemyError, Exception) as e:
        st.error(f"Error generating MRN: {e}")
        return None

def create_indent(engine, indent_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Creates a new indent record and its associated items."""
    required_header = ["mrn", "requested_by", "department", "date_required"]
    if not all(indent_data.get(k) for k in required_header):
        missing = [k for k in required_header if not indent_data.get(k)]
        return False, f"Missing required indent header fields: {', '.join(missing)}"

    if not items_data:
        return False, "Indent must contain at least one item."

    # Validate item data (basic check)
    for item in items_data:
        if not item.get('item_id') or not item.get('requested_qty') or item['requested_qty'] <= 0:
            return False, f"Invalid item data found: {item}. Ensure item ID and positive quantity are present."

    indent_query = text("""
        INSERT INTO indents (mrn, requested_by, department, date_required, notes, status)
        VALUES (:mrn, :requested_by, :department, :date_required, :notes, :status)
        RETURNING indent_id;
    """)
    item_query = text("""
        INSERT INTO indent_items (indent_id, item_id, requested_qty, notes)
        VALUES (:indent_id, :item_id, :requested_qty, :notes);
    """)

    indent_params = {
        "mrn": indent_data["mrn"],
        "requested_by": indent_data["requested_by"].strip(),
        "department": indent_data["department"], # Assuming already validated/selected
        "date_required": indent_data["date_required"],
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
                    raise Exception("Failed to retrieve indent_id after insertion.") # Rollback transaction

                # 2. Insert indent items
                item_params_list = [
                    {
                        "indent_id": new_indent_id,
                        "item_id": item['item_id'],
                        "requested_qty": item['requested_qty'],
                        "notes": item.get('notes', "").strip() or None
                    }
                    for item in items_data
                ]
                connection.execute(item_query, item_params_list) # Bulk insert items

        get_indents.clear() # Clear indent list cache
        return True, f"Indent {indent_data['mrn']} created successfully."

    except IntegrityError as e:
        # Could be duplicate MRN if generation somehow failed/collided, or FK violation
        return False, f"Database integrity error creating indent: {e}"
    except (SQLAlchemyError, Exception) as e:
        # The transaction ensures rollback on error
        return False, f"Database error creating indent: {e}"


@st.cache_data(ttl=120) # Cache indent list for 2 minutes
def get_indents(
    engine,
    mrn_filter: Optional[str] = None,
    dept_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    date_start_filter: Optional[date] = None,
    date_end_filter: Optional[date] = None
) -> pd.DataFrame:
    """Fetches indent records with optional filters."""
    query = """
        SELECT
            i.indent_id,
            i.mrn,
            i.requested_by,
            i.department,
            i.date_required,
            i.date_submitted,
            i.status,
            i.notes AS indent_notes,
            COUNT(ii.indent_item_id) AS item_count -- Count items per indent
        FROM indents i
        LEFT JOIN indent_items ii ON i.indent_id = ii.indent_id -- Join to count items
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
    if date_start_filter:
        query += " AND i.date_submitted >= :date_from"
        params['date_from'] = date_start_filter
    if date_end_filter:
        effective_date_to = date_end_filter + timedelta(days=1)
        query += " AND i.date_submitted < :date_to"
        params['date_to'] = effective_date_to

    query += """
        GROUP BY
            i.indent_id, i.mrn, i.requested_by, i.department, i.date_required,
            i.date_submitted, i.status, i.notes
        ORDER BY i.date_submitted DESC, i.indent_id DESC
    """

    df = fetch_data(engine, query, params)
    # Format dates for display
    if not df.empty:
        df['date_required'] = pd.to_datetime(df['date_required']).dt.strftime('%Y-%m-%d')
        df['date_submitted'] = pd.to_datetime(df['date_submitted']).dt.strftime('%Y-%m-%d %H:%M')
    return df

# ─────────────────────────────────────────────────────────
# DASHBOARD UI (Main App Page)
# ─────────────────────────────────────────────────────────
def run_dashboard():
    """Defines the UI for the main dashboard page."""
    st.set_page_config(page_title="Inv Manager", page_icon="🍲", layout="wide")
    st.title("🍲 Restaurant Inventory Dashboard")
    st.caption(f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    engine = connect_db()
    if not engine:
        st.warning("Database connection failed. Dashboard data cannot be loaded.")
        st.stop()

    # Fetch data for KPIs and low stock
    items_df = get_all_items_with_stock(engine, include_inactive=False) # Only active items for dashboard
    suppliers_df = get_all_suppliers(engine, include_inactive=False)
    # Consider fetching recent indents or transactions if needed for KPIs

    total_active_items = len(items_df)
    total_active_suppliers = len(suppliers_df)

    # Calculate Low Stock Count
    low_stock_df = pd.DataFrame()
    low_stock_count = 0
    if not items_df.empty and 'current_stock' in items_df.columns and 'reorder_point' in items_df.columns:
        try:
            # Ensure columns are numeric, coercing errors
            items_df['current_stock_num'] = pd.to_numeric(items_df['current_stock'], errors='coerce')
            items_df['reorder_point_num'] = pd.to_numeric(items_df['reorder_point'], errors='coerce')

            # Filter condition
            mask = (
                items_df['current_stock_num'].notna() &
                items_df['reorder_point_num'].notna() &
                (items_df['reorder_point_num'] > 0) & # Only consider items with a defined reorder point > 0
                (items_df['current_stock_num'] <= items_df['reorder_point_num'])
            )
            low_stock_df = items_df.loc[mask, ['name', 'unit', 'current_stock', 'reorder_point']] # Select relevant columns
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
    # Add more KPIs as needed (e.g., Pending Indents, Recent Transactions)

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
    else:
        st.info("No items are currently below their reorder point.")

    # Add other dashboard elements (charts, recent activity) here later if needed

# --- Main execution ---
if __name__ == "__main__":
    # This check ensures that the dashboard UI only runs when item_manager_app.py
    # is executed directly, not when its functions are imported by pages.
    run_dashboard()
