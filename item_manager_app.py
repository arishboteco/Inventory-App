import streamlit as st
from sqlalchemy import create_engine, text # For database connection and executing SQL
from sqlalchemy.exc import OperationalError, ProgrammingError # For catching DB errors
import pandas as pd # For handling data in DataFrames
from typing import Any, Optional # For type hinting

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
            st.info("Ensure secrets are added via Streamlit Cloud dashboard if deployed.")
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

def get_all_items(engine) -> pd.DataFrame:
    """
    Fetches all active items from the 'items' table.
    Returns a pandas DataFrame.
    """
    if not engine:
        st.error("Database connection not available for fetching items.")
        return pd.DataFrame() # Return empty DataFrame if no engine

    query = text("""
        SELECT
            item_id,
            name,
            unit,
            category,
            sub_category,
            permitted_departments,
            reorder_point,
            current_stock,
            is_active,
            notes
        FROM items
        WHERE is_active = TRUE
        ORDER BY category, sub_category, name;
    """)
    try:
        with engine.connect() as connection:
            # Use pandas read_sql for convenience
            df = pd.read_sql(query, connection)
            return df
    except ProgrammingError as e:
        # Catch errors like table not existing
        st.error(f"Database query failed. Does the 'items' table exist with the correct columns? Error: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to fetch items from database: {e}")
        st.exception(e)
        return pd.DataFrame()

# --- Main App Logic ---

# Set page title and layout
st.set_page_config(page_title="Boteco Item Manager", layout="wide")

st.title("Boteco Item Manager 🛒")
st.write("Manage inventory items stored in the database.")

# --- Attempt to Connect to Database ---
db_engine = connect_db()

# Stop the app if the database connection could not be established
if not db_engine:
    st.info("Please ensure database credentials in `.streamlit/secrets.toml` (locally) or Streamlit Cloud secrets (deployed) are correct and the database is accessible.")
    st.stop()
else:
    # --- Display Items ---
    st.subheader("Current Active Items")

    items_df = get_all_items(db_engine) # Fetch items using the engine

    if items_df.empty:
        st.info("No active items found in the database, or failed to load items.")
        st.write("Use the 'Add Item' section below (coming soon!) or ensure the 'items' table exists and contains data.")
    else:
        # Display the DataFrame with configurations for better readability
        st.dataframe(
            items_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "item_id": st.column_config.NumberColumn("ID", width="small"),
                "name": st.column_config.TextColumn("Item Name", width="medium"),
                "unit": st.column_config.TextColumn("Unit", width="small"),
                "category": st.column_config.TextColumn("Category"),
                "sub_category": st.column_config.TextColumn("Sub-Category"),
                "permitted_departments": st.column_config.TextColumn("Permitted Depts", width="medium"),
                "reorder_point": st.column_config.NumberColumn("Reorder Lvl", width="small"),
                "current_stock": st.column_config.NumberColumn("Stock Qty", width="small"),
                "is_active": st.column_config.CheckboxColumn("Active?", width="small"), # Should always be True here
                "notes": st.column_config.TextColumn("Notes", width="large"),
            },
            # Define column order explicitly if needed
            column_order=[
                "item_id", "name", "category", "sub_category", "unit",
                "current_stock", "reorder_point", "permitted_departments",
                "is_active", "notes"
            ]
        )

    st.divider()

    # --- Placeholder for Add/Edit Forms ---
    st.subheader("Add / Edit Item (Coming Soon)")
    st.write("Functionality to add new items or edit existing ones will be added here.")

    # Example structure for adding later:
    # with st.expander("Add New Item"):
    #     with st.form("new_item_form"):
    #         # Input fields for name, unit, category etc.
    #         submitted = st.form_submit_button("Save New Item")
    #         if submitted:
    #             # Call backend function to INSERT into database
    #             pass

    # Example structure for editing later:
    # selected_item_id = st.selectbox("Select Item ID to Edit:", options=[""] + items_df['item_id'].tolist())
    # if selected_item_id:
    #    with st.form("edit_item_form"):
    #       # Populate fields with selected item's data
    #       # Allow editing
    #       update_submitted = st.form_submit_button("Update Item")
    #       if update_submitted:
    #            # Call backend function to UPDATE database
    #            pass
