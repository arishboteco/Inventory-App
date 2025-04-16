import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta

# Import shared functions and engine from the main app file
try:
    from item_manager_app import (
        connect_db,
        get_stock_transactions,
        get_all_items_with_stock # Needed for item filter dropdown
    )
except ImportError:
    st.error("Could not import functions from item_manager_app.py. Ensure it's in the parent directory.")
    st.stop()

# --- Page Content ---
st.header("History & Reports")

# Establish DB connection for this page
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed on this page.")
    st.stop()
else:
    # --- Stock Transaction History Section ---
    st.subheader("📜 Stock Transaction History")

    # Fetch item list for filter dropdown
    # Note: We might want to show history for inactive items too, so fetch all?
    # Let's fetch all items (active/inactive) for the filter dropdown here.
    items_df_hist_page = get_all_items_with_stock(db_engine, include_inactive=True)
    if not items_df_hist_page.empty and 'item_id' in items_df_hist_page.columns and 'name' in items_df_hist_page.columns:
        hist_item_options_list: List[Tuple[str, int]] = [
            (f"{row['name']}{'' if row['is_active'] else ' (Inactive)'}", row['item_id'])
            for index, row in items_df_hist_page.dropna(subset=['name']).iterrows()
        ]
        hist_item_options_list.sort()
    else:
        hist_item_options_list = []

    # Filters for the history view
    hist_item_options = [("All Items", None)] + hist_item_options_list
    col_hist1, col_hist2, col_hist3 = st.columns([2,1,1])
    with col_hist1:
        hist_selected_item = st.selectbox("Filter by Item:", options=hist_item_options, format_func=lambda x: x[0], key="hist_item_select")
    with col_hist2:
        hist_start_date = st.date_input("From Date", value=None, key="hist_start_date", format="YYYY-MM-DD") # Use standard format
    with col_hist3:
        hist_end_date = st.date_input("To Date", value=None, key="hist_end_date", format="YYYY-MM-DD") # Use standard format

    # Fetch filtered transaction data
    hist_item_id = hist_selected_item[1] if hist_selected_item else None
    # Call imported function, pass engine with underscore for cache
    transactions_df = get_stock_transactions(
        _engine=db_engine,
        item_id=hist_item_id,
        start_date=st.session_state.hist_start_date,
        end_date=st.session_state.hist_end_date
    )

    # Display the transaction history table
    if transactions_df.empty:
        st.info("No stock transactions found matching the selected filters.")
    else:
        st.dataframe(
            transactions_df, use_container_width=True, hide_index=True,
            column_config={
                "transaction_date": st.column_config.TextColumn("Timestamp", width="small"),
                "item_name": st.column_config.TextColumn("Item Name", width="medium"),
                "transaction_type": st.column_config.TextColumn("Type", width="small"),
                "quantity_change": st.column_config.NumberColumn("Qty Change", format="%.2f", width="small"),
                "user_id": st.column_config.TextColumn("User", width="small"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
                "related_mrn": st.column_config.TextColumn("Related MRN", width="small"),
            },
             column_order=[ "transaction_date", "item_name", "transaction_type", "quantity_change", "user_id", "notes", "related_mrn" ]
        )

    # --- Placeholder for Low Stock Report (moved here) ---
    # We could move the low stock logic here as well
    # st.divider()
    # st.subheader("⚠️ Low Stock Items Report")
    # low_stock_df = ... (calculate based on get_all_items_with_stock) ...
    # st.dataframe(low_stock_df, ...)


