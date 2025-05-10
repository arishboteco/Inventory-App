# app/pages/3_Stock_Movements.py

import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
import math

# Import shared functions and constants
try:
    # Import connect_db from its new location
    from app.db.database_utils import connect_db
    # Functions still temporarily in app.item_manager_app
    from app.item_manager_app import (
        get_all_items_with_stock,
        record_stock_transaction,
    )
    # Import constants from their new location
    from app.core.constants import TX_RECEIVING, TX_ADJUSTMENT, TX_WASTAGE
except ImportError as e:
    st.error(f"Import error in 3_Stock_Movements.py: {e}. Ensure 'INVENTORY-APP' is the root for 'streamlit run app/item_manager_app.py'.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 3_Stock_Movements.py: {e}")
    st.stop()

# --- Page Content ---
# st.set_page_config(layout="wide") # Ideally called only once in the main app script
st.header("🚚 Stock Movements")
st.write("Record stock coming in (Goods Received), adjustments, or wastage/spoilage.")

db_engine = connect_db() # Uses imported connect_db
if not db_engine:
    st.error("Database connection failed on this page.")
    st.stop()

@st.cache_data(ttl=60)
def fetch_active_items_for_dropdown(_engine):
    # Calls get_all_items_with_stock (imported from app.item_manager_app)
    items_df = get_all_items_with_stock(_engine, include_inactive=False)
    if not items_df.empty and 'item_id' in items_df.columns and 'name' in items_df.columns and 'unit' in items_df.columns:
        item_options_list: List[Tuple[str, int]] = [
            (f"{row['name']} ({row['unit']})", row['item_id'])
            for index, row in items_df.iterrows()
        ]
        return item_options_list
    return []

active_item_options = fetch_active_items_for_dropdown(db_engine)

placeholder_option = ("Select an item...", -1)
item_options_with_placeholder = [placeholder_option] + active_item_options

# --- Forms for Stock Movements ---
tab_recv, tab_adj, tab_waste = st.tabs(["📥 Goods Received", "📊 Stock Adjustment", "🗑️ Wastage/Spoilage"])

# --- Goods Received Tab ---
with tab_recv:
    st.subheader("Record Goods Received")
    with st.form("receiving_form", clear_on_submit=True):
        recv_selected_item_tuple = st.selectbox(
            "Item Received*",
            options=item_options_with_placeholder,
            format_func=lambda x: x[0],
            key="recv_item_select",
            index=0
        )
        recv_qty = st.number_input("Quantity Received*", min_value=0.01, step=0.01, format="%.2f", key="recv_qty")
        recv_user_id = st.text_input("Receiver's Name/ID*", key="recv_user_id")
        recv_po_id = st.text_input("Related PO ID (Optional)", key="recv_po")
        recv_notes = st.text_area("Notes (e.g., Supplier, Invoice #)", key="recv_notes")

        recv_submitted = st.form_submit_button("Record Receiving")
        if recv_submitted:
            selected_item_id = recv_selected_item_tuple[1] if recv_selected_item_tuple else -1

            if selected_item_id == -1:
                st.warning("Please select an item.")
            elif recv_qty <= 0:
                st.warning("Quantity must be greater than 0.")
            elif not recv_user_id:
                st.warning("Please enter the Receiver's Name/ID.")
            else:
                related_po = None
                if recv_po_id.strip():
                   try:
                       related_po = int(recv_po_id.strip())
                   except ValueError:
                       st.warning("Related PO ID must be a valid number if provided.")
                       related_po = -1 # Indicate error

                if related_po != -1:
                     # Calls record_stock_transaction (imported from app.item_manager_app)
                     success = record_stock_transaction(
                        engine=db_engine,
                        item_id=selected_item_id,
                        quantity_change=abs(float(recv_qty)),
                        transaction_type=TX_RECEIVING, # Imported constant
                        user_id=recv_user_id.strip(),
                        related_po_id=related_po,
                        notes=recv_notes.strip() or None
                    )
                     if success:
                        st.success(f"Successfully recorded receipt of {recv_qty:.2f} units for '{recv_selected_item_tuple[0]}'.")
                        fetch_active_items_for_dropdown.clear()
                        # record_stock_transaction should clear get_all_items_with_stock and get_stock_transactions
                        # For now, ensure they are cleared if record_stock_transaction doesn't do it.
                        get_all_items_with_stock.clear() # To refresh current stock in dropdown if needed elsewhere
                     else:
                        st.error("Failed to record stock receiving.")

# --- Stock Adjustment Tab ---
with tab_adj:
    st.subheader("Record Stock Adjustment")
    with st.form("adjustment_form", clear_on_submit=True):
        adj_selected_item_tuple = st.selectbox(
            "Item to Adjust*",
            options=item_options_with_placeholder,
            format_func=lambda x: x[0],
            key="adj_item_select",
            index=0
        )
        adj_qty = st.number_input(
            "Quantity Adjusted*",
            step=0.01,
            format="%.2f",
            help="Enter positive number for stock increase, negative number for stock decrease.",
            key="adj_qty",
            value=0.0
        )
        adj_user_id = st.text_input("Adjuster's Name/ID*", key="adj_user_id")
        adj_notes = st.text_area("Reason for Adjustment*", key="adj_notes")

        adj_submitted = st.form_submit_button("Record Adjustment")
        if adj_submitted:
            selected_item_id = adj_selected_item_tuple[1] if adj_selected_item_tuple else -1

            if selected_item_id == -1:
                st.warning("Please select an item.")
            elif adj_qty == 0:
                st.warning("Quantity adjusted cannot be zero. Enter a positive or negative value.")
            elif not adj_user_id:
                st.warning("Please enter the Adjuster's Name/ID.")
            elif not adj_notes:
                st.warning("Please enter a reason for the adjustment.")
            else:
                # Calls record_stock_transaction (imported from app.item_manager_app)
                success = record_stock_transaction(
                    engine=db_engine,
                    item_id=selected_item_id,
                    quantity_change=float(adj_qty),
                    transaction_type=TX_ADJUSTMENT, # Imported constant
                    user_id=adj_user_id.strip(),
                    notes=adj_notes.strip()
                )
                if success:
                    change_type = "increase" if adj_qty > 0 else "decrease"
                    st.success(f"Successfully recorded stock {change_type} of {abs(adj_qty):.2f} units for '{adj_selected_item_tuple[0]}'.")
                    fetch_active_items_for_dropdown.clear()
                    get_all_items_with_stock.clear()
                else:
                    st.error("Failed to record stock adjustment.")

# --- Wastage/Spoilage Tab ---
with tab_waste:
    st.subheader("Record Wastage / Spoilage")
    with st.form("wastage_form", clear_on_submit=True):
        waste_selected_item_tuple = st.selectbox(
            "Item Wasted/Spoiled*",
            options=item_options_with_placeholder,
            format_func=lambda x: x[0],
            key="waste_item_select",
            index=0
        )
        waste_qty = st.number_input(
            "Quantity Wasted*",
            min_value=0.01,
            step=0.01,
            format="%.2f",
            help="Enter the positive quantity that was wasted.",
            key="waste_qty"
        )
        waste_user_id = st.text_input("Recorder's Name/ID*", key="waste_user_id")
        waste_notes = st.text_area("Reason for Wastage*", key="waste_notes")

        waste_submitted = st.form_submit_button("Record Wastage")
        if waste_submitted:
            selected_item_id = waste_selected_item_tuple[1] if waste_selected_item_tuple else -1

            if selected_item_id == -1:
                st.warning("Please select an item.")
            elif waste_qty <= 0:
                st.warning("Quantity wasted must be greater than 0.")
            elif not waste_user_id:
                st.warning("Please enter the Recorder's Name/ID.")
            elif not waste_notes:
                st.warning("Please enter a reason for the wastage.")
            else:
                # Calls record_stock_transaction (imported from app.item_manager_app)
                success = record_stock_transaction(
                    engine=db_engine,
                    item_id=selected_item_id,
                    quantity_change=-abs(float(waste_qty)),
                    transaction_type=TX_WASTAGE, # Imported constant
                    user_id=waste_user_id.strip(),
                    notes=waste_notes.strip()
                )
                if success:
                    st.success(f"Successfully recorded wastage of {waste_qty:.2f} units for '{waste_selected_item_tuple[0]}'.")
                    fetch_active_items_for_dropdown.clear()
                    get_all_items_with_stock.clear()
                else:
                    st.error("Failed to record wastage.")