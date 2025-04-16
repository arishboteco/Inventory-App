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
        # Check if database secrets exist in st.secrets
        if "database" not in st.secrets:
            st.error("Database configuration (`[database]`) missing in st.secrets!")
            st.info("Ensure secrets are added via Streamlit Cloud dashboard if deployed, or in local `.streamlit/secrets.toml`.")
            return None

        db_secrets = st.secrets["database"]

        # Validate that required keys are present in the secrets
        required_keys = ["engine", "user", "password", "host", "port", "dbname"]
        if not all(key in db_secrets for key in required_keys):
            st.error("Database secrets are missing required keys (engine, user, password, host, port, dbname).")
            return None

        # Construct the database connection URL (DSN - Data Source Name)
        db_url = (
            f"{db_secrets['engine']}://"
            f"{db_secrets['user']}:{db_secrets['password']}"
            f"@{db_secrets['host']}:{db_secrets['port']}"
            f"/{db_secrets['dbname']}"
        )

        # Create the SQLAlchemy engine.
        engine = create_engine(db_url, pool_pre_ping=True)

        # --- Test connection immediately ---
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1")) # Simple query to test connection
            # st.toast("Database connection successful!", icon="✅") # Optional: Can be noisy
        except OperationalError as oe:
            st.error(f"Database connection failed. Check credentials/network in secrets. Error: {oe}")
            return None
        except Exception as test_e:
            st.error(f"Database connection test failed: {test_e}")
            return None
        # --- End Connection Test ---

        return engine # Return the engine object if successful

    except OperationalError as e:
        st.error(f"Database engine creation failed: Check secrets format/values. Error: {e}")
        return None
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        st.exception(e)
        return None

# --- Database Interaction Functions ---

# Add cache decorator if fetching items is slow or done frequently without changes
# @st.cache_data(ttl=600) # Cache for 10 minutes, for example
def get_all_items(engine) -> pd.DataFrame:
    """
    Fetches all active items from the 'items' table.
    Takes the SQLAlchemy engine as input.
    Returns a pandas DataFrame.
    """
    if not engine:
        st.error("Database connection not available for fetching items.")
        return pd.DataFrame() # Return empty DataFrame if no engine

    # SQL query to select relevant columns from active items, ordered nicely
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
        # Use a connection from the engine
        with engine.connect() as connection:
            # Execute the query and read results directly into pandas DataFrame
            df = pd.read_sql(query, connection)
            return df
    except ProgrammingError as e:
        # Catch errors like the table not existing (e.g., after schema change)
        st.error(f"Database query failed. Does the 'items' table exist with the correct columns? Error: {e}")
        st.info("Ensure you have run the CREATE TABLE commands for the 'items' table in your database.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to fetch items from database: {e}")
        st.exception(e) # Log full traceback for debugging
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
    st.info("Please ensure database credentials in Streamlit secrets are correct and the database is accessible.")
    st.stop()
else:
    # --- Display Items ---
    st.subheader("Current Active Items")

    # Fetch the items from the database
    items_df = get_all_items(db_engine)

    # Check if any items were returned
    if items_df.empty:
        st.info("No active items found in the database, or failed to load items.")
        st.write("Use the 'Add Item' section below (coming soon!) or ensure the 'items' table exists and contains data.")
    else:
        # Display the DataFrame with configurations for better readability
        st.dataframe(
            items_df,
            use_container_width=True, # Make table use full width
            hide_index=True, # Don't show the default pandas index
            column_config={ # Customize column display
                "item_id": st.column_config.NumberColumn("ID", width="small", help="Unique database ID for the item"),
                "name": st.column_config.TextColumn("Item Name", width="medium", help="Name of the inventory item"),
                "unit": st.column_config.TextColumn("Unit", width="small"),
                "category": st.column_config.TextColumn("Category"),
                "sub_category": st.column_config.TextColumn("Sub-Category"),
                "permitted_departments": st.column_config.TextColumn("Permitted Depts", width="medium", help="Departments allowed to request this item (comma-separated or All)"),
                "reorder_point": st.column_config.NumberColumn("Reorder Lvl", width="small", help="Stock level that triggers reordering"),
                "current_stock": st.column_config.NumberColumn("Stock Qty", width="small", help="Calculated or last known stock quantity"),
                "is_active": None, # Hide the is_active column as we only show active items
                "notes": st.column_config.TextColumn("Notes", width="large"),
            },
            # Define the order columns should appear in
            column_order=[
                "item_id", "name", "category", "sub_category", "unit",
                "current_stock", "reorder_point", "permitted_departments",
                "notes" # is_active is hidden by setting config to None
            ]
        )

    st.divider()

    # --- Placeholder for Add/Edit Forms ---
    st.subheader("Add / Edit Item (Coming Soon)")
    st.write("Functionality to add new items or edit existing ones will be added here.")
