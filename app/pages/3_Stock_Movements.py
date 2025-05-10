# app/pages/3_Stock_Movements.py
import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
import math # Keep if any math ops are used, otherwise optional

try:
    from app.db.database_utils import connect_db
    from app.services import item_service # For get_all_items_with_stock
    from app.services import stock_service # For record_stock_transaction
    from app.core.constants import TX_RECEIVING, TX_ADJUSTMENT, TX_WASTAGE
except ImportError as e:
    st.error(f"Import error in 3_Stock_Movements.py: {e}.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 3_Stock_Movements.py: {e}")
    st.stop()

st.header("🚚 Stock Movements")
st.write("Record stock coming in (Goods Received), adjustments, or wastage/spoilage.")
db_engine = connect_db()
if not db_engine: st.error("Database connection failed."); st.stop()

@st.cache_data(ttl=60)
def fetch_active_items_for_dropdown(_engine):
    items_df = item_service.get_all_items_with_stock(_engine, include_inactive=False)
    if not items_df.empty:
        return [(f"{row['name']} ({row['unit']})", row['item_id']) for _, row in items_df.iterrows()]
    return []

active_item_options = fetch_active_items_for_dropdown(db_engine)
placeholder_option = ("Select an item...", -1)
item_options_with_placeholder = [placeholder_option] + active_item_options

tab_recv, tab_adj, tab_waste = st.tabs(["📥 Goods Received", "📊 Stock Adjustment", "🗑️ Wastage/Spoilage"])

with tab_recv:
    st.subheader("Record Goods Received")
    with st.form("receiving_form", clear_on_submit=True):
        recv_selected_item_tuple = st.selectbox("Item Received*", options=item_options_with_placeholder, format_func=lambda x: x[0], key="recv_item_select", index=0)
        recv_qty = st.number_input("Quantity Received*", min_value=0.01, step=0.01, format="%.2f", key="recv_qty")
        recv_user_id = st.text_input("Receiver's Name/ID*", key="recv_user_id")
        recv_po_id = st.text_input("Related PO ID (Optional)", key="recv_po")
        recv_notes = st.text_area("Notes (e.g., Supplier, Invoice #)", key="recv_notes")
        if st.form_submit_button("Record Receiving"):
            selected_item_id = recv_selected_item_tuple[1]
            if selected_item_id == -1: st.warning("Please select an item.")
            elif recv_qty <= 0: st.warning("Quantity must be > 0.")
            elif not recv_user_id: st.warning("Receiver's Name/ID required.")
            else:
                related_po = None
                if recv_po_id.strip():
                   try: related_po = int(recv_po_id.strip())
                   except ValueError: st.warning("PO ID must be a number."); related_po = "ERROR"
                if related_po != "ERROR":
                     success = stock_service.record_stock_transaction( # Use service
                        engine=db_engine, item_id=selected_item_id, quantity_change=abs(float(recv_qty)),
                        transaction_type=TX_RECEIVING, user_id=recv_user_id.strip(),
                        related_po_id=related_po, notes=recv_notes.strip() or None)
                     if success:
                        st.success(f"Recorded receipt: {recv_qty:.2f} units for '{recv_selected_item_tuple[0]}'.")
                        fetch_active_items_for_dropdown.clear() # This page's cache
                        st.rerun()
                     else: st.error("Failed to record stock receiving.")
with tab_adj:
    st.subheader("Record Stock Adjustment")
    with st.form("adjustment_form", clear_on_submit=True):
        adj_selected_item_tuple = st.selectbox("Item to Adjust*", options=item_options_with_placeholder, format_func=lambda x: x[0], key="adj_item_select", index=0)
        adj_qty = st.number_input("Quantity Adjusted*", step=0.01, format="%.2f", help="Positive for increase, negative for decrease.", key="adj_qty", value=0.0)
        adj_user_id = st.text_input("Adjuster's Name/ID*", key="adj_user_id")
        adj_notes = st.text_area("Reason for Adjustment*", key="adj_notes")
        if st.form_submit_button("Record Adjustment"):
            selected_item_id = adj_selected_item_tuple[1]
            if selected_item_id == -1: st.warning("Please select an item.")
            elif adj_qty == 0: st.warning("Quantity adjusted cannot be zero.")
            elif not adj_user_id: st.warning("Adjuster's Name/ID required.")
            elif not adj_notes: st.warning("Reason for adjustment required.")
            else:
                success = stock_service.record_stock_transaction( # Use service
                    engine=db_engine, item_id=selected_item_id, quantity_change=float(adj_qty),
                    transaction_type=TX_ADJUSTMENT, user_id=adj_user_id.strip(), notes=adj_notes.strip())
                if success:
                    st.success(f"Recorded adjustment for '{adj_selected_item_tuple[0]}'.")
                    fetch_active_items_for_dropdown.clear()
                    st.rerun()
                else: st.error("Failed to record adjustment.")
with tab_waste:
    st.subheader("Record Wastage / Spoilage")
    with st.form("wastage_form", clear_on_submit=True):
        waste_selected_item_tuple = st.selectbox("Item Wasted/Spoiled*", options=item_options_with_placeholder, format_func=lambda x: x[0], key="waste_item_select", index=0)
        waste_qty = st.number_input("Quantity Wasted*", min_value=0.01, step=0.01, format="%.2f", help="Positive quantity wasted.", key="waste_qty")
        waste_user_id = st.text_input("Recorder's Name/ID*", key="waste_user_id")
        waste_notes = st.text_area("Reason for Wastage*", key="waste_notes")
        if st.form_submit_button("Record Wastage"):
            selected_item_id = waste_selected_item_tuple[1]
            if selected_item_id == -1: st.warning("Please select an item.")
            elif waste_qty <= 0: st.warning("Quantity wasted must be > 0.")
            elif not waste_user_id: st.warning("Recorder's Name/ID required.")
            elif not waste_notes: st.warning("Reason for wastage required.")
            else:
                success = stock_service.record_stock_transaction( # Use service
                    engine=db_engine, item_id=selected_item_id, quantity_change=-abs(float(waste_qty)),
                    transaction_type=TX_WASTAGE, user_id=waste_user_id.strip(), notes=waste_notes.strip())
                if success:
                    st.success(f"Recorded wastage for '{waste_selected_item_tuple[0]}'.")
                    fetch_active_items_for_dropdown.clear()
                    st.rerun()
                else: st.error("Failed to record wastage.")