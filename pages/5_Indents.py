# pages/5_Indents.py
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time

# --- Page Config (REMOVED) ---

# Import shared functions
try:
    from item_manager_app import (
        connect_db, get_all_items_with_stock, generate_mrn, create_indent,
        # get_indents, get_indent_details, update_indent_status, fulfill_indent_item, get_departments # Future
    )
    if 'get_indents' not in locals(): get_indents = lambda **kwargs: pd.DataFrame()
except ImportError as e:
    st.error(f"Import Error: {e}.")
    st.stop()

# --- Constants ---
DEPARTMENTS = ["Kitchen", "Bar", "Housekeeping", "Admin", "Maintenance", "Service"]
# Static Keys
KEY_DEPT = "indent_req_dept"
KEY_REQ_BY = "indent_req_by"
KEY_REQ_DATE = "indent_req_date"
KEY_NOTES = "indent_notes"
KEY_FORM = "new_indent_form"
# Keys for simplified item entry
KEY_ITEM_SELECT = "indent_item_select"
KEY_ITEM_QTY = "indent_item_qty"


# --- Initialize Session State ---
if 'indent_dept_confirmed' not in st.session_state: st.session_state.indent_dept_confirmed = False
if 'indent_selected_dept' not in st.session_state: st.session_state.indent_selected_dept = None
# REMOVED: indent_items_df - no longer using data editor state here

# --- Simplified Reset Function ---
def reset_indent_form_state():
    st.session_state.indent_dept_confirmed = False
    st.session_state.indent_selected_dept = None
    # Explicitly reset widget values in state using static keys
    st.session_state[KEY_DEPT] = None
    st.session_state[KEY_REQ_BY] = ""
    st.session_state[KEY_REQ_DATE] = date.today() + timedelta(days=1)
    st.session_state[KEY_NOTES] = ""
    # Reset simplified item widgets
    st.session_state[KEY_ITEM_SELECT] = None
    st.session_state[KEY_ITEM_QTY] = 1.0 # Reset qty to default


# --- Page Content ---
st.header("🛒 Material Indents")
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed.")
    st.stop()
else:
    tab_create, tab_view, tab_process = st.tabs([
        "📝 Create New Indent", "📊 View Indents", "⚙️ Process Indent (Future)"
    ])

    with tab_create:
        st.subheader("Create a New Material Request")

        with st.form(KEY_FORM, clear_on_submit=False):
            confirm_dept_button = False
            submit_indent_button = False
            change_dept_button = False

            st.markdown("**Step 1: Select Department**")
            current_selected_dept = st.session_state.get('indent_selected_dept', None)

            dept_selectbox_val = st.selectbox(
                "Requesting Department*", options=DEPARTMENTS,
                index=DEPARTMENTS.index(current_selected_dept) if current_selected_dept in DEPARTMENTS else None,
                placeholder="Select department...", key=KEY_DEPT,
                disabled=st.session_state.indent_dept_confirmed
            )

            if not st.session_state.indent_dept_confirmed:
                confirm_dept_button = st.form_submit_button("Confirm Department & Load Items")
            if st.session_state.indent_dept_confirmed:
                 change_dept_button = st.form_submit_button("Change Department", type="secondary")

            st.divider()

            items_loaded_successfully = False
            item_options_list = [] # Will still hold [(display, id), ...]

            if st.session_state.indent_dept_confirmed:
                st.markdown(f"**Step 2: Add Items for {st.session_state.indent_selected_dept} Department**")
                with st.spinner(f"Loading items for {st.session_state.indent_selected_dept}..."):
                    filtered_items_df = get_all_items_with_stock(
                        db_engine, include_inactive=False,
                        department=st.session_state.indent_selected_dept
                    )
                if filtered_items_df.empty:
                    st.warning(f"No active items permitted for '{st.session_state.indent_selected_dept}'.", icon="⚠️")
                else:
                    items_loaded_successfully = True
                    if 'item_id' in filtered_items_df.columns and 'name' in filtered_items_df.columns:
                        # Still need the options list for the selectbox
                        item_options_list = [(f"{r['name']} ({r.get('unit', 'N/A')})", r['item_id']) for i, r in filtered_items_df.iterrows()]
                        # No item_unit_map needed for this simplified version

                # --- Display Rest of Form Fields ---
                c2, c3 = st.columns(2)
                with c2: st.text_input("Requested By*", placeholder="Enter name", key=KEY_REQ_BY)
                with c3: st.date_input("Date Required*", value=st.session_state.get(KEY_REQ_DATE, date.today() + timedelta(days=1)), min_value=date.today(), key=KEY_REQ_DATE)

                st.markdown("**Add Item to Request (Simplified):**")
                if not items_loaded_successfully:
                    st.info("No items available to add for the selected department.")
                else:
                    # --- SIMPLIFIED ITEM ENTRY ---
                    item_c1, item_c2 = st.columns([3, 1])
                    with item_c1:
                        st.selectbox(
                            "Select Item*",
                            options=item_options_list,
                            format_func=lambda x: x[0] if isinstance(x, tuple) else x, # Show display name
                            key=KEY_ITEM_SELECT,
                            index=None, # Default to empty selection
                            placeholder="Choose an item...",
                            disabled=not items_loaded_successfully
                        )
                    with item_c2:
                        st.number_input(
                            "Quantity*",
                            min_value=0.01,
                            step=0.1,
                            format="%.2f",
                            key=KEY_ITEM_QTY,
                            disabled=not items_loaded_successfully
                        )
                    # --- END SIMPLIFIED ITEM ENTRY ---

                st.divider()
                st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES)
                submit_indent_button = st.form_submit_button("Submit Full Indent Request", disabled=not items_loaded_successfully, type="primary")

            # --- Logic after the form definition ---
            if change_dept_button:
                 reset_indent_form_state()
                 st.rerun()

            elif confirm_dept_button:
                selected_dept_val = st.session_state.get(KEY_DEPT)
                if not selected_dept_val: st.warning("Please select department first.")
                else:
                    st.session_state.indent_selected_dept = selected_dept_val
                    st.session_state.indent_dept_confirmed = True
                    # Reset simplified item widgets when dept confirmed
                    st.session_state[KEY_ITEM_SELECT] = None
                    st.session_state[KEY_ITEM_QTY] = 1.0
                    st.rerun()

            elif submit_indent_button:
                if not st.session_state.indent_dept_confirmed: st.error("Department not confirmed.")
                else:
                    # Get values using static keys
                    current_req_by = st.session_state.get(KEY_REQ_BY, "").strip()
                    current_req_date = st.session_state.get(KEY_REQ_DATE, date.today())
                    current_notes = st.session_state.get(KEY_NOTES, "").strip()
                    # Get simplified item details
                    selected_item_tuple = st.session_state.get(KEY_ITEM_SELECT)
                    selected_qty = st.session_state.get(KEY_ITEM_QTY, 0.0)

                    # Validation
                    if not current_req_by: st.warning("Enter Requester Name/ID.", icon="⚠️")
                    elif not selected_item_tuple or not isinstance(selected_item_tuple, tuple): # Check item selected
                         st.warning("Please select a valid item.", icon="⚠️")
                    elif selected_qty <= 0: # Check quantity
                         st.warning("Please enter a quantity greater than 0.", icon="⚠️")
                    else:
                         # Prepare item list (with only one item)
                         item_list = [{
                             "item_id": selected_item_tuple[1], # Get ID from tuple
                             "requested_qty": selected_qty,
                             "notes": ""
                         }]

                         # Proceed with backend call
                         mrn = generate_mrn(engine=db_engine)
                         if not mrn: st.error("Failed to generate MRN.")
                         else:
                            indent_header = {
                                "mrn": mrn, "requested_by": current_req_by,
                                "department": st.session_state.indent_selected_dept,
                                "date_required": current_req_date, "status": "Submitted",
                                "notes": current_notes
                            }
                            success = create_indent(engine=db_engine, indent_details=indent_header, item_list=item_list)
                            if success:
                                st.success(f"Indent '{mrn}' submitted!", icon="✅")
                                reset_indent_form_state()
                                time.sleep(0.5)
                                st.rerun()
                            else: st.error("Failed to submit Indent.", icon="❌")

    # --- Tabs 2 & 3 ---
    with tab_view: st.subheader("View Indents"); st.info("To be implemented.")
    with tab_process: st.subheader("Process Indents"); st.info("To be implemented.")
