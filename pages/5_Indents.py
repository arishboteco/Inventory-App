# pages/5_Indents.py – full file with date string fix applied to user's latest version

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
        get_all_items_with_stock, # Uses _engine fix
        generate_mrn,             # No cache
        create_indent,            # No cache
        get_indents,              # Uses _engine fix, accepts date strings
        get_distinct_departments_from_items, # Uses _engine fix
        ALL_INDENT_STATUSES,
        STATUS_SUBMITTED # Import default status
    )
except ImportError as e:
    st.error(f"Import error from item_manager_app.py: {e}. Ensure it's in the parent directory.")
    st.stop()
except Exception as e:
    st.error(f"Unexpected error during import: {e}")
    st.stop()

# --- Constants (Using user's provided constants) ---
DEPARTMENTS = ["Kitchen", "Bar", "Housekeeping", "Admin", "Maintenance", "Service"] # User's version still used this

# --- Page Setup ---
st.set_page_config(layout="wide")
st.header("🛒 Material Indents")
db_engine = connect_db() # Keep original name for connection variable
if not db_engine:
    st.error("Database connection failed.")
    st.stop()

# --- Session State Initialization for Create Indent ---
if 'create_indent_rows' not in st.session_state: st.session_state.create_indent_rows = [{'id': 0}]
if 'create_indent_next_row_id' not in st.session_state: st.session_state.create_indent_next_row_id = 1
# Note: User's uploaded file didn't have create_indent_selected_department state, but adding it back based on logic below
if 'create_indent_selected_department' not in st.session_state: st.session_state.create_indent_selected_department = None


# --- Fetch Data needed across Tabs (Cached) ---
@st.cache_data(ttl=120)
def fetch_indent_page_data(_engine): # Definition uses _engine
    """Fetches data needed for the indent page (items, departments)."""
    # Pass _engine to backend functions expecting _engine
    items = get_all_items_with_stock(_engine, include_inactive=False)
    # Use the dynamic department fetching function if available (it is in item_manager_app.py)
    try:
        dynamic_departments = get_distinct_departments_from_items(_engine)
    except NameError: # Fallback if function wasn't defined correctly (shouldn't happen now)
        dynamic_departments = DEPARTMENTS # Fallback to hardcoded if needed
    # Pass _engine to fetch_data
    indent_info_df = fetch_data(_engine, "SELECT DISTINCT status, department FROM indents")
    statuses = ["All"] + sorted(indent_info_df['status'].unique().tolist()) if not indent_info_df.empty else ["All"]
    view_departments = ["All"] + sorted(indent_info_df['department'].unique().tolist()) if not indent_info_df.empty else ["All"]

    # Return dynamic departments for create tab if found, else the hardcoded list
    create_depts = dynamic_departments if dynamic_departments else DEPARTMENTS
    return items, create_depts, statuses, view_departments

# Pass original 'db_engine' variable here; fetch_indent_page_data receives it as _engine
items_df, create_dept_options, view_status_options, view_dept_options = fetch_indent_page_data(db_engine)


# --- Callbacks for Create Indent ---
def add_indent_row():
    new_row_id = st.session_state.create_indent_next_row_id
    st.session_state.create_indent_rows.append({'id': new_row_id})
    st.session_state.create_indent_next_row_id += 1

def remove_indent_row(row_id):
    st.session_state.create_indent_rows = [row for row in st.session_state.create_indent_rows if row['id'] != row_id]
    keys_to_remove = [key for key in st.session_state if key.startswith(f"create_item_{row_id}_")]
    for key in keys_to_remove: del st.session_state[key]

def department_changed():
    st.session_state.create_indent_selected_department = st.session_state.get('create_indent_department_select')


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
    # Using dynamic departments fetched earlier
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            requested_by = st.text_input("Requested By*", key="create_indent_requested_by_input")
        with col2:
            # Use dynamically fetched departments (or fallback DEPARTMENTS list)
            if not create_dept_options:
                st.warning("No departments found linked to active items or defined. Cannot create indent.")
                selected_dept = None
            else:
                current_dept_val = st.session_state.create_indent_selected_department
                try: dept_index = create_dept_options.index(current_dept_val) if current_dept_val in create_dept_options else 0
                except ValueError: dept_index = 0
                selected_dept = st.selectbox(
                    "Requesting Department*",
                    create_dept_options, # Use fetched/fallback list
                    key='create_indent_department_select',
                    index=dept_index,
                    on_change=department_changed,
                    placeholder="Select department..."
                )
                if selected_dept != st.session_state.create_indent_selected_department:
                     st.session_state.create_indent_selected_department = selected_dept
            current_selected_dept = st.session_state.create_indent_selected_department
        with col3:
            date_required = st.date_input(
                "Date Required*", datetime.now().date() + timedelta(days=1), key="create_indent_date_required_input")
        notes_header = st.text_area("Indent Notes (Optional)", key="create_indent_notes_header_input", height=75)


    st.subheader("Indent Items")
    # --- Filter items based on selected department ---
    filtered_items_df = pd.DataFrame() # Initialize empty
    if current_selected_dept and not items_df.empty:
        def is_dept_permitted(permitted_str):
            if pd.isna(permitted_str) or not isinstance(permitted_str, str) or not permitted_str.strip(): return False
            permitted_list = [d.strip() for d in permitted_str.split(',') if d.strip()]
            return current_selected_dept in permitted_list
        mask = items_df['permitted_departments'].apply(is_dept_permitted)
        filtered_items_df = items_df[mask].copy()


    # --- Dynamic Item Rows --- (Logic seems okay from user's file)
    item_rows_data = []
    if not filtered_items_df.empty:
        item_options = filtered_items_df[['item_id', 'name', 'unit']].to_dict('records')
        item_display_options = {item['item_id']: f"{item['name']} ({item['unit']})" for item in item_options}
        item_unit_map = {item['item_id']: item['unit'] for item in item_options}
        header_cols = st.columns([3, 1, 1, 3, 1])
        header_cols[0].write("**Item**"); header_cols[1].write("**Unit**"); header_cols[2].write("**Req. Qty***")
        header_cols[3].write("**Item Notes**"); header_cols[4].write("**Action**")
        st.markdown("---")
        for i, row_state in enumerate(st.session_state.create_indent_rows):
            row_id = row_state['id']; key_base = f"create_item_{row_id}"
            cols = st.columns([3, 1, 1, 3, 1])
            with cols[0]:
                current_item_selection = st.session_state.get(f"{key_base}_select", None)
                valid_item_ids = list(item_display_options.keys())
                try: item_index = valid_item_ids.index(current_item_selection) if current_item_selection in valid_item_ids else None
                except ValueError: item_index = None
                selected_item_id = st.selectbox(
                    f"Item##{key_base}_select", options=valid_item_ids,
                    format_func=lambda x: item_display_options.get(x, "Select..."), label_visibility="collapsed",
                    key=f"{key_base}_select", index=item_index, placeholder="Select item...")
            with cols[1]:
                unit = item_unit_map.get(selected_item_id, "")
                st.text_input(f"Unit##{key_base}_unit", value=unit, key=f"{key_base}_unit_display", disabled=True, label_visibility="collapsed")
            with cols[2]:
                requested_qty = st.number_input(
                    f"Qty##{key_base}_qty", min_value=0.01, step=1.0,
                    value=float(st.session_state.get(f"{key_base}_qty", 1.0)), format="%.2f",
                    label_visibility="collapsed", key=f"{key_base}_qty")
            with cols[3]:
                item_notes = st.text_input(f"Notes##{key_base}_notes", key=f"{key_base}_notes", label_visibility="collapsed")
            with cols[4]:
                disable_remove = len(st.session_state.create_indent_rows) <= 1
                st.button("➖", key=f"{key_base}_remove", on_click=remove_indent_row, args=(row_id,), disabled=disable_remove, help="Remove item row")
            if selected_item_id:
                item_rows_data.append({'item_id': selected_item_id, 'requested_qty': requested_qty,
                                       'notes': item_notes.strip() or None, 'row_id': row_id})
    else:
        if current_selected_dept: st.warning(f"No active items found permitted for department: '{current_selected_dept}'.")
        else: st.warning("Please select a requesting department to see available items.")

    # --- Action Buttons --- (Logic seems okay from user's file)
    st.markdown("---")
    col_add, col_submit = st.columns([1, 10])
    with col_add:
        st.button("➕ Add Item", key="create_indent_add_item_btn", on_click=add_indent_row, disabled=filtered_items_df.empty)
    with col_submit:
        can_submit = bool(item_rows_data and requested_by and current_selected_dept and date_required)
        submit_indent = st.button("✅ Submit Indent", key="create_indent_submit_btn", type="primary", disabled=not can_submit)

    # --- Indent Submission Logic --- (Logic seems okay from user's file)
    if submit_indent:
        is_valid = True; validation_errors = []
        if not requested_by: validation_errors.append("'Requested By' field cannot be empty."); is_valid = False
        if not current_selected_dept: validation_errors.append("'Requesting Department' must be selected."); is_valid = False
        if not date_required: validation_errors.append("'Date Required' must be selected."); is_valid = False
        if not item_rows_data: validation_errors.append("At least one valid item must be added."); is_valid = False
        else:
            seen_item_ids = set()
            for idx, item_data in enumerate(item_rows_data):
                if not item_data.get('item_id'): validation_errors.append(f"Row {idx + 1}: An item must be selected."); is_valid = False
                elif item_data['item_id'] in seen_item_ids:
                    item_name = item_display_options.get(item_data['item_id'], f"ID {item_data['item_id']}")
                    validation_errors.append(f"Row {idx + 1}: Item '{item_name}' is duplicated."); is_valid = False
                else: seen_item_ids.add(item_data['item_id'])
                if not item_data.get('requested_qty') or item_data['requested_qty'] <= 0:
                    item_name = item_display_options.get(item_data['item_id'], f"ID {item_data['item_id']}")
                    validation_errors.append(f"Row {idx + 1}: Quantity for '{item_name}' must be > 0."); is_valid = False
        if not is_valid: st.error("Indent validation failed:\n" + "\n".join(f"- {e}" for e in validation_errors))
        else:
            with st.spinner("Submitting Indent..."):
                try:
                    new_mrn = generate_mrn(db_engine) # Pass original engine
                    if not new_mrn: st.error("Failed to generate MRN. Indent not created.")
                    else:
                        indent_data = {'mrn': new_mrn, 'requested_by': requested_by.strip(), 'department': current_selected_dept,
                                       'date_required': date_required, 'notes': notes_header.strip() or None, 'status': STATUS_SUBMITTED}
                        items_to_submit = [{'item_id': item['item_id'], 'requested_qty': item['requested_qty'], 'notes': item['notes']}
                                           for item in item_rows_data]
                        success, message = create_indent(db_engine, indent_data, items_to_submit) # Pass original engine
                        if success:
                            st.success(f"Indent {new_mrn} created successfully!")
                            st.session_state.create_indent_rows = [{'id': 0}]; st.session_state.create_indent_next_row_id = 1
                            st.session_state.create_indent_selected_department = None
                            if 'create_indent_requested_by_input' in st.session_state: del st.session_state['create_indent_requested_by_input']
                            if 'create_indent_notes_header_input' in st.session_state: del st.session_state['create_indent_notes_header_input']
                            keys_to_clear = [k for k in st.session_state if k.startswith("create_item_")]
                            for k in keys_to_clear: del st.session_state[k]
                            fetch_indent_page_data.clear(); st.rerun()
                        else: st.error(f"Failed to create indent: {message}")
                except Exception as e: st.error(f"An unexpected error occurred during submission: {e}")

# ============================
# 📊 VIEW INDENTS TAB (MODIFIED TO PASS DATE STRINGS)
# ============================
with tab_view:
    st.subheader("View Submitted Indents")
    st.write("Apply filters to find specific indents:")

    # --- Filters --- (Using user's latest layout)
    col_flt1, col_flt2 = st.columns([1, 3])
    with col_flt1:
        mrn_filter = st.text_input("MRN", key="view_mrn_filter")
        dept_filter = st.selectbox( "Department", options=view_dept_options, index=0, key="view_dept_filter")
        status_filter = st.selectbox("Status", options=view_status_options, index=0, key="view_status_filter")

    # Get Date Objects using user's date_input method
    with col_flt2:
        # Use default start/end logic from user's file if desired, otherwise None
        DEFAULT_START_DATE = date.today() - timedelta(days=90)
        DEFAULT_END_DATE = date.today()

        # Check if user used range slider or individual inputs, adapt as needed.
        # Assuming individual inputs based on previous working version:
        filter_date_from_obj = st.date_input(
            "Submitted From", value=DEFAULT_START_DATE, key="view_date_from_obj",
             help="Leave blank for no start date limit." # Or set value=None if no default wanted
        )
        filter_date_to_obj = st.date_input(
            "Submitted To", value=DEFAULT_END_DATE, key="view_date_to_obj",
            help="Leave blank for no end date limit." # Or set value=None if no default wanted
        )
        # If user's latest file used range slider like:
        # date_range = st.date_input(...)
        # Then adapt like this:
        # if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        #     filter_date_from_obj, filter_date_to_obj = date_range
        # else: # Handle case where only one date might be selected if range slider allows it
        #     filter_date_from_obj = date_range[0] if isinstance(date_range, (list, tuple)) and len(date_range)>0 else None
        #     filter_date_to_obj = None # Or handle appropriately

    # Basic date range validation
    indents_df = pd.DataFrame() # Initialize empty
    if filter_date_from_obj and filter_date_to_obj and filter_date_from_obj > filter_date_to_obj:
        st.warning("'Submitted From' date cannot be after 'Submitted To' date.")
    else:
        # *** MODIFIED SECTION START ***
        # --- Convert dates to strings for caching ---
        date_start_str_arg = filter_date_from_obj.strftime('%Y-%m-%d') if filter_date_from_obj else None
        date_end_str_arg = filter_date_to_obj.strftime('%Y-%m-%d') if filter_date_to_obj else None
        # --- End Date Conversion ---

        # --- Fetch and Display Data ---
        dept_arg = dept_filter if dept_filter != "All" else None
        status_arg = status_filter if status_filter != "All" else None
        mrn_arg = mrn_filter.strip() if mrn_filter else None

        # Call get_indents with string dates (Pass original engine variable positionally)
        indents_df = get_indents(
            db_engine, # <-- Pass original engine variable positionally
            mrn_filter=mrn_arg,
            dept_filter=dept_arg,
            status_filter=status_arg,
            date_start_str=date_start_str_arg, # MODIFIED: Pass string version
            date_end_str=date_end_str_arg      # MODIFIED: Pass string version
        )
        # *** MODIFIED SECTION END ***

    st.divider()
    # Display result or info message (Using user's column order preference)
    if indents_df.empty:
         st.info("No indents found matching the selected criteria.")
    else:
        st.success(f"Found {len(indents_df)} indent(s).")
        st.dataframe(
            indents_df,
            use_container_width=True,
            hide_index=True,
            column_order=["mrn", "date_submitted", "department", "requested_by", "date_required", "status", "item_count", "indent_notes"] # Adjusted based on function output
        )

# ============================
# ⚙️ PROCESS INDENT TAB
# ============================
with tab_process:
    st.subheader("Process Indent (Future Implementation)")
    st.info("This section will allow viewing indent details, marking items as fulfilled, and updating indent status.")
    # Placeholder as before