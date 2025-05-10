# app/pages/4_History_Reports.py
import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime, date, timedelta

try:
    from app.db.database_utils import connect_db
    from app.services import item_service
    from app.services import stock_service
    from app.core.constants import TX_RECEIVING, TX_ADJUSTMENT, TX_WASTAGE, TX_INDENT_FULFILL, TX_SALE
except ImportError as e:
    st.error(f"Import error in 4_History_Reports.py: {e}.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 4_History_Reports.py: {e}")
    st.stop()

st.header("📜 Stock Transaction History & Reports")
st.write("Review the detailed history of all stock movements. Use the filters below to narrow down your search.")
st.divider()

db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed. Cannot load history reports.")
    st.stop()

@st.cache_data(ttl=120)
def fetch_filter_options(_engine):
    items_df = item_service.get_all_items_with_stock(_engine, include_inactive=True)
    item_options = [("-- All Items --", -1)]
    if not items_df.empty:
        item_options.extend(
            sorted(
                [(f"{r['name']} ({r.get('unit','N/A')}){' [Inactive]' if not r['is_active'] else ''}", r['item_id'])
                 for _, r in items_df.dropna(subset=['name']).iterrows()],
                key=lambda x: x[0]
            )
        )
    transaction_type_options = {
        "-- All Types --": None, "Goods Received": TX_RECEIVING, "Stock Adjustments": TX_ADJUSTMENT,
        "Wastage/Spoilage": TX_WASTAGE, "Indent Fulfillment": TX_INDENT_FULFILL, "Sales (Future Use)": TX_SALE
    }
    return item_options, transaction_type_options

item_filter_options, transaction_type_filter_options_map = fetch_filter_options(db_engine)

if 'hist_filter_item_id' not in st.session_state: st.session_state.hist_filter_item_id = -1
if 'hist_filter_trans_type' not in st.session_state: st.session_state.hist_filter_trans_type = "-- All Types --"
if 'hist_filter_user_id' not in st.session_state: st.session_state.hist_filter_user_id = ""
if 'hist_filter_related_mrn' not in st.session_state: st.session_state.hist_filter_related_mrn = ""
if 'hist_filter_start_date' not in st.session_state: st.session_state.hist_filter_start_date = datetime.now().date() - timedelta(days=30)
if 'hist_filter_end_date' not in st.session_state: st.session_state.hist_filter_end_date = datetime.now().date()

st.subheader("🔎 Filter Transactions")
filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    selected_item_tuple_key = "hist_item_filter_select_v4_tuple" # Use a key for the selectbox itself
    if selected_item_tuple_key not in st.session_state: # Initialize if not present
         current_item_id_for_filter = st.session_state.hist_filter_item_id
         st.session_state[selected_item_tuple_key] = next((opt for opt in item_filter_options if opt[1] == current_item_id_for_filter), item_filter_options[0])

    selected_item_tuple = st.selectbox(
        "Filter by Item:", options=item_filter_options, format_func=lambda x: x[0],
        key=selected_item_tuple_key, help="Select a specific item."
    )
    st.session_state.hist_filter_item_id = selected_item_tuple[1] if selected_item_tuple else -1

    selected_trans_type_display_name = st.selectbox(
        "Filter by Transaction Type:", options=list(transaction_type_filter_options_map.keys()),
        index=list(transaction_type_filter_options_map.keys()).index(st.session_state.hist_filter_trans_type) if st.session_state.hist_filter_trans_type in transaction_type_filter_options_map else 0,
        key="hist_trans_type_select_v4", help="Select a transaction type."
    )
    st.session_state.hist_filter_trans_type = selected_trans_type_display_name
with filter_col2:
    st.session_state.hist_filter_start_date = st.date_input("Start Date:", value=st.session_state.hist_filter_start_date, key="hist_start_date_v4")
    st.session_state.hist_filter_end_date = st.date_input("End Date:", value=st.session_state.hist_filter_end_date, key="hist_end_date_v4")

with st.expander("More Filters (User, MRN)"):
    adv_filter_col1, adv_filter_col2 = st.columns(2)
    with adv_filter_col1:
        st.session_state.hist_filter_user_id = st.text_input("Filter by User ID (contains):", value=st.session_state.hist_filter_user_id, key="hist_user_filter_v4", placeholder="e.g., JohnD").strip()
    with adv_filter_col2:
        st.session_state.hist_filter_related_mrn = st.text_input("Filter by Related MRN (contains):", value=st.session_state.hist_filter_related_mrn, key="hist_mrn_filter_v4", placeholder="e.g., MRN-202505").strip()

if st.session_state.hist_filter_start_date and st.session_state.hist_filter_end_date and st.session_state.hist_filter_start_date > st.session_state.hist_filter_end_date:
    st.warning("Start date cannot be after end date.")

st.divider()
st.subheader("Transaction Records")

filter_item_id_arg = st.session_state.hist_filter_item_id if st.session_state.hist_filter_item_id != -1 else None
filter_trans_type_arg = transaction_type_filter_options_map[st.session_state.hist_filter_trans_type]
filter_user_id_arg = st.session_state.hist_filter_user_id if st.session_state.hist_filter_user_id else None
filter_related_mrn_arg = st.session_state.hist_filter_related_mrn if st.session_state.hist_filter_related_mrn else None

transactions_df = stock_service.get_stock_transactions(
    db_engine, item_id=filter_item_id_arg, transaction_type=filter_trans_type_arg,
    user_id=filter_user_id_arg, related_mrn=filter_related_mrn_arg,
    start_date=st.session_state.hist_filter_start_date, end_date=st.session_state.hist_filter_end_date
)

if transactions_df.empty:
    st.info("No stock transactions found matching the selected filters.")
else:
    st.success(f"Found {len(transactions_df)} transaction(s).")
    
    display_df = transactions_df.copy()
    if 'transaction_date' in display_df.columns:
        display_df['transaction_date'] = pd.to_datetime(display_df['transaction_date']).dt.strftime('%Y-%m-%d %H:%M:%S')

    # --- MEDIUM COMPLEXITY: Visual Cue for Quantity Change using Pandas Styler ---
    def style_quantity_change(val):
        color = 'black' # Default color for zero or non-numeric
        if pd.isna(val): return ''
        try:
            qty = float(val)
            if qty > 0: color = 'green'
            elif qty < 0: color = 'red'
        except ValueError:
            pass # Keep default color if not a number
        return f'color: {color}'

    def format_qty_with_emoji(qty_series):
        # This function will create a new series with emojis + text
        # It operates on the original 'quantity_change' column
        formatted_series = []
        for qty_val in qty_series:
            if pd.isna(qty_val):
                formatted_series.append("")
                continue
            qty_val = float(qty_val)
            if qty_val > 0:
                formatted_series.append(f"▲ +{qty_val:.2f}")
            elif qty_val < 0:
                formatted_series.append(f"▼ {qty_val:.2f}") # Negative sign is already there
            else:
                formatted_series.append(f"{qty_val:.2f}")
        return formatted_series
    
    # Apply emoji formatting to a new column for display
    if 'quantity_change' in display_df.columns:
        display_df['qty_display'] = format_qty_with_emoji(display_df['quantity_change'])

    # Apply color styling using Pandas Styler object
    # We will style the original 'quantity_change' column numbers but display the 'qty_display'
    # Or, we can try to style the 'qty_display' if it's rendered as text by dataframe
    # For simplicity with st.dataframe, we'll style the original numeric column
    # and then rely on column_config to show our emoji version, but st.dataframe doesn't directly take styled text.
    #
    # A better approach is to use st.table(df.style.applymap(...)) for full control,
    # but st.table lacks some features of st.dataframe.
    #
    # Let's try styling the *numeric* 'quantity_change' column for color,
    # and use the 'qty_display' for the text with emoji.
    # `st.dataframe` will show the styled numbers for `quantity_change` if we include it.
    # However, `column_config` for `TextColumn` doesn't directly render HTML from the DataFrame cell.
    # The simplest visual cue that works across Streamlit versions without unsafe_html on st.dataframe
    # is to just have the emoji in the text. Color is harder without unsafe_html.

    # So, we will only use the emoji column and forgo cell color for st.dataframe without unsafe_allow_html.
    # If unsafe_allow_html were available on st.dataframe, we could use the HTML span method.

    st.dataframe(
        display_df, # Pass the DataFrame with the new 'qty_display' column
        use_container_width=True,
        hide_index=True,
        column_config={
            "transaction_id": None, "item_id": None,
            "quantity_change": None, # Hide the original numeric column
            "transaction_date": st.column_config.TextColumn("Timestamp", width="medium", help="Date and time."),
            "item_name": st.column_config.TextColumn("Item Name", width="large"),
            "transaction_type": st.column_config.TextColumn("Type", width="medium", help="Type of movement."),
            "qty_display": st.column_config.TextColumn("Qty Change", width="small", help="Stock change. ▲ In, ▼ Out."), # Display the emoji version
            "user_id": st.column_config.TextColumn("User", width="medium"),
            "notes": st.column_config.TextColumn("Notes/Reason", width="large"),
            "related_mrn": st.column_config.TextColumn("Related MRN", width="medium"),
            "related_po_id": st.column_config.TextColumn("Related PO", width="medium"),
        },
        column_order=[
            "transaction_date", "item_name", "transaction_type", "qty_display", # Use qty_display
            "user_id", "notes", "related_mrn", "related_po_id"
        ]
        # No unsafe_allow_html here as it's not a valid param for st.dataframe
    )

    @st.cache_data
    def convert_df_to_csv(df_to_convert):
        cols_to_export = [col for col in [
            "transaction_date", "item_name", "transaction_type", "quantity_change", # Export original numeric qty
            "user_id", "notes", "related_mrn", "related_po_id"
        ] if col in df_to_convert.columns]
        return df_to_convert[cols_to_export].to_csv(index=False).encode('utf-8')

    csv_data = convert_df_to_csv(transactions_df) # Use original df for CSV

    st.download_button(
        label="📥 Download Report as CSV", data=csv_data,
        file_name=f"stock_history_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv", key="download_stock_history_csv_v3"
    )