# app/pages/4_History_Reports.py
import os
import sys
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_CUR_DIR, os.pardir, os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from app.db.database_utils import connect_db
    from app.services import item_service
    from app.services import stock_service
    from app.core.constants import (
        TX_RECEIVING,
        TX_ADJUSTMENT,
        TX_WASTAGE,
        TX_INDENT_FULFILL,
        TX_SALE,
        PLACEHOLDER_SELECT_ITEM,
        FILTER_ALL_TYPES,
    )
    from app.ui.theme import load_css, render_sidebar_logo
    from app.ui import show_success, show_error
except ImportError as e:
    show_error(f"Import error in 4_History_Reports.py: {e}.")
    st.stop()
except Exception as e:
    show_error(f"An unexpected error occurred during import in 4_History_Reports.py: {e}")
    st.stop()

load_css()
render_sidebar_logo()

st.title("📜 Stock Transaction History & Reports")
st.write(
    "Review the detailed history of all stock movements. Use the filters below to narrow down your search."
)
st.divider()

db_engine = connect_db()
if not db_engine:
    show_error("Database connection failed. Cannot load history reports.")
    st.stop()


@st.cache_data(ttl=120)
def fetch_filter_options_pg4(_engine):
    items_df = item_service.get_all_items_with_stock(_engine, include_inactive=True)
    item_options_pg4 = [(PLACEHOLDER_SELECT_ITEM, -1)]
    if not items_df.empty:
        item_options_pg4.extend(
            sorted(
                [
                    (
                        f"{r['name']} ({r.get('unit','N/A')}){' [Inactive]' if not r['is_active'] else ''}",
                        r["item_id"],
                    )
                    for _, r in items_df.dropna(subset=["name"]).iterrows()
                ],
                key=lambda x_opt: x_opt[0],
            )
        )

    transaction_type_options_map_pg4 = {
        FILTER_ALL_TYPES: None,
        "Goods Received": TX_RECEIVING,
        "Stock Adjustments": TX_ADJUSTMENT,
        "Wastage/Spoilage": TX_WASTAGE,
        "Indent Fulfillment": TX_INDENT_FULFILL,
        "Sales (Future Use)": TX_SALE,
    }
    return item_options_pg4, transaction_type_options_map_pg4


item_filter_options_pg4, transaction_type_filter_options_map_pg4 = (
    fetch_filter_options_pg4(db_engine)
)

# --- Session State Initialization ---
default_start_date = datetime.now().date() - timedelta(days=30)
default_end_date = datetime.now().date()

if "pg4_filter_item_id" not in st.session_state:  # This will store the INTEGER ID
    st.session_state.pg4_filter_item_id = -1
# No need for pg4_filter_item_tuple if using on_change correctly with a distinct widget key

if "pg4_filter_trans_type_key" not in st.session_state:
    st.session_state.pg4_filter_trans_type_key = FILTER_ALL_TYPES
if "pg4_filter_user_id" not in st.session_state:
    st.session_state.pg4_filter_user_id = ""
if "pg4_filter_related_mrn" not in st.session_state:
    st.session_state.pg4_filter_related_mrn = ""
if "pg4_start_date_val" not in st.session_state:
    st.session_state.pg4_start_date_val = default_start_date
if "pg4_end_date_val" not in st.session_state:
    st.session_state.pg4_end_date_val = default_end_date


# --- Filter Callbacks ---
def on_item_filter_change_pg4():
    """Callback to update pg4_filter_item_id (int) based on tuple from selectbox."""
    selected_tuple = st.session_state.pg4_item_filter_select_widget_key  # Widget key
    if selected_tuple and len(selected_tuple) == 2:
        st.session_state.pg4_filter_item_id = selected_tuple[1]  # Store the ID part
    else:  # Should not happen if options are tuples
        st.session_state.pg4_filter_item_id = -1


# For dates, we can simplify if we ensure widget keys are distinct from session state value keys
def on_date_filters_update_pg4():
    st.session_state.pg4_start_date_val = st.session_state.pg4_start_date_widget_key
    st.session_state.pg4_end_date_val = st.session_state.pg4_end_date_widget_key


st.subheader("🔎 Filter Transactions")
filter_col1_pg4, filter_col2_pg4 = st.columns(2)

with filter_col1_pg4:
    # Determine current index for item selectbox
    # This logic correctly uses the integer pg4_filter_item_id
    current_selected_item_id_for_idx = st.session_state.pg4_filter_item_id
    item_filter_idx_pg4 = 0
    try:
        # Create a list of just the IDs from item_filter_options_pg4 to find the index
        item_ids_in_options = [opt[1] for opt in item_filter_options_pg4]
        item_filter_idx_pg4 = item_ids_in_options.index(
            current_selected_item_id_for_idx
        )
    except ValueError:
        # If current ID not in options, default to placeholder ("-- Select an Item --", -1)
        st.session_state.pg4_filter_item_id = -1
        item_filter_idx_pg4 = 0  # Index of the placeholder

    st.selectbox(
        "Filter by Item:",
        options=item_filter_options_pg4,
        format_func=lambda x_opt: x_opt[0],  # Display only name
        index=item_filter_idx_pg4,
        key="pg4_item_filter_select_widget_key",  # DISTINCT WIDGET KEY
        on_change=on_item_filter_change_pg4,
        help="Select a specific item to view its transaction history.",
    )

    # Transaction Type Filter
    current_trans_type_key_display_name = st.session_state.pg4_filter_trans_type_key
    trans_type_options_keys_pg4 = list(transaction_type_filter_options_map_pg4.keys())
    trans_type_idx_pg4 = 0
    if current_trans_type_key_display_name in trans_type_options_keys_pg4:
        trans_type_idx_pg4 = trans_type_options_keys_pg4.index(
            current_trans_type_key_display_name
        )
    else:
        st.session_state.pg4_filter_trans_type_key = (
            FILTER_ALL_TYPES  # Reset if invalid
        )

    st.selectbox(
        "Filter by Transaction Type:",
        options=trans_type_options_keys_pg4,
        index=trans_type_idx_pg4,
        key="pg4_filter_trans_type_key",  # Session state key for selected display name
        # No on_change needed if key directly updates the session state used for filtering logic
        help="Select a specific transaction type.",
    )

with filter_col2_pg4:
    st.date_input(  # Assign to session state directly via key
        "Start Date:",
        value=st.session_state.pg4_start_date_val,
        key="pg4_start_date_val",  # Use the value session state key
        # on_change=on_date_filters_update_pg4 # Can add if complex interactions needed
    )
    st.date_input(  # Assign to session state directly via key
        "End Date:",
        value=st.session_state.pg4_end_date_val,
        key="pg4_end_date_val",  # Use the value session state key
        # on_change=on_date_filters_update_pg4
    )

with st.expander("More Filters (User, MRN)"):
    adv_filter_col1_pg4, adv_filter_col2_pg4 = st.columns(2)
    with adv_filter_col1_pg4:
        st.text_input(  # Assign to session state directly via key
            "Filter by User ID (contains):",
            key="pg4_filter_user_id",
            placeholder="e.g., JohnD",
        )  # .strip() will be applied when using the value
    with adv_filter_col2_pg4:
        st.text_input(  # Assign to session state directly via key
            "Filter by Related MRN (contains):",
            key="pg4_filter_related_mrn",
            placeholder="e.g., MRN-202505",
        )  # .strip() will be applied when using the value

if st.session_state.pg4_start_date_val > st.session_state.pg4_end_date_val:
    st.warning("Start date cannot be after end date. Please adjust the dates.")

st.divider()
st.subheader("📋 Transaction Records")

# Prepare arguments for the service function using the correct session state values
filter_item_id_arg_pg4 = (
    st.session_state.pg4_filter_item_id
    if st.session_state.pg4_filter_item_id != -1
    else None
)
filter_trans_type_arg_pg4 = transaction_type_filter_options_map_pg4.get(
    st.session_state.pg4_filter_trans_type_key
)
filter_user_id_arg_pg4 = (
    st.session_state.pg4_filter_user_id.strip()
    if st.session_state.pg4_filter_user_id
    else None
)
filter_related_mrn_arg_pg4 = (
    st.session_state.pg4_filter_related_mrn.strip()
    if st.session_state.pg4_filter_related_mrn
    else None
)

# Only fetch if dates are valid
if st.session_state.pg4_start_date_val <= st.session_state.pg4_end_date_val:
    transactions_df_pg4 = stock_service.get_stock_transactions(
        db_engine,
        item_id=filter_item_id_arg_pg4,
        transaction_type=filter_trans_type_arg_pg4,
        user_id=filter_user_id_arg_pg4,
        related_mrn=filter_related_mrn_arg_pg4,
        start_date=st.session_state.pg4_start_date_val,
        end_date=st.session_state.pg4_end_date_val,
    )
    # ... (rest of the DataFrame display and CSV download logic from the previous correct version) ...
    if transactions_df_pg4.empty:
        st.info("No stock transactions found matching the selected filters.")
    else:
        show_success(f"Found {len(transactions_df_pg4)} transaction(s).")

        display_df_pg4 = transactions_df_pg4.copy()
        if "transaction_date" in display_df_pg4.columns:
            display_df_pg4["transaction_date_display"] = pd.to_datetime(
                display_df_pg4["transaction_date"]
            ).dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            display_df_pg4["transaction_date_display"] = "N/A"

        def format_qty_with_emoji_pg4(qty_series):
            formatted_series = []
            for qty_val in qty_series:
                if pd.isna(qty_val):
                    formatted_series.append("")
                    continue
                try:
                    qty_float = float(qty_val)
                    if qty_float > 0:
                        formatted_series.append(f"▲ +{qty_float:.2f}")
                    elif qty_float < 0:
                        formatted_series.append(f"▼ {qty_float:.2f}")
                    else:
                        formatted_series.append(f"{qty_float:.2f}")
                except (ValueError, TypeError):
                    formatted_series.append(str(qty_val))
            return formatted_series

        if "quantity_change" in display_df_pg4.columns:
            display_df_pg4["qty_display"] = format_qty_with_emoji_pg4(
                display_df_pg4["quantity_change"]
            )
        else:
            display_df_pg4["qty_display"] = "N/A"

        st.dataframe(
            display_df_pg4,
            use_container_width=True,
            hide_index=True,
            column_config={
                "transaction_id": None,
                "item_id": None,
                "transaction_date": None,
                "quantity_change": None,
                "transaction_date_display": st.column_config.TextColumn(
                    "Timestamp",
                    width="medium",
                    help="Date and time of the transaction.",
                ),
                "item_name": st.column_config.TextColumn("Item Name", width="large"),
                "item_unit": st.column_config.TextColumn("Unit", width="small"),
                "transaction_type": st.column_config.TextColumn(
                    "Type", width="medium", help="Type of stock movement."
                ),
                "qty_display": st.column_config.TextColumn(
                    "Qty Change", width="small", help="Stock change. ▲ In, ▼ Out."
                ),
                "user_id": st.column_config.TextColumn(
                    "User/System ID", width="medium"
                ),
                "notes": st.column_config.TextColumn("Notes/Reason", width="large"),
                "related_mrn": st.column_config.TextColumn(
                    "Related MRN", width="medium"
                ),
                "related_po_id": st.column_config.TextColumn(
                    "Related PO ID", width="medium"
                ),
            },
            column_order=[
                "transaction_date_display",
                "item_name",
                "item_unit",
                "transaction_type",
                "qty_display",
                "user_id",
                "notes",
                "related_mrn",
                "related_po_id",
            ],
        )

        @st.cache_data
        def convert_df_to_csv_pg4(df_to_convert):
            cols_to_export = [
                col
                for col in [
                    "transaction_date",
                    "item_name",
                    "item_unit",
                    "transaction_type",
                    "quantity_change",
                    "user_id",
                    "notes",
                    "related_mrn",
                    "related_po_id",
                ]
                if col in df_to_convert.columns
            ]
            return df_to_convert[cols_to_export].to_csv(index=False).encode("utf-8")

        csv_data_pg4 = convert_df_to_csv_pg4(transactions_df_pg4)

        st.download_button(
            label="📥 Download Report as CSV",
            data=csv_data_pg4,
            file_name=f"stock_history_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key="download_stock_history_csv_pg4_v5",
        )
else:
    st.info("Adjust date filters to view transactions.")
