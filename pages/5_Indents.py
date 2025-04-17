# pages/5_Indents.py
# Fresh implementation using No Form + st.data_editor + Department Filtering

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time
import numpy as np

# --- Page Config (REMOVED) ---

# Import shared functions
try:
    from item_manager_app import (
        connect_db, get_all_items_with_stock, generate_mrn, create_indent
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
# Use distinct keys for this clean version
STATE_PREFIX = "indent_clean_" # "nf" for "no form"
KEY_DEPT = f"{STATE_PREFIX}dept"
KEY_REQ_BY = f"{STATE_PREFIX}req_by"
KEY_REQ_DATE = f"{STATE_PREFIX}req_date"
KEY_NOTES = f"{STATE_PREFIX}notes"
KEY_EDITOR = f"{STATE_PREFIX}editor" # Key for the data_editor widget itself <-- ADDED THIS LINE
KEY_EDITOR_DF = f"{STATE_PREFIX}editor_df" # Holds the DataFrame for the editor
KEY_ITEM_OPTIONS = f"{STATE_PREFIX}item_options" # Holds [(display, id),...] for current dept
KEY_UNIT_MAP = f"{STATE_PREFIX}unit_map" # Holds {id: unit,...} for current dept
KEY_CURRENT_DEPT = f"{STATE_PREFIX}current_dept" # Tracks which dept's items are loaded

# --- Initialize Session State ---
def init_state():
    """Initializes session state variables if they don't exist."""
    state_defaults = {
        KEY_EDITOR_DF: pd.DataFrame([{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]),
        KEY_ITEM_OPTIONS: [],
        KEY_UNIT_MAP: {},
        KEY_CURRENT_DEPT: None,
        # Initialize keys for widgets used outside data editor too
        KEY_DEPT: None,
        KEY_REQ_BY: "",
        KEY_REQ_DATE: date.today() + timedelta(days=1),
        KEY_NOTES: "",
    }
    for key, default_value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# Call initialization function at the start
init_state()

# --- Reset Function ---
def reset_state():
    """Resets state variables to initial values."""
    # Reset custom state variables
    st.session_state[KEY_EDITOR_DF] = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )
    st.session_state[KEY_ITEM_OPTIONS] = []
    st.session_state[KEY_UNIT_MAP] = {}
    st.session_state[KEY_CURRENT_DEPT] = None
    # Reset widget values by clearing/setting keys
    # Use pop for safety, or direct set if preferred for defaults
    st.session_state.pop(KEY_DEPT, None)
    st.session_state.pop(KEY_REQ_BY, None)
    st.session_state.pop(KEY_REQ_DATE, None)
    st.session_state.pop(KEY_NOTES, None)
    # Optionally re-set date to default
    st.session_state[KEY_REQ_DATE] = date.today() + timedelta(days=1)


# --- Helper function for validation ---
def is_valid_item_tuple(val):
    """Checks if the value is a tuple representing a valid item selection."""
    if val is None: return False
    try:
        # Check tuple structure and ensure ID is int
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
        needs_item_reload = False
        if selected_dept and selected_dept != st.session_state.get(KEY_CURRENT_DEPT):
            st.session_state[KEY_CURRENT_DEPT] = selected_dept
            needs_item_reload = True
            st.session_state[KEY_ITEM_OPTIONS] = []
            st.session_state[KEY_UNIT_MAP] = {}
            st.session_state[KEY_EDITOR_DF] = pd.DataFrame([{"Item": None, "Quantity": 1.0, "Unit": ""}])

        # Load items if needed
        if selected_dept and not st.session_state.get(KEY_ITEM_OPTIONS):
            with st.spinner(f"Loading items for {selected_dept}..."):
                filtered_items_df = get_all_items_with_stock(db_engine, include_inactive=False, department=selected_dept)
            if not filtered_items_df.empty and 'item_id' in filtered_items_df.columns and 'name' in filtered_items_df.columns:
                temp_options = []
                temp_map = {}
                filtered_items_df['item_id'] = pd.to_numeric(filtered_items_df['item_id'], errors='coerce').fillna(-1).astype(int)
                valid_items = filtered_items_df[filtered_items_df['item_id'] != -1]
                for i, r in valid_items.iterrows():
                    display_name = f"{r['name']} ({r.get('unit', 'N/A')})"
                    temp_options.append((display_name, r['item_id']))
                    temp_map[r['item_id']] = r.get('unit', '')
                st.session_state[KEY_ITEM_OPTIONS] = temp_options
                st.session_state[KEY_UNIT_MAP] = temp_map
            else:
                 st.warning(f"No active items permitted for '{selected_dept}'.", icon="⚠️")
                 st.session_state[KEY_ITEM_OPTIONS] = []
                 st.session_state[KEY_UNIT_MAP] = {}
            # Rerun only if triggered by department change flag
            if needs_item_reload:
                 st.rerun()

        current_item_options = st.session_state[KEY_ITEM_OPTIONS]
        current_unit_map = st.session_state[KEY_UNIT_MAP]
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
             # --- Data Editor (No Form) ---
             edited_df = st.data_editor(
                 st.session_state[KEY_EDITOR_DF],
                 key=KEY_EDITOR, # Use the specific editor key defined above
                 num_rows="dynamic", use_container_width=True,
                 column_config={
                    "Item": st.column_config.SelectboxColumn("Select Item*", help="Choose item", width="large", options=current_item_options, required=False),
                    "Quantity": st.column_config.NumberColumn("Quantity*", help="Enter quantity", min_value=0.01, format="%.2f", step=0.1, required=False),
                    "Unit": st.column_config.TextColumn("Unit", help="Auto-filled", disabled=True, width="small"),
                 }, hide_index=True
             )

             # --- Update Session State DF AFTER editor interaction ---
             processed_rows = []
             data_changed = False # Flag to check if actual data differs
             if not edited_df.equals(st.session_state[KEY_EDITOR_DF]): # Check if editor output differs from state
                 data_changed = True
                 if not edited_df.empty:
                     for i, row in edited_df.iterrows():
                        new_row = row.to_dict()
                        selected_option = new_row.get("Item")
                        if is_valid_item_tuple(selected_option):
                            item_id = selected_option[1]
                            new_row["Unit"] = current_unit_map.get(item_id, '')
                        else:
                             new_row["Unit"] = ''
                        processed_rows.append(new_row)
                     st.session_state[KEY_EDITOR_DF] = pd.DataFrame(processed_rows) # Update state
                 else: # Handle editor being cleared
                      st.session_state[KEY_EDITOR_DF] = pd.DataFrame([{"Item": None, "Quantity": 1.0, "Unit": ""}])


        # --- Notes ---
        st.divider()
        notes = st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES)

        # --- Submit Button ---
        st.divider()
        submit_disabled = not selected_dept or not can_add_items # Also disable if no items can be added
        if st.button("Submit Indent Request", type="primary", disabled=submit_disabled):

            # Get values directly from state using keys
            current_req_by = st.session_state.get(KEY_REQ_BY, "").strip()
            current_req_date = st.session_state.get(KEY_REQ_DATE, date.today())
            current_notes = st.session_state.get(KEY_NOTES, "").strip()
            current_dept = selected_dept
            items_df_to_validate = st.session_state[KEY_EDITOR_DF].copy()

            # Validation
            items_df_validated_items = items_df_to_validate[items_df_to_validate['Item'].apply(is_valid_item_tuple)]
            items_df_validated_items['Quantity'] = pd.to_numeric(items_df_validated_items['Quantity'], errors='coerce')
            items_df_validated_items = items_df_validated_items.dropna(subset=['Quantity'])
            items_df_final = items_df_validated_items[items_df_validated_items['Quantity'] > 0]

            if not current_dept: st.warning("Select Department.", icon="⚠️")
            elif not current_req_by: st.warning("Enter Requester.", icon="⚠️")
            elif items_df_final.empty: st.warning("Add valid item(s) with quantity > 0.", icon="⚠️")
            elif items_df_final['Item'].apply(lambda x: x[1]).duplicated().any(): st.warning("Duplicate items found.", icon="⚠️")
            else:
                 item_list = [{"item_id": r['Item'][1], "requested_qty": float(r['Quantity']), "notes": ""} for i, r in items_df_final.iterrows()]
                 mrn = generate_mrn(engine=db_engine)
                 if not mrn: st.error("Failed to generate MRN.")
                 else:
                    indent_header = {
                        "mrn": mrn, "requested_by": current_req_by,
                        "department": current_dept, "date_required": current_req_date,
                        "status": "Submitted", "notes": current_notes
                    }
                    success = create_indent(engine=db_engine, indent_details=indent_header, item_list=item_list)
                    if success:
                        st.success(f"Indent '{mrn}' submitted!", icon="✅")
                        reset_state() # Call reset
                        time.sleep(0.5)
                        st.rerun() # Rerun to clear fields visually
                    else: st.error("Failed to submit Indent.", icon="❌")


    # --- Tabs 2 & 3 ---
    with tab_view: st.subheader("View Indents"); st.info("To be implemented.")
    with tab_process: st.subheader("Process Indents"); st.info("To be implemented.")
