# app/pages/3_Stock_Movements.py
import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
from datetime import date # Only date is used from datetime, no need for full datetime

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

placeholder_option_stock_pg3 = ("-- Select an Item --", -1) # Unique placeholder name

# --- Session State Initialization ---
if 'active_stock_movement_section_pg3' not in st.session_state: # Unique key
    st.session_state.active_stock_movement_section_pg3 = SECTION_KEYS[0]

for section_key_prefix_pg3 in SECTION_KEYS: # Unique loop var
    # Use more descriptive and unique keys for session state
    item_tuple_key_pg3 = f"pg3_{section_key_prefix_pg3}_item_tuple_val"
    selected_id_key_pg3 = f"pg3_{section_key_prefix_pg3}_selected_item_id"
    reset_signal_key_pg3 = f"pg3_{section_key_prefix_pg3}_reset_signal"
    qty_key_pg3 = f"pg3_{section_key_prefix_pg3}_qty_form_val"
    user_id_key_pg3 = f"pg3_{section_key_prefix_pg3}_user_id_form_val"
    notes_key_pg3 = f"pg3_{section_key_prefix_pg3}_notes_form_val"

    if item_tuple_key_pg3 not in st.session_state:
        st.session_state[item_tuple_key_pg3] = placeholder_option_stock_pg3
    if selected_id_key_pg3 not in st.session_state:
        st.session_state[selected_id_key_pg3] = None
    if reset_signal_key_pg3 not in st.session_state:
        st.session_state[reset_signal_key_pg3] = False
    
    # Initialize form field persistent values
    if qty_key_pg3 not in st.session_state: 
        st.session_state[qty_key_pg3] = 0.0
    if user_id_key_pg3 not in st.session_state: 
        st.session_state[user_id_key_pg3] = ""
    if notes_key_pg3 not in st.session_state: 
        st.session_state[notes_key_pg3] = ""
    if section_key_prefix_pg3 == "receive" and "pg3_receive_po_id_form_val" not in st.session_state: 
        st.session_state.pg3_receive_po_id_form_val = ""


st.title("🚚 Stock Movements Log")
st.write("Use this page to accurately record all changes to your inventory: goods received, adjustments, or wastage/spoilage.")
st.divider()

db_engine = connect_db()
if not db_engine: 
    st.error("❌ Database connection failed. Cannot proceed with stock movements.")
    st.stop() # Crucial: Stop execution if no DB engine

@st.cache_data(ttl=60)
def fetch_active_items_for_stock_mv_page_v3(_engine): # Unique cache function name
    items_df = item_service.get_all_items_with_stock(_engine, include_inactive=False)
    if not items_df.empty:
        return [(f"{r['name']} ({r['unit']})", r['item_id']) for _, r in items_df.sort_values('name').iterrows()]
    return []

active_item_options_pg3 = fetch_active_items_for_stock_mv_page_v3(db_engine) # Use new name
item_options_with_placeholder_pg3 = [placeholder_option_stock_pg3] + active_item_options_pg3 # Use new name

def update_selected_item_id_mv_page_v3(tuple_key_arg, id_key_arg): # Unique func name
    selected_tuple_val = st.session_state[tuple_key_arg]
    if selected_tuple_val and len(selected_tuple_val) == 2 and selected_tuple_val[1] != -1:
        st.session_state[id_key_arg] = selected_tuple_val[1]
    else:
        st.session_state[id_key_arg] = None

def set_active_section_mv_page_v3(): # Unique func name
    selected_display_name_val = st.session_state.stock_mv_radio_key_v10 # New key for radio
    st.session_state.active_stock_movement_section_pg3 = next(
        (key for key, display_name in SECTIONS.items() if display_name == selected_display_name_val), 
        SECTION_KEYS[0] 
    )

st.radio(
    "Select Movement Type:",
    options=SECTION_DISPLAY_NAMES,
    index=SECTION_KEYS.index(st.session_state.active_stock_movement_section_pg3),
    key="stock_mv_radio_key_v10", # New unique key
    on_change=set_active_section_mv_page_v3,
    horizontal=True,
)
st.divider()

active_section_prefix_pg3 = st.session_state.active_stock_movement_section_pg3 # Unique var
# Define current session state keys based on active section
current_item_tuple_key = f"pg3_{active_section_prefix_pg3}_item_tuple_val"
current_selected_item_id_key = f"pg3_{active_section_prefix_pg3}_selected_item_id"
current_reset_signal_key = f"pg3_{active_section_prefix_pg3}_reset_signal"
current_qty_ss_key = f"pg3_{active_section_prefix_pg3}_qty_form_val"
current_user_id_ss_key = f"pg3_{active_section_prefix_pg3}_user_id_form_val"
current_notes_ss_key = f"pg3_{active_section_prefix_pg3}_notes_form_val"
current_po_id_ss_key = "pg3_receive_po_id_form_val" # Specific to receive section

if st.session_state[current_reset_signal_key]:
    st.session_state[current_item_tuple_key] = placeholder_option_stock_pg3
    st.session_state[current_selected_item_id_key] = None
    st.session_state[current_qty_ss_key] = 0.0 
    st.session_state[current_user_id_ss_key] = ""
    st.session_state[current_notes_ss_key] = ""
    if active_section_prefix_pg3 == "receive":
        st.session_state[current_po_id_ss_key] = ""
    st.session_state[current_reset_signal_key] = False

st.subheader(SECTIONS[active_section_prefix_pg3])
if active_section_prefix_pg3 == "adjust": st.caption("Correct discrepancies or make other non-wastage adjustments.")
elif active_section_prefix_pg3 == "waste": st.caption("Record items damaged, expired, or otherwise unusable.")

item_col_pg3, _ = st.columns([2,1]) # Unique var
with item_col_pg3:
    default_item_tuple_pg3 = placeholder_option_stock_pg3 # Unique var
    if st.session_state.get(current_selected_item_id_key):
        item_id_to_find_pg3 = st.session_state[current_selected_item_id_key]
        found_tuple_pg3 = next((opt for opt in item_options_with_placeholder_pg3 if opt[1] == item_id_to_find_pg3), None)
        if found_tuple_pg3:
            default_item_tuple_pg3 = found_tuple_pg3
    try:
        current_item_idx_pg3 = item_options_with_placeholder_pg3.index(default_item_tuple_pg3)
    except ValueError:
        current_item_idx_pg3 = 0

    st.selectbox(
        "Item*", options=item_options_with_placeholder_pg3, format_func=lambda x: x[0],
        index=current_item_idx_pg3,
        key=current_item_tuple_key, # This key will store the selected tuple
        help=f"Select the item for {active_section_prefix_pg3}.",
        on_change=update_selected_item_id_mv_page_v3, 
        args=(current_item_tuple_key, current_selected_item_id_key)
    )
    selected_item_id_for_display_pg3 = st.session_state[current_selected_item_id_key]
    if selected_item_id_for_display_pg3 and selected_item_id_for_display_pg3 != -1:
        item_details = item_service.get_item_details(db_engine, selected_item_id_for_display_pg3)
        if item_details: st.caption(f"Current Stock: {item_details.get('current_stock', 0):.2f} {item_details.get('unit', '')}")
        else: st.caption("Could not fetch stock details.")
st.divider()

form_key_pg3 = f"pg3_{active_section_prefix_pg3}_form_v11" # New unique key
with st.form(form_key_pg3, clear_on_submit=False):
    qty_form_col_pg3, user_form_col_pg3 = st.columns(2) # Unique var names
    
    with qty_form_col_pg3:
        qty_label_pg3 = "Quantity*"
        min_widget_val_pg3 = 0.00 
        help_text_qty = "Enter the quantity for this movement."

        if active_section_prefix_pg3 == "receive":
            qty_label_pg3 = "Quantity Received*"; help_text_qty = "Quantity of goods received."
        elif active_section_prefix_pg3 == "adjust":
            qty_label_pg3 = "Quantity Adjusted*"; min_widget_val_pg3 = -float('inf'); help_text_qty = "Positive for increase, negative for decrease."
        elif active_section_prefix_pg3 == "waste":
            qty_label_pg3 = "Quantity Wasted*"; help_text_qty = "Quantity of items wasted."
        
        # Use the specific session state key for quantity
        st.session_state[current_qty_ss_key] = st.number_input(
            qty_label_pg3, 
            min_value=min_widget_val_pg3, 
            step=0.01, format="%.2f", 
            key=f"widget_pg3_{active_section_prefix_pg3}_qty", # Unique widget key
            value=float(st.session_state[current_qty_ss_key]), # Read from session state
            help=help_text_qty
        )

    with user_form_col_pg3:
        user_label_pg3 = "Recorder's Name/ID*" if active_section_prefix_pg3 != "receive" else "Receiver's Name/ID*"
        st.session_state[current_user_id_ss_key] = st.text_input(
            user_label_pg3, 
            key=f"widget_pg3_{active_section_prefix_pg3}_user_id", # Unique widget key
            placeholder="e.g., John Doe",
            value=st.session_state[current_user_id_ss_key], # Read from session state
            help="Person responsible for this stock movement."
        )

    if active_section_prefix_pg3 == "receive":
        st.session_state[current_po_id_ss_key] = st.text_input( # Use current_po_id_ss_key
            "Related PO ID (Optional, numeric part)", 
            key="widget_pg3_receive_po_id", # Unique widget key
            placeholder="e.g., 10023 (enter only the number)",
            value=st.session_state[current_po_id_ss_key], # Read from session state
            help="Numeric PO ID if this receipt is against a Purchase Order."
        )
    
    notes_label_pg3 = "Reason*" if active_section_prefix_pg3 in ["adjust","waste"] else "Notes / Remarks"
    notes_placeholder_pg3 = "Crucial: Explain reason..." if active_section_prefix_pg3 in ["adjust","waste"] else "e.g., Supplier name, Invoice #"
    
    st.session_state[current_notes_ss_key] = st.text_area(
        notes_label_pg3, 
        key=f"widget_pg3_{active_section_prefix_pg3}_notes", # Unique widget key
        placeholder=notes_placeholder_pg3,
        value=st.session_state[current_notes_ss_key], # Read from session state
        help="Provide details or reasons for this stock movement."
    )

    submit_button_label_pg3 = SECTIONS[active_section_prefix_pg3]
    if st.form_submit_button(submit_button_label_pg3): 
        # Retrieve values from session state for processing
        selected_item_id_submit = st.session_state[current_selected_item_id_key]
        qty_to_process_submit = st.session_state[current_qty_ss_key]
        user_id_to_process_submit = st.session_state[current_user_id_ss_key]
        notes_to_process_submit = st.session_state[current_notes_ss_key]
        
        valid_submission = True
        if not selected_item_id_submit or selected_item_id_submit == -1:
            st.warning("⚠️ Please select an item first."); valid_submission = False
        
        if active_section_prefix_pg3 == "adjust" and qty_to_process_submit == 0: 
            st.warning("⚠️ Quantity adjusted cannot be zero."); valid_submission = False
        elif active_section_prefix_pg3 != "adjust" and qty_to_process_submit <= 0: 
            st.warning("⚠️ Quantity must be greater than 0."); valid_submission = False
        
        if not user_id_to_process_submit.strip():
            st.warning(f"⚠️ {user_label_pg3.replace('*','')} required."); valid_submission = False
        if active_section_prefix_pg3 in ["adjust","waste"] and not notes_to_process_submit.strip():
            st.warning("⚠️ A reason/note is mandatory for adjustments and wastage."); valid_submission = False
        
        related_po_id_val_submit = None
        if active_section_prefix_pg3 == "receive" and st.session_state[current_po_id_ss_key].strip():
            try:
                related_po_id_val_submit = int(st.session_state[current_po_id_ss_key].strip())
            except ValueError:
                st.warning("⚠️ Related PO ID must be a numeric value if provided."); valid_submission = False
        
        if valid_submission:
            transaction_type_submit = ""
            quantity_change_val_submit = 0.0

            if active_section_prefix_pg3 == "receive":
                transaction_type_submit = TX_RECEIVING
                quantity_change_val_submit = abs(float(qty_to_process_submit))
            elif active_section_prefix_pg3 == "adjust":
                transaction_type_submit = TX_ADJUSTMENT
                quantity_change_val_submit = float(qty_to_process_submit)
            elif active_section_prefix_pg3 == "waste":
                transaction_type_submit = TX_WASTAGE
                quantity_change_val_submit = -abs(float(qty_to_process_submit))
            
            success = stock_service.record_stock_transaction(
                item_id=selected_item_id_submit,
                quantity_change=quantity_change_val_submit,
                transaction_type=transaction_type_submit,
                user_id=user_id_to_process_submit.strip(),
                related_po_id=related_po_id_val_submit, 
                notes=notes_to_process_submit.strip() or None,
                db_engine_param=db_engine 
            )
            if success:
                item_display_name_success = st.session_state[current_item_tuple_key][0]
                st.success(f"✅ Successfully recorded {active_section_prefix_pg3} for '{item_display_name_success}'.")
                fetch_active_items_for_stock_mv_page_v3.clear() # Use correct cache func name
                st.session_state[current_reset_signal_key] = True 
                st.rerun()
            else:
                st.error(f"❌ Failed to record stock {active_section_prefix_pg3}.")