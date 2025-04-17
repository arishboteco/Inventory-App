# pages/5_Indents.py
# Implementation: No Form, Looped Widgets, Callbacks for Rows, Dept Filtering
# Modified reset function to assign defaults instead of popping widget keys

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time
import numpy as np

# --- Imports and Error Handling ---
try:
    from item_manager_app import (
        connect_db, get_all_items_with_stock, generate_mrn, create_indent
    )
    if 'get_indents' not in locals(): get_indents = lambda **kwargs: pd.DataFrame()
except ImportError as e:
    st.error(f"Import Error from item_manager_app.py: {e}.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import: {e}")
    st.stop()

# --- Constants ---
DEPARTMENTS = ["Kitchen", "Bar", "Housekeeping", "Admin", "Maintenance", "Service"]
STATE_PREFIX = "indent_loop_v1_" # Keep prefix consistent for this version
KEY_DEPT = f"{STATE_PREFIX}dept"
KEY_REQ_BY = f"{STATE_PREFIX}req_by"
KEY_REQ_DATE = f"{STATE_PREFIX}req_date"
KEY_NOTES = f"{STATE_PREFIX}notes"
KEY_ITEM_LIST = f"{STATE_PREFIX}item_list"
KEY_NEXT_ITEM_ROW_KEY = f"{STATE_PREFIX}next_row_key"
KEY_ITEM_OPTIONS = f"{STATE_PREFIX}item_options"
KEY_CURRENT_DEPT = f"{STATE_PREFIX}current_dept"

# --- Initialize Session State ---
def init_state():
    """Initializes session state variables if they don't exist."""
    if KEY_ITEM_LIST not in st.session_state:
        st.session_state[KEY_ITEM_LIST] = [{"row_key": 0}]
        st.session_state[f"item_select_0"] = None
        st.session_state[f"item_qty_0"] = 1.0
    if KEY_NEXT_ITEM_ROW_KEY not in st.session_state: st.session_state[KEY_NEXT_ITEM_ROW_KEY] = 1
    if KEY_ITEM_OPTIONS not in st.session_state: st.session_state[KEY_ITEM_OPTIONS] = []
    if KEY_CURRENT_DEPT not in st.session_state: st.session_state[KEY_CURRENT_DEPT] = None
    # Initialize header widget keys if they don't exist
    if KEY_DEPT not in st.session_state: st.session_state[KEY_DEPT] = None
    if KEY_REQ_BY not in st.session_state: st.session_state[KEY_REQ_BY] = ""
    if KEY_REQ_DATE not in st.session_state: st.session_state[KEY_REQ_DATE] = date.today() + timedelta(days=1)
    if KEY_NOTES not in st.session_state: st.session_state[KEY_NOTES] = ""

# Call initialization function at the start
init_state()

# --- Callback Functions for Row Management ---
def add_row_callback():
    new_key = st.session_state[KEY_NEXT_ITEM_ROW_KEY]
    st.session_state[KEY_ITEM_LIST].append({"row_key": new_key})
    st.session_state[f"item_select_{new_key}"] = None
    st.session_state[f"item_qty_{new_key}"] = 1.0
    st.session_state[KEY_NEXT_ITEM_ROW_KEY] += 1

def remove_row_callback(row_key_to_remove):
    current_list = st.session_state[KEY_ITEM_LIST]
    if len(current_list) <= 1:
        st.toast("Cannot remove the last item row.", icon="⚠️"); return
    st.session_state[KEY_ITEM_LIST] = [d for d in current_list if d["row_key"] != row_key_to_remove]
    st.session_state.pop(f"item_select_{row_key_to_remove}", None)
    st.session_state.pop(f"item_qty_{row_key_to_remove}", None)

# --- Reset Function (MODIFIED) ---
def reset_state():
    """Resets all state for the indent creation page by assigning defaults."""
    # Get all current dynamic row keys before resetting the list
    keys_to_clear = [d["row_key"] for d in st.session_state.get(KEY_ITEM_LIST, [])]

    # Reset control and list state
    st.session_state[KEY_ITEM_LIST] = [{"row_key": 0}]
    st.session_state[KEY_NEXT_ITEM_ROW_KEY] = 1
    st.session_state[KEY_ITEM_OPTIONS] = []
    st.session_state[KEY_CURRENT_DEPT] = None

    # Reset header widget values by ASSIGNING defaults
    st.session_state[KEY_DEPT] = None
    st.session_state[KEY_REQ_BY] = ""
    st.session_state[KEY_REQ_DATE] = date.today() + timedelta(days=1) # Assign valid date
    st.session_state[KEY_NOTES] = ""

    # Clear dynamic widget keys that existed before reset using pop
    for k in keys_to_clear:
        st.session_state.pop(f"item_select_{k}", None)
        st.session_state.pop(f"item_qty_{k}", None)

    # Initialize state for the single remaining row (key 0)
    st.session_state["item_select_0"] = None
    st.session_state["item_qty_0"] = 1.0
    # No need to call init_state() again as we explicitly set defaults

# --- Helper function for validation ---
def is_valid_item_tuple(val):
    if val is None: return False
    try: return isinstance(val, tuple) and len(val) == 2 and isinstance(int(val[1]), int)
    except: return False

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
        # --- NO FORM WRAPPER ---

        # --- Department Selection ---
        dept_value_on_load = st.session_state.get(KEY_DEPT, None)
        dept_index = DEPARTMENTS.index(dept_value_on_load) if dept_value_on_load in DEPARTMENTS else None
        selected_dept = st.selectbox(
            "Requesting Department*", options=DEPARTMENTS, key=KEY_DEPT, index=dept_index,
            placeholder="Select department...", help="Select department to filter items below."
        )

        # --- Handle Department Change and Load Items ---
        if selected_dept and selected_dept != st.session_state.get(KEY_CURRENT_DEPT):
            st.session_state[KEY_CURRENT_DEPT] = selected_dept
            st.session_state[KEY_ITEM_OPTIONS] = []
            st.session_state[KEY_ITEM_LIST] = [{"row_key": 0}]
            st.session_state[KEY_NEXT_ITEM_ROW_KEY] = 1
            st.session_state["item_select_0"] = None
            st.session_state["item_qty_0"] = 1.0
            with st.spinner(f"Loading items for {selected_dept}..."):
                filtered_items_df = get_all_items_with_stock(db_engine, include_inactive=False, department=selected_dept)
            if not filtered_items_df.empty and 'item_id' in filtered_items_df.columns and 'name' in filtered_items_df.columns:
                temp_options = []
                filtered_items_df['item_id'] = pd.to_numeric(filtered_items_df['item_id'], errors='coerce').fillna(-1).astype(int)
                valid_items = filtered_items_df[filtered_items_df['item_id'] != -1]
                for i, r in valid_items.iterrows():
                    display_name = f"{r['name']} ({r.get('unit', 'N/A')})"
                    temp_options.append((display_name, r['item_id']))
                st.session_state[KEY_ITEM_OPTIONS] = temp_options
            else:
                 st.warning(f"No active items permitted for '{selected_dept}'.", icon="⚠️")
                 st.session_state[KEY_ITEM_OPTIONS] = []
            st.rerun()

        current_item_options = st.session_state[KEY_ITEM_OPTIONS]
        can_add_items = bool(current_item_options)

        # --- Other Header Inputs ---
        # Use default_value argument which reads from state if key exists
        req_by = st.text_input("Requested By*", placeholder="Enter name", key=KEY_REQ_BY)
        req_date = st.date_input("Date Required*", value=st.session_state[KEY_REQ_DATE], min_value=date.today(), key=KEY_REQ_DATE) # Read value from state

        st.divider()
        st.markdown("**Add Items to Request:**")

        if not selected_dept: st.info("Select a department to load items.")
        elif not can_add_items: st.warning(f"No items available for {selected_dept}.")
        else:
             # --- Dynamic Item Rows ---
             hdr_cols = st.columns([4, 2, 1])
             hdr_cols[0].markdown("**Item**")
             hdr_cols[1].markdown("**Quantity**")
             list_copy = st.session_state[KEY_ITEM_LIST][:]
             for i, item_dict in enumerate(list_copy):
                 item_key = item_dict["row_key"]
                 if f"item_select_{item_key}" not in st.session_state: st.session_state[f"item_select_{item_key}"] = None
                 if f"item_qty_{item_key}" not in st.session_state: st.session_state[f"item_qty_{item_key}"] = 1.0
                 row_cols = st.columns([4, 2, 1])
                 with row_cols[0]:
                     st.selectbox(f"Item Row {i+1}", options=current_item_options, format_func=lambda x: x[0] if isinstance(x, tuple) else "Select...", key=f"item_select_{item_key}", index=None, label_visibility="collapsed")
                 with row_cols[1]:
                     st.number_input(f"Qty Row {i+1}", min_value=0.01, step=0.1, format="%.2f", key=f"item_qty_{item_key}", label_visibility="collapsed")
                 with row_cols[2]:
                     st.button("➖", key=f"remove_{item_key}", on_click=remove_row_callback, args=(item_key,), help="Remove this item row", disabled=(len(st.session_state[KEY_ITEM_LIST]) <= 1))
             st.button("➕ Add Item Row", on_click=add_row_callback, disabled=not can_add_items)

        # --- Notes ---
        st.divider()
        notes = st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES)

        # --- Submit Button ---
        st.divider()
        submit_disabled = not selected_dept or not can_add_items
        if st.button("Submit Indent Request", type="primary", disabled=submit_disabled):
            current_req_by = st.session_state.get(KEY_REQ_BY, "").strip()
            current_req_date = st.session_state.get(KEY_REQ_DATE, date.today())
            current_notes = st.session_state.get(KEY_NOTES, "").strip()
            current_dept = selected_dept
            item_list_final, processed_item_ids, duplicate_found, invalid_row_found = [], set(), False, False
            for item_dict in st.session_state[KEY_ITEM_LIST]:
                item_key = item_dict["row_key"]
                selected_item = st.session_state.get(f"item_select_{item_key}")
                quantity = st.session_state.get(f"item_qty_{item_key}")
                if is_valid_item_tuple(selected_item) and quantity is not None:
                     qty_numeric = pd.to_numeric(quantity, errors='coerce')
                     if qty_numeric is not None and qty_numeric > 0:
                         item_id = selected_item[1]; qty_float = float(qty_numeric)
                         if item_id in processed_item_ids: duplicate_found = True; break
                         processed_item_ids.add(item_id)
                         item_list_final.append({"item_id": item_id, "requested_qty": qty_float, "notes": ""})
                     elif selected_item is not None: invalid_row_found = True
                elif selected_item is not None or (quantity is not None and quantity != 1.0): invalid_row_found = True

            if not current_dept: st.warning("Select Department.", icon="⚠️")
            elif not current_req_by: st.warning("Enter Requester.", icon="⚠️")
            elif not item_list_final and invalid_row_found: st.warning("Found rows with invalid item/quantity.", icon="⚠️")
            elif not item_list_final: st.warning("Add at least one valid item row with quantity > 0.", icon="⚠️")
            elif duplicate_found: st.warning("Duplicate items found. Please remove or combine rows.", icon="⚠️")
            else:
                 mrn = generate_mrn(engine=db_engine)
                 if not mrn: st.error("Failed to generate MRN.")
                 else:
                    indent_header = {"mrn": mrn, "requested_by": current_req_by, "department": current_dept, "date_required": current_req_date, "status": "Submitted", "notes": current_notes}
                    success = create_indent(engine=db_engine, indent_details=indent_header, item_list=item_list_final)
                    if success:
                        st.success(f"Indent '{mrn}' submitted!", icon="✅")
                        reset_state() # Call MODIFIED reset
                        time.sleep(0.5)
                        st.rerun() # Rerun to clear fields visually
                    else: st.error("Failed to submit Indent.", icon="❌")

    # --- Tabs 2 & 3 ---
    with tab_view: st.subheader("View Indents"); st.info("To be implemented.") # Placeholder
    with tab_process: st.subheader("Process Indents"); st.info("To be implemented.") # Placeholder

