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
# Static Keys for widgets outside grid
KEY_DEPT_AG = "indent_aggrid_dept"
KEY_REQ_BY_AG = "indent_aggrid_req_by"
KEY_REQ_DATE_AG = "indent_aggrid_req_date"
KEY_NOTES_AG = "indent_aggrid_notes"


# --- Initialize Session State ---
# Keep track of selected department
if 'aggrid_selected_dept' not in st.session_state: st.session_state.aggrid_selected_dept = None
# Store the grid data
if 'aggrid_indent_items_df' not in st.session_state:
    # Start with 1 empty row structure
    st.session_state.aggrid_indent_items_df = pd.DataFrame(
        [{"Item": None, "Quantity": None, "Unit": ""}],
        columns=["Item", "Quantity", "Unit"]
    )
# Store fetched item details for lookup
if 'aggrid_item_details' not in st.session_state: st.session_state.aggrid_item_details = {}


# --- Reset Function ---
def reset_aggrid_indent_form():
    st.session_state.aggrid_selected_dept = None
    st.session_state.aggrid_indent_items_df = pd.DataFrame(
        [{"Item": None, "Quantity": None, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )
    st.session_state.aggrid_item_details = {}
    # Reset other widgets by clearing their keys if they exist
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
        selected_dept = st.selectbox(
            "Requesting Department*", options=DEPARTMENTS,
            key=KEY_DEPT_AG, index=None, placeholder="Select department...",
            help="Select the department requesting items."
        )
        # Update selected dept in state if changed
        if selected_dept != st.session_state.aggrid_selected_dept:
            st.session_state.aggrid_selected_dept = selected_dept
            # Reset grid when department changes
            st.session_state.aggrid_indent_items_df = pd.DataFrame(
                [{"Item": None, "Quantity": None, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
            )
            st.rerun() # Rerun to load correct items

        # --- Other Header Inputs ---
        req_by = st.text_input("Requested By*", placeholder="Enter name", key=KEY_REQ_BY_AG)
        req_date = st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today(), key=KEY_REQ_DATE_AG)

        st.divider()
        st.markdown("**Add Items to Request:**")

        # --- Load Items based on Selected Department ---
        item_options_display_list = []
        item_lookup_dict = {} # Maps display string back to id/unit

        if st.session_state.aggrid_selected_dept:
            with st.spinner(f"Loading items for {st.session_state.aggrid_selected_dept}..."):
                filtered_items_df = get_all_items_with_stock(
                    db_engine, include_inactive=False,
                    department=st.session_state.aggrid_selected_dept
                )
            if not filtered_items_df.empty and 'item_id' in filtered_items_df.columns and 'name' in filtered_items_df.columns:
                # Create list of display strings for dropdown, store details for lookup
                for i, r in filtered_items_df.iterrows():
                    display_name = f"{r['name']} ({r.get('unit', 'N/A')})"
                    item_options_display_list.append(display_name)
                    item_lookup_dict[display_name] = {"id": r['item_id'], "unit": r.get('unit', '')}
                # Store lookup dict in session state for use during submission
                st.session_state.aggrid_item_details = item_lookup_dict

            else:
                 st.warning(f"No active items permitted for '{st.session_state.aggrid_selected_dept}'.", icon="⚠️")
                 st.session_state.aggrid_item_details = {} # Clear lookup if no items
        else:
            st.info("Select a department to load and add items.")
            st.session_state.aggrid_item_details = {} # Clear lookup if no dept

        # --- Configure AgGrid ---
        gb = GridOptionsBuilder.from_dataframe(st.session_state.aggrid_indent_items_df)

        gb.configure_column(
            "Item",
            cellEditor='agSelectCellEditor', # Use a dropdown editor
            cellEditorParams={'values': item_options_display_list}, # Populate with filtered display names
            editable=True,
            width=350
        )
        gb.configure_column(
            "Quantity",
            editable=True,
            type=["numericColumn", "numberColumnFilter", "customNumericFormat"],
            precision=2, # Set precision for numeric input
            width=100
        )
        gb.configure_column("Unit", editable=False, width=80)

        # Enable adding/deleting rows via context menu (more advanced)
        # gb.configure_grid_options(rowSelection='single', enableRangeSelection=True) # Example options
        # gb.configure_grid_options(suppressRowClickSelection=True, stopEditingWhenCellsLoseFocus=True)

        gridOptions = gb.build()

        # --- Display AgGrid ---
        # Cannot add/delete rows easily without buttons/callbacks outside grid
        # User needs to edit the existing rows (initially 1 blank row)
        st.caption("Edit quantity and select items below. Add more rows if needed (manually for now).") # Placeholder text
        grid_response = AgGrid(
            st.session_state.aggrid_indent_items_df,
            gridOptions=gridOptions,
            data_return_mode=DataReturnMode.AS_INPUT, # Get data as displayed
            update_mode=GridUpdateMode.MODEL_CHANGED, # Update state as user types
            allow_unsafe_jscode=True, # Needed for some features like custom formatting or editors
            enable_enterprise_modules=False,
            key='indent_aggrid_editor', # Unique key
            # Set height or use theme default
            height=200,
            width='100%',
            reload_data=True # Try to force reload if data changes
        )

        # --- IMPORTANT: Update session state with grid changes ---
        # Do this *after* the AgGrid call so edits are reflected on next rerun
        if grid_response['data'] is not None:
             current_grid_df = grid_response['data']
             # Simple way to add a blank row if user might need more (needs better UI)
             if not current_grid_df.empty and current_grid_df.iloc[-1]['Item'] is not None:
                  blank_row = pd.DataFrame([{"Item": None, "Quantity": None, "Unit": ""}], columns=["Item", "Quantity", "Unit"])
                  current_grid_df = pd.concat([current_grid_df, blank_row], ignore_index=True)

             st.session_state.aggrid_indent_items_df = current_grid_df


        # --- Notes ---
        st.divider()
        notes = st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES_AG)

        # --- Submit Button (outside grid) ---
        if st.button("Submit Indent Request", type="primary", disabled=(not st.session_state.aggrid_selected_dept)):

            # Get other values
            current_req_by = st.session_state.get(KEY_REQ_BY_AG, "").strip()
            current_req_date = st.session_state.get(KEY_REQ_DATE_AG, date.today())
            current_notes = st.session_state.get(KEY_NOTES_AG, "").strip()
            current_dept = st.session_state.aggrid_selected_dept # Already validated above basically

            # Get data from grid state and process it
            items_df_to_validate = st.session_state.aggrid_indent_items_df.copy()
            item_list = []
            validation_warning = None

            # Filter rows with selected item and valid quantity
            valid_rows = items_df_to_validate.dropna(subset=['Item', 'Quantity'])
            valid_rows = valid_rows[pd.to_numeric(valid_rows['Quantity'], errors='coerce').fillna(0) > 0]

            item_ids_added = set() # To check for duplicates

            if not valid_rows.empty:
                for i, row in valid_rows.iterrows():
                    item_display_name = row['Item']
                    qty = pd.to_numeric(row['Quantity'], errors='coerce')

                    # Lookup item details based on display name
                    item_details = st.session_state.aggrid_item_details.get(item_display_name)

                    if item_details and qty is not None and qty > 0:
                         item_id = item_details['id']
                         if item_id in item_ids_added:
                              validation_warning = "Duplicate items found. Please combine quantities."
                              break # Stop processing on first duplicate
                         item_list.append({"item_id": item_id, "requested_qty": qty, "notes": ""})
                         item_ids_added.add(item_id)
                    # else: Allow skipping rows that aren't fully valid

            # Final Validation
            if not current_dept: validation_warning = "Select Department."
            elif not current_req_by: validation_warning = "Enter Requester Name/ID."
            elif not item_list: validation_warning = "Add at least one valid item with quantity > 0."
            # Duplicate check already handled above

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
