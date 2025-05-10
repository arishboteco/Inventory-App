# pages/4_History_Reports.py

import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta

# Import shared functions and engine from the main app file
try:
    from app.item_manager_app import (
        connect_db,
        get_stock_transactions,     # Receives _engine fix in definition
        get_all_items_with_stock,   # Receives _engine fix in definition
        # Import transaction type constants if needed for filtering UI later
        # TX_RECEIVING, TX_ADJUSTMENT, TX_WASTAGE, TX_INDENT_FULFILL, TX_SALE
    )
except ImportError as e:
    st.error(f"Import error from item_manager_app.py: {e}. Ensure it's in the parent directory.")
    st.stop()
except Exception as e:
    st.error(f"Unexpected error during import: {e}")
    st.stop()

# --- Page Content ---
st.set_page_config(layout="wide")
st.header("📜 History & Reports")

# Establish DB connection for this page
db_engine = connect_db() # Keep original name for connection variable
if not db_engine:
    st.error("Database connection failed on this page.")
    st.stop()

# --- Stock Transaction History Section ---
st.subheader("Stock Transaction History")

# --- Filters ---
st.write("Apply filters to narrow down the transaction history:")

# Fetch item list for filter dropdown (include inactive items for history)
@st.cache_data(ttl=120)
def fetch_all_items_for_filter(_engine): # Definition uses _engine
    # Pass _engine to the backend function which now expects _engine
    items_df = get_all_items_with_stock(_engine, include_inactive=True)
    if not items_df.empty and 'item_id' in items_df.columns and 'name' in items_df.columns and 'is_active' in items_df.columns:
        # Create list of tuples: (display_name, item_id)
        item_options_list: List[Tuple[str, int]] = [
            # Handle potential missing 'unit' gracefully
            (f"{row['name']} ({row.get('unit', 'N/A')}){' [Inactive]' if not row['is_active'] else ''}", row['item_id'])
            for index, row in items_df.dropna(subset=['name']).iterrows() # Ensure name is not NaN
        ]
        # Add an "All Items" option
        return [("All Items", -1)] + sorted(item_options_list, key=lambda x: x[0])
    return [("All Items", -1)]

# Pass original 'db_engine' variable here; fetch_all_items_for_filter receives it as _engine
all_item_filter_options = fetch_all_items_for_filter(db_engine)

# Transaction Types Filter Options (Add this if you want the filter)
# transaction_types = [
#     "All Types", TX_RECEIVING, TX_ADJUSTMENT, TX_WASTAGE, TX_INDENT_FULFILL, TX_SALE
# ]

filt_col1, filt_col2, filt_col3 = st.columns(3) # Adjusted column ratios

with filt_col1:
    selected_item_tuple = st.selectbox(
        "Filter by Item",
        options=all_item_filter_options,
        format_func=lambda x: x[0], # Show only name
        key="hist_item_filter",
        index=0 # Default to "All Items"
    )
    filter_item_id = selected_item_tuple[1] if selected_item_tuple and selected_item_tuple[1] != -1 else None

    # Optional Filters (Uncomment if needed and add to get_stock_transactions call)
    # filter_user_id = st.text_input("Filter by User (contains)", key="hist_user_filter")
    # filter_related_mrn = st.text_input("Filter by Related MRN (contains)", key="hist_mrn_filter")


with filt_col2:
    # Optional Filter (Uncomment if needed and add to get_stock_transactions call)
    # filter_trans_type = st.selectbox(
    #     "Filter by Transaction Type",
    #     options=transaction_types,
    #     key="hist_type_filter",
    #     index=0 # Default to "All Types"
    # )
    # filter_trans_type = filter_trans_type if filter_trans_type != "All Types" else None
    pass # Placeholder if no filter widget here

with filt_col3:
    # Use separate date inputs
    today = datetime.now().date()
    default_start = today - timedelta(days=30) # Default to last 30 days
    filter_start_date = st.date_input("Start Date", value=default_start, key="hist_start_date")
    filter_end_date = st.date_input("End Date", value=today, key="hist_end_date")

    # Basic validation for date range
    if filter_start_date and filter_end_date and filter_start_date > filter_end_date:
        st.warning("Start date cannot be after end date.")
        filter_start_date = None # Effectively disable filtering if range is invalid
        filter_end_date = None

# --- Fetch Data based on Filters ---
st.divider()

# Correct the call: Pass db_engine positionally as the first argument
# Include all filters defined above
transactions_df = get_stock_transactions(
    db_engine,  # <-- CORRECTED CALL (positional argument)
    item_id=filter_item_id,
    start_date=filter_start_date,
    end_date=filter_end_date
    # Add other filters here if you uncommented them above:
    # transaction_type=filter_trans_type,
    # user_id=filter_user_id.strip() if filter_user_id else None,
    # related_mrn=filter_related_mrn.strip() if filter_related_mrn else None
)

# --- Display Results ---
if transactions_df.empty:
    st.info("No stock transactions found matching the selected filters.")
else:
    st.success(f"Found {len(transactions_df)} transaction(s).")

    # Define expected columns for display order and config
    expected_columns = [
        "transaction_date", "item_name", "transaction_type", "quantity_change",
        "user_id", "related_mrn", "related_po_id", "notes"
    ]
    # Filter out columns not present in the dataframe
    display_columns = [col for col in expected_columns if col in transactions_df.columns]

    st.dataframe(
        transactions_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "transaction_id": None, # Hide internal ID if present
            "item_id": None, # Hide internal ID if present
            "transaction_date": st.column_config.TextColumn("Timestamp", width="medium"),
            "item_name": st.column_config.TextColumn("Item Name", width="large"),
            "transaction_type": st.column_config.TextColumn("Type", width="small"),
            "quantity_change": st.column_config.NumberColumn("Qty Change", format="%.2f", width="small"),
            "user_id": st.column_config.TextColumn("User", width="small"),
            "notes": st.column_config.TextColumn("Notes", width="large"),
            "related_mrn": st.column_config.TextColumn("Related MRN", width="medium"),
            "related_po_id": st.column_config.TextColumn("Related PO", width="medium"),
        },
         column_order=display_columns # Use columns actually present
    )

# --- Placeholder for other reports ---
# st.divider()
# st.subheader("Other Reports")