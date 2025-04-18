# pages/5_Indents.py – full file with sys.path and _engine fix

# ─── Ensure repo root is on sys.path ─────────────────────────────────
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
# ────────────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time
import numpy as np

# --- Imports and Error Handling ---
try:
    from item_manager_app import (
        connect_db,
        fetch_data, # Needed by fetch_indent_page_data
        get_all_items_with_stock, # Will receive _engine fix
        generate_mrn,             # Does not need fix (not cached)
        create_indent,            # Does not need fix (not cached)
        get_indents,              # Will receive _engine fix
        get_distinct_departments_from_items, # Will receive _engine fix
        ALL_INDENT_STATUSES,
        STATUS_SUBMITTED # Import default status
    )
except ImportError as e:
    st.error(f"Import error from item_manager_app.py: {e}. Ensure it's in the parent directory.")
    st.stop()
except Exception as e:
    st.error(f"Unexpected error during import: {e}")
    st.stop()

# --- Page Setup ---
st.set_page_config(layout="wide")
st.header("🛒 Material Indents")
db_engine = connect_db() # Keep original name for connection variable
if not db_engine:
    st.error("Database connection failed.")
    st.stop()

# --- Session State Initialization for Create Indent ---
# Use more specific keys to avoid potential future conflicts across tabs/pages
if 'create_indent_rows' not in st.session_state:
    st.session_state.create_indent_rows = [{'id': 0}] # Start with one row
if 'create_indent_next_row_id' not in st.session_state:
    st.session_state.create_indent_next_row_id = 1
if 'create_indent_selected_department' not in st.session_state:
    st.session_state.create_indent_selected_department = None

# --- Fetch Data needed across Tabs (Cached) ---
@st.cache_data(ttl=120)
def fetch_indent_page_data(_engine): # MODIFIED: _engine
    """Fetches data needed for the indent page (items, departments)."""
    # Pass _engine to backend functions expecting _engine
    items = get_all_items_with_stock(_engine, include_inactive=False)
    departments = get_distinct_departments_from_items(_engine)
    # Pass _engine to fetch_data (which expects 'engine', but receives _engine here)
    indent_info_df = fetch_data(_engine, "SELECT DISTINCT status, department FROM indents")
    statuses = ["All"] + sorted(indent_info_df['status'].unique().tolist()) if not indent_info_df.empty else ["All"]
    view_departments = ["All"] + sorted(indent_info_df['department'].unique().tolist()) if not indent_info_df.empty else ["All"]

    return items, departments, statuses, view_departments

# Pass original 'db_engine' variable here; fetch_indent_page_data receives it as _engine
items_df, create_dept_options, view_status_options, view_dept_options = fetch_indent_page_data(db_engine)

# --- Callbacks for Create Indent ---
def add_indent_row():
    new_row_id = st.session_state.create_indent_next_row_id
    st.session_state.create_indent_rows.append({'id': new_row_id})
    st.session_state.create_indent_next_row_id += 1

def remove_indent_row(row_id):
    st.session_state.create_indent_rows = [row for row in st.session_state.create_indent_rows if row['id'] != row_id]
    # Clean up session state for removed row widgets if necessary (optional)
    keys_to_remove = [key for key in st.session_state if key.startswith(f"create_item_{row_id}_")]
    for key in keys_to_remove:
        del st.session_state[key]

def department_changed():
    # Store selected department for filtering items
    st.session_state.create_indent_selected_department = st.session_state.get('create_indent_department_select')
    # Reset item selections or rows if department changes? Optional UX decision.
    # For now, just update state. Filtering happens during rendering.

# --- Tabs ---
tab_create, tab_view, tab_process = st.tabs([
    "📝 Create New Indent", "📊 View Indents", "⚙️ Process Indent (Future)"
])

# ============================
# 📝 CREATE NEW INDENT TAB
# ============================
with tab_create:
    st.subheader("Create a New Material Request")

    # --- Indent Header ---
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            # Use a unique key for the widget
            requested_by = st.text_input("Requested By*", key="create_indent_requested_by_input")
        with col2:
            # Use dynamically fetched departments
            if not create_dept_options:
                st.warning("No departments found linked to active items. Cannot create indent.")
                selected_dept = None
            else:
                # Find index for current session state value, default to 0 if not found or None
                current_dept_val = st.session_state.create_indent_selected_department
                try:
                    dept_index = create_dept_options.index(current_dept_val) if current_dept_val in create_dept_options else 0
                except ValueError:
                     dept_index = 0 # Fallback if value somehow not in list

                selected_dept = st.selectbox(
                    "Requesting Department*",
                    create_dept_options,
                    key='create_indent_department_select',
                    index=dept_index,
                    on_change=department_changed,
                    placeholder="Select department..."
                )
                # Ensure session state is updated immediately (on_change handles rerun)
                if selected_dept != st.session_state.create_indent_selected_department:
                     st.session_state.create_indent_selected_department = selected_dept
            # Assign current value AFTER widget rendering and state update
            current_selected_dept = st.session_state.create_indent_selected_department

        with col3:
            # Use unique key
            date_required = st.date_input(
                "Date Required*",
                datetime.now().date() + timedelta(days=1),
                key="create_indent_date_required_input"
            )

        notes_header = st.text_area("Indent Notes (Optional)", key="create_indent_notes_header_input", height=75)

    st.subheader("Indent Items")

    # --- Filter items based on selected department ---
    filtered_items_df = pd.DataFrame() # Initialize empty
    if current_selected_dept and not items_df.empty:
        # Standardized parsing: assumes comma-separated string in DB
        def is_dept_permitted(permitted_str):
            if pd.isna(permitted_str) or not isinstance(permitted_str, str) or not permitted_str.strip():
                return False
            permitted_list = [d.strip() for d in permitted_str.split(',') if d.strip()]
            return current_selected_dept in permitted_list

        mask = items_df['permitted_departments'].apply(is_dept_permitted)
        filtered_items_df = items_df[mask].copy() # Create a copy to avoid modifying original


    # --- Dynamic Item Rows ---
    item_rows_data = []
    if not filtered_items_df.empty:
        item_options = filtered_items_df[['item_id', 'name', 'unit']].to_dict('records')
        item_display_options = {item['item_id']: f"{item['name']} ({item['unit']})" for item in item_options}
        item_unit_map = {item['item_id']: item['unit'] for item in item_options}

        # Header Row (Optional but good UX)
        header_cols = st.columns([3, 1, 1, 3, 1]) # Adjust ratios as needed
        header_cols[0].write("**Item**")
        header_cols[1].write("**Unit**")
        header_cols[2].write("**Req. Qty***")
        header_cols[3].write("**Item Notes**")
        header_cols[4].write("**Action**")
        st.markdown("---") # Visual separator

        for i, row_state in enumerate(st.session_state.create_indent_rows):
            row_id = row_state['id']
            # Use unique keys incorporating row_id
            key_base = f"create_item_{row_id}"

            cols = st.columns([3, 1, 1, 3, 1]) # Align with header

            with cols[0]:
                # Try to preserve selection on rerun if item still valid for dept
                current_item_selection = st.session_state.get(f"{key_base}_select", None)
                valid_item_ids = list(item_display_options.keys())
                try:
                   item_index = valid_item_ids.index(current_item_selection) if current_item_selection in valid_item_ids else None
                except ValueError:
                    item_index = None # Not found

                selected_item_id = st.selectbox(
                    f"Item##{key_base}_select",
                    options=valid_item_ids,
                    format_func=lambda x: item_display_options.get(x, "Select..."),
                    label_visibility="collapsed",
                    key=f"{key_base}_select",
                    index=item_index,
                    placeholder="Select item..."
                )

            with cols[1]:
                unit = item_unit_map.get(selected_item_id, "")
                st.text_input(f"Unit##{key_base}_unit", value=unit, key=f"{key_base}_unit_display", disabled=True, label_visibility="collapsed")

            with cols[2]:
                requested_qty = st.number_input(
                    f"Qty##{key_base}_qty",
                    min_value=0.01,
                    step=1.0,
                    value=float(st.session_state.get(f"{key_base}_qty", 1.0)), # Preserve value on rerun
                    format="%.2f",
                    label_visibility="collapsed",
                    key=f"{key_base}_qty"
                )

            with cols[3]:
                item_notes = st.text_input(f"Notes##{key_base}_notes", key=f"{key_base}_notes", label_visibility="collapsed")

            with cols[4]:
                disable_remove = len(st.session_state.create_indent_rows) <= 1
                st.button("➖", key=f"{key_base}_remove", on_click=remove_indent_row, args=(row_id,), disabled=disable_remove, help="Remove item row")

            # Collect data only if an item is selected
            if selected_item_id:
                item_rows_data.append({
                    'item_id': selected_item_id,
                    'requested_qty': requested_qty,
                    'notes': item_notes.strip() or None,
                    'row_id': row_id # Keep track for validation messages
                })

    else:
        if current_selected_dept:
            st.warning(f"No active items found permitted for the selected department: '{current_selected_dept}'. Cannot add items.")
        else:
            st.warning("Please select a requesting department to see available items.")


    # --- Action Buttons ---
    st.markdown("---") # Visual separator
    col_add, col_submit = st.columns([1, 10])
    with col_add:
        # Disable Add if no items available for the selected department
        st.button("➕ Add Item", key="create_indent_add_item_btn", on_click=add_indent_row, disabled=filtered_items_df.empty)

    with col_submit:
        # Disable submit if no items added or header invalid
        can_submit = bool(item_rows_data and requested_by and current_selected_dept and date_required)
        submit_indent = st.button("✅ Submit Indent", key="create_indent_submit_btn", type="primary", disabled=not can_submit)

    # --- Indent Submission Logic ---
    if submit_indent:
        is_valid = True
        validation_errors = []

        # Re-validate header just in case
        if not requested_by: validation_errors.append("'Requested By' field cannot be empty."); is_valid = False
        if not current_selected_dept: validation_errors.append("'Requesting Department' must be selected."); is_valid = False
        if not date_required: validation_errors.append("'Date Required' must be selected."); is_valid = False

        # Validate items (check collected data)
        if not item_rows_data:
            validation_errors.append("At least one valid item must be added to the indent.")
            is_valid = False
        else:
            seen_item_ids = set()
            for idx, item_data in enumerate(item_rows_data):
                # Basic checks (already filtered by selection, but good practice)
                if not item_data.get('item_id'):
                    validation_errors.append(f"Row {idx + 1}: An item must be selected.")
                    is_valid = False
                elif item_data['item_id'] in seen_item_ids:
                    item_name = item_display_options.get(item_data['item_id'], f"ID {item_data['item_id']}")
                    validation_errors.append(f"Row {idx + 1}: Item '{item_name}' is duplicated.")
                    is_valid = False
                else:
                    seen_item_ids.add(item_data['item_id'])

                if not item_data.get('requested_qty') or item_data['requested_qty'] <= 0:
                    item_name = item_display_options.get(item_data['item_id'], f"ID {item_data['item_id']}")
                    validation_errors.append(f"Row {idx + 1}: Quantity for '{item_name}' must be greater than 0.")
                    is_valid = False

        if not is_valid:
            st.error("Indent validation failed:\n" + "\n".join(f"- {e}" for e in validation_errors))
        else:
            # Proceed with submission
            with st.spinner("Submitting Indent..."):
                try:
                    # 1. Generate MRN (Pass original db_engine)
                    new_mrn = generate_mrn(db_engine)
                    if not new_mrn:
                        st.error("Failed to generate MRN. Indent not created.")
                    else:
                        # 2. Prepare data for create_indent
                        indent_data = {
                            'mrn': new_mrn,
                            'requested_by': requested_by.strip(),
                            'department': current_selected_dept,
                            'date_required': date_required,
                            'notes': notes_header.strip() or None,
                            'status': STATUS_SUBMITTED # Default status
                        }
                        # Prepare items data (filter out unnecessary keys like row_id)
                        items_to_submit = [
                            {'item_id': item['item_id'], 'requested_qty': item['requested_qty'], 'notes': item['notes']}
                            for item in item_rows_data
                        ]

                        # 3. Call create_indent function (Pass original db_engine)
                        success, message = create_indent(db_engine, indent_data, items_to_submit)

                        if success:
                            st.success(f"Indent {new_mrn} created successfully!")
                            # Clear form / reset state
                            st.session_state.create_indent_rows = [{'id': 0}]
                            st.session_state.create_indent_next_row_id = 1
                            st.session_state.create_indent_selected_department = None
                            # Clear widget states manually by resetting keys (or use st.form clear_on_submit=True if applicable)
                            # For non-form elements, we often rely on rerun and default values
                            # Clear specific input keys if needed:
                            if 'create_indent_requested_by_input' in st.session_state: del st.session_state['create_indent_requested_by_input']
                            if 'create_indent_notes_header_input' in st.session_state: del st.session_state['create_indent_notes_header_input']
                            # Clear item row states explicitly
                            keys_to_clear = [k for k in st.session_state if k.startswith("create_item_")]
                            for k in keys_to_clear:
                                 del st.session_state[k]
                            fetch_indent_page_data.clear() # Clear cached data
                            st.rerun()

                        else:
                            st.error(f"Failed to create indent: {message}")

                except Exception as e:
                    st.error(f"An unexpected error occurred during submission: {e}")


# ============================
# 📊 VIEW INDENTS TAB
# ============================
with tab_view:
    st.subheader("View Submitted Indents")

    # --- Filters ---
    st.write("Apply filters to find specific indents:")
    filt_col1, filt_col2, filt_col3 = st.columns(3)

    with filt_col1:
        filter_mrn = st.text_input("Filter by MRN (contains)", key="view_filter_mrn")

    with filt_col2:
        filter_dept = st.selectbox(
            "Filter by Department",
            options=view_dept_options, # Use departments fetched from existing indents
            key="view_filter_dept",
            index=0 # Default to "All"
        )

    with filt_col3:
        filter_status = st.selectbox(
            "Filter by Status",
            options=view_status_options, # Use statuses fetched from existing indents
            key="view_filter_status",
            index=0 # Default to "All"
        )

    # Date Filter (placed below other filters)
    today_view = datetime.now().date()
    default_start_view = today_view - timedelta(days=90) # Default to last 90 days
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        filter_date_from = st.date_input("Submitted From", value=None, key="view_filter_date_from", help="Leave blank for no start date limit.")
    with date_col2:
        filter_date_to = st.date_input("Submitted To", value=None, key="view_filter_date_to", help="Leave blank for no end date limit.")

    # Basic date range validation
    indents_df = pd.DataFrame() # Initialize empty
    if filter_date_from and filter_date_to and filter_date_from > filter_date_to:
        st.warning("'Submitted From' date cannot be after 'Submitted To' date.")
        # Avoid calling backend with invalid range; display empty dataframe
    else:
        # --- Fetch and Display Data ---
        dept_arg = filter_dept if filter_dept != "All" else None
        status_arg = filter_status if filter_status != "All" else None
        mrn_arg = filter_mrn.strip() if filter_mrn else None

        # Pass original 'db_engine' variable here; get_indents receives it as _engine
        indents_df = get_indents(
            engine=db_engine, # MODIFIED: Pass original variable name
            mrn_filter=mrn_arg,
            dept_filter=dept_arg,
            status_filter=status_arg,
            date_start_filter=filter_date_from,
            date_end_filter=filter_date_to
        )

    st.divider()
    # Display result or info message
    if indents_df.empty:
         st.info("No indents found matching the selected criteria.")
    else:
        st.success(f"Found {len(indents_df)} indent(s).")
        st.dataframe(
            indents_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "indent_id": None, # Hide internal ID
                "mrn": st.column_config.TextColumn("MRN", help="Material Request Note ID", width="medium"),
                "requested_by": st.column_config.TextColumn("Requested By", width="small"),
                "department": st.column_config.TextColumn("Department", width="small"),
                "date_required": st.column_config.DateColumn("Date Required", format="YYYY-MM-DD", width="small"),
                "date_submitted": st.column_config.DatetimeColumn("Submitted On", format="YYYY-MM-DD HH:mm", width="medium"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "item_count": st.column_config.NumberColumn("# Items", help="Number of unique items in this indent", width="small"),
                "indent_notes": st.column_config.TextColumn("Indent Notes", width="large")
            },
            column_order=[ # Define the order of columns
                "mrn", "department", "requested_by", "date_required", "date_submitted",
                "status", "item_count", "indent_notes"
            ]
        )

# ============================
# ⚙️ PROCESS INDENT TAB
# ============================
with tab_process:
    st.subheader("Process Indent (Future Implementation)")
    st.info("This section will allow viewing indent details, marking items as fulfilled, and updating indent status.")
    # Placeholder for future functionality:
    # 1. Select an indent (e.g., by MRN from View tab or dropdown)
    # 2. Display indent header details
    # 3. Display indent items in an editable format (e.g., st.data_editor or custom rows)
    #    - Show Item Name, Requested Qty, Notes
    #    - Add input for Fulfilled Qty
    #    - Add input for Store Notes (optional)
    # 4. Button to "Update Fulfilled Quantities" -> Update indent_items table
    # 5. Button/Selectbox to change Indent Status (e.g., Processing, Completed, Cancelled) -> Update indents table
    # 6. (Optional) Button to "Complete & Record Stock Issue" -> Update status, record negative stock transactions in stock_transactions table based on fulfilled quantities.