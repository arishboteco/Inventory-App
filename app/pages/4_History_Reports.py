# app/pages/4_History_Reports.py
import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta

try:
    from app.db.database_utils import connect_db
    from app.services import item_service # For get_all_items_with_stock (used in item filter)
    from app.services import stock_service # For get_stock_transactions
    # from app.core.constants import TX_RECEIVING, TX_ADJUSTMENT, TX_WASTAGE, TX_INDENT_FULFILL, TX_SALE # If filter re-enabled
except ImportError as e:
    st.error(f"Import error in 4_History_Reports.py: {e}.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 4_History_Reports.py: {e}")
    st.stop()

st.header("📜 History & Reports")
db_engine = connect_db()
if not db_engine: st.error("Database connection failed."); st.stop()

st.subheader("Stock Transaction History")
st.write("Apply filters to narrow down the transaction history:")

@st.cache_data(ttl=120)
def fetch_all_items_for_filter(_engine): # This helper uses item_service
    items_df = item_service.get_all_items_with_stock(_engine, include_inactive=True)
    if not items_df.empty:
        item_options_list = [(f"{r['name']} ({r.get('unit','N/A')}){' [Inactive]' if not r['is_active'] else ''}", r['item_id'])
                             for _, r in items_df.dropna(subset=['name']).iterrows()]
        return [("All Items", -1)] + sorted(item_options_list, key=lambda x: x[0])
    return [("All Items", -1)]

all_item_filter_options = fetch_all_items_for_filter(db_engine)

filt_col1, filt_col2, filt_col3 = st.columns(3)
with filt_col1:
    selected_item_tuple = st.selectbox("Filter by Item", options=all_item_filter_options, format_func=lambda x: x[0], key="hist_item_filter", index=0)
    filter_item_id = selected_item_tuple[1] if selected_item_tuple and selected_item_tuple[1] != -1 else None
with filt_col3: # Date filters
    today = datetime.now().date()
    default_start = today - timedelta(days=30)
    filter_start_date = st.date_input("Start Date", value=default_start, key="hist_start_date")
    filter_end_date = st.date_input("End Date", value=today, key="hist_end_date")
    if filter_start_date and filter_end_date and filter_start_date > filter_end_date:
        st.warning("Start date cannot be after end date."); filter_start_date = None; filter_end_date = None

st.divider()
# Use stock_service to get transactions
transactions_df = stock_service.get_stock_transactions(
    db_engine, item_id=filter_item_id, start_date=filter_start_date, end_date=filter_end_date
)

if transactions_df.empty:
    st.info("No stock transactions found matching filters.")
else:
    st.success(f"Found {len(transactions_df)} transaction(s).")
    expected_columns = ["transaction_date", "item_name", "transaction_type", "quantity_change", "user_id", "related_mrn", "related_po_id", "notes"]
    display_columns = [col for col in expected_columns if col in transactions_df.columns]
    st.dataframe(transactions_df, use_container_width=True, hide_index=True,
                 column_config={"transaction_id": None, "item_id": None,
                                "transaction_date": st.column_config.TextColumn("Timestamp", width="medium"),
                                "item_name": st.column_config.TextColumn("Item Name", width="large"),
                                "transaction_type": st.column_config.TextColumn("Type", width="small"),
                                "quantity_change": st.column_config.NumberColumn("Qty Change", format="%.2f", width="small"),
                                "user_id": st.column_config.TextColumn("User", width="small"),
                                "notes": st.column_config.TextColumn("Notes", width="large"),
                                "related_mrn": st.column_config.TextColumn("Related MRN", width="medium"),
                                "related_po_id": st.column_config.TextColumn("Related PO", width="medium")},
                 column_order=display_columns)