import streamlit as st
from sqlalchemy import create_engine, text # For database connection and executing SQL
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError # For catching DB errors
import pandas as pd # For handling data in DataFrames
from typing import Any, Optional, Dict, List, Tuple # For type hinting
from decimal import Decimal # Use Decimal for precise quantity changes

# --- Constants ---
# Define standard transaction types for consistency
TX_RECEIVING = "RECEIVING"
TX_ADJUSTMENT = "ADJUSTMENT"
TX_WASTAGE = "WASTAGE"
TX_INDENT_FULFILL = "INDENT_FULFILL"
TX_SALE = "SALE" # For potential future POS integration

# --- Database Connection ---
@st.cache_resource(show_spinner="Connecting to database...")
def connect_db():
    """Connects to the DB. Returns SQLAlchemy engine or None."""
    try:
        if "database" not in st.secrets:
            st.error("DB config missing in secrets!")
            return None
        db_secrets = st.secrets["database"]
        required_keys = ["engine", "user", "password", "host", "port", "dbname"]
        if not all(key in db_secrets for key in required_keys):
            st.error("DB secrets missing required keys.")
            return None
        db_url = (
            f"{db_secrets['engine']}://"
            f"{db_secrets['user']}:{db_secrets['password']}"
            f"@{db_secrets['host']}:{db_secrets['port']}"
            f"/{db_secrets['dbname']}"
        )
        engine = create_engine(db_url, pool_pre_ping=True)
        # Test connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"DB connection failed: {e}")
        return None

# --- Database Interaction Functions ---

@st.cache_data(ttl=600)
def get_all_items(_engine) -> pd.DataFrame:
    """Fetches all active items."""
    if not _engine: return pd.DataFrame()
    query = text("""
        SELECT item_id, name, unit, category, sub_category,
               permitted_departments, reorder_point, current_stock, notes
        FROM items WHERE is_active = TRUE ORDER BY category, sub_category, name;
    """)
    try:
        with _engine.connect() as connection:
            df = pd.read_sql(query, connection)
            for col in ['reorder_point', 'current_stock']:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
    except Exception as e: st.error(f"Failed to fetch items: {e}"); return pd.DataFrame()

def get_item_details(engine, item_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a specific item_id."""
    if not engine or item_id is None: return None
    query = text("SELECT * FROM items WHERE item_id = :id")
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"id": item_id})
            row = result.fetchone()
            return row._mapping if row else None
    except Exception as e: st.error(f"Failed to fetch item details {item_id}: {e}"); return None

def add_new_item(engine, item_details: Dict[str, Any]) -> bool:
    """Inserts a new item."""
    if not engine: return False
    insert_query = text("""
        INSERT INTO items (name, unit, category, sub_category, permitted_departments, reorder_point, notes)
        VALUES (:name, :unit, :category, :sub_category, :permitted_departments, :reorder_point, :notes)
    """)
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(insert_query, item_details)
        return True
    except IntegrityError as e: st.error(f"Failed to add: Duplicate name? Error: {e}"); return False
    except Exception as e: st.error(f"Failed to add item: {e}"); st.exception(e); return False

def update_item_details(engine, item_id: int, updated_details: Dict[str, Any]) -> bool:
    """Updates an existing item."""
    if not engine or item_id is None: return False
    update_parts = []; params = {"item_id": item_id}
    editable_fields = ['name', 'unit', 'category', 'sub_category', 'permitted_departments', 'reorder_point', 'notes']
    for key, value in updated_details.items():
        if key in editable_fields: update_parts.append(f"{key} = :{key}"); params[key] = value
    if not update_parts: st.warning("No changes detected."); return False
    update_query = text(f"UPDATE items SET {', '.join(update_parts)} WHERE item_id = :item_id")
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(update_query, params)
        return True
    except IntegrityError as e: st.error(f"Failed to update: Duplicate name? Error: {e}"); return False
    except Exception as e: st.error(f"Failed to update item {item_id}: {e}"); st.exception(e); return False

def deactivate_item(engine, item_id: int) -> bool:
    """Sets the is_active flag to FALSE."""
    if not engine or item_id is None: return False
    deactivate_query = text("UPDATE items SET is_active = FALSE WHERE item_id = :item_id")
    params = {"item_id": item_id}
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(deactivate_query, params)
        return True
    except Exception as e: st.error(f"Failed to deactivate item {item_id}: {e}"); st.exception(e); return False

def record_stock_transaction(
    engine, item_id: int, quantity_change: float, transaction_type: str,
    user_id: str, notes: Optional[str] = None, related_mrn: Optional[str] = None,
    related_po_id: Optional[int] = None
) -> bool:
    """Records a single stock movement in the stock_transactions table."""
    if not engine: st.error("DB connection unavailable."); return False
    if not all([item_id, quantity_change is not None, transaction_type, user_id]):
        st.error("Missing required fields for stock transaction."); return False

    insert_query = text("""
        INSERT INTO stock_transactions
            (item_id, quantity_change, transaction_type, user_id, notes, related_mrn, related_po_id)
        VALUES
            (:item_id, :quantity_change, :transaction_type, :user_id, :notes, :related_mrn, :related_po_id)
    """)
    params = {
        "item_id": item_id, "quantity_change": quantity_change,
        "transaction_type": transaction_type, "user_id": user_id,
        "notes": notes, "related_mrn": related_mrn, "related_po_id": related_po_id
    }
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(insert_query, params)
        return True
    except Exception as e: st.error(f"Failed to record stock transaction: {e}"); st.exception(e); return False

# --- Initialize Session State ---
if 'item_to_edit_id' not in st.session_state: st.session_state.item_to_edit_id = None
if 'edit_form_values' not in st.session_state: st.session_state.edit_form_values = None

# --- Main App Logic ---
st.set_page_config(page_title="Boteco Item Manager", layout="wide")
st.title("Boteco Item Manager 🛒")
st.write("Manage inventory items stored in the database.")

db_engine = connect_db()

if not db_engine:
    st.info("Please ensure database credentials are correct and the database is accessible.")
    st.stop()
else:
    # --- Display Items ---
    st.subheader("Current Active Items")
    items_df = get_all_items(db_engine)
    if items_df.empty and 'name' not in items_df.columns:
        st.info("No active items found.")
    else:
        st.dataframe(
            items_df, use_container_width=True, hide_index=True,
            column_config={ # Customize columns
                "item_id": st.column_config.NumberColumn("ID", width="small"),
                "name": st.column_config.TextColumn("Item Name", width="medium"),
                "unit": st.column_config.TextColumn("Unit", width="small"),
                "category": st.column_config.TextColumn("Category"),
                "sub_category": st.column_config.TextColumn("Sub-Category"),
                "permitted_departments": st.column_config.TextColumn("Permitted Depts", width="medium"),
                "reorder_point": st.column_config.NumberColumn("Reorder Lvl", width="small", format="%d"),
                "current_stock": st.column_config.NumberColumn("Stock Qty", width="small", help="Value from items table (may not reflect recent transactions yet)"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
            },
            column_order=["item_id", "name", "category", "sub_category", "unit", "current_stock", "reorder_point", "permitted_departments", "notes"]
        )
    st.divider()

    # --- Add New Item Form ---
    with st.expander("➕ Add New Item"):
        with st.form("new_item_form", clear_on_submit=True):
            # ... (Add form code remains the same) ...
            st.subheader("Enter New Item Details:")
            new_name = st.text_input("Item Name*")
            new_unit = st.text_input("Unit (e.g., Kg, Pcs, Ltr)")
            new_category = st.text_input("Category")
            new_sub_category = st.text_input("Sub-Category")
            new_permitted_departments = st.text_input("Permitted Departments (Comma-separated or All)")
            new_reorder_point = st.number_input("Reorder Point", min_value=0, value=0, step=1)
            new_notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save New Item")
            if submitted:
                if not new_name: st.warning("Item Name is required.")
                else:
                    item_data = {
                        "name": new_name.strip(), "unit": new_unit.strip() or None,
                        "category": new_category.strip() or "Uncategorized",
                        "sub_category": new_sub_category.strip() or "General",
                        "permitted_departments": new_permitted_departments.strip() or None,
                        "reorder_point": new_reorder_point, "notes": new_notes.strip() or None
                    }
                    success = add_new_item(db_engine, item_data)
                    if success: st.success(f"Item '{new_name}' added!"); get_all_items.clear(); st.rerun()

    st.divider()

    # --- Edit/Deactivate Existing Item Section ---
    st.subheader("✏️ Edit / Deactivate Existing Item")
    if not items_df.empty and 'item_id' in items_df.columns and 'name' in items_df.columns:
        item_options: List[Tuple[str, int]] = [(row['name'], row['item_id']) for index, row in items_df.dropna(subset=['name']).iterrows()]
        item_options.sort()
    else: item_options = []
    edit_options = [("--- Select ---", None)] + item_options

    def load_item_for_edit(): # Callback
        selected_option = st.session_state.item_to_edit_select
        item_id_to_load = selected_option[1] if selected_option else None
        if item_id_to_load:
            details = get_item_details(db_engine, item_id_to_load)
            st.session_state.item_to_edit_id = item_id_to_load if details else None
            st.session_state.edit_form_values = details if details else None
        else: st.session_state.item_to_edit_id = None; st.session_state.edit_form_values = None

    current_edit_id = st.session_state.get('item_to_edit_id')
    try: current_index = [i for i, opt in enumerate(edit_options) if opt[1] == current_edit_id][0] if current_edit_id is not None else 0
    except IndexError: current_index = 0

    selected_item_tuple = st.selectbox( # Dropdown
        "Select Item to Edit / Deactivate:", options=edit_options,
        format_func=lambda x: x[0], key="item_to_edit_select",
        on_change=load_item_for_edit, index=current_index
    )

    if st.session_state.item_to_edit_id is not None and st.session_state.edit_form_values is not None:
        current_details = st.session_state.edit_form_values
        # Edit Form
        with st.form("edit_item_form"):
            # ... (Edit form code remains the same) ...
            st.subheader(f"Editing Item: {current_details.get('name', '')} (ID: {st.session_state.item_to_edit_id})")
            edit_name = st.text_input("Item Name*", value=current_details.get('name', ''), key="edit_name")
            edit_unit = st.text_input("Unit", value=current_details.get('unit', ''), key="edit_unit")
            edit_category = st.text_input("Category", value=current_details.get('category', ''), key="edit_category")
            edit_sub_category = st.text_input("Sub-Category", value=current_details.get('sub_category', ''), key="edit_sub_category")
            edit_permitted_departments = st.text_input("Permitted Departments", value=current_details.get('permitted_departments', ''), key="edit_permitted_departments")
            reorder_val = current_details.get('reorder_point', 0)
            edit_reorder_point = st.number_input("Reorder Point", min_value=0, value=int(reorder_val) if pd.notna(reorder_val) else 0, step=1, key="edit_reorder_point")
            edit_notes = st.text_area("Notes", value=current_details.get('notes', ''), key="edit_notes")
            update_submitted = st.form_submit_button("Update Item Details")
            if update_submitted:
                if not edit_name: st.warning("Item Name cannot be empty.")
                else:
                    updated_data = {
                        "name": st.session_state.edit_name.strip(), "unit": st.session_state.edit_unit.strip() or None,
                        "category": st.session_state.edit_category.strip() or "Uncategorized",
                        "sub_category": st.session_state.edit_sub_category.strip() or "General",
                        "permitted_departments": st.session_state.edit_permitted_departments.strip() or None,
                        "reorder_point": st.session_state.edit_reorder_point, "notes": st.session_state.edit_notes.strip() or None
                    }
                    update_success = update_item_details(db_engine, st.session_state.item_to_edit_id, updated_data)
                    if update_success:
                        st.success(f"Item '{st.session_state.edit_name}' updated!"); get_all_items.clear()
                        st.session_state.item_to_edit_id = None; st.session_state.edit_form_values = None; st.rerun()

        st.divider()
        # Deactivate Button Section
        st.subheader("Deactivate Item")
        st.warning("⚠️ Deactivating removes item from active lists. History remains.")
        if st.button("🗑️ Deactivate This Item", key="deactivate_button", type="secondary"):
            item_name_to_deactivate = current_details.get('name', 'this item')
            # Simple confirmation via button click - consider adding st.confirm if needed
            deactivate_success = deactivate_item(db_engine, st.session_state.item_to_edit_id)
            if deactivate_success:
                st.success(f"Item '{item_name_to_deactivate}' deactivated!"); get_all_items.clear()
                st.session_state.item_to_edit_id = None; st.session_state.edit_form_values = None; st.rerun()
            else: st.error("Failed to deactivate item.")

    st.divider()

    # --- NEW: Stock Adjustment Form ---
    with st.expander("📈 Record Stock Adjustment"):
        with st.form("adjustment_form", clear_on_submit=True):
            st.subheader("Enter Adjustment Details:")

            # Select item to adjust
            adj_item_options = [("--- Select Item ---", None)] + item_options[1:] # Reuse item list, skip blank
            adj_selected_item = st.selectbox(
                "Item to Adjust*",
                options=adj_item_options,
                format_func=lambda x: x[0], # Show name
                key="adj_item_select"
            )

            # Input for quantity change (positive or negative)
            adj_qty_change = st.number_input(
                "Quantity Change*",
                step=0.01, # Allow decimals
                format="%.2f", # Format as float with 2 decimals
                help="Enter positive value for stock IN (e.g., found stock), negative for stock OUT (e.g., correction)",
                key="adj_qty_change"
            )

            # Input for user performing adjustment
            adj_user_id = st.text_input("Your Name/ID*", help="Who is making this adjustment?", key="adj_user_id")

            # Input for reason/notes (mandatory for adjustments)
            adj_notes = st.text_area("Reason for Adjustment*", help="Explain why this adjustment is needed (e.g., Stock count correction, Initial stock entry)", key="adj_notes")

            # Form submission button
            adj_submitted = st.form_submit_button("Record Adjustment")

            if adj_submitted:
                # Validation
                selected_item_id = adj_selected_item[1] if adj_selected_item else None
                if not selected_item_id:
                    st.warning("Please select an item to adjust.")
                elif adj_qty_change == 0:
                    st.warning("Quantity Change cannot be zero.")
                elif not adj_user_id:
                    st.warning("Please enter Your Name/ID.")
                elif not adj_notes:
                    st.warning("Please enter a reason for the adjustment in the Notes.")
                else:
                    # Call the backend function to record the transaction
                    adj_success = record_stock_transaction(
                        engine=db_engine,
                        item_id=selected_item_id,
                        quantity_change=float(adj_qty_change), # Ensure float
                        transaction_type=TX_ADJUSTMENT, # Use the constant
                        user_id=adj_user_id.strip(),
                        notes=adj_notes.strip()
                        # related_mrn and related_po_id are None by default
                    )

                    if adj_success:
                        st.success(f"Stock adjustment for item ID {selected_item_id} recorded successfully!")
                        # Note: We are NOT clearing get_all_items cache or rerunning here
                        # because this action doesn't update the displayed 'current_stock' yet.
                    else:
                        st.error("Failed to record stock adjustment.")

