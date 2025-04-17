# pages/5_Indents.py
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time
# AgGrid Imports
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode

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
KEY_DEPT_AG = "indent_aggrid_dept"
KEY_REQ_BY_AG = "indent_aggrid_req_by"
KEY_REQ_DATE_AG = "indent_aggrid_req_date"
KEY_NOTES_AG = "indent_aggrid_notes"
KEY_GRID_AG = "indent_aggrid_editor" # Key for the grid itself


# --- Initialize Session State ---
# Store the grid data (initialize only if not present)
if 'aggrid_indent_items_df' not in st.session_state:
    st.session_state.aggrid_indent_items_df = pd.DataFrame(
        [{"Item": None, "Quantity": None, "Unit": ""}], # Start with one blank row
        columns=["Item", "Quantity", "Unit"]
    )
# Store fetched item details for lookup based on selected department
if 'aggrid_item_details' not in st.session_state:
    st.session_state.aggrid_item_details = {}
# Store currently selected department to detect changes
if 'aggrid_current_dept' not in st.session_state:
    st.session_state.aggrid_current_dept = None


# --- Reset Function ---
def reset_aggrid_indent_form():
    st.session_state.aggrid_indent_items_df = pd.DataFrame(
        [{"Item": None, "Quantity": None, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )
    st.session_state.aggrid_item_details = {}
    st.session_state.aggrid_current_dept = None
    # Reset widget values by clearing keys (safe default)
    st.session_state.pop(KEY_DEPT_AG, None)
    st.session_state.pop(KEY_REQ_BY_AG, None)
    st.session_state.pop(KEY_REQ_DATE_AG, None)
    st.session_state.pop(KEY_NOTES_AG, None)


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
        # Use session state to retain selection across reruns
        selected_dept = st.selectbox(
            "Requesting Department*", options=DEPARTMENTS,
            key=KEY_DEPT_AG,
            index=DEPARTMENTS.index(st.session_state.aggrid_current_dept) if st.session_state.aggrid_current_dept in DEPARTMENTS else None,
            placeholder="Select department...",
            help="Select the department requesting items."
        )

        # --- Handle Department Change ---
        # Check if department selection changed from last run
        if selected_dept != st.session_state.aggrid_current_dept:
            st.session_state.aggrid_current_dept = selected_dept
            # Clear previous item details and grid data when department changes
            st.session_state.aggrid_item_details = {}
            st.session_state.aggrid_indent_items_df = pd.DataFrame(
                 [{"Item": None, "Quantity": None, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
             )
            st.rerun() # Rerun immediately to load items for new dept

        # --- Other Header Inputs ---
        req_by = st.text_input("Requested By*", placeholder="Enter name", key=KEY_REQ_BY_AG)
        req_date = st.date_input("Date Required*", value=st.session_state.get(KEY_REQ_DATE_AG, date.today() + timedelta(days=1)), min_value=date.today(), key=KEY_REQ_DATE_AG)

        st.divider()
        st.markdown("**Add Items to Request:**")

        # --- Load Items based on Selected Department ---
        item_options_display_list = []
        can_add_items = False

        if st.session_state.aggrid_current_dept: # Only load if a department is selected
            # Attempt to retrieve from state first (might be populated in previous run)
            item_lookup_dict = st.session_state.get('aggrid_item_details', {})
            if not item_lookup_dict: # If not in state, fetch now
                with st.spinner(f"Loading items for {st.session_state.aggrid_current_dept}..."):
                    filtered_items_df = get_all_items_with_stock(
                        db_engine, include_inactive=False,
                        department=st.session_state.aggrid_current_dept
                    )
                if not filtered_items_df.empty and 'item_id' in filtered_items_df.columns and 'name' in filtered_items_df.columns:
                    for i, r in filtered_items_df.iterrows():
                        display_name = f"{r['name']} ({r.get('unit', 'N/A')})"
                        # Add display name for dropdown options
                        item_options_display_list.append(display_name)
                        # Store details needed for lookup
                        item_lookup_dict[display_name] = {"id": r['item_id'], "unit": r.get('unit', '')}
                    st.session_state.aggrid_item_details = item_lookup_dict # Store in state
                    can_add_items = True
                else:
                     st.warning(f"No active items permitted for '{st.session_state.aggrid_current_dept}'.", icon="⚠️")
                     st.session_state.aggrid_item_details = {} # Clear lookup
            else: # Already have lookup in state, just rebuild display list
                 item_options_display_list = list(item_lookup_dict.keys())
                 can_add_items = True
        else:
            st.info("Select a department to load and add items.")
            st.session_state.aggrid_item_details = {} # Clear lookup

        # --- Configure AgGrid ---
        # Ensure DataFrame exists in state before building options
        if 'aggrid_indent_items_df' not in st.session_state:
             st.session_state.aggrid_indent_items_df = pd.DataFrame([{"Item": None, "Quantity": None, "Unit": ""}])

        gb = GridOptionsBuilder.from_dataframe(st.session_state.aggrid_indent_items_df)
        gb.configure_column(
            "Item",
            cellEditor='agSelectCellEditor',
            cellEditorParams={'values': item_options_display_list}, # Use filtered display names
            editable=can_add_items, # Only editable if items loaded
            width=350
        )
        gb.configure_column(
            "Quantity", editable=can_add_items, type=["numericColumn", "numberColumnFilter", "customNumericFormat"],
            precision=2, width=100
        )
        gb.configure_column("Unit", editable=False, width=80)
        # Make grid editable even if only one row initially
        gb.configure_grid_options(singleClickEdit=True)
        gridOptions = gb.build()

        # --- Display AgGrid ---
        st.caption("Select item and edit quantity. (Manual row add/delete not implemented yet)")
        grid_response = AgGrid(
            st.session_state.aggrid_indent_items_df,
            gridOptions=gridOptions,
            data_return_mode=DataReturnMode.AS_INPUT,
            update_mode=GridUpdateMode.MODEL_CHANGED, # Update state on cell change
            allow_unsafe_jscode=True,
            enable_enterprise_modules=False,
            key=KEY_GRID_AG,
            reload_data=True, # Force reload if underlying data changes
            # Set height or use theme default
            height=200, width='100%',
            theme="streamlit" # Use streamlit theme
        )

        # --- IMPORTANT: Update session state DF with changes from grid ---
        if grid_response['data'] is not None:
            # Check if data returned is different from state to avoid unnecessary updates/reruns
            # Comparing DataFrames can be tricky, use a simple length check or checksum if needed
            # For now, just assign back, accepting potential extra reruns
             st.session_state.aggrid_indent_items_df = grid_response['data']

        # --- Add Row Button (Basic Example) ---
        # This is outside the grid, modifies state, causing grid reload
        if st.button("➕ Add Item Row", disabled=not can_add_items):
             new_row = pd.DataFrame([{"Item": None, "Quantity": None, "Unit": ""}], columns=["Item", "Quantity", "Unit"])
             st.session_state.aggrid_indent_items_df = pd.concat([st.session_state.aggrid_indent_items_df, new_row], ignore_index=True)
             st.rerun()

        # --- Notes ---
        st.divider()
        notes = st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES_AG)

        # --- Submit Button ---
        st.divider()
        if st.button("Submit Indent Request", type="primary", disabled=(not st.session_state.aggrid_current_dept)):

            # Get values from widgets via state
            current_req_by = st.session_state.get(KEY_REQ_BY_AG, "").strip()
            current_req_date = st.session_state.get(KEY_REQ_DATE_AG, date.today())
            current_notes = st.session_state.get(KEY_NOTES_AG, "").strip()
            current_dept = st.session_state.aggrid_current_dept # Already validated

            # Get data from grid state and process
            items_df_to_validate = st.session_state.aggrid_indent_items_df.copy()
            item_list = []
            validation_warning = None
            processed_indices = set() # Keep track of rows processed

            # Filter valid rows from grid data
            valid_grid_rows = items_df_to_validate.dropna(subset=['Item', 'Quantity']) # Must have item selected and qty entered
            valid_grid_rows = valid_grid_rows[pd.to_numeric(valid_grid_rows['Quantity'], errors='coerce').fillna(0) > 0] # Qty > 0

            item_ids_added = set() # Check for duplicates based on item ID

            if not valid_grid_rows.empty:
                current_item_lookup = st.session_state.get('aggrid_item_details', {}) # Use lookup from state
                for index, row in valid_grid_rows.iterrows():
                    item_display_name = row['Item']
                    qty = pd.to_numeric(row['Quantity'], errors='coerce') # Already validated > 0

                    # Lookup item details based on display name
                    item_details = current_item_lookup.get(item_display_name)

                    if item_details:
                         item_id = item_details['id']
                         if item_id in item_ids_added:
                              validation_warning = f"Duplicate item found: '{item_display_name}'. Combine quantities."
                              break
                         item_list.append({"item_id": item_id, "requested_qty": qty, "notes": ""})
                         item_ids_added.add(item_id)
                         processed_indices.add(index) # Mark row as processed
                    # else: Item name from grid not found in lookup (shouldn't happen if dropdown populated correctly)

            # Final Validation
            if not current_dept: validation_warning = "Select Department."
            elif not current_req_by: validation_warning = "Enter Requester Name/ID."
            elif not item_list: validation_warning = "Add at least one valid item with quantity > 0."
            # Duplicate check happened above

            if validation_warning:
                st.warning(validation_warning, icon="⚠️")
            else:
                # --- Prepare & Execute Backend Call ---
                 mrn = generate_mrn(engine=db_engine)
                 if not mrn: st.error("Failed to generate MRN.")
                 else:
                    indent_header = {
                        "mrn": mrn, "requested_by": current_req_by,
                        "department": current_dept,
                        "date_required": current_req_date, "status": "Submitted",
                        "notes": current_notes
                    }
                    success = create_indent(engine=db_engine, indent_details=indent_header, item_list=item_list)
                    if success:
                        st.success(f"Indent '{mrn}' submitted!", icon="✅")
                        reset_aggrid_indent_form() # Call reset
                        time.sleep(0.5)
                        st.rerun() # Rerun to clear form visually
                    else: st.error("Failed to submit Indent.", icon="❌")


    # --- Tabs 2 & 3 ---
    with tab_view: st.subheader("View Indents"); st.info("To be implemented.")
    with tab_process: st.subheader("Process Indents"); st.info("To be implemented.")
