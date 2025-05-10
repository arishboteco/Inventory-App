# app/pages/3_Stock_Movements.py
import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple

try:
    from app.db.database_utils import connect_db
    from app.services import item_service
    from app.services import stock_service
    from app.core.constants import TX_RECEIVING, TX_ADJUSTMENT, TX_WASTAGE
except ImportError as e:
    st.error(f"Import error in 3_Stock_Movements.py: {e}.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 3_Stock_Movements.py: {e}")
    st.stop()

# --- Constants for this page ---
SECTIONS = {
    "receive": "📥 Goods Received",
    "adjust": "📊 Stock Adjustment",
    "waste": "🗑️ Wastage/Spoilage"
}
SECTION_KEYS = list(SECTIONS.keys())
SECTION_DISPLAY_NAMES = list(SECTIONS.values())

placeholder_option_stock = ("-- Select an Item --", -1)

# --- Session State Initialization ---
if 'active_stock_movement_section' not in st.session_state:
    st.session_state.active_stock_movement_section = SECTION_KEYS[0] # Default to 'receive'

# Keys for selectbox widget value (the tuple) and derived ID
for section_key_prefix in SECTION_KEYS:
    selectbox_tuple_key = f"{section_key_prefix}_item_select_key_for_tuple"
    selected_id_key = f"{section_key_prefix}_selected_item_id"
    reset_signal_key = f"{section_key_prefix}_reset_signal"

    if selectbox_tuple_key not in st.session_state:
        st.session_state[selectbox_tuple_key] = placeholder_option_stock
    if selected_id_key not in st.session_state:
        st.session_state[selected_id_key] = None
    if reset_signal_key not in st.session_state:
        st.session_state[reset_signal_key] = False


st.header("🚚 Stock Movements Log")
st.write("Use this page to accurately record all changes to your inventory: goods received, adjustments, or wastage/spoilage.")
st.divider()

db_engine = connect_db()
if not db_engine: st.error("Database connection failed."); st.stop()

@st.cache_data(ttl=60)
def fetch_active_items_for_stock_dropdown(_engine):
    items_df = item_service.get_all_items_with_stock(_engine, include_inactive=False)
    if not items_df.empty:
        return [(f"{r['name']} ({r['unit']})", r['item_id']) for _, r in items_df.sort_values('name').iterrows()]
    return []

active_item_options_for_stock = fetch_active_items_for_stock_dropdown(db_engine)
item_options_with_placeholder_stock = [placeholder_option_stock] + active_item_options_for_stock

def update_selected_item_id_from_tuple(selectbox_key_for_tuple, session_state_id_key):
    selected_tuple = st.session_state[selectbox_key_for_tuple]
    if selected_tuple and len(selected_tuple) == 2 and selected_tuple[1] != -1:
        st.session_state[session_state_id_key] = selected_tuple[1]
    else:
        st.session_state[session_state_id_key] = None

def set_active_section(): # Callback for radio button
    # Map display name back to simple key if needed, or store simple key directly
    selected_display_name = st.session_state.stock_movement_radio_key_v6 # Key of the radio
    for key, display_name in SECTIONS.items():
        if display_name == selected_display_name:
            st.session_state.active_stock_movement_section = key
            break

# --- Radio buttons for section navigation ---
st.radio(
    "Select Movement Type:",
    options=SECTION_DISPLAY_NAMES, # Show user-friendly names with icons
    index=SECTION_KEYS.index(st.session_state.active_stock_movement_section), # Set based on session state
    key="stock_movement_radio_key_v6",
    on_change=set_active_section,
    horizontal=True,
)
st.divider()

# --- Conditionally render sections based on active_stock_movement_section ---

if st.session_state.active_stock_movement_section == "receive":
    st.subheader(SECTIONS["receive"]) # Use display name
    # Handle reset signal
    if st.session_state[f"{SECTION_KEYS[0]}_reset_signal"]:
        st.session_state[f"{SECTION_KEYS[0]}_item_select_key_for_tuple"] = placeholder_option_stock
        st.session_state[f"{SECTION_KEYS[0]}_selected_item_id"] = None
        st.session_state[f"{SECTION_KEYS[0]}_reset_signal"] = False

    item_col_recv, _ = st.columns([2,1])
    with item_col_recv:
        st.selectbox(
            "Item Received*", options=item_options_with_placeholder_stock, format_func=lambda x: x[0],
            key=f"{SECTION_KEYS[0]}_item_select_key_for_tuple",
            help="Select the item that was received.",
            on_change=update_selected_item_id_from_tuple,
            args=(f"{SECTION_KEYS[0]}_item_select_key_for_tuple", f"{SECTION_KEYS[0]}_selected_item_id")
        )
        if st.session_state[f"{SECTION_KEYS[0]}_selected_item_id"] and st.session_state[f"{SECTION_KEYS[0]}_selected_item_id"] != -1:
            item_details = item_service.get_item_details(db_engine, st.session_state[f"{SECTION_KEYS[0]}_selected_item_id"])
            if item_details: st.caption(f"Current Stock: {item_details.get('current_stock', 0):.2f} {item_details.get('unit', '')}")
            else: st.caption("Could not fetch stock details.")
    st.markdown("---")
    with st.form("receiving_form_v7", clear_on_submit=True):
        qty_form_col, user_form_col = st.columns(2)
        with qty_form_col: recv_qty = st.number_input("Quantity Received*", min_value=0.01, format="%.2f", key="recv_qty_v7")
        with user_form_col: recv_user_id = st.text_input("Receiver's Name/ID*", key="recv_user_id_v7", placeholder="e.g., John Doe")
        recv_po_id = st.text_input("Related PO ID (Optional)", key="recv_po_v7", placeholder="e.g., PO-10023")
        recv_notes = st.text_area("Notes / Remarks", key="recv_notes_v7", placeholder="e.g., Supplier name, Invoice #")
        if st.form_submit_button("📥 Record Receiving"):
            selected_item_id = st.session_state[f"{SECTION_KEYS[0]}_selected_item_id"]
            if not selected_item_id or selected_item_id == -1: st.warning("Please select an item first.")
            elif recv_qty <= 0: st.warning("Quantity must be > 0.")
            elif not recv_user_id: st.warning("Receiver's Name/ID required.")
            else:
                related_po = None
                if recv_po_id.strip():
                   try: related_po = int(recv_po_id.strip())
                   except ValueError: st.warning("PO ID must be a number."); related_po = "ERROR"
                if related_po != "ERROR":
                    success = stock_service.record_stock_transaction(
                        db_engine, selected_item_id, abs(float(recv_qty)), TX_RECEIVING,
                        recv_user_id.strip(), related_po_id=related_po, notes=recv_notes.strip() or None)
                    if success:
                        item_display_name = st.session_state[f"{SECTION_KEYS[0]}_item_select_key_for_tuple"][0]
                        st.success(f"Recorded receipt: {recv_qty:.2f} units for '{item_display_name}'.")
                        fetch_active_items_for_stock_dropdown.clear()
                        st.session_state[f"{SECTION_KEYS[0]}_reset_signal"] = True
                        # st.session_state.active_stock_movement_section = SECTION_KEYS[0] # Ensure we stay
                        st.rerun()
                    else: st.error("Failed to record stock receiving.")

elif st.session_state.active_stock_movement_section == "adjust":
    st.subheader(SECTIONS["adjust"])
    st.caption("Use for correcting discrepancies or other non-wastage adjustments.")
    if st.session_state[f"{SECTION_KEYS[1]}_reset_signal"]: # Handle reset signal
        st.session_state[f"{SECTION_KEYS[1]}_item_select_key_for_tuple"] = placeholder_option_stock
        st.session_state[f"{SECTION_KEYS[1]}_selected_item_id"] = None
        st.session_state[f"{SECTION_KEYS[1]}_reset_signal"] = False
    item_col_adj, _ = st.columns([2,1])
    with item_col_adj:
        st.selectbox("Item to Adjust*", options=item_options_with_placeholder_stock, format_func=lambda x: x[0],
                     key=f"{SECTION_KEYS[1]}_item_select_key_for_tuple", help="Select item for adjustment.",
                     on_change=update_selected_item_id_from_tuple, args=(f"{SECTION_KEYS[1]}_item_select_key_for_tuple", f"{SECTION_KEYS[1]}_selected_item_id"))
        if st.session_state[f"{SECTION_KEYS[1]}_selected_item_id"] and st.session_state[f"{SECTION_KEYS[1]}_selected_item_id"] != -1:
            item_details = item_service.get_item_details(db_engine, st.session_state[f"{SECTION_KEYS[1]}_selected_item_id"])
            if item_details: st.caption(f"Current Stock: {item_details.get('current_stock', 0):.2f} {item_details.get('unit', '')}")
    st.markdown("---")
    with st.form("adjustment_form_v7", clear_on_submit=True):
        qty_form_col_adj, user_form_col_adj = st.columns(2)
        with qty_form_col_adj: adj_qty = st.number_input("Quantity Adjusted*", step=0.01, format="%.2f", help="Positive for increase, negative for decrease.", key="adj_qty_v7", value=0.0)
        with user_form_col_adj: adj_user_id = st.text_input("Adjuster's Name/ID*", key="adj_user_id_v7", placeholder="e.g., Jane Smith")
        adj_notes = st.text_area("Reason for Adjustment*", key="adj_notes_v7", placeholder="Crucial: Explain adjustment reason...")
        if st.form_submit_button("📊 Record Adjustment"):
            selected_item_id = st.session_state[f"{SECTION_KEYS[1]}_selected_item_id"]
            if not selected_item_id or selected_item_id == -1: st.warning("Please select an item.")
            elif adj_qty == 0: st.warning("Quantity adjusted cannot be zero.")
            elif not adj_user_id: st.warning("Adjuster's Name/ID required.")
            elif not adj_notes.strip(): st.warning("A reason for adjustment is mandatory.")
            else:
                success = stock_service.record_stock_transaction(
                    db_engine, selected_item_id, float(adj_qty), TX_ADJUSTMENT,
                    adj_user_id.strip(), notes=adj_notes.strip())
                if success:
                    item_display_name = st.session_state[f"{SECTION_KEYS[1]}_item_select_key_for_tuple"][0]
                    change_type = "increase" if adj_qty > 0 else "decrease"
                    st.success(f"Recorded stock {change_type} of {abs(adj_qty):.2f} for '{item_display_name}'.")
                    fetch_active_items_for_stock_dropdown.clear()
                    st.session_state[f"{SECTION_KEYS[1]}_reset_signal"] = True
                    # st.session_state.active_stock_movement_section = SECTION_KEYS[1] # Ensure we stay
                    st.rerun()
                else: st.error("Failed to record stock adjustment.")

elif st.session_state.active_stock_movement_section == "waste":
    st.subheader(SECTIONS["waste"])
    st.caption("Use for items that are damaged, expired, or otherwise unusable.")
    if st.session_state[f"{SECTION_KEYS[2]}_reset_signal"]: # Handle reset signal
        st.session_state[f"{SECTION_KEYS[2]}_item_select_key_for_tuple"] = placeholder_option_stock
        st.session_state[f"{SECTION_KEYS[2]}_selected_item_id"] = None
        st.session_state[f"{SECTION_KEYS[2]}_reset_signal"] = False
    item_col_waste, _ = st.columns([2,1])
    with item_col_waste:
        st.selectbox("Item Wasted/Spoiled*", options=item_options_with_placeholder_stock, format_func=lambda x: x[0],
                     key=f"{SECTION_KEYS[2]}_item_select_key_for_tuple", help="Select item wasted/spoiled.",
                     on_change=update_selected_item_id_from_tuple, args=(f"{SECTION_KEYS[2]}_item_select_key_for_tuple", f"{SECTION_KEYS[2]}_selected_item_id"))
        if st.session_state[f"{SECTION_KEYS[2]}_selected_item_id"] and st.session_state[f"{SECTION_KEYS[2]}_selected_item_id"] != -1:
            item_details = item_service.get_item_details(db_engine, st.session_state[f"{SECTION_KEYS[2]}_selected_item_id"])
            if item_details: st.caption(f"Current Stock: {item_details.get('current_stock', 0):.2f} {item_details.get('unit', '')}")
    st.markdown("---")
    with st.form("wastage_form_v7", clear_on_submit=True):
        qty_form_col_waste, user_form_col_waste = st.columns(2)
        with qty_form_col_waste: waste_qty = st.number_input("Quantity Wasted*", min_value=0.01, format="%.2f", help="Positive quantity wasted.", key="waste_qty_v7")
        with user_form_col_waste: waste_user_id = st.text_input("Recorder's Name/ID*", key="waste_user_id_v7", placeholder="e.g., Chef Mike")
        waste_notes = st.text_area("Reason for Wastage*", key="waste_notes_v7", placeholder="Crucial: Explain wastage reason...")
        if st.form_submit_button("🗑️ Record Wastage"):
            selected_item_id = st.session_state[f"{SECTION_KEYS[2]}_selected_item_id"]
            if not selected_item_id or selected_item_id == -1: st.warning("Please select an item.")
            elif waste_qty <= 0: st.warning("Quantity wasted must be > 0.")
            elif not waste_user_id: st.warning("Recorder's Name/ID required.")
            elif not waste_notes.strip(): st.warning("A reason for wastage is mandatory.")
            else:
                success = stock_service.record_stock_transaction(
                    db_engine, selected_item_id, -abs(float(waste_qty)), TX_WASTAGE,
                    waste_user_id.strip(), notes=waste_notes.strip())
                if success:
                    item_display_name = st.session_state[f"{SECTION_KEYS[2]}_item_select_key_for_tuple"][0]
                    st.success(f"Recorded wastage of {waste_qty:.2f} units for '{item_display_name}'.")
                    fetch_active_items_for_stock_dropdown.clear()
                    st.session_state[f"{SECTION_KEYS[2]}_reset_signal"] = True
                    # st.session_state.active_stock_movement_section = SECTION_KEYS[2] # Ensure we stay
                    st.rerun()
                else: st.error("Failed to record wastage.")