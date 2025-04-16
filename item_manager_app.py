import streamlit as st
from sqlalchemy import create_engine, text # For database connection and executing SQL
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError # For catching DB errors
import pandas as pd # For handling data in DataFrames
from typing import Any, Optional, Dict, List, Tuple # For type hinting

# --- Database Connection ---

# Cache the database connection (engine) to reuse it across reruns
@st.cache_resource(show_spinner="Connecting to database...")
def connect_db():
    """
    Connects to the PostgreSQL database using credentials from Streamlit Secrets.
    Returns the SQLAlchemy engine object, or None if connection fails.
    """
    try:
        if "database" not in st.secrets:
            st.error("Database configuration (`[database]`) missing in st.secrets!")
            st.info("Ensure secrets are added via Streamlit Cloud dashboard if deployed, or in local `.streamlit/secrets.toml`.")
            return None
        db_secrets = st.secrets["database"]
        required_keys = ["engine", "user", "password", "host", "port", "dbname"]
        if not all(key in db_secrets for key in required_keys):
            st.error("Database secrets are missing required keys (engine, user, password, host, port, dbname).")
            return None
        db_url = (
            f"{db_secrets['engine']}://"
            f"{db_secrets['user']}:{db_secrets['password']}"
            f"@{db_secrets['host']}:{db_secrets['port']}"
            f"/{db_secrets['dbname']}"
        )
        engine = create_engine(db_url, pool_pre_ping=True)
        # Test connection
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except OperationalError as oe:
            st.error(f"Database connection failed. Check credentials/network in secrets. Error: {oe}")
            return None
        except Exception as test_e:
            st.error(f"Database connection test failed: {test_e}")
            return None
        return engine
    except OperationalError as e:
        st.error(f"Database engine creation failed: Check secrets format/values. Error: {e}")
        return None
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        st.exception(e)
        return None

# --- Database Interaction Functions ---

@st.cache_data(ttl=600) # Cache item list for 10 minutes
def get_all_items(_engine) -> pd.DataFrame:
    """
    Fetches all active items from the 'items' table.
    Takes the SQLAlchemy engine as input (prefixed with _ for caching).
    Returns a pandas DataFrame.
    """
    if not _engine:
        st.error("Database connection not available for fetching items.")
        return pd.DataFrame()

    query = text("""
        SELECT
            item_id, name, unit, category, sub_category,
            permitted_departments, reorder_point, current_stock, notes
        FROM items
        WHERE is_active = TRUE
        ORDER BY category, sub_category, name;
    """)

    try:
        with _engine.connect() as connection:
            df = pd.read_sql(query, connection)
            for col in ['reorder_point', 'current_stock']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
    except ProgrammingError as e:
        st.error(f"Database query failed. Does the 'items' table exist? Error: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to fetch items from database: {e}")
        st.exception(e)
        return pd.DataFrame()

# Function to get details for a SINGLE item
def get_item_details(engine, item_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a specific item_id."""
    if not engine or item_id is None:
        return None
    query = text("SELECT * FROM items WHERE item_id = :id")
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"id": item_id})
            row = result.fetchone()
            if row:
                return row._mapping # Use ._mapping for compatibility
            else:
                return None
    except Exception as e:
        st.error(f"Failed to fetch details for item ID {item_id}: {e}")
        return None

# Function to add a new item
def add_new_item(engine, item_details: Dict[str, Any]) -> bool:
    """Inserts a new item into the 'items' table."""
    if not engine: return False
    insert_query = text("""
        INSERT INTO items (name, unit, category, sub_category, permitted_departments, reorder_point, notes)
        VALUES (:name, :unit, :category, :sub_category, :permitted_departments, :reorder_point, :notes)
    """)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(insert_query, item_details)
        return True
    except IntegrityError as e:
        st.error(f"Failed to add item: Likely duplicate item name. Error: {e}")
        return False
    except Exception as e:
        st.error(f"Failed to add item to database: {e}")
        st.exception(e)
        return False

# Function to update an existing item
def update_item_details(engine, item_id: int, updated_details: Dict[str, Any]) -> bool:
    """Updates an existing item in the 'items' table."""
    if not engine or item_id is None:
        return False
    update_parts = []
    params = {"item_id": item_id}
    for key, value in updated_details.items():
        if key in ['name', 'unit', 'category', 'sub_category', 'permitted_departments', 'reorder_point', 'notes']:
             update_parts.append(f"{key} = :{key}")
             params[key] = value
    if not update_parts:
        st.warning("No changes detected to update.")
        return False
    update_query = text(f"""
        UPDATE items
        SET {', '.join(update_parts)}
        WHERE item_id = :item_id
    """)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(update_query, params)
        return True
    except IntegrityError as e:
        st.error(f"Failed to update item {item_id}: Likely duplicate item name introduced. Error: {e}")
        return False
    except Exception as e:
        st.error(f"Failed to update item {item_id} in database: {e}")
        st.exception(e)
        return False

# --- Initialize Session State ---
if 'item_to_edit_id' not in st.session_state:
    st.session_state.item_to_edit_id = None
if 'edit_form_values' not in st.session_state:
    st.session_state.edit_form_values = None

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
        st.info("No active items found in the database or table structure might be incorrect.")
    else:
        st.dataframe(
            items_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "item_id": st.column_config.NumberColumn("ID", width="small", help="Unique database ID"),
                "name": st.column_config.TextColumn("Item Name", width="medium"),
                "unit": st.column_config.TextColumn("Unit", width="small"),
                "category": st.column_config.TextColumn("Category"),
                "sub_category": st.column_config.TextColumn("Sub-Category"),
                "permitted_departments": st.column_config.TextColumn("Permitted Depts", width="medium"),
                "reorder_point": st.column_config.NumberColumn("Reorder Lvl", width="small", format="%d"),
                "current_stock": st.column_config.NumberColumn("Stock Qty", width="small"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
            },
            column_order=[
                "item_id", "name", "category", "sub_category", "unit",
                "current_stock", "reorder_point", "permitted_departments",
                "notes"
            ]
        )
    st.divider()

    # --- Add New Item Form ---
    with st.expander("➕ Add New Item"):
        with st.form("new_item_form", clear_on_submit=True):
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
                if not new_name:
                    st.warning("Item Name is required.")
                else:
                    item_data = {
                        "name": new_name.strip(),
                        "unit": new_unit.strip() if new_unit else None,
                        "category": new_category.strip() if new_category else "Uncategorized",
                        "sub_category": new_sub_category.strip() if new_sub_category else "General",
                        "permitted_departments": new_permitted_departments.strip() if new_permitted_departments else None,
                        "reorder_point": new_reorder_point,
                        "notes": new_notes.strip() if new_notes else None
                    }
                    success = add_new_item(db_engine, item_data)
                    if success:
                        st.success(f"Item '{new_name}' added successfully!")
                        get_all_items.clear()
                        st.rerun()

    st.divider()

    # --- Edit Existing Item Section ---
    st.subheader("✏️ Edit Existing Item")

    if not items_df.empty and 'item_id' in items_df.columns and 'name' in items_df.columns:
        item_options: List[Tuple[str, int]] = [
            (row['name'], row['item_id'])
            for index, row in items_df.dropna(subset=['name']).iterrows()
        ]
        item_options.sort()
    else:
        item_options = []

    edit_options = [("", None)] + item_options

    def load_item_for_edit():
        selected_option = st.session_state.item_to_edit_select
        if selected_option and selected_option[1] is not None:
            item_id_to_load = selected_option[1]
            details = get_item_details(db_engine, item_id_to_load)
            if details:
                st.session_state.item_to_edit_id = item_id_to_load
                st.session_state.edit_form_values = details
            else:
                st.warning(f"Could not load details for selected item ID: {item_id_to_load}")
                st.session_state.item_to_edit_id = None
                st.session_state.edit_form_values = None
        else:
            st.session_state.item_to_edit_id = None
            st.session_state.edit_form_values = None

    # Calculate index for selectbox based on current state
    current_edit_id = st.session_state.get('item_to_edit_id')
    try:
        current_index = 0
        if current_edit_id is not None:
            current_index = [i for i, opt in enumerate(edit_options) if opt[1] == current_edit_id][0]
    except IndexError:
        current_index = 0 # Default to blank if ID not found in options (e.g., after deletion)


    selected_item_tuple = st.selectbox(
        "Select Item to Edit:",
        options=edit_options,
        format_func=lambda x: x[0] if isinstance(x, tuple) and x[0] else "--- Select ---",
        key="item_to_edit_select",
        on_change=load_item_for_edit,
        index=current_index # Set index based on state
    )

    if st.session_state.item_to_edit_id is not None and st.session_state.edit_form_values is not None:
        current_details = st.session_state.edit_form_values
        with st.form("edit_item_form"):
            st.subheader(f"Editing Item: {current_details.get('name', '')} (ID: {st.session_state.item_to_edit_id})")
            edit_name = st.text_input("Item Name*", value=current_details.get('name', ''), key="edit_name")
            edit_unit = st.text_input("Unit", value=current_details.get('unit', ''), key="edit_unit")
            edit_category = st.text_input("Category", value=current_details.get('category', ''), key="edit_category")
            edit_sub_category = st.text_input("Sub-Category", value=current_details.get('sub_category', ''), key="edit_sub_category")
            edit_permitted_departments = st.text_input("Permitted Departments", value=current_details.get('permitted_departments', ''), key="edit_permitted_departments")
            # Ensure value passed to number_input is a number, default to 0 if None/invalid
            reorder_val = current_details.get('reorder_point', 0)
            edit_reorder_point = st.number_input("Reorder Point", min_value=0, value=int(reorder_val) if pd.notna(reorder_val) else 0, step=1, key="edit_reorder_point")
            edit_notes = st.text_area("Notes", value=current_details.get('notes', ''), key="edit_notes")
            update_submitted = st.form_submit_button("Update Item Details")

            if update_submitted:
                if not edit_name:
                    st.warning("Item Name cannot be empty.")
                else:
                    updated_data = {
                        "name": st.session_state.edit_name.strip(),
                        "unit": st.session_state.edit_unit.strip() if st.session_state.edit_unit else None,
                        "category": st.session_state.edit_category.strip() if st.session_state.edit_category else "Uncategorized",
                        "sub_category": st.session_state.edit_sub_category.strip() if st.session_state.edit_sub_category else "General",
                        "permitted_departments": st.session_state.edit_permitted_departments.strip() if st.session_state.edit_permitted_departments else None,
                        "reorder_point": st.session_state.edit_reorder_point,
                        "notes": st.session_state.edit_notes.strip() if st.session_state.edit_notes else None
                    }
                    update_success = update_item_details(db_engine, st.session_state.item_to_edit_id, updated_data)
                    if update_success:
                        st.success(f"Item '{st.session_state.edit_name}' updated successfully!")
                        get_all_items.clear()
                        # Reset edit state to hide form and clear selection
                        st.session_state.item_to_edit_id = None
                        st.session_state.edit_form_values = None
                        # *** FIXED: Removed direct state modification for selectbox key ***
                        # st.session_state.item_to_edit_select = ("", None)
                        st.rerun()

