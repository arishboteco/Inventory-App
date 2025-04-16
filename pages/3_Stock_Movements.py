import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
import math

# Import shared functions and engine from the main app file
try:
    from item_manager_app import (
        connect_db,
        get_all_items_with_stock, # Needed for item dropdowns
        record_stock_transaction,
        get_all_suppliers, # Potentially needed for Receiving notes later
        TX_RECEIVING,             # Import constants
        TX_ADJUSTMENT,
        TX_WASTAGE
    )
except ImportError:
    st.error("Could not import functions from item_manager_app.py. Ensure it's in the parent directory.")
    st.stop()

# --- Page Content ---
st.header("Stock Movements")
st.write("Record stock coming in, adjustments, or wastage.")

# Establish DB connection for this page
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed on this page.")
    st.stop()
else:
    # Fetch item data needed for dropdowns ONCE
    # Only fetch ACTIVE items for these forms
    items_df_stock_page = get_all_items_with_stock(db_engine, include_inactive=False)
    if not items_df_stock_page.empty and 'item_id' in items_df_stock_page.columns and 'name' in items_df_stock_page.columns:
        item_options_list_active: List[Tuple[str, int]] = [
            (row['name'], row['item_id'])
            for index, row in items_df_stock_page.dropna(subset=['name']).iterrows()
        ]
        item_options_list_active.sort()
    else:
        item_options_list_active = []

    # --- Define Tabs ---
    tab_recv, tab_adj, tab_waste = st.tabs([
        "📥 Record Receiving",
        "📈 Record Adjustment",
        "🗑️ Record Wastage"
    ])

    # --- Tab 1: Receiving ---
    with tab_recv:
        # Removed expander
        recv_item_options = [("--- Select ---", None)] + item_options_list_active
        with st.form("receiving_form", clear_on_submit=True):
            st.subheader("Enter Details of Stock Received:") # Keep subheader inside form
            recv_selected_item = st.selectbox("Item Received*", options=recv_item_options, format_func=lambda x: x[0], key="recv_item_select"); recv_qty = st.number_input("Quantity Received*", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="recv_qty"); recv_user_id = st.text_input("Receiver's Name/ID*", key="recv_user_id"); recv_notes = st.text_area("Notes (Optional)", help="e.g., Supplier, PO#, Invoice#", key="recv_notes")
            recv_submitted = st.form_submit_button("Record Receipt")
            if recv_submitted:
                selected_item_id = recv_selected_item[1] if recv_selected_item else None
                if not selected_item_id: st.warning("Select item.")
                elif recv_qty <= 0: st.warning("Quantity must be > 0.")
                elif not recv_user_id: st.warning("Enter Receiver's Name/ID.")
                else:
                    # Call imported function
                    recv_success = record_stock_transaction(engine=db_engine, item_id=selected_item_id, quantity_change=float(recv_qty), transaction_type=TX_RECEIVING, user_id=recv_user_id.strip(), notes=recv_notes.strip() or None)
                    if recv_success: st.success(f"Receipt recorded!"); get_all_items_with_stock.clear(); st.rerun()
                    else: st.error("Failed to record receipt.")

    # --- Tab 2: Adjustment ---
    with tab_adj:
        # Removed expander
        # Allow adjusting active or inactive? Let's stick to active for now for simplicity
        adj_item_options = [("--- Select ---", None)] + item_options_list_active
        with st.form("adjustment_form", clear_on_submit=True):
            st.subheader("Enter Adjustment Details:") # Keep subheader inside form
            adj_selected_item = st.selectbox("Item to Adjust*", options=adj_item_options, format_func=lambda x: x[0], key="adj_item_select"); adj_qty_change = st.number_input("Quantity Change*", step=0.01, format="%.2f", help="+ for IN, - for OUT", key="adj_qty_change"); adj_user_id = st.text_input("Your Name/ID*", key="adj_user_id"); adj_notes = st.text_area("Reason*", key="adj_notes")
            adj_submitted = st.form_submit_button("Record Adjustment")
            if adj_submitted:
                selected_item_id = adj_selected_item[1] if adj_selected_item else None
                if not selected_item_id: st.warning("Select item.")
                elif math.isclose(adj_qty_change, 0): st.warning("Change cannot be zero.")
                elif not adj_user_id: st.warning("Enter Your Name/ID.")
                elif not adj_notes: st.warning("Enter a reason.")
                else:
                     # Call imported function
                    adj_success = record_stock_transaction(engine=db_engine, item_id=selected_item_id, quantity_change=float(adj_qty_change), transaction_type=TX_ADJUSTMENT, user_id=adj_user_id.strip(), notes=adj_notes.strip())
                    if adj_success: st.success(f"Adjustment recorded!"); get_all_items_with_stock.clear(); st.rerun()
                    else: st.error("Failed to record adjustment.")

    # --- Tab 3: Wastage ---
    with tab_waste:
        # Removed expander
        waste_item_options = [("--- Select ---", None)] + item_options_list_active
        with st.form("wastage_form", clear_on_submit=True):
            st.subheader("Enter Details of Wasted Stock:") # Keep subheader inside form
            waste_selected_item = st.selectbox("Item Wasted*", options=waste_item_options, format_func=lambda x: x[0], key="waste_item_select"); waste_qty = st.number_input("Quantity Wasted*", min_value=0.01, step=0.01, format="%.2f", help="Enter positive quantity wasted", key="waste_qty"); waste_user_id = st.text_input("Recorder's Name/ID*", key="waste_user_id"); waste_notes = st.text_area("Reason*", key="waste_notes")
            waste_submitted = st.form_submit_button("Record Wastage")
            if waste_submitted:
                selected_item_id = waste_selected_item[1] if waste_selected_item else None
                if not selected_item_id: st.warning("Select item.")
                elif waste_qty <= 0: st.warning("Quantity must be > 0.")
                elif not waste_user_id: st.warning("Enter Recorder's Name/ID.")
                elif not waste_notes: st.warning("Enter a reason.")
                else:
                     # Call imported function
                    waste_success = record_stock_transaction(engine=db_engine, item_id=selected_item_id, quantity_change=-abs(float(waste_qty)), transaction_type=TX_WASTAGE, user_id=waste_user_id.strip(), notes=waste_notes.strip())
                    if waste_success: st.success(f"Wastage recorded!"); get_all_items_with_stock.clear(); st.rerun()
                    else: st.error("Failed to record wastage.")

