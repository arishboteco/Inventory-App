# pages/5_Indents.py
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time
import numpy as np

# --- Page Config (REMOVED) ---

# --- Imports and Error Handling ---
try:
    from item_manager_app import (
        connect_db, get_all_items_with_stock, generate_mrn, create_indent
    )
    # Placeholder for future functions if needed
    if 'get_indents' not in locals(): get_indents = lambda **kwargs: pd.DataFrame()
except ImportError as e:
    st.error(f"Import Error from item_manager_app.py: {e}. Ensure file exists and functions are defined.")
    st.stop()

# --- Constants ---
DEPARTMENTS = ["Kitchen", "Bar", "Housekeeping", "Admin", "Maintenance", "Service"]
# Use distinct keys for this version to avoid leftover state issues
STATE_PREFIX = "indent_nf_" # "nf" for "no form"
KEY_DEPT = f"{STATE_PREFIX}dept"
KEY_REQ_BY = f"{STATE_PREFIX}req_by"
KEY_REQ_DATE = f"{STATE_PREFIX}req_date"
KEY_NOTES = f"{STATE_PREFIX}notes"
KEY_EDITOR = f"{STATE_PREFIX}editor"
KEY_EDITOR_DF = f"{STATE_PREFIX}editor_df"
KEY_ITEM_OPTIONS = f"{STATE_PREFIX}item_options"
KEY_UNIT_MAP = f"{STATE_PREFIX}unit_map"
KEY_CURRENT_DEPT = f"{STATE_PREFIX}current_dept" # Internal state to track loaded dept

# --- Initialize Session State ---
def init_indent_state():
    """Initializes session state variables if they don't exist."""
    # Data editor's DataFrame
    if KEY_EDITOR_DF not in st.session_state:
        st.session_state[KEY_EDITOR_DF] = pd.DataFrame(
            [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
        )
    # Item options for the current department's dropdown
    if KEY_ITEM_OPTIONS not in st.session_state:
         st.session_state[KEY_ITEM_OPTIONS] = []
    # Map item IDs to units for the current department
    if KEY_UNIT_MAP not in st.session_state:
        st.session_state[KEY_UNIT_MAP] = {}
    # Control state for loaded department
    if KEY_CURRENT_DEPT not in st.session_state:
        st.session_state[KEY_CURRENT_DEPT] = None
    # Ensure keys for basic widgets exist (optional, .get handles missing keys too)
    if KEY_DEPT not in st.session_state: st.session_state[KEY_DEPT] = None
    if KEY_REQ_BY not in st.session_state: st.session_state[KEY_REQ_BY] = ""
    if KEY_REQ_DATE not in st.session_state: st.session_state[KEY_REQ_DATE] = date.today() + timedelta(days=1)
    if KEY_NOTES not in st.session_state: st.session_state[KEY_NOTES] = ""

# Call initialization function
init_indent_state()

# --- CORRECTED Reset Function ---
def reset_indent_state_noform():
    """Resets custom state variables for the indent form."""
    # Reset data editor's DataFrame state
    st.session_state.indent_editor_df_nf = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )
    # Reset custom state related to items/department
    st.session_state.indent_item_unit_map_nf = {}
    st.session_state.indent_current_dept_nf = None
    st.session_state.indent_item_options_nf = []
    # DO NOT pop or set widget keys (KEY_DEPT_NF, KEY_REQ_BY_NF etc.) here
# --- Helper function for validation ---
def is_valid_item_tuple(val):
    """Checks if the value is a tuple representing a valid item selection."""
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
        # Read potential value from state for persistence
        dept_value_on_load = st.session_state.get(KEY_DEPT, None)
        dept_index = DEPARTMENTS.index(dept_value_on_load) if dept_value_on_load in DEPARTMENTS else None

        selected_dept = st.selectbox(
            "Requesting Department*", options=DEPARTMENTS, index=dept_index,
            placeholder="Select department...", key=KEY_DEPT,
            help="Select department to filter items below."
        )

        # --- Handle Department Change and Load Items ---
        # Load/reload items if selected dept differs from the one items were loaded for
        if selected_dept and selected_dept != st.session_state.get(KEY_CURRENT_DEPT):
            st.session_state[KEY_CURRENT_DEPT] = selected_dept # Store the new dept
            st.session_state[KEY_ITEM_OPTIONS] = [] # Clear old options
            st.session_state[KEY_UNIT_MAP] = {} # Clear old map
            # Reset editor when department changes
            st.session_state[KEY_EDITOR_DF] = pd.DataFrame([{"Item": None, "Quantity": 1.0, "Unit": ""}])

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
                    temp_map[r['item_id']] = r.get('unit', '') # Map ID to unit
                st.session_state[KEY_ITEM_OPTIONS] = temp_options # Store new options
                st.session_state[KEY_UNIT_MAP] = temp_map # Store new map
                st.rerun() # Rerun NOW to update editor options
            else:
                 st.warning(f"No active items permitted for '{selected_dept}'.", icon="⚠️")
                 # State already cleared above, rerun will show warning

        # Get current options and map from state for editor config
        current_item_options = st.session_state.get(KEY_ITEM_OPTIONS, [])
        current_unit_map = st.session_state.get(KEY_UNIT_MAP, {})
        can_add_items = bool(current_item_options) # Enable editor if options exist

        # --- Other Header Inputs ---
        # These widgets manage their state via their key
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
             # Input DF comes from session state
             edited_df = st.data_editor(
                 st.session_state[KEY_EDITOR_DF],
                 key=KEY_EDITOR_NF, # Use a distinct key for the editor itself
                 num_rows="dynamic", use_container_width=True,
                 column_config={
                    "Item": st.column_config.SelectboxColumn("Select Item*", help="Choose item", width="large", options=current_item_options, required=False),
                    "Quantity": st.column_config.NumberColumn("Quantity*", help="Enter quantity", min_value=0.01, format="%.2f", step=0.1, required=False),
                    "Unit": st.column_config.TextColumn("Unit", help="Auto-filled", disabled=True, width="small"),
                 }, hide_index=True
             )

             # --- Update Session State DF AFTER editor interaction ---
             # Process edited_df to add units and save back to state
             processed_rows = []
             if not edited_df.empty:
                 for i, row in edited_df.iterrows():
                    new_row = row.to_dict()
                    selected_option = new_row.get("Item")
                    if is_valid_item_tuple(selected_option): # Use helper here too
                        item_id = selected_option[1]
                        new_row["Unit"] = current_unit_map.get(item_id, '') # Use current map
                    else:
                         new_row["Unit"] = ''
                    processed_rows.append(new_row)
                 # Update the state DataFrame that the editor reads from
                 st.session_state[KEY_EDITOR_DF] = pd.DataFrame(processed_rows)
             else: # Handle editor being cleared
                  st.session_state[KEY_EDITOR_DF] = pd.DataFrame([{"Item": None, "Quantity": 1.0, "Unit": ""}])


        # --- Notes ---
        st.divider()
        notes = st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES)

        # --- Submit Button ---
        st.divider()
        # Disable button if no department selected or no items available
        submit_disabled = not selected_dept or not can_add_items
        if st.button("Submit Indent Request", type="primary", disabled=submit_disabled):

            # Get values directly from state using keys for simple widgets
            current_req_by = st.session_state.get(KEY_REQ_BY, "").strip()
            current_req_date = st.session_state.get(KEY_REQ_DATE, date.today())
            current_notes = st.session_state.get(KEY_NOTES, "").strip()
            current_dept = selected_dept # Use the validated selected dept
            # Get data editor items from session state
            items_df_to_validate = st.session_state[KEY_EDITOR_DF].copy()

            # Validation
            items_df_validated_items = items_df_to_validate[items_df_to_validate['Item'].apply(is_valid_item_tuple)]
            items_df_validated_items['Quantity'] = pd.to_numeric(items_df_validated_items['Quantity'], errors='coerce')
            items_df_validated_items = items_df_validated_items.dropna(subset=['Quantity'])
            items_df_final = items_df_validated_items[items_df_validated_items['Quantity'] > 0]

            if not current_dept: st.warning("Select Department.", icon="⚠️") # Failsafe
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
                        reset_indent_state() # Call reset
                        time.sleep(0.5)
                        st.rerun() # Rerun to clear fields visually
                    else: st.error("Failed to submit Indent.", icon="❌")


    # --- Tabs 2 & 3 ---
    with tab_view: st.subheader("View Indents"); st.info("To be implemented.")
    with tab_process: st.subheader("Process Indents"); st.info("To be implemented.")
