# app/pages/3_Stock_Movements.py
import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
from datetime import date 

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

placeholder_option_stock_pg3 = ("-- Select an Item --", -1) 

# --- Session State Initialization ---
if 'active_stock_movement_section_pg3' not in st.session_state: 
    st.session_state.active_stock_movement_section_pg3 = SECTION_KEYS[0]

for section_key_prefix_pg3 in SECTION_KEYS: 
    item_tuple_key_pg3 = f"pg3_{section_key_prefix_pg3}_item_tuple_val"
    selected_id_key_pg3 = f"pg3_{section_key_prefix_pg3}_selected_item_id"
    reset_signal_key_pg3 = f"pg3_{section_key_prefix_pg3}_reset_signal"
    qty_key_pg3 = f"pg3_{section_key_prefix_pg3}_qty_form_val"
    user_id_key_pg3 = f"pg3_{section_key_prefix_pg3}_user_id_form_val"
    notes_key_pg3 = f"pg3_{section_key_prefix_pg3}_notes_form_val"

    if item_tuple_key_pg3 not in st.session_state:
        st.session_state[item_tuple_key_pg3] = placeholder_option_stock_pg3
    if selected_id_key_pg3 not in st.session_state:
        st.session_state[selected_id_key_pg3] = None # Initialize to None
    if reset_signal_key_pg3 not in st.session_state:
        st.session_state[reset_signal_key_pg3] = False
    
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
    st.stop() 

@st.cache_data(ttl=60)
def fetch_active_items_for_stock_mv_page_v3(_engine): 
    items_df = item_service.get_all_items_with_stock(_engine, include_inactive=False)
    if not items_df.empty:
        return [(f"{r['name']} ({r['unit']})", r['item_id']) for _, r in items_df.sort_values('name').iterrows()]
    return []

active_item_options_pg3 = fetch_active_items_for_stock_mv_page_v3(db_engine) 
item_options_with_placeholder_pg3 = [placeholder_option_stock_pg3] + active_item_options_pg3 

def update_selected_item_id_mv_page_v3(tuple_key_arg, id_key_arg): 
    selected_tuple_val = st.session_state[tuple_key_arg]
    st.session_state[id_key_arg] = selected_tuple_val[1] if selected_tuple_val and selected_tuple_val[1] != -1 else None

def set_active_section_mv_page_v3(): 
    selected_display_name_val = st.session_state.stock_mv_radio_key_v10 
    st.session_state.active_stock_movement_section_pg3 = next(
        (key for key, display_name in SECTIONS.items() if display_name == selected_display_name_val), 
        SECTION_KEYS[0] 
    )
    # When section changes, reset the specific form fields for the NEW active section if needed,
    # or rely on the reset signal logic below. For now, let's ensure the reset signal works correctly.
    new_active_section_prefix = st.session_state.active_stock_movement_section_pg3
    st.session_state[f"pg3_{new_active_section_prefix}_reset_signal"] = True


st.radio(
    "Select Movement Type:",
    options=SECTION_DISPLAY_NAMES,
    index=SECTION_KEYS.index(st.session_state.active_stock_movement_section_pg3),
    key="stock_mv_radio_key_v10", 
    on_change=set_active_section_mv_page_v3,
    horizontal=True,
)
st.divider()

active_section_prefix_pg3 = st.session_state.active_stock_movement_section_pg3 
current_item_tuple_key = f"pg3_{active_section_prefix_pg3}_item_tuple_val"
current_selected_item_id_key = f"pg3_{active_section_prefix_pg3}_selected_item_id"
current_reset_signal_key = f"pg3_{active_section_prefix_pg3}_reset_signal"
current_qty_ss_key = f"pg3_{active_section_prefix_pg3}_qty_form_val"
current_user_id_ss_key = f"pg3_{active_section_prefix_pg3}_user_id_form_val"
current_notes_ss_key = f"pg3_{active_section_prefix_pg3}_notes_form_val"
current_po_id_ss_key = "pg3_receive_po_id_form_val" 

if st.session_state.get(current_reset_signal_key, False): # Check if key exists before accessing
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

item_col_pg3, _ = st.columns([2,1]) 
with item_col_pg3:
    # Determine default index for selectbox
    default_item_index_pg3 = 0
    current_selected_item_id_val = st.session_state.get(current_selected_item_id_key)
    if current_selected_item_id_val is not None:
        try:
            default_item_index_pg3 = [opt[1] for opt in item_options_with_placeholder_pg3].index(current_selected_item_id_val)
        except ValueError:
            default_item_index_pg3 = 0 # Fallback if ID not in options (e.g., item became inactive)
            # Optionally reset if item becomes invalid for selection
            # st.session_state[current_selected_item_id_key] = None 
            # st.session_state[current_item_tuple_key] = placeholder_option_stock_pg3


    st.selectbox(
        "Item*", options=item_options_with_placeholder_pg3, format_func=lambda x: x[0],
        index=default_item_index_pg3, # Use calculated index
        key=current_item_tuple_key, 
        help=f"Select the item for {active_section_prefix_pg3}.",
        on_change=update_selected_item_id_mv_page_v3, 
        args=(current_item_tuple_key, current_selected_item_id_key)
    )
    selected_item_id_for_display_pg3 = st.session_state.get(current_selected_item_id_key) # Use .get for safety
    if selected_item_id_for_display_pg3 and selected_item_id_for_display_pg3 != -1:
        item_details = item_service.get_item_details(db_engine, selected_item_id_for_display_pg3)
        if item_details: st.caption(f"Current Stock: {item_details.get('current_stock', 0):.2f} {item_details.get('unit', '')}")
        else: st.caption("Could not fetch stock details.")
st.divider()

form_key_pg3 = f"pg3_{active_section_prefix_pg3}_form_v12" # Incremented form key version
with st.form(form_key_pg3, clear_on_submit=False): # clear_on_submit=True will reset fields on successful submission
    qty_form_col_pg3, user_form_col_pg3 = st.columns(2) 
    
    with qty_form_col_pg3:
        qty_label_pg3 = "Quantity*"
        # Define a very large representable number for Streamlit if actual infinity is not supported
        PRACTICAL_MAX_NEGATIVE_NUMBER = -1.7976931348623157e+308 # Max negative for float64,
                                                            # Streamlit might have its own slightly different internal limit for JS

        min_widget_val_pg3 = 0.00 
        help_text_qty = "Enter the quantity for this movement."

        if active_section_prefix_pg3 == "receive":
            qty_label_pg3 = "Quantity Received*"; help_text_qty = "Quantity of goods received."
        elif active_section_prefix_pg3 == "adjust":
            qty_label_pg3 = "Quantity Adjusted*"; 
            min_widget_val_pg3 = PRACTICAL_MAX_NEGATIVE_NUMBER # MODIFIED HERE
            help_text_qty = "Positive for increase, negative for decrease."
        elif active_section_prefix_pg3 == "waste":
            qty_label_pg3 = "Quantity Wasted*"; help_text_qty = "Quantity of items wasted."
        
        # Read initial value from session state correctly
        initial_qty_value = float(st.session_state.get(current_qty_ss_key, 0.0))

        st.session_state[current_qty_ss_key] = st.number_input( # This is line 173 from the traceback
            qty_label_pg3, 
            min_value=min_widget_val_pg3, 
            step=0.01, format="%.2f", 
            key=f"widget_pg3_{active_section_prefix_pg3}_qty_v2", # Ensure key is unique per form instance
            value=initial_qty_value, 
            help=help_text_qty
        )

    with user_form_col_pg3:
        user_label_pg3 = "Recorder's Name/ID*" if active_section_prefix_pg3 != "receive" else "Receiver's Name/ID*"
        st.session_state[current_user_id_ss_key] = st.text_input(
            user_label_pg3, 
            key=f"widget_pg3_{active_section_prefix_pg3}_user_id_v2", 
            placeholder="e.g., John Doe",
            value=st.session_state.get(current_user_id_ss_key, ""), 
            help="Person responsible for this stock movement."
        )

    if active_section_prefix_pg3 == "receive":
        st.session_state[current_po_id_ss_key] = st.text_input( 
            "Related PO ID (Optional, numeric part)", 
            key="widget_pg3_receive_po_id_v2", 
            placeholder="e.g., 10023 (enter only the number)",
            value=st.session_state.get(current_po_id_ss_key, ""), 
            help="Numeric PO ID if this receipt is against a Purchase Order."
        )
    
    notes_label_pg3 = "Reason*" if active_section_prefix_pg3 in ["adjust","waste"] else "Notes / Remarks"
    notes_placeholder_pg3 = "Crucial: Explain reason..." if active_section_prefix_pg3 in ["adjust","waste"] else "e.g., Supplier name, Invoice #"
    
    st.session_state[current_notes_ss_key] = st.text_area(
        notes_label_pg3, 
        key=f"widget_pg3_{active_section_prefix_pg3}_notes_v2", 
        placeholder=notes_placeholder_pg3,
        value=st.session_state.get(current_notes_ss_key, ""), 
        help="Provide details or reasons for this stock movement."
    )

    submit_button_label_pg3 = SECTIONS[active_section_prefix_pg3]
    # Ensure st.form_submit_button is INSIDE the 'with st.form(...):' block
    submitted = st.form_submit_button(submit_button_label_pg3) 

    if submitted: 
        # Retrieve values from session state for processing
        selected_item_id_submit = st.session_state.get(current_selected_item_id_key)
        qty_to_process_submit = st.session_state.get(current_qty_ss_key, 0.0) # Use .get for safety
        user_id_to_process_submit = st.session_state.get(current_user_id_ss_key, "")
        notes_to_process_submit = st.session_state.get(current_notes_ss_key, "")
        
        valid_submission = True
        if not selected_item_id_submit or selected_item_id_submit == -1:
            st.warning("⚠️ Please select an item first."); valid_submission = False
        
        # Ensure qty_to_process_submit is float before comparison
        try:
            qty_float_submit = float(qty_to_process_submit)
            if active_section_prefix_pg3 == "adjust" and qty_float_submit == 0: 
                st.warning("⚠️ Quantity adjusted cannot be zero."); valid_submission = False
            elif active_section_prefix_pg3 != "adjust" and qty_float_submit <= 0: 
                st.warning("⚠️ Quantity must be greater than 0."); valid_submission = False
        except (ValueError, TypeError):
            st.warning("⚠️ Invalid quantity entered."); valid_submission = False

        
        if not user_id_to_process_submit.strip():
            st.warning(f"⚠️ {user_label_pg3.replace('*','').strip()} required."); valid_submission = False # Cleaned label
        if active_section_prefix_pg3 in ["adjust","waste"] and not notes_to_process_submit.strip():
            st.warning("⚠️ A reason/note is mandatory for adjustments and wastage."); valid_submission = False
        
        related_po_id_val_submit = None
        if active_section_prefix_pg3 == "receive" and st.session_state.get(current_po_id_ss_key, "").strip():
            try:
                related_po_id_val_submit = int(st.session_state.get(current_po_id_ss_key).strip())
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
                item_display_name_success_tuple = st.session_state.get(current_item_tuple_key)
                item_display_name_success = item_display_name_success_tuple[0] if item_display_name_success_tuple else "Selected Item"
                st.success(f"✅ Successfully recorded {active_section_prefix_pg3} for '{item_display_name_success}'.")
                fetch_active_items_for_stock_mv_page_v3.clear() 
                st.session_state[current_reset_signal_key] = True 
                # Set clear_on_submit=True in st.form OR manually reset fields after success
                # For clear_on_submit=False, manual reset for next entry in same section might be desired
                # The current_reset_signal_key should handle resetting fields upon next rerun if it's set.
                # If clear_on_submit=True is used in st.form, Streamlit handles field resets.
                # To keep fields for potential re-submission on error, clear_on_submit=False is fine.
                # To clear fields after SUCCESS (with clear_on_submit=False), do it here:
                st.session_state[current_qty_ss_key] = 0.0
                st.session_state[current_user_id_ss_key] = ""
                st.session_state[current_notes_ss_key] = ""
                if active_section_prefix_pg3 == "receive":
                     st.session_state[current_po_id_ss_key] = ""
                # Item selection can persist unless explicitly reset by user or section change.
                st.rerun()
            else:
                # Error message should be returned from service and displayed by UI
                st.error(f"❌ Failed to record stock {active_section_prefix_pg3}. Check console for details from service.")