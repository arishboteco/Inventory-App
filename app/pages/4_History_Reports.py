# app/pages/4_History_Reports.py

import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple # Ensure all necessary typing imports
from datetime import datetime, date, timedelta # Ensure all necessary datetime imports

# Import shared functions
try:
    # Import connect_db from its new location
    from app.db.database_utils import connect_db
    # Functions still temporarily in app.item_manager_app
    from app.item_manager_app import (
        get_stock_transactions,
        get_all_items_with_stock,
        # No constants from app.core.constants appear to be directly imported here
        # TX_RECEIVING, TX_ADJUSTMENT, etc. were commented out in your original file's import for this page
    )
except ImportError as e:
    st.error(f"Import error in 4_History_Reports.py: {e}. Ensure 'INVENTORY-APP' is the root for 'streamlit run app/item_manager_app.py'.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 4_History_Reports.py: {e}")
    st.stop()

# --- Page Content ---
# st.set_page_config(layout="wide") # Ideally called only once in the main app script
st.header("📜 History & Reports")

db_engine = connect_db() # Uses imported connect_db
if not db_engine:
    st.error("Database connection failed on this page.")
    st.stop()

# --- Stock Transaction History Section ---
st.subheader("Stock Transaction History")

st.write("Apply filters to narrow down the transaction history:")

@st.cache_data(ttl=120)
def fetch_all_items_for_filter(_engine):
    # Calls get_all_items_with_stock (imported from app.item_manager_app)
    items_df = get_all_items_with_stock(_engine, include_inactive=True)
    if not items_df.empty and 'item_id' in items_df.columns and 'name' in items_df.columns and 'is_active' in items_df.columns:
        item_options_list: List[Tuple[str, int]] = [
            (f"{row['name']} ({row.get('unit', 'N/A')}){' [Inactive]' if not row['is_active'] else ''}", row['item_id'])
            for index, row in items_df.dropna(subset=['name']).iterrows()
        ]
        return [("All Items", -1)] + sorted(item_options_list, key=lambda x: x[0])
    return [("All Items", -1)]

all_item_filter_options = fetch_all_items_for_filter(db_engine)

# Transaction Types Filter Options (If you re-enable this, ensure constants are imported from app.core.constants)
# from app.core.constants import TX_RECEIVING, TX_ADJUSTMENT, TX_WASTAGE, TX_INDENT_FULFILL, TX_SALE
# transaction_types_for_filter = [
#     "All Types", TX_RECEIVING, TX_ADJUSTMENT, TX_WASTAGE, TX_INDENT_FULFILL, TX_SALE
# ]

filt_col1, filt_col2, filt_col3 = st.columns(3)

with filt_col1:
    selected_item_tuple = st.selectbox(
        "Filter by Item",
        options=all_item_filter_options,
        format_func=lambda x: x[0],
        key="hist_item_filter",
        index=0
    )
    filter_item_id = selected_item_tuple[1] if selected_item_tuple and selected_item_tuple[1] != -1 else None
    # filter_user_id = st.text_input("Filter by User (contains)", key="hist_user_filter") # Example
    # filter_related_mrn = st.text_input("Filter by Related MRN (contains)", key="hist_mrn_filter") # Example

with filt_col2:
    # filter_trans_type_selected = st.selectbox( # Example if re-enabled
    #     "Filter by Transaction Type",
    #     options=transaction_types_for_filter, # Requires import of constants
    #     key="hist_type_filter",
    #     index=0
    # )
    # filter_trans_type = filter_trans_type_selected if filter_trans_type_selected != "All Types" else None
    pass

with filt_col3:
    today = datetime.now().date()
    default_start = today - timedelta(days=30)
    filter_start_date = st.date_input("Start Date", value=default_start, key="hist_start_date")
    filter_end_date = st.date_input("End Date", value=today, key="hist_end_date")

    if filter_start_date and filter_end_date and filter_start_date > filter_end_date:
        st.warning("Start date cannot be after end date.")
        filter_start_date = None
        filter_end_date = None

st.divider()

# Calls get_stock_transactions (imported from app.item_manager_app)
transactions_df = get_stock_transactions(
    db_engine,
    item_id=filter_item_id,
    start_date=filter_start_date,
    end_date=filter_end_date
    # transaction_type=filter_trans_type, # Add if filter is enabled
    # user_id=filter_user_id.strip() if filter_user_id else None, # Add if filter is enabled
    # related_mrn=filter_related_mrn.strip() if filter_related_mrn else None # Add if filter is enabled
)

if transactions_df.empty:
    st.info("No stock transactions found matching the selected filters.")
else:
    st.success(f"Found {len(transactions_df)} transaction(s).")
    expected_columns = [
        "transaction_date", "item_name", "transaction_type", "quantity_change",
        "user_id", "related_mrn", "related_po_id", "notes"
    ]
    display_columns = [col for col in expected_columns if col in transactions_df.columns]

    st.dataframe(
        transactions_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "transaction_id": None,
            "item_id": None,
            "transaction_date": st.column_config.TextColumn("Timestamp", width="medium"),
            "item_name": st.column_config.TextColumn("Item Name", width="large"),
            "transaction_type": st.column_config.TextColumn("Type", width="small"),
            "quantity_change": st.column_config.NumberColumn("Qty Change", format="%.2f", width="small"),
            "user_id": st.column_config.TextColumn("User", width="small"),
            "notes": st.column_config.TextColumn("Notes", width="large"),
            "related_mrn": st.column_config.TextColumn("Related MRN", width="medium"),
            "related_po_id": st.column_config.TextColumn("Related PO", width="medium"),
        },
         column_order=display_columns
    )

# st.divider()
# st.subheader("Other Reports") # Placeholder for future