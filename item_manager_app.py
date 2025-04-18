# item_manager_app.py
# Main Streamlit application file for Restaurant Inventory Manager
# Includes database connection, core backend logic, and dashboard page.

import streamlit as st
from sqlalchemy import create_engine, text, func, inspect, select, MetaData, Table
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError, SQLAlchemyError
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple, Set
from datetime import datetime, date, timedelta
import re # Import regular expressions for parsing departments
from fpdf import FPDF # <-- Import added for PDF generation
import io # <-- Import needed for PDF bytes output

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
        if "url" not in st.secrets.database:
             st.error("Database 'url' missing in secrets.toml under [database] section!")
             return None

        # Ensure the URL starts with postgresql://
        db_url = st.secrets.database.url
        if not db_url.startswith("postgresql://"):
            if db_url.startswith("postgres://"): # Common Supabase format
                 db_url = db_url.replace("postgres://", "postgresql://", 1)
            else:
                st.error("Database URL in secrets.toml must start with 'postgresql://' or 'postgres://'")
                return None

        engine = create_engine(db_url, pool_pre_ping=True)

        # Test connection
        with engine.connect() as connection:
            st.success("Database connection established successfully!")
            return engine

    except OperationalError as e:
        st.error(f"Database connection failed: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during database connection: {e}")
        return None

# ─────────────────────────────────────────────────────────
# DATA FETCHING & HELPER FUNCTIONS (Cached where appropriate)
# ─────────────────────────────────────────────────────────

# --- Helper for executing queries ---
def fetch_data(_engine: Any, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Helper function to execute a SQL query and return a DataFrame."""
    if _engine is None:
        st.error("Database connection not available.")
        return pd.DataFrame()
    try:
        with _engine.connect() as connection:
            # Use text() for literal SQL strings
            result = connection.execute(text(query), params or {})
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df
    except ProgrammingError as e:
        st.error(f"Database programming error: {e}")
        st.error(f"Query attempted: {query}") # Log the query
        st.error(f"Parameters: {params}")
        return pd.DataFrame()
    except SQLAlchemyError as e:
        st.error(f"Database error during data fetch: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An unexpected error occurred during data fetch: {e}")
        return pd.DataFrame()

# --- Get All Items (with stock) ---
@st.cache_data(ttl=300, show_spinner="Fetching item data...") # Cache for 5 mins
def get_all_items_with_stock(_engine: Any, show_inactive: bool = False) -> pd.DataFrame:
    """Fetches all items, optionally including inactive ones, joining with current stock."""
    # This function now correctly uses the _engine convention for caching
    if _engine is None: return pd.DataFrame()
    where_clause = "" if show_inactive else "WHERE i.is_active = TRUE"
    query = f"""
        SELECT
            i.item_id,
            i.name,
            i.unit,
            i.category,
            COALESCE(s.current_stock, 0) AS current_stock, -- Use current_stock from dedicated column
            i.reorder_point,
            i.permitted_departments,
            i.is_active
        FROM items i
        LEFT JOIN ( -- Ensure we get the latest stock level if needed (though items.current_stock should be canonical)
             SELECT item_id, current_stock FROM items
        ) s ON i.item_id = s.item_id
        {where_clause}
        ORDER BY i.name;
    """
    return fetch_data(_engine, query)

# --- Get Item Details ---
# No caching needed as it's usually for editing a specific item
def get_item_details(engine: Any, item_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a single item."""
    if engine is None: return None
    query = "SELECT * FROM items WHERE item_id = :item_id;"
    df = fetch_data(engine, query, {"item_id": item_id})
    if not df.empty:
        # Convert DataFrame row to dictionary
        details = df.iloc[0].to_dict()
        # Ensure numeric types are correct (Pandas might infer them as objects sometimes)
        for col in ['reorder_point', 'current_stock']: # Add other numeric cols if any
            if col in details and pd.notna(details[col]):
                try:
                    details[col] = pd.to_numeric(details[col])
                except ValueError:
                    st.warning(f"Could not convert column '{col}' to numeric for item {item_id}.")
                    details[col] = 0 # Or some default
            elif col in details and pd.isna(details[col]):
                 details[col] = 0 # Handle None/NaN explicitly if needed
        return details
    return None


# --- Get All Suppliers ---
@st.cache_data(ttl=300, show_spinner="Fetching supplier data...") # Cache for 5 mins
def get_all_suppliers(_engine: Any, show_inactive: bool = False) -> pd.DataFrame:
    """Fetches all suppliers, optionally including inactive ones."""
    if _engine is None: return pd.DataFrame()
    where_clause = "" if show_inactive else "WHERE is_active = TRUE"
    query = f"SELECT supplier_id, name, contact_person, email, phone, is_active FROM suppliers {where_clause} ORDER BY name;"
    return fetch_data(_engine, query)

# --- Get Supplier Details ---
# No caching needed
def get_supplier_details(engine: Any, supplier_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a single supplier."""
    if engine is None: return None
    query = "SELECT * FROM suppliers WHERE supplier_id = :supplier_id;"
    df = fetch_data(engine, query, {"supplier_id": supplier_id})
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

# --- Get Stock Transactions ---
@st.cache_data(ttl=120, show_spinner="Fetching transaction history...") # Cache for 2 mins
def get_stock_transactions(
    _engine: Any,
    item_id_filter: Optional[int] = None,
    date_start_str_filter: Optional[str] = None, # Accept string dates
    date_end_str_filter: Optional[str] = None,   # Accept string dates
    transaction_type_filter: Optional[str] = None,
    user_filter: Optional[str] = None,
    mrn_filter: Optional[str] = None
) -> pd.DataFrame:
    """Fetches stock transaction history with optional filters."""
    if _engine is None: return pd.DataFrame()

    params = {}
    filters = []

    if item_id_filter:
        filters.append("st.item_id = :item_id")
        params["item_id"] = item_id_filter
    if date_start_str_filter:
        filters.append("st.transaction_date >= :date_start")
        params["date_start"] = date_start_str_filter # Pass string directly
    if date_end_str_filter:
        # Add 1 day to end date to make it inclusive for date comparison
        try:
            end_date = datetime.strptime(date_end_str_filter, '%Y-%m-%d').date()
            inclusive_end_date = end_date + timedelta(days=1)
            filters.append("st.transaction_date < :date_end")
            params["date_end"] = inclusive_end_date.strftime('%Y-%m-%d') # Pass string directly
        except ValueError:
             st.warning(f"Invalid end date format: {date_end_str_filter}. Expected YYYY-MM-DD.")
             # Optionally skip this filter or handle error differently
    if transaction_type_filter:
        filters.append("st.transaction_type = :transaction_type")
        params["transaction_type"] = transaction_type_filter
    if user_filter:
        filters.append("st.user_id ILIKE :user_id")
        params["user_id"] = f"%{user_filter}%"
    if mrn_filter:
        filters.append("st.related_mrn = :related_mrn")
        params["related_mrn"] = mrn_filter

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    query = f"""
        SELECT
            st.transaction_id,
            st.item_id,
            i.name AS item_name,
            st.transaction_date,
            st.transaction_type,
            st.quantity_change,
            st.user_id,
            st.notes,
            st.related_mrn,
            st.related_po_id
        FROM stock_transactions st
        JOIN items i ON st.item_id = i.item_id
        {where_clause}
        ORDER BY st.transaction_date DESC;
    """
    return fetch_data(_engine, query, params)


# --- Get Indents ---
@st.cache_data(ttl=120, show_spinner="Fetching indent data...") # Cache for 2 mins
def get_indents(
    _engine: Any,
    mrn_filter: Optional[str] = None,
    dept_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    date_start_str: Optional[str] = None, # Accept string date
    date_end_str: Optional[str] = None    # Accept string date
) -> pd.DataFrame:
    """Fetches indent header information with optional filters."""
    if _engine is None: return pd.DataFrame()

    params = {}
    filters = []

    if mrn_filter:
        filters.append("ind.mrn = :mrn")
        params["mrn"] = mrn_filter
    if dept_filter:
        filters.append("ind.department = :department")
        params["department"] = dept_filter
    if status_filter:
        filters.append("ind.status = :status")
        params["status"] = status_filter
    if date_start_str:
        filters.append("ind.date_submitted >= :date_start")
        params["date_start"] = date_start_str # Pass string directly
    if date_end_str:
         # Add 1 day to end date to make it inclusive for date comparison
        try:
            end_date = datetime.strptime(date_end_str, '%Y-%m-%d').date()
            inclusive_end_date = end_date + timedelta(days=1)
            filters.append("ind.date_submitted < :date_end")
            params["date_end"] = inclusive_end_date.strftime('%Y-%m-%d') # Pass string directly
        except ValueError:
             st.warning(f"Invalid end date format: {date_end_str}. Expected YYYY-MM-DD.")
             # Optionally skip this filter

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    # Query to get indent headers and count of items per indent
    query = f"""
        SELECT
            ind.indent_id,
            ind.mrn,
            ind.department,
            ind.requested_by,
            ind.date_submitted,
            ind.date_required,
            ind.status,
            ind.notes AS indent_notes,
            COUNT(ii.indent_item_id) AS item_count
        FROM indents ind
        LEFT JOIN indent_items ii ON ind.indent_id = ii.indent_id
        {where_clause}
        GROUP BY
            ind.indent_id, ind.mrn, ind.department, ind.requested_by,
            ind.date_submitted, ind.date_required, ind.status, ind.notes
        ORDER BY ind.date_submitted DESC, ind.mrn DESC;
    """
    return fetch_data(_engine, query, params)


# --- Get Distinct Departments from Items ---
@st.cache_data(ttl=600, show_spinner="Fetching department list...") # Cache for 10 mins
def get_distinct_departments_from_items(_engine: Any) -> List[str]:
    """
    Fetches all 'permitted_departments' strings from active items,
    parses them, and returns a unique, sorted list of departments.
    """
    if _engine is None: return []
    query = "SELECT DISTINCT permitted_departments FROM items WHERE is_active = TRUE AND permitted_departments IS NOT NULL AND permitted_departments <> '';"
    df = fetch_data(_engine, query)
    if df.empty:
        return []

    all_departments: Set[str] = set()
    # Iterate through the DataFrame column containing comma-separated strings
    for dept_string in df['permitted_departments']:
        # Split the string by comma, strip whitespace from each part,
        # filter out empty strings, and add to the set
        departments = {dept.strip() for dept in dept_string.split(',') if dept.strip()}
        all_departments.update(departments)

    # Convert the set to a sorted list
    return sorted(list(all_departments))


# ─────────────────────────────────────────────────────────
# DATABASE MODIFICATION FUNCTIONS (Generally not cached)
# ─────────────────────────────────────────────────────────

# --- Add New Item ---
def add_new_item(engine: Any, name: str, unit: str, category: str, reorder_point: float, permitted_departments: str) -> bool:
    """Adds a new item to the database."""
    if engine is None: return False
    query = text("""
        INSERT INTO items (name, unit, category, reorder_point, permitted_departments, current_stock, is_active)
        VALUES (:name, :unit, :category, :reorder_point, :permitted_departments, 0, TRUE)
        ON CONFLICT (name) DO NOTHING; -- Basic conflict handling: ignore duplicates by name
    """)
    params = {
        "name": name, "unit": unit, "category": category,
        "reorder_point": reorder_point, "permitted_departments": permitted_departments
    }
    try:
        with engine.connect() as connection:
            result = connection.execute(query, params)
            connection.commit()
            return result.rowcount > 0 # Return True if a row was inserted
    except IntegrityError as e:
         st.error(f"Database integrity error (e.g., duplicate name): {e}")
         return False
    except SQLAlchemyError as e:
        st.error(f"Database error adding item: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred adding item: {e}")
        return False

# --- Update Item Details ---
def update_item_details(engine: Any, item_id: int, details: Dict[str, Any]) -> bool:
    """Updates details for an existing item."""
    if engine is None: return False
    # Ensure only valid columns are updated
    valid_columns = ["name", "unit", "category", "reorder_point", "permitted_departments"]
    set_clauses = []
    params = {"item_id": item_id}
    for key, value in details.items():
        if key in valid_columns:
            set_clauses.append(f"{key} = :{key}")
            params[key] = value

    if not set_clauses:
        st.warning("No valid fields provided for update.")
        return False

    query = text(f"""
        UPDATE items
        SET {', '.join(set_clauses)}
        WHERE item_id = :item_id;
    """)
    try:
        with engine.connect() as connection:
            result = connection.execute(query, params)
            connection.commit()
            return result.rowcount > 0 # Return True if a row was updated
    except IntegrityError as e:
         st.error(f"Database integrity error (e.g., duplicate name if name is updated): {e}")
         return False
    except SQLAlchemyError as e:
        st.error(f"Database error updating item: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred updating item: {e}")
        return False

# --- Deactivate Item ---
def deactivate_item(engine: Any, item_id: int) -> bool:
    """Marks an item as inactive."""
    if engine is None: return False
    query = text("UPDATE items SET is_active = FALSE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"item_id": item_id})
            connection.commit()
            return result.rowcount > 0
    except SQLAlchemyError as e:
        st.error(f"Database error deactivating item: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred deactivating item: {e}")
        return False

# --- Reactivate Item ---
def reactivate_item(engine: Any, item_id: int) -> bool:
    """Marks an item as active."""
    if engine is None: return False
    query = text("UPDATE items SET is_active = TRUE WHERE item_id = :item_id;")
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"item_id": item_id})
            connection.commit()
            return result.rowcount > 0
    except SQLAlchemyError as e:
        st.error(f"Database error reactivating item: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred reactivating item: {e}")
        return False


# --- Add Supplier ---
def add_supplier(engine: Any, name: str, contact_person: Optional[str], email: Optional[str], phone: Optional[str]) -> bool:
    """Adds a new supplier."""
    if engine is None: return False
    query = text("""
        INSERT INTO suppliers (name, contact_person, email, phone, is_active)
        VALUES (:name, :contact_person, :email, :phone, TRUE)
        ON CONFLICT (name) DO NOTHING; -- Basic conflict handling
    """)
    params = {"name": name, "contact_person": contact_person, "email": email, "phone": phone}
    try:
        with engine.connect() as connection:
            result = connection.execute(query, params)
            connection.commit()
            return result.rowcount > 0
    except IntegrityError as e:
         st.error(f"Database integrity error (e.g., duplicate name): {e}")
         return False
    except SQLAlchemyError as e:
        st.error(f"Database error adding supplier: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred adding supplier: {e}")
        return False

# --- Update Supplier ---
def update_supplier(engine: Any, supplier_id: int, details: Dict[str, Any]) -> bool:
    """Updates supplier details."""
    if engine is None: return False
    valid_columns = ["name", "contact_person", "email", "phone"]
    set_clauses = []
    params = {"supplier_id": supplier_id}
    for key, value in details.items():
        if key in valid_columns:
            set_clauses.append(f"{key} = :{key}")
            params[key] = value

    if not set_clauses:
        st.warning("No valid fields provided for supplier update.")
        return False

    query = text(f"""
        UPDATE suppliers
        SET {', '.join(set_clauses)}
        WHERE supplier_id = :supplier_id;
    """)
    try:
        with engine.connect() as connection:
            result = connection.execute(query, params)
            connection.commit()
            return result.rowcount > 0
    except IntegrityError as e:
         st.error(f"Database integrity error (e.g., duplicate name): {e}")
         return False
    except SQLAlchemyError as e:
        st.error(f"Database error updating supplier: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred updating supplier: {e}")
        return False

# --- Deactivate Supplier ---
def deactivate_supplier(engine: Any, supplier_id: int) -> bool:
    """Marks a supplier as inactive."""
    if engine is None: return False
    query = text("UPDATE suppliers SET is_active = FALSE WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"supplier_id": supplier_id})
            connection.commit()
            return result.rowcount > 0
    except SQLAlchemyError as e:
        st.error(f"Database error deactivating supplier: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred deactivating supplier: {e}")
        return False

# --- Reactivate Supplier ---
def reactivate_supplier(engine: Any, supplier_id: int) -> bool:
    """Marks a supplier as active."""
    if engine is None: return False
    query = text("UPDATE suppliers SET is_active = TRUE WHERE supplier_id = :supplier_id;")
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"supplier_id": supplier_id})
            connection.commit()
            return result.rowcount > 0
    except SQLAlchemyError as e:
        st.error(f"Database error reactivating supplier: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred reactivating supplier: {e}")
        return False


# --- Record Stock Transaction ---
def record_stock_transaction(
    engine: Any,
    item_id: int,
    quantity_change: float,
    transaction_type: str,
    user_id: str,
    notes: Optional[str] = None,
    related_mrn: Optional[str] = None,
    related_po_id: Optional[str] = None
) -> bool:
    """
    Records a stock transaction and updates the item's current stock level.
    Uses a transaction to ensure atomicity.
    """
    if engine is None: return False

    # Validate transaction type
    valid_types = [TX_RECEIVING, TX_ADJUSTMENT, TX_WASTAGE, TX_INDENT_FULFILL, TX_SALE]
    if transaction_type not in valid_types:
        st.error(f"Invalid transaction type: {transaction_type}")
        return False

    # Start a transaction
    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                # 1. Update the item's current stock
                update_stock_query = text("""
                    UPDATE items
                    SET current_stock = current_stock + :quantity_change
                    WHERE item_id = :item_id;
                """)
                connection.execute(update_stock_query, {
                    "quantity_change": quantity_change,
                    "item_id": item_id
                })

                # 2. Insert the transaction log
                insert_log_query = text("""
                    INSERT INTO stock_transactions (
                        item_id, transaction_date, transaction_type, quantity_change,
                        user_id, notes, related_mrn, related_po_id
                    ) VALUES (
                        :item_id, NOW(), :transaction_type, :quantity_change,
                        :user_id, :notes, :related_mrn, :related_po_id
                    );
                """)
                connection.execute(insert_log_query, {
                    "item_id": item_id,
                    "transaction_type": transaction_type,
                    "quantity_change": quantity_change,
                    "user_id": user_id,
                    "notes": notes,
                    "related_mrn": related_mrn,
                    "related_po_id": related_po_id
                })
            # Transaction automatically commits here if no exceptions occurred
            return True
    except SQLAlchemyError as e:
        # Transaction automatically rolls back on exception
        st.error(f"Database error during stock transaction: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred during stock transaction: {e}")
        return False


# --- Generate MRN ---
def generate_mrn(engine: Any) -> Optional[str]:
    """Generates a unique Material Request Number (MRN) using a database sequence."""
    if engine is None: return None
    query = text("SELECT nextval('mrn_seq');") # Assumes sequence name is 'mrn_seq'
    prefix = "MRN"
    current_year = datetime.now().strftime("%y") # e.g., 24
    try:
        with engine.connect() as connection:
            result = connection.execute(query)
            sequence_number = result.scalar_one()
            # Format: MRN-YY-0000N (e.g., MRN-24-00001)
            mrn = f"{prefix}-{current_year}-{sequence_number:05d}"
            return mrn
    except ProgrammingError as e:
        st.error(f"Database error generating MRN: Sequence 'mrn_seq' might not exist or user lacks permissions. {e}")
        return None
    except SQLAlchemyError as e:
        st.error(f"Database error generating MRN: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred generating MRN: {e}")
        return None


# --- Create Indent ---
def create_indent(
    engine: Any,
    mrn: str,
    department: str,
    requested_by: str,
    date_required: date,
    status: str,
    notes: Optional[str],
    items: List[Dict[str, Any]] # List of {'item_id': int, 'requested_qty': float, 'notes': Optional[str]}
) -> bool:
    """Creates an indent header and its associated items within a transaction."""
    if engine is None: return False
    if not items:
        st.error("Cannot create an indent with no items.")
        return False

    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                # 1. Insert Indent Header
                insert_header_query = text("""
                    INSERT INTO indents (mrn, department, requested_by, date_submitted, date_required, status, notes)
                    VALUES (:mrn, :department, :requested_by, NOW(), :date_required, :status, :notes)
                    RETURNING indent_id;
                """)
                result = connection.execute(insert_header_query, {
                    "mrn": mrn,
                    "department": department,
                    "requested_by": requested_by,
                    "date_required": date_required,
                    "status": status,
                    "notes": notes
                })
                indent_id = result.scalar_one() # Get the newly created indent_id

                # 2. Insert Indent Items
                insert_item_query = text("""
                    INSERT INTO indent_items (indent_id, item_id, requested_qty, notes)
                    VALUES (:indent_id, :item_id, :requested_qty, :notes);
                """)
                # Prepare list of parameters for executemany
                item_params = [
                    {
                        "indent_id": indent_id,
                        "item_id": item['item_id'],
                        "requested_qty": item['requested_qty'],
                        "notes": item.get('notes') # Use .get for optional notes
                    } for item in items
                ]
                connection.execute(insert_item_query, item_params)

            # Transaction commits here if successful
            return True
    except IntegrityError as e:
        st.error(f"Database integrity error creating indent (e.g., invalid item_id): {e}")
        return False
    except SQLAlchemyError as e:
        st.error(f"Database error creating indent: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred creating indent: {e}")
        return False


# ─────────────────────────────────────────────────────────
# PDF GENERATION FUNCTIONALITY
# ─────────────────────────────────────────────────────────

# --- Generate Indent PDF ---
def generate_indent_pdf(engine: Any, mrn: str) -> Optional[bytes]:
    """
    Generates a PDF document for a specific indent.

    Args:
        engine: The SQLAlchemy engine instance.
        mrn: The Material Request Number (MRN) of the indent.

    Returns:
        PDF content as bytes, or None if an error occurs or indent not found.
    """
    if engine is None:
        st.error("Database connection not available for PDF generation.")
        return None
    if not mrn:
        st.error("MRN must be provided to generate PDF.")
        return None

    try:
        with engine.connect() as connection:
            # 1. Fetch Indent Header Details
            header_query = text("""
                SELECT
                    ind.mrn, ind.department, ind.requested_by,
                    ind.date_submitted, ind.date_required, ind.status, ind.notes
                FROM indents ind
                WHERE ind.mrn = :mrn;
            """)
            header_result = connection.execute(header_query, {"mrn": mrn}).fetchone()

            if not header_result:
                st.error(f"Indent with MRN '{mrn}' not found.")
                return None

            header_data = header_result._asdict() # Convert Row to dict-like

            # 2. Fetch Indent Items
            items_query = text("""
                SELECT
                    i.name AS item_name,
                    ii.requested_qty,
                    i.unit,
                    ii.notes AS item_notes
                FROM indent_items ii
                JOIN items i ON ii.item_id = i.item_id
                JOIN indents ind ON ii.indent_id = ind.indent_id
                WHERE ind.mrn = :mrn
                ORDER BY i.name;
            """)
            items_result = connection.execute(items_query, {"mrn": mrn}).fetchall()
            items_data = [row._asdict() for row in items_result] # Convert list of Rows

        # 3. Create PDF using FPDF2
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Material Indent Request", ln=True, align='C')
        pdf.ln(10) # Line break

        # --- Header Section ---
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(40, 10, "MRN:", border=0)
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 10, header_data.get("mrn", "N/A"), ln=True, border=0)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(40, 10, "Department:", border=0)
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 10, header_data.get("department", "N/A"), ln=True, border=0)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(40, 10, "Requested By:", border=0)
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 10, header_data.get("requested_by", "N/A"), ln=True, border=0)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(40, 10, "Date Submitted:", border=0)
        pdf.set_font("Helvetica", "", 12)
        submitted_date = header_data.get("date_submitted")
        pdf.cell(0, 10, submitted_date.strftime('%Y-%m-%d %H:%M') if submitted_date else "N/A", ln=True, border=0)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(40, 10, "Date Required:", border=0)
        pdf.set_font("Helvetica", "", 12)
        required_date = header_data.get("date_required")
        pdf.cell(0, 10, required_date.strftime('%Y-%m-%d') if required_date else "N/A", ln=True, border=0)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(40, 10, "Status:", border=0)
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 10, header_data.get("status", "N/A"), ln=True, border=0)

        pdf.ln(5) # Line break

        # --- Items Table ---
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Requested Items", ln=True, align='L')
        pdf.ln(2)

        # Table Header
        pdf.set_fill_color(220, 220, 220) # Light grey background
        pdf.set_font("Helvetica", "B", 10)
        col_widths = [80, 30, 20, 60] # Adjust widths as needed: Name, Qty, Unit, Notes
        pdf.cell(col_widths[0], 8, "Item Name", border=1, fill=True, align='C')
        pdf.cell(col_widths[1], 8, "Req. Qty", border=1, fill=True, align='C')
        pdf.cell(col_widths[2], 8, "Unit", border=1, fill=True, align='C')
        pdf.cell(col_widths[3], 8, "Item Notes", border=1, fill=True, align='C')
        pdf.ln()

        # Table Rows
        pdf.set_font("Helvetica", "", 10)
        for item in items_data:
            pdf.cell(col_widths[0], 7, str(item.get("item_name", "")), border=1)
            pdf.cell(col_widths[1], 7, f"{item.get('requested_qty', 0):.2f}", border=1, align='R')
            pdf.cell(col_widths[2], 7, str(item.get("unit", "")), border=1, align='C')
            pdf.cell(col_widths[3], 7, str(item.get("item_notes", "")), border=1)
            pdf.ln()

        pdf.ln(10) # Line break

        # --- Indent Notes ---
        indent_notes = header_data.get("notes")
        if indent_notes:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 10, "Overall Indent Notes:", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, indent_notes)
            pdf.ln(5)

        # --- Footer (Optional) ---
        pdf.set_y(-15) # Position 1.5 cm from bottom
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 0, 'C')

        # 4. Output PDF to bytes
        pdf_output = pdf.output(dest='S').encode('latin-1') # Output as bytes string
        return pdf_output

    except SQLAlchemyError as e:
        st.error(f"Database error generating PDF for MRN {mrn}: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred generating PDF for MRN {mrn}: {e}")
        return None


# ─────────────────────────────────────────────────────────
# MAIN APP / DASHBOARD PAGE LOGIC
# ─────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Restaurant Inventory Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Restaurant Inventory Dashboard")

# --- Database Connection ---
engine = connect_db()

if engine:
    # --- Fetch data for KPIs ---
    total_active_items = 0
    total_active_suppliers = 0
    low_stock_count = 0
    low_stock_df = pd.DataFrame() # Initialize empty DataFrame

    try:
        # Pass engine using '_engine' convention for cached functions
        items_df = get_all_items_with_stock(engine, show_inactive=False)
        suppliers_df = get_all_suppliers(engine, show_inactive=False)

        total_active_items = len(items_df)
        total_active_suppliers = len(suppliers_df)

        # Calculate Low Stock Items (where current_stock <= reorder_point AND reorder_point > 0)
        # Ensure columns exist and handle potential NaN values
        if 'current_stock' in items_df.columns and 'reorder_point' in items_df.columns:
            # Convert to numeric, coercing errors to NaN, then fill NaN with 0
            items_df['current_stock'] = pd.to_numeric(items_df['current_stock'], errors='coerce').fillna(0)
            items_df['reorder_point'] = pd.to_numeric(items_df['reorder_point'], errors='coerce').fillna(0)

            low_stock_df = items_df[
                (items_df['current_stock'] <= items_df['reorder_point']) &
                (items_df['reorder_point'] > 0)
            ].copy() # Create a copy to avoid SettingWithCopyWarning

            # Select and rename columns for display if needed
            low_stock_df = low_stock_df[['name', 'unit', 'current_stock', 'reorder_point']] # Select relevant columns
            low_stock_count = len(low_stock_df)
        else:
             missing_cols = [col for col in ['current_stock', 'reorder_point'] if col not in items_df.columns]
             if missing_cols:
                 st.warning(f"Missing columns needed for low-stock calculation: {', '.join(missing_cols)}")
             low_stock_count = 0 # Cannot calculate

    except Exception as e:
        st.error(f"Error fetching data for dashboard KPIs: {e}")
        # Reset counts/df on error
        total_active_items = 0
        total_active_suppliers = 0
        low_stock_count = 0
        low_stock_df = pd.DataFrame()


    # --- Display KPIs ---
    st.header("Key Metrics")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Active Items", total_active_items)
    kpi2.metric("Low Stock Items", low_stock_count, help="Items at or below reorder point (where reorder point > 0)")
    kpi3.metric("Active Suppliers", total_active_suppliers)

    st.divider()

    # --- Display Low Stock Table ---
    st.header("⚠️ Low Stock Items")
    if not low_stock_df.empty:
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
    elif low_stock_count == 0 and total_active_items > 0:
         st.info("No items are currently below their reorder point.")
    elif total_active_items == 0:
         st.info("No active items found to check stock levels.")
    # else: # Error occurred during data fetching, message shown above

    st.divider()
    st.markdown("Navigate using the sidebar to manage Items, Suppliers, Stock, and Indents.")

else:
    st.warning("Database connection could not be established. Please check your configuration and ensure the database is running.")
    st.info("Please configure your database connection details in `.streamlit/secrets.toml`.")
    st.code("""
[database]
url = "postgresql://user:password@host:port/database"
    """, language="toml")

