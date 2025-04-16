import streamlit as st
from sqlalchemy import create_engine, text # For database connection and executing SQL
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError # For catching DB errors
import pandas as pd # For handling data in DataFrames
from typing import Any, Optional, Dict # For type hinting

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

# Cache item list for 10 minutes
# *** FIXED: Added underscore to engine parameter name to prevent hashing error ***
@st.cache_data(ttl=600)
def get_all_items(_engine) -> pd.DataFrame:
    """
    Fetches all active items from the 'items' table.
    Takes the SQLAlchemy engine as input (prefixed with _ for caching).
    Returns a pandas DataFrame.
    """
    # Use the parameter name with underscore internally
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
        # Use the parameter name with underscore internally
        with _engine.connect() as connection:
            df = pd.read_sql(query, connection)
            # Ensure numeric columns are numeric, handle potential errors
            for col in ['reorder_point', 'current_stock']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
    except ProgrammingError as e:
        st.error(f"Database query failed. Does the 'items' table exist with the correct columns? Error: {e}")
        st.info("Ensure you have run the CREATE TABLE commands for the 'items' table in your database.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to fetch items from database: {e}")
        st.exception(e)
        return pd.DataFrame()

# Function to add a new item
def add_new_item(engine, item_details: Dict[str, Any]) -> bool:
    """
    Inserts a new item into the 'items' table.
    Takes the SQLAlchemy engine and a dictionary of item details.
    Returns True on success, False on failure.
    """
    if not engine:
        st.error("Database connection not available for adding item.")
        return False

    insert_query = text("""
        INSERT INTO items (name, unit, category, sub_category, permitted_departments, reorder_point, notes)
        VALUES (:name, :unit, :category, :sub_category, :permitted_departments, :reorder_point, :notes)
    """)

    try:
        with engine.connect() as connection:
            with connection.begin(): # Start transaction
                connection.execute(insert_query, item_details)
        return True # Success
    except IntegrityError as e:
        st.error(f"Failed to add item: Likely duplicate item name. Error: {e}")
        return False
    except Exception as e:
        st.error(f"Failed to add item to database: {e}")
        st.exception(e)
        return False

# --- Main App Logic ---

st.set_page_config(page_title="Boteco Item Manager", layout="wide")
st.title("Boteco Item Manager 🛒")
st.write("Manage inventory items stored in the database.")

db_engine = connect_db()

if not db_engine:
    st.info("Please ensure database credentials in Streamlit secrets are correct and the database is accessible.")
    st.stop()
else:
    # --- Display Items ---
    st.subheader("Current Active Items")
    # *** Call function normally, without underscore ***
    items_df = get_all_items(db_engine)

    if items_df.empty:
        st.info("No active items found in the database.")
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
                    # Pass engine normally when calling add_new_item
                    success = add_new_item(db_engine, item_data)
                    if success:
                        st.success(f"Item '{new_name}' added successfully!")
                        get_all_items.clear() # Clear cache
                        st.rerun() # Rerun to update table

    st.divider()
    # --- Placeholder for Edit Item ---
    st.subheader("Edit Item (Coming Soon)")
    st.write("Functionality to edit existing items will be added here.")
