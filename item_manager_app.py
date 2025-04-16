import streamlit as st
from sqlalchemy import create_engine, text, exc as sqlalchemy_exc # Import specific exceptions
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError # For catching DB errors
import pandas as pd # For handling data in DataFrames
from typing import Any, Optional, Dict, List, Tuple # For type hinting
from datetime import datetime, date, timedelta # Import timedelta
import math # For checking quantity > 0 robustly

# --- Constants ---
TX_RECEIVING = "RECEIVING"
TX_ADJUSTMENT = "ADJUSTMENT"
TX_WASTAGE = "WASTAGE"
TX_INDENT_FULFILL = "INDENT_FULFILL"
TX_SALE = "SALE"

# --- Database Connection ---
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
        with engine.connect() as connection: connection.execute(text("SELECT 1"))
        return engine
    except Exception as e: st.error(f"DB connection failed: {e}"); return None

# --- Database Interaction Functions ---

# *** MODIFIED: Added include_inactive flag and select is_active ***
@st.cache_data(ttl=600)
def get_all_items_with_stock(_engine, include_inactive: bool = False) -> pd.DataFrame:
    """
    Fetches items and calculates their current stock level from transactions.
    Optionally includes inactive items.
    Returns a pandas DataFrame including 'current_stock' and 'is_active'.
    """
    if not _engine: st.error("DB connection unavailable."); return pd.DataFrame()

    # Base query selects most columns
    items_query_sql = """
        SELECT item_id, name, unit, category, sub_category,
               permitted_departments, reorder_point, notes, is_active
        FROM items
    """
    # Add WHERE clause only if not including inactive items
    if not include_inactive:
        items_query_sql += " WHERE is_active = TRUE"

    items_query_sql += " ORDER BY category, sub_category, name;"
    items_query = text(items_query_sql)

    # Query to calculate stock levels remains the same
    stock_query = text("""
        SELECT item_id, SUM(quantity_change) AS calculated_stock
        FROM stock_transactions GROUP BY item_id;
    """)

    # Define expected columns including is_active
    expected_cols = ["item_id", "name", "unit", "category", "sub_category", "permitted_departments", "reorder_point", "notes", "is_active", "current_stock"]

    try:
        with _engine.connect() as connection:
            items_df = pd.read_sql(items_query, connection)
            stock_levels_df = pd.read_sql(stock_query, connection)

            if items_df.empty: return pd.DataFrame(columns=expected_cols)

            # Ensure item_id is int for merging
            items_df['item_id'] = items_df['item_id'].astype(int)
            if not stock_levels_df.empty:
                 stock_levels_df['item_id'] = stock_levels_df['item_id'].astype(int)
                 stock_levels_df['calculated_stock'] = pd.to_numeric(stock_levels_df['calculated_stock'], errors='coerce').fillna(0)
            else: stock_levels_df = pd.DataFrame(columns=['item_id', 'calculated_stock'])

            # Merge and calculate stock
            combined_df = pd.merge(items_df, stock_levels_df, on='item_id', how='left')
            combined_df['calculated_stock'] = combined_df['calculated_stock'].fillna(0)
            combined_df.rename(columns={'calculated_stock': 'current_stock'}, inplace=True)

            # Ensure numeric types
            if 'reorder_point' in combined_df.columns: combined_df['reorder_point'] = pd.to_numeric(combined_df['reorder_point'], errors='coerce').fillna(0)
            if 'current_stock' in combined_df.columns: combined_df['current_stock'] = pd.to_numeric(combined_df['current_stock'], errors='coerce').fillna(0)

            # Ensure all expected columns exist before returning
            for col in expected_cols:
                if col not in combined_df.columns:
                    if col == 'is_active': combined_df[col] = True # Default to active if missing
                    elif col in ['reorder_point', 'current_stock']: combined_df[col] = 0
                    else: combined_df[col] = None

            return combined_df[expected_cols] # Return with consistent columns

    except ProgrammingError as e: st.error(f"DB query failed. Tables exist? Error: {e}"); return pd.DataFrame(columns=expected_cols)
    except Exception as e: st.error(f"Failed to fetch items/stock: {e}"); st.exception(e); return pd.DataFrame(columns=expected_cols)

def get_item_details(engine, item_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a specific item_id."""
    # ... (function unchanged) ...
    if not engine or item_id is None: return None
    query = text("SELECT * FROM items WHERE item_id = :id")
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"id": item_id}); row = result.fetchone()
            return row._mapping if row else None
    except Exception as e: st.error(f"Failed to fetch item details {item_id}: {e}"); return None

def add_new_item(engine, item_details: Dict[str, Any]) -> bool:
    """Inserts a new item."""
    # ... (function unchanged) ...
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
    # ... (function unchanged) ...
    if not engine or item_id is None: return False
    update_parts = []; params = {"item_id": item_id}; editable_fields = ['name', 'unit', 'category', 'sub_category', 'permitted_departments', 'reorder_point', 'notes']
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
    # ... (function unchanged) ...
    if not engine or item_id is None: return False
    deactivate_query = text("UPDATE items SET is_active = FALSE WHERE item_id = :item_id"); params = {"item_id": item_id}
    try:
        with engine.connect() as connection:
            with connection.begin(): connection.execute(deactivate_query, params)
        return True
    except Exception as e: st.error(f"Failed to deactivate item {item_id}: {e}"); st.exception(e); return False

# *** NEW: Function to reactivate an item ***
def reactivate_item(engine, item_id: int) -> bool:
    """Sets the is_active flag to TRUE for the given item_id."""
    if not engine or item_id is None:
        return False

    # SQL query to update the is_active flag
    reactivate_query = text("""
        UPDATE items
        SET is_active = TRUE
        WHERE item_id = :item_id
    """)
    params = {"item_id": item_id}

    try:
        with engine.connect() as connection:
            with connection.begin(): # Use transaction
                connection.execute(reactivate_query, params)
        return True # Success
    except Exception as e:
        st.error(f"Failed to reactivate item {item_id} in database: {e}")
        st.exception(e)
        return False

def record_stock_transaction(engine, item_id: int, quantity_change: float, transaction_type: str, user_id: str, notes: Optional[str] = None, related_mrn: Optional[str] = None, related_po_id: Optional[int] = None) -> bool:
    """Records a single stock movement."""
    # ... (function unchanged) ...
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
    # ... (function unchanged) ...
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

# --- Initialize Session State ---
if 'item_to_edit_id' not in st.session_state: st.session_state.item_to_edit_id = None
if 'edit_form_values' not in st.session_state: st.session_state.edit_form_values = None
# *** NEW: State for showing inactive items ***
if 'show_inactive' not in st.session_state: st.session_state.show_inactive = False

# --- Main App Logic ---
st.set_page_config(page_title="Boteco Item Manager", layout="wide")
st.title("Boteco Item Manager 🛒")
st.write("Manage inventory items and stock movements.")

db_engine = connect_db()

if not db_engine:
    st.info("Please ensure database credentials are correct and the database is accessible.")
    st.stop()
else:
    # --- Controls for Viewing Items ---
    st.checkbox("Show Deactivated Items?", key="show_inactive", value=st.session_state.show_inactive)
    st.divider()

    # --- Display Items (Potentially includes inactive) ---
    st.subheader("Item List")
    # *** Pass checkbox state to fetch function ***
    items_df_with_stock = get_all_items_with_stock(db_engine, include_inactive=st.session_state.show_inactive)

    # --- Low Stock Report Section ---
    # (Calculated based on the potentially filtered items_df_with_stock)
    st.subheader("⚠️ Low Stock Items")
    if not items_df_with_stock.empty:
        # Filter only active items for low stock report
        active_items_df = items_df_with_stock[items_df_with_stock['is_active']].copy()
        if not active_items_df.empty:
            active_items_df['current_stock'] = pd.to_numeric(active_items_df['current_stock'], errors='coerce').fillna(0)
            active_items_df['reorder_point'] = pd.to_numeric(active_items_df['reorder_point'], errors='coerce').fillna(0)
            low_stock_df = active_items_df[
                (active_items_df['reorder_point'] > 0) &
                (active_items_df['current_stock'] <= active_items_df['reorder_point'])
            ].copy()
            if low_stock_df.empty: st.info("No active items are currently at or below their reorder point.")
            else:
                st.warning("The following active items need attention:")
                st.dataframe(
                    low_stock_df, use_container_width=True, hide_index=True,
                    column_config={ # Reuse or adapt config from main table
                        "item_id": st.column_config.NumberColumn("ID", width="small"),
                        "name": st.column_config.TextColumn("Item Name", width="medium"),
                        "unit": st.column_config.TextColumn("Unit", width="small"),
                        "category": st.column_config.TextColumn("Category"),
                        "sub_category": st.column_config.TextColumn("Sub-Category"),
                        "permitted_departments": st.column_config.TextColumn("Permitted Depts", width="small"),
                        "reorder_point": st.column_config.NumberColumn("Reorder Lvl", width="small", format="%d"),
                        "current_stock": st.column_config.NumberColumn("Current Stock", width="small"),
                        "notes": None, "is_active": None, # Hide notes & status here
                    },
                     column_order=[col for col in ["item_id", "name", "current_stock", "reorder_point", "unit", "category", "sub_category", "permitted_departments"] if col in low_stock_df.columns]
                )
        else:
             st.info("No active items found to check stock levels.") # Case where only inactive items exist
    else:
        st.info("No item data available to check stock levels.")
    st.divider()

    # Display Full Item List (Active or All based on checkbox)
    st.subheader("Full Item List" + (" (Including Deactivated)" if st.session_state.show_inactive else " (Active Only)"))
    if items_df_with_stock.empty and 'name' not in items_df_with_stock.columns:
        st.info("No items found matching the current view setting.")
    else:
        st.dataframe(
            items_df_with_stock, use_container_width=True, hide_index=True,
            column_config={ # Customize columns
                "item_id": st.column_config.NumberColumn("ID", width="small"),
                "name": st.column_config.TextColumn("Item Name", width="medium"),
                "unit": st.column_config.TextColumn("Unit", width="small"),
                "category": st.column_config.TextColumn("Category"),
                "sub_category": st.column_config.TextColumn("Sub-Category"),
                "permitted_departments": st.column_config.TextColumn("Permitted Depts", width="medium"),
                "reorder_point": st.column_config.NumberColumn("Reorder Lvl", width="small", format="%d"),
                "current_stock": st.column_config.NumberColumn("Current Stock", width="small", help="Calculated from transactions."),
                "notes": st.column_config.TextColumn("Notes", width="large"),
                # *** ADDED: Display is_active status when showing all ***
                "is_active": st.column_config.CheckboxColumn("Active?", width="small", disabled=True),
            },
            # Define column order, include is_active
            column_order=[col for col in ["item_id", "name", "category", "sub_category", "unit", "current_stock", "reorder_point", "permitted_departments", "is_active", "notes"] if col in items_df_with_stock.columns]
        )
    st.divider()

    # Prepare item options for dropdowns (use the potentially filtered list)
    if not items_df_with_stock.empty and 'item_id' in items_df_with_stock.columns and 'name' in items_df_with_stock.columns:
        item_options_list: List[Tuple[str, int]] = [(f"{row['name']}{'' if row['is_active'] else ' (Inactive)'}", row['item_id']) for index, row in items_df_with_stock.dropna(subset=['name']).iterrows()]
        item_options_list.sort() # Sort by name (including inactive marker)
    else: item_options_list = []

    # --- Add New Item Form ---
    with st.expander("➕ Add New Item"):
        # ... (Form remains the same) ...
        with st.form("new_item_form", clear_on_submit=True):
            st.subheader("Enter New Item Details:"); new_name = st.text_input("Item Name*"); new_unit = st.text_input("Unit (e.g., Kg, Pcs, Ltr)"); new_category = st.text_input("Category"); new_sub_category = st.text_input("Sub-Category"); new_permitted_departments = st.text_input("Permitted Departments (Comma-separated or All)"); new_reorder_point = st.number_input("Reorder Point", min_value=0, value=0, step=1); new_notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save New Item")
            if submitted:
                if not new_name: st.warning("Item Name is required.")
                else:
                    item_data = {"name": new_name.strip(), "unit": new_unit.strip() or None, "category": new_category.strip() or "Uncategorized", "sub_category": new_sub_category.strip() or "General", "permitted_departments": new_permitted_departments.strip() or None, "reorder_point": new_reorder_point, "notes": new_notes.strip() or None}
                    success = add_new_item(db_engine, item_data)
                    if success: st.success(f"Item '{new_name}' added!"); get_all_items_with_stock.clear(); st.rerun()

    st.divider()

    # --- Edit/Deactivate/Reactivate Existing Item Section ---
    st.subheader("✏️ Edit / Deactivate / Reactivate Existing Item")
    # Use the potentially filtered item_options_list for the dropdown
    edit_options = [("--- Select ---", None)] + item_options_list

    def load_item_for_edit(): # Callback
        selected_option = st.session_state.item_to_edit_select; item_id_to_load = selected_option[1] if selected_option else None
        if item_id_to_load: details = get_item_details(db_engine, item_id_to_load); st.session_state.item_to_edit_id = item_id_to_load if details else None; st.session_state.edit_form_values = details if details else None
        else: st.session_state.item_to_edit_id = None; st.session_state.edit_form_values = None

    current_edit_id = st.session_state.get('item_to_edit_id')
    try: current_index = [i for i, opt in enumerate(edit_options) if opt[1] == current_edit_id][0] if current_edit_id is not None else 0
    except IndexError: current_index = 0

    selected_item_tuple = st.selectbox( # Dropdown
        "Select Item to Edit / Deactivate / Reactivate:", # Updated label
        options=edit_options,
        format_func=lambda x: x[0], # Display name (might include ' (Inactive)')
        key="item_to_edit_select",
        on_change=load_item_for_edit, index=current_index
    )

    # Display Edit form OR Reactivate button based on selected item's status
    if st.session_state.item_to_edit_id is not None and st.session_state.edit_form_values is not None:
        current_details = st.session_state.edit_form_values
        item_is_active = current_details.get('is_active', True) # Default to active if missing

        if item_is_active:
            # --- Show Edit Form and Deactivate Button for ACTIVE items ---
            with st.form("edit_item_form"):
                st.subheader(f"Editing Item: {current_details.get('name', '')} (ID: {st.session_state.item_to_edit_id})")
                # ... (Edit form inputs remain the same) ...
                edit_name = st.text_input("Item Name*", value=current_details.get('name', ''), key="edit_name"); edit_unit = st.text_input("Unit", value=current_details.get('unit', ''), key="edit_unit"); edit_category = st.text_input("Category", value=current_details.get('category', ''), key="edit_category"); edit_sub_category = st.text_input("Sub-Category", value=current_details.get('sub_category', ''), key="edit_sub_category"); edit_permitted_departments = st.text_input("Permitted Departments", value=current_details.get('permitted_departments', ''), key="edit_permitted_departments"); reorder_val = current_details.get('reorder_point', 0); edit_reorder_point = st.number_input("Reorder Point", min_value=0, value=int(reorder_val) if pd.notna(reorder_val) else 0, step=1, key="edit_reorder_point"); edit_notes = st.text_area("Notes", value=current_details.get('notes', ''), key="edit_notes")
                update_submitted = st.form_submit_button("Update Item Details")
                if update_submitted:
                    if not edit_name: st.warning("Item Name cannot be empty.")
                    else:
                        updated_data = {"name": st.session_state.edit_name.strip(), "unit": st.session_state.edit_unit.strip() or None, "category": st.session_state.edit_category.strip() or "Uncategorized", "sub_category": st.session_state.edit_sub_category.strip() or "General", "permitted_departments": st.session_state.edit_permitted_departments.strip() or None, "reorder_point": st.session_state.edit_reorder_point, "notes": st.session_state.edit_notes.strip() or None}
                        update_success = update_item_details(db_engine, st.session_state.item_to_edit_id, updated_data)
                        if update_success: st.success(f"Item '{st.session_state.edit_name}' updated!"); get_all_items_with_stock.clear(); st.session_state.item_to_edit_id = None; st.session_state.edit_form_values = None; st.rerun()
            st.divider()
            st.subheader("Deactivate Item"); st.warning("⚠️ Deactivating removes item from active lists.")
            if st.button("🗑️ Deactivate This Item", key="deactivate_button", type="secondary"):
                item_name_to_deactivate = current_details.get('name', 'this item')
                # Add confirmation if desired: if st.confirm(f"Deactivate '{item_name_to_deactivate}'?"):
                deactivate_success = deactivate_item(db_engine, st.session_state.item_to_edit_id)
                if deactivate_success: st.success(f"Item '{item_name_to_deactivate}' deactivated!"); get_all_items_with_stock.clear(); st.session_state.item_to_edit_id = None; st.session_state.edit_form_values = None; st.rerun()
                else: st.error("Failed to deactivate item.")
        else:
            # --- Show Reactivate Button for INACTIVE items ---
            st.info(f"Item **'{current_details.get('name', '')}'** (ID: {st.session_state.item_to_edit_id}) is currently deactivated.")
            if st.button("✅ Reactivate This Item", key="reactivate_button"):
                reactivate_success = reactivate_item(db_engine, st.session_state.item_to_edit_id)
                if reactivate_success:
                    st.success(f"Item '{current_details.get('name', '')}' reactivated successfully!")
                    get_all_items_with_stock.clear() # Clear cache
                    # Reset edit state
                    st.session_state.item_to_edit_id = None
                    st.session_state.edit_form_values = None
                    st.rerun() # Rerun to refresh list
                else:
                    st.error("Failed to reactivate item.")

    st.divider()

    # --- Stock Adjustment Form ---
    with st.expander("📈 Record Stock Adjustment"):
        # Use item_options_list prepared earlier (contains active/inactive based on checkbox)
        # Filter here to only show ACTIVE items for adjustment? Or allow adjusting inactive? Let's allow adjusting inactive for now.
        adj_item_options = [("--- Select Item ---", None)] + item_options_list
        with st.form("adjustment_form", clear_on_submit=True):
             # ... (Adjustment form code remains the same) ...
            st.subheader("Enter Adjustment Details:"); adj_selected_item = st.selectbox("Item to Adjust*", options=adj_item_options, format_func=lambda x: x[0], key="adj_item_select"); adj_qty_change = st.number_input("Quantity Change*", step=0.01, format="%.2f", help="Positive for IN, negative for OUT", key="adj_qty_change"); adj_user_id = st.text_input("Your Name/ID*", help="Who is making this adjustment?", key="adj_user_id"); adj_notes = st.text_area("Reason for Adjustment*", help="Why is this adjustment needed?", key="adj_notes")
            adj_submitted = st.form_submit_button("Record Adjustment")
            if adj_submitted:
                selected_item_id = adj_selected_item[1] if adj_selected_item else None
                if not selected_item_id: st.warning("Please select an item.")
                elif math.isclose(adj_qty_change, 0): st.warning("Quantity Change cannot be zero.") # Use math.isclose for float
                elif not adj_user_id: st.warning("Please enter Your Name/ID.")
                elif not adj_notes: st.warning("Please enter a reason.")
                else:
                    adj_success = record_stock_transaction(engine=db_engine, item_id=selected_item_id, quantity_change=float(adj_qty_change), transaction_type=TX_ADJUSTMENT, user_id=adj_user_id.strip(), notes=adj_notes.strip())
                    if adj_success: st.success(f"Stock adjustment for item ID {selected_item_id} recorded!"); get_all_items_with_stock.clear(); st.rerun()
                    else: st.error("Failed to record stock adjustment.")

    st.divider()

    # --- Record Goods Received Form ---
    with st.expander("📥 Record Goods Received"):
        # Use item_options_list prepared earlier (contains active/inactive based on checkbox)
        # Filter here to only show ACTIVE items for receiving? Probably makes sense.
        recv_item_options = [("--- Select Item Received ---", None)] + [opt for opt in item_options_list if st.session_state.edit_form_values.get(opt[1], {}).get('is_active', True)] if st.session_state.show_inactive else item_options_list
        # Simpler: just use active items from original df
        active_item_options = [opt for opt in item_options_list if items_df_with_stock.loc[items_df_with_stock['item_id'] == opt[1], 'is_active'].iloc[0]] if not items_df_with_stock.empty else []
        recv_item_options = [("--- Select Item Received ---", None)] + active_item_options

        with st.form("receiving_form", clear_on_submit=True):
             # ... (Receiving form code remains the same) ...
            recv_selected_item = st.selectbox("Item Received*", options=recv_item_options, format_func=lambda x: x[0], key="recv_item_select"); recv_qty = st.number_input("Quantity Received*", min_value=0.0, value=0.0, step=1.0, format="%.2f", help="Enter the positive quantity received", key="recv_qty"); recv_user_id = st.text_input("Receiver's Name/ID*", help="Who received this stock?", key="recv_user_id"); recv_notes = st.text_area("Notes (Optional)", help="e.g., Supplier Name, PO#, Invoice#, Delivery Note#", key="recv_notes")
            recv_submitted = st.form_submit_button("Record Received Stock")
            if recv_submitted:
                selected_item_id = recv_selected_item[1] if recv_selected_item else None
                if not selected_item_id: st.warning("Please select the item received.")
                elif recv_qty <= 0: st.warning("Quantity Received must be greater than zero.")
                elif not recv_user_id: st.warning("Please enter the Receiver's Name/ID.")
                else:
                    recv_success = record_stock_transaction(engine=db_engine, item_id=selected_item_id, quantity_change=float(recv_qty), transaction_type=TX_RECEIVING, user_id=recv_user_id.strip(), notes=recv_notes.strip() if recv_notes else None)
                    if recv_success: st.success(f"Recorded receipt of {recv_qty} for item ID {selected_item_id}!"); get_all_items_with_stock.clear(); st.rerun()
                    else: st.error("Failed to record received stock.")

    st.divider()

    # --- Record Wastage / Spoilage Form ---
    with st.expander("🗑️ Record Wastage / Spoilage"):
        # Use active_item_options (can only waste active items)
        waste_item_options = [("--- Select Item Wasted ---", None)] + active_item_options
        with st.form("wastage_form", clear_on_submit=True):
             # ... (Wastage form code remains the same) ...
            waste_selected_item = st.selectbox("Item Wasted*", options=waste_item_options, format_func=lambda x: x[0], key="waste_item_select"); waste_qty = st.number_input("Quantity Wasted*", min_value=0.01, step=0.01, format="%.2f", help="Enter the positive quantity wasted", key="waste_qty"); waste_user_id = st.text_input("Recorder's Name/ID*", help="Who is recording wastage?", key="waste_user_id"); waste_notes = st.text_area("Reason for Wastage*", help="Why was this item wasted?", key="waste_notes")
            waste_submitted = st.form_submit_button("Record Wastage")
            if waste_submitted:
                selected_item_id = waste_selected_item[1] if waste_selected_item else None
                if not selected_item_id: st.warning("Please select the item wasted.")
                elif waste_qty <= 0: st.warning("Quantity Wasted must be greater than zero.")
                elif not waste_user_id: st.warning("Please enter the Recorder's Name/ID.")
                elif not waste_notes: st.warning("Please enter a reason.")
                else:
                    waste_success = record_stock_transaction(engine=db_engine, item_id=selected_item_id, quantity_change=-abs(float(waste_qty)), transaction_type=TX_WASTAGE, user_id=waste_user_id.strip(), notes=waste_notes.strip())
                    if waste_success: st.success(f"Recorded wastage of {waste_qty} for item ID {selected_item_id}!"); get_all_items_with_stock.clear(); st.rerun()
                    else: st.error("Failed to record wastage.")

    st.divider()

    # --- Stock Transaction History Section ---
    st.subheader("📜 Stock Transaction History")
    # Use item_options_list (allow filtering history by inactive items too)
    hist_item_options = [("All Items", None)] + item_options_list
    col_hist1, col_hist2, col_hist3 = st.columns([2,1,1])
    with col_hist1: hist_selected_item = st.selectbox("Filter by Item:", options=hist_item_options, format_func=lambda x: x[0], key="hist_item_select")
    with col_hist2: hist_start_date = st.date_input("From Date", value=None, key="hist_start_date", format="DD/MM/YYYY")
    with col_hist3: hist_end_date = st.date_input("To Date", value=None, key="hist_end_date", format="DD/MM/YYYY")
    hist_item_id = hist_selected_item[1] if hist_selected_item else None
    transactions_df = get_stock_transactions(_engine=db_engine, item_id=hist_item_id, start_date=st.session_state.hist_start_date, end_date=st.session_state.hist_end_date)
    if transactions_df.empty: st.info("No stock transactions found matching filters.")
    else:
        st.dataframe(
            transactions_df, use_container_width=True, hide_index=True,
            column_config={ "transaction_date": st.column_config.TextColumn("Timestamp", width="small"), "item_name": st.column_config.TextColumn("Item Name", width="medium"), "transaction_type": st.column_config.TextColumn("Type", width="small"), "quantity_change": st.column_config.NumberColumn("Qty Change", format="%.2f", width="small"), "user_id": st.column_config.TextColumn("User", width="small"), "notes": st.column_config.TextColumn("Notes", width="large"), "related_mrn": st.column_config.TextColumn("Related MRN", width="small"), },
             column_order=[ "transaction_date", "item_name", "transaction_type", "quantity_change", "user_id", "notes", "related_mrn" ]
        )

