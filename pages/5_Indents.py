# pages/5_Indents.py
# Fresh implementation: No Form, Looped Widgets, Callbacks for Rows
# Fixed reset function name mismatch

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time
import numpy as np

# --- Imports and Error Handling ---
try:
    # Ensure all necessary functions are imported from your main app file
    from item_manager_app import (
        connect_db,
        get_all_items_with_stock, # Needs to support department filtering
        generate_mrn,
        create_indent
    )
    # Placeholder for future functions if needed
    if 'get_indents' not in locals(): get_indents = lambda **kwargs: pd.DataFrame()
except ImportError as e:
    st.error(f"Import Error from item_manager_app.py: {e}. Ensure file exists and functions are defined.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import: {e}")
    st.stop()

# --- Constants ---
DEPARTMENTS = ["Kitchen", "Bar", "Housekeeping", "Admin", "Maintenance", "Service"]
# Use distinct keys for this fresh version
STATE_PREFIX = "indent_fresh_"
KEY_DEPT = f"{STATE_PREFIX}dept"
KEY_REQ_BY = f"{STATE_PREFIX}req_by"
KEY_REQ_DATE = f"{STATE_PREFIX}req_date"
KEY_NOTES = f"{STATE_PREFIX}notes"
# Session state keys for internal logic
KEY_ITEM_LIST = f"{STATE_PREFIX}item_list" # Holds list of item row dicts
KEY_NEXT_ITEM_ROW_KEY = f"{STATE_PREFIX}next_row_key" # Counter for unique row keys
KEY_ITEM_OPTIONS = f"{STATE_PREFIX}item_options" # Holds [(display, id),...] for current dept
KEY_CURRENT_DEPT = f"{STATE_PREFIX}current_dept" # Tracks which dept's items are loaded

# --- Initialize Session State ---
def init_state_fresh():
    """Initializes session state variables if they don't exist."""
    if KEY_ITEM_LIST not in st.session_state:
        st.session_state[KEY_ITEM_LIST] = [{"row_key": 0}]
    if KEY_NEXT_ITEM_ROW_KEY not in st.session_state:
        st.session_state[KEY_NEXT_ITEM_ROW_KEY] = 1
    if KEY_ITEM_OPTIONS not in st.session_state: st.session_state[KEY_ITEM_OPTIONS] = []
    if KEY_CURRENT_DEPT not in st.session_state: st.session_state[KEY_CURRENT_DEPT] = None
    if KEY_DEPT not in st.session_state: st.session_state[KEY_DEPT] = None
    if KEY_REQ_BY not in st.session_state: st.session_state[KEY_REQ_BY] = ""
    if KEY_REQ_DATE not in st.session_state: st.session_state[KEY_REQ_DATE] = date.today() + timedelta(days=1)
    if KEY_NOTES not in st.session_state: st.session_state[KEY_NOTES] = ""

# Call initialization function at the start
init_state_fresh()

# --- Callback Functions for Row Management ---
def add_row_callback():
    """Appends a new row structure to the item list state."""
    new_key = st.session_state[KEY_NEXT_ITEM_ROW_KEY]
    st.session_state[KEY_ITEM_LIST].append({"row_key": new_key})
    st.session_state[f"item_select_{new_key}"] = None
    st.session_state[f"item_qty_{new_key}"] = 1.0
    st.session_state[KEY_NEXT_ITEM_ROW_KEY] += 1

def remove_row_callback(row_key_to_remove):
    """Removes a row structure and its associated state keys."""
    st.session_state[KEY_ITEM_LIST] = [
        item_dict for item_dict in st.session_state[KEY_ITEM_LIST]
        if item_dict["row_key"] != row_key_to_remove
    ]
    st.session_state.pop(f"item_select_{row_key_to_remove}", None)
    st.session_state.pop(f"item_qty_{row_key_to_remove}", None)
    if not st.session_state[KEY_ITEM_LIST]:
         add_row_callback()

# --- Reset Function ---
# Renamed from reset_state_fresh to reset_state
def reset_state():
    """Resets all state for the indent creation page."""
    st.session_state[KEY_ITEM_LIST] = [{"row_key": 0}]
    st.session_state[KEY_NEXT_ITEM_ROW_KEY] = 1
    st.session_state[KEY_ITEM_OPTIONS] = []
    st.session_state[KEY_CURRENT_DEPT] = None
    st.session_state.pop(KEY_DEPT, None)
    st.session_state.pop(KEY_REQ_BY, None)
    st.session_state.pop(KEY_REQ_DATE, None)
    st.session_state.pop(KEY_NOTES, None)
    st.session_state[KEY_REQ_BY] = "" # Re-initialize defaults after pop
    st.session_state[KEY_REQ_DATE] = date.today() + timedelta(days=1)
    st.session_state[KEY_NOTES] = ""
    st.session_state.pop("item_select_0", None) # Clear initial row widgets too
    st.session_state.pop("item_qty_0", None)


# --- Helper function for validation ---
def is_valid_item_tuple_fresh(val):
    if val is None: return False
    try:
        return isinstance(val, tuple) and len(val) == 2 and isinstance(int(val[1]), int)
    except (TypeError, ValueError, IndexError): return False

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
        req_by = st.text_input("Requested By*", placeholder="Enter name", key=KEY_REQ_BY)
        req_date = st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today(), key=KEY_REQ_DATE)

        st.divider()
        st.markdown("**Add Items to Request:**")

        if not selected_dept:
            st.info("Select a department to load items.")
        elif not can_add_items:
             st.warning(f"No items available for {selected_dept}.")
        else:
             # --- Dynamic Item Rows ---
             hdr_cols = st.columns([4, 2, 1])
             hdr_cols[0].markdown("**Item**")
             hdr_cols[1].markdown("**Quantity**")

             # Use a copy to avoid issues if list modified during iteration (by remove callback)
             list_copy = st.session_state[KEY_ITEM_LIST][:]
             for i, item_dict in enumerate(list_copy):
                 item_key = item_dict["row_key"]
                 # Check if state exists for this key, initialize if not (e.g., after add_row)
                 if f"item_select_{item_key}" not in st.session_state: st.session_state[f"item_select_{item_key}"] = None
                 if f"item_qty_{item_key}" not in st.session_state: st.session_state[f"item_qty_{item_key}"] = 1.0

                 row_cols = st.columns([4, 2, 1])
                 with row_cols[0]:
                     st.selectbox(
                         f"Item Row {i+1}", options=current_item_options,
                         format_func=lambda x: x[0] if isinstance(x, tuple) else "Select...",
                         key=f"item_select_{item_key}",
                         index=None, # Let state handle value
                         label_visibility="collapsed"
                     )
                 with row_cols[1]:
                     st.number_input(
                         f"Qty Row {i+1}", min_value=0.01, step=0.1, format="%.2f",
                         key=f"item_qty_{item_key}",
                         # value=1.0, # Let state handle value
                         label_visibility="collapsed"
                     )
                 with row_cols[2]:
                     st.button(
                         "➖", key=f"remove_{item_key}",
                         on_click=remove_row_callback, args=(item_key,),
                         help="Remove this item row",
                         disabled=(len(st.session_state[KEY_ITEM_LIST]) <= 1)
                     )

             # --- Add Item Button ---
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

            # --- Process item rows from session state ---
            item_list_final = []
            processed_item_ids = set()
            duplicate_found = False
            invalid_row_found = False

            for item_dict in st.session_state[KEY_ITEM_LIST]:
                item_key = item_dict["row_key"]
                selected_item = st.session_state.get(f"item_select_{item_key}")
                quantity = st.session_state.get(f"item_qty_{item_key}")

                if is_valid_item_tuple_fresh(selected_item) and quantity is not None and pd.to_numeric(quantity, errors='coerce') > 0:
                    item_id = selected_item[1]
                    qty_float = float(quantity)
                    if item_id in processed_item_ids: duplicate_found = True; break
                    processed_item_ids.add(item_id)
                    item_list_final.append({"item_id": item_id, "requested_qty": qty_float, "notes": ""})
                elif selected_item is not None or (quantity is not None and quantity != 1.0):
                     invalid_row_found = True

            # --- Final Validation ---
            if not current_dept: st.warning("Select Department.", icon="⚠️")
            elif not current_req_by: st.warning("Enter Requester.", icon="⚠️")
            elif not item_list_final and invalid_row_found: st.warning("Found rows with invalid item/quantity.", icon="⚠️")
            elif not item_list_final: st.warning("Add at least one valid item row with quantity > 0.", icon="⚠️")
            elif duplicate_found: st.warning("Duplicate items found. Please remove or combine rows.", icon="⚠️")
            else:
                 mrn = generate_mrn(engine=db_engine)
                 if not mrn: st.error("Failed to generate MRN.")
                 else:
                    indent_header = {
                        "mrn": mrn, "requested_by": current_req_by,
                        "department": current_dept, "date_required": current_req_date,
                        "status": "Submitted", "notes": current_notes
                    }
                    success = create_indent(engine=db_engine, indent_details=indent_header, item_list=item_list_final)
                    if success:
                        st.success(f"Indent '{mrn}' submitted!", icon="✅")
                        reset_state() # Call reset using the CORRECT name
                        time.sleep(0.5)
                        st.rerun() # Rerun to clear fields visually
                    else: st.error("Failed to submit Indent.", icon="❌")


    # --- Tabs 2 & 3 ---
    with tab_view: st.subheader("View Indents"); st.info("To be implemented.")
    with tab_process: st.subheader("Process Indents"); st.info("To be implemented.")
