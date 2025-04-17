# pages/5_Indents.py
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
        connect_db, get_all_items_with_stock, generate_mrn, create_indent,
        # get_indents, get_indent_details, update_indent_status, fulfill_indent_item, get_departments # Future
    )
    if 'get_indents' not in locals(): get_indents = lambda **kwargs: pd.DataFrame()
except ImportError as e:
    st.error(f"Import Error: {e}.")
    st.stop()

# --- Constants ---
DEPARTMENTS = ["Kitchen", "Bar", "Housekeeping", "Admin", "Maintenance", "Service"]
# Static Keys for widgets
KEY_DEPT_NF = "indent_dept_noform"
KEY_REQ_BY_NF = "indent_req_by_noform"
KEY_REQ_DATE_NF = "indent_req_date_noform"
KEY_EDITOR_NF = "indent_editor_noform"
KEY_NOTES_NF = "indent_notes_noform"

# --- Initialize Session State ---
# Store the data editor's dataframe
if 'indent_editor_df_nf' not in st.session_state:
    st.session_state.indent_editor_df_nf = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )
# Store fetched item details for lookup based on selected department
if 'indent_item_details_nf' not in st.session_state:
    st.session_state.indent_item_details_nf = {}
# Store currently selected department to detect changes
if 'indent_current_dept_nf' not in st.session_state:
    st.session_state.indent_current_dept_nf = None


# --- Reset Function ---
def reset_indent_state_noform():
    st.session_state.indent_editor_df_nf = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )
    st.session_state.indent_item_details_nf = {}
    st.session_state.indent_current_dept_nf = None
    # Reset widget values by clearing keys
    st.session_state.pop(KEY_DEPT_NF, None)
    st.session_state.pop(KEY_REQ_BY_NF, None)
    st.session_state.pop(KEY_REQ_DATE_NF, None)
    st.session_state.pop(KEY_NOTES_NF, None)
    # The editor dataframe state above handles the editor reset


# --- Helper function for validation ---
def is_valid_item_tuple_nf(val):
    if val is None: return False
    try:
        # Check tuple structure and ensure ID is int
        return isinstance(val, tuple) and len(val) == 2 and isinstance(int(val[1]), int)
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
        # Read potential value from state for persistence
        dept_value_on_load = st.session_state.get(KEY_DEPT_NF, None)
        dept_index = DEPARTMENTS.index(dept_value_on_load) if dept_value_on_load in DEPARTMENTS else None

        selected_dept = st.selectbox(
            "Requesting Department*", options=DEPARTMENTS,
            key=KEY_DEPT_NF, index=dept_index, placeholder="Select department...",
            help="Select department to filter items & record request."
        )

        # --- Handle Department Change and Load Items ---
        item_options_list = []
        item_unit_map = {}
        can_add_items = False

        # Detect if department changed OR if it's selected but details haven't been loaded yet
        if selected_dept and (selected_dept != st.session_state.get('indent_current_dept_nf') or not st.session_state.get('indent_item_details_nf')):
            st.session_state.indent_current_dept_nf = selected_dept
            st.session_state.indent_item_details_nf = {} # Clear old details
            with st.spinner(f"Loading items for {selected_dept}..."):
                filtered_items_df = get_all_items_with_stock(db_engine, include_inactive=False, department=selected_dept)
            if not filtered_items_df.empty and 'item_id' in filtered_items_df.columns and 'name' in filtered_items_df.columns:
                item_lookup_dict = {}
                filtered_items_df['item_id'] = pd.to_numeric(filtered_items_df['item_id'], errors='coerce').fillna(-1).astype(int)
                valid_items = filtered_items_df[filtered_items_df['item_id'] != -1]
                for i, r in valid_items.iterrows():
                    display_name = f"{r['name']} ({r.get('unit', 'N/A')})"
                    item_options_list.append((display_name, r['item_id']))
                    item_lookup_dict[r['item_id']] = r.get('unit', '') # Map ID to unit
                st.session_state.indent_item_details_nf = item_lookup_dict # Store unit map
                can_add_items = True
            else:
                 st.warning(f"No active items permitted for '{selected_dept}'.", icon="⚠️")
            # Reset the editor DF when department changes
            st.session_state.indent_editor_df_nf = pd.DataFrame([{"Item": None, "Quantity": 1.0, "Unit": ""}])
            st.rerun() # Rerun to update options and clear editor state visually

        # If department already selected and details loaded, just use them
        elif st.session_state.indent_current_dept_nf:
             selected_dept = st.session_state.indent_current_dept_nf # Ensure selected_dept is correct
             item_unit_map = st.session_state.get('indent_item_details_nf', {})
             # Rebuild options list from keys/values if needed, or fetch again if map empty? Let's assume map implies options exist
             # This part might need refinement - fetch items if map exists but options list is empty?
             # For now, assume if dept is set, we can proceed
             if item_unit_map: # Check if details were loaded previously
                 can_add_items = True
                 # Rebuild options list needed for the editor config
                 # This requires fetching item names again - inefficient.
                 # Better: Store item_options_list in state too? Or fetch if needed.
                 # Let's fetch again if options list is empty but dept is set
                 temp_items_df = get_all_items_with_stock(db_engine, include_inactive=False, department=selected_dept)
                 if not temp_items_df.empty:
                      temp_items_df['item_id'] = pd.to_numeric(temp_items_df['item_id'], errors='coerce').fillna(-1).astype(int)
                      valid_items = temp_items_df[temp_items_df['item_id'] != -1]
                      item_options_list = [(f"{r['name']} ({r.get('unit', 'N/A')})", r['item_id']) for i, r in valid_items.iterrows()]


        # --- Other Header Inputs ---
        req_by = st.text_input("Requested By*", placeholder="Enter name", key=KEY_REQ_BY_NF)
        req_date = st.date_input("Date Required*", value=st.session_state.get(KEY_REQ_DATE_NF, date.today() + timedelta(days=1)), min_value=date.today(), key=KEY_REQ_DATE_NF)

        st.divider()
        st.markdown("**Add Items to Request:**")

        if not selected_dept:
            st.info("Select a department to load items.")
        elif not can_add_items:
             st.warning(f"No items available for {selected_dept}.")
        else:
             # --- Data Editor (No Form) ---
             edited_df = st.data_editor(
                 st.session_state.indent_editor_df_nf, # Use stateful DataFrame
                 key=KEY_EDITOR_NF,
                 num_rows="dynamic", use_container_width=True,
                 column_config={
                    "Item": st.column_config.SelectboxColumn("Select Item*", help="Choose item", width="large", options=item_options_list, required=False),
                    "Quantity": st.column_config.NumberColumn("Quantity*", help="Enter quantity", min_value=0.01, format="%.2f", step=0.1, required=False),
                    "Unit": st.column_config.TextColumn("Unit", help="Auto-filled", disabled=True, width="small"),
                 }, hide_index=True
             )

             # --- Update Session State DF AFTER editor interaction ---
             # This ensures state reflects edits on the next rerun
             processed_rows = []
             if not edited_df.empty:
                 current_unit_map = st.session_state.get('indent_item_details_nf', {})
                 for i, row in edited_df.iterrows():
                    new_row = row.to_dict()
                    selected_option = new_row.get("Item")
                    if is_valid_item_tuple_nf(selected_option):
                        item_id = selected_option[1]
                        new_row["Unit"] = current_unit_map.get(item_id, '') # Use current map
                    else:
                         new_row["Unit"] = ''
                    processed_rows.append(new_row)
                 st.session_state.indent_editor_df_nf = pd.DataFrame(processed_rows)
             else: # Handle editor being cleared
                  st.session_state.indent_editor_df_nf = pd.DataFrame([{"Item": None, "Quantity": 1.0, "Unit": ""}])


             st.divider()
             notes = st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES_NF)

             # --- Submit Button ---
             st.divider()
             if st.button("Submit Indent Request", type="primary", disabled=(not selected_dept)):

                 # Get values directly from state/widgets for submission
                 current_req_by = st.session_state.get(KEY_REQ_BY_NF, "").strip()
                 current_req_date = st.session_state.get(KEY_REQ_DATE_NF, date.today())
                 current_notes = st.session_state.get(KEY_NOTES_NF, "").strip()
                 current_dept = selected_dept # Use the confirmed selected department
                 items_df_to_validate = st.session_state.indent_editor_df_nf.copy() # Use state DF

                 # Validation
                 items_df_validated_items = items_df_to_validate[items_df_to_validate['Item'].apply(is_valid_item_tuple_nf)]
                 items_df_validated_items['Quantity'] = pd.to_numeric(items_df_validated_items['Quantity'], errors='coerce')
                 items_df_validated_items = items_df_validated_items.dropna(subset=['Quantity'])
                 items_df_final = items_df_validated_items[items_df_validated_items['Quantity'] > 0]

                 if not current_dept: st.warning("Select Department.", icon="⚠️") # Should be blocked by button disable
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
                             reset_indent_state_noform() # Call reset
                             time.sleep(0.5)
                             st.rerun() # Rerun to clear fields
                         else: st.error("Failed to submit Indent.", icon="❌")


    # --- Tabs 2 & 3 ---
    with tab_view: st.subheader("View Indents"); st.info("To be implemented.")
    with tab_process: st.subheader("Process Indents"); st.info("To be implemented.")
