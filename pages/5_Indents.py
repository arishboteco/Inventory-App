# pages/5_Indents.py – full file with PDF download integration

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
        generate_indent_pdf,      # <-- Import the new PDF function
        ALL_INDENT_STATUSES,
        STATUS_SUBMITTED # Import default status
    )
except ImportError as e:
    st.error(f"Import error from item_manager_app.py: {e}. Ensure it's in the parent directory.")
    st.stop()
except Exception as e:
    st.error(f"Unexpected error during import: {e}")
    st.stop()

# --- Page Config ---
st.set_page_config(layout="wide")
st.title("📝 Material Indents")
st.write("Create, view, and manage material requests (indents).")

# --- Database Connection ---
# Use the shared connection function
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed. Cannot load Indent Management page.")
    st.stop()

# --- Helper Functions Specific to this Page ---

# Cache data needed across tabs (items, departments)
@st.cache_data(ttl=300, show_spinner="Loading item data...") # Cache for 5 mins
def fetch_indent_page_data(_engine):
    """Fetches active items and distinct departments needed for the Indents page."""
    if _engine is None:
        return pd.DataFrame(), [] # Return empty structures if no engine

    # Fetch active items (simplified columns needed for dropdowns/filtering)
    items_query = "SELECT item_id, name, unit, permitted_departments FROM items WHERE is_active = TRUE ORDER BY name;"
    items_df = fetch_data(_engine, items_query) # Use the helper from main app

    # Fetch distinct departments using the function from main app
    departments = get_distinct_departments_from_items(_engine)

    return items_df, departments

# --- Load Data ---
all_active_items_df, distinct_departments = fetch_indent_page_data(db_engine)

# --- Initialize Session State for Dynamic Rows ---
if 'create_indent_rows' not in st.session_state:
    # Start with one empty row
    st.session_state.create_indent_rows = [{'item_id': None, 'requested_qty': 1.0, 'notes': ''}]
if 'selected_department_for_create' not in st.session_state:
     st.session_state.selected_department_for_create = None


# --- Define Callbacks for Dynamic Rows ---
def add_indent_row():
    st.session_state.create_indent_rows.append({'item_id': None, 'requested_qty': 1.0, 'notes': ''})

def remove_indent_row(index):
    if len(st.session_state.create_indent_rows) > 1: # Prevent removing the last row
        st.session_state.create_indent_rows.pop(index)
    else:
        st.warning("Cannot remove the last item row.")


# --- Tabs for Indent Management ---
tab_create, tab_view, tab_process = st.tabs([
    "➕ Create Indent",
    "📄 View Indents",
    "⚙️ Process Indent"
])

# ===========================
# ➕ CREATE INDENT TAB
# ===========================
with tab_create:
    st.subheader("Create New Material Indent")

    # --- Header Information ---
    col1, col2 = st.columns(2)
    with col1:
        # Use dynamic list of departments fetched earlier
        department = st.selectbox(
            "Requesting Department*",
            options=distinct_departments,
            index=None, # Default to no selection
            placeholder="Select Department...",
            key="create_dept" # Assign key for potential future use/reset
        )
        # Store selected department in session state to filter items dynamically
        st.session_state.selected_department_for_create = department

    with col2:
        requested_by = st.text_input("Requested By*", placeholder="Your Name/ID", key="create_req_by")

    col3, col4 = st.columns(2)
    with col3:
        date_required = st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today(), key="create_date_req")
    with col4:
        # Status defaults to Submitted and is usually read-only at creation
        st.text_input("Status", value=STATUS_SUBMITTED, disabled=True, key="create_status")

    header_notes = st.text_area("Overall Indent Notes (Optional)", key="create_header_notes")

    st.divider()
    st.subheader("Indent Items")

    # --- Filter Items based on Selected Department ---
    if st.session_state.selected_department_for_create and not all_active_items_df.empty:
        selected_dept = st.session_state.selected_department_for_create
        try:
            # Filter items where permitted_departments contains the selected department
            # Handle potential NaN/None in 'permitted_departments'
            # Ensure case-insensitive and whitespace-tolerant matching
            available_items_df = all_active_items_df[
                all_active_items_df['permitted_departments'].fillna('').astype(str).str.split(',')
                .apply(lambda depts: selected_dept.strip().lower() in [d.strip().lower() for d in depts] if isinstance(depts, list) else False)
            ].copy()

            if available_items_df.empty:
                 st.warning(f"No active items found permitted for the '{selected_dept}' department. Check item configurations.")
                 item_options = []
            else:
                 # Create list of tuples for selectbox: (display_name, item_id)
                 item_options = list(available_items_df[['name', 'item_id', 'unit']].itertuples(index=False, name=None))
                 # Prepend a placeholder
                 item_options.insert(0, ("Select Item...", None))

        except Exception as e:
             st.error(f"Error filtering items by department: {e}")
             item_options = [("Error loading items", None)]
             available_items_df = pd.DataFrame() # Ensure it's empty on error

    elif not st.session_state.selected_department_for_create:
        st.info("Select a department above to see available items.")
        item_options = [("Select Department First", None)]
        available_items_df = pd.DataFrame() # Ensure it's empty
    else: # all_active_items_df is empty
         st.warning("No active items found in the system.")
         item_options = [("No Items Available", None)]
         available_items_df = pd.DataFrame()


    # --- Dynamic Item Rows ---
    item_rows_container = st.container()
    with item_rows_container:
        for i, row_data in enumerate(st.session_state.create_indent_rows):
            cols = st.columns([4, 2, 3, 1]) # Adjust column ratios as needed
            with cols[0]: # Item Selection
                # Use the filtered item_options
                selected_item_tuple = cols[0].selectbox(
                    f"Item*",
                    options=item_options,
                    format_func=lambda x: x[0], # Display only the name part of the tuple
                    key=f"item_select_{i}",
                    label_visibility="collapsed", # Hide label for cleaner look
                    index = item_options.index(next((opt for opt in item_options if opt[1] == row_data['item_id']), item_options[0])) if row_data['item_id'] else 0
                )
                # Store the selected item_id back into the session state row
                st.session_state.create_indent_rows[i]['item_id'] = selected_item_tuple[1] if selected_item_tuple else None

                # Display unit if item is selected
                if selected_item_tuple and selected_item_tuple[1] is not None:
                     item_details = available_items_df[available_items_df['item_id'] == selected_item_tuple[1]].iloc[0]
                     st.caption(f"Unit: {item_details['unit']}")


            with cols[1]: # Quantity
                st.session_state.create_indent_rows[i]['requested_qty'] = cols[1].number_input(
                    "Quantity*",
                    min_value=0.01,
                    value=float(row_data['requested_qty']), # Ensure float for consistency
                    step=1.0,
                    key=f"item_qty_{i}",
                    label_visibility="collapsed"
                )
            with cols[2]: # Item Notes
                st.session_state.create_indent_rows[i]['notes'] = cols[2].text_input(
                    "Item Notes",
                    value=row_data['notes'],
                    placeholder="Optional notes for this item",
                    key=f"item_notes_{i}",
                    label_visibility="collapsed"
                )
            with cols[3]: # Remove Button
                if len(st.session_state.create_indent_rows) > 1: # Show remove button only if more than one row
                    cols[3].button("➖", key=f"remove_row_{i}", on_click=remove_indent_row, args=(i,), help="Remove this item")

    # --- Add Row Button ---
    st.button("➕ Add Another Item", on_click=add_indent_row)

    st.divider()

    # --- Submit Button ---
    if st.button("Submit Indent", type="primary"):
        # --- Validation ---
        valid = True
        items_to_submit = []
        seen_item_ids = set()

        if not department:
            st.error("Requesting Department is required.")
            valid = False
        if not requested_by.strip():
            st.error("Requested By is required.")
            valid = False
        if not date_required: # Should always have a value due to default, but check anyway
            st.error("Date Required is required.")
            valid = False

        # Validate item rows
        for i, row in enumerate(st.session_state.create_indent_rows):
            item_id = row.get('item_id')
            qty = row.get('requested_qty')

            if item_id is None:
                st.error(f"Row {i+1}: Please select an item.")
                valid = False
                continue # Skip further checks for this row

            if item_id in seen_item_ids:
                 st.error(f"Row {i+1}: Item '{available_items_df[available_items_df['item_id']==item_id]['name'].iloc[0]}' is duplicated. Please combine quantities.")
                 valid = False

            if not isinstance(qty, (int, float)) or qty <= 0:
                st.error(f"Row {i+1}: Quantity must be a positive number.")
                valid = False

            if valid and item_id is not None: # Only add if row is valid so far
                 items_to_submit.append({
                     "item_id": item_id,
                     "requested_qty": float(qty),
                     "notes": row.get('notes', '').strip() or None # Store None if empty
                 })
                 seen_item_ids.add(item_id)


        if not items_to_submit and valid: # Check if list is empty even if other fields were valid
             st.error("Indent must contain at least one valid item.")
             valid = False


        # --- Submission ---
        if valid:
            st.info("Submitting indent...")
            # 1. Generate MRN
            new_mrn = generate_mrn(db_engine)

            if new_mrn:
                # 2. Call create_indent
                success = create_indent(
                    engine=db_engine,
                    mrn=new_mrn,
                    department=department,
                    requested_by=requested_by.strip(),
                    date_required=date_required,
                    status=STATUS_SUBMITTED,
                    notes=header_notes.strip() or None,
                    items=items_to_submit
                )

                if success:
                    st.success(f"Indent '{new_mrn}' created successfully!")
                    # Clear form state after successful submission
                    st.session_state.create_indent_rows = [{'item_id': None, 'requested_qty': 1.0, 'notes': ''}]
                    # Potentially clear other fields using st.session_state and keys if needed
                    # e.g., st.session_state.create_dept = None (might trigger rerun depending on widget)
                    # Consider a more robust reset mechanism if required
                    st.balloons()
                    # Clear relevant caches
                    get_indents.clear()
                    time.sleep(2) # Give user time to see success message
                    st.rerun() # Rerun to reset the form visually

                else:
                    st.error("Failed to create indent. Check error messages above.")
            else:
                st.error("Failed to generate MRN. Cannot create indent.")


# ===========================
# 📄 VIEW INDENTS TAB
# ===========================
with tab_view:
    st.subheader("View Existing Indents")

    # --- Filters ---
    view_cols = st.columns([1, 1, 1, 2])
    with view_cols[0]:
        mrn_filter = st.text_input("Filter by MRN", key="view_mrn")
    with view_cols[1]:
        # Use dynamic department list
        dept_filter = st.selectbox(
            "Filter by Department",
            options=["All"] + distinct_departments, # Add "All" option
            key="view_dept"
        )
    with view_cols[2]:
        status_filter = st.selectbox(
            "Filter by Status",
            options=["All"] + ALL_INDENT_STATUSES, # Add "All" option
            key="view_status"
        )
    with view_cols[3]:
        # Date Range Filter (Corrected to pass strings)
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            date_start_filter = st.date_input("Submitted From", value=None, key="view_date_start")
        with date_col2:
            date_end_filter = st.date_input("Submitted To", value=None, key="view_date_end")

    # --- Fetch Data based on Filters ---
    # Convert dates to strings *before* passing to the cached function
    date_start_str_arg = date_start_filter.strftime('%Y-%m-%d') if date_start_filter else None
    date_end_str_arg = date_end_filter.strftime('%Y-%m-%d') if date_end_filter else None

    # Prepare other arguments
    dept_arg = dept_filter if dept_filter != "All" else None
    status_arg = status_filter if status_filter != "All" else None
    mrn_arg = mrn_filter.strip() if mrn_filter else None

    # Call get_indents with string dates (Pass original engine variable)
    indents_df = get_indents(
        db_engine, # <-- Pass original engine variable
        mrn_filter=mrn_arg,
        dept_filter=dept_arg,
        status_filter=status_arg,
        date_start_str=date_start_str_arg, # Pass string version
        date_end_str=date_end_str_arg      # Pass string version
    )

    st.divider()
    # --- Display Results ---
    if indents_df.empty:
         st.info("No indents found matching the selected criteria.")
    else:
        st.success(f"Found {len(indents_df)} indent(s).")
        st.dataframe(
            indents_df,
            use_container_width=True,
            hide_index=True,
            column_order=["mrn", "date_submitted", "department", "requested_by", "date_required", "status", "item_count", "indent_notes"], # Adjusted based on function output
             column_config={
                "indent_id": None, # Hide internal ID
                "mrn": st.column_config.TextColumn("MRN", width="medium"),
                "date_submitted": st.column_config.DatetimeColumn("Submitted", format="YYYY-MM-DD HH:mm", width="medium"),
                "department": st.column_config.TextColumn("Department", width="medium"),
                "requested_by": st.column_config.TextColumn("Requestor", width="medium"),
                "date_required": st.column_config.DateColumn("Required By", format="YYYY-MM-DD", width="small"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "item_count": st.column_config.NumberColumn("Items", format="%d", width="small"),
                "indent_notes": st.column_config.TextColumn("Notes", width="large"),
            }
        )

        # --- PDF Download Section ---
        st.divider()
        st.subheader("Download Indent as PDF")

        # Get list of MRNs from the displayed dataframe
        available_mrns = ["Select MRN..."] + indents_df['mrn'].tolist()
        selected_mrn_for_pdf = st.selectbox(
            "Choose an MRN to download:",
            options=available_mrns,
            key="pdf_mrn_select"
        )

        # Placeholder for the download button
        download_button_placeholder = st.empty()

        if selected_mrn_for_pdf != "Select MRN...":
            if st.button("Generate PDF", key="generate_pdf_btn"):
                with st.spinner(f"Generating PDF for {selected_mrn_for_pdf}..."):
                    # Call the backend function to generate PDF bytes
                    pdf_bytes = generate_indent_pdf(db_engine, selected_mrn_for_pdf)

                    if pdf_bytes:
                        # Display the download button in the placeholder
                        download_button_placeholder.download_button(
                            label=f"Download PDF for {selected_mrn_for_pdf}",
                            data=pdf_bytes,
                            file_name=f"indent_{selected_mrn_for_pdf}.pdf",
                            mime="application/pdf",
                            key="download_pdf_btn" # Add key for potential state management
                        )
                        st.success("PDF generated successfully. Click the button above to download.")
                    else:
                        # Error message should be displayed by generate_indent_pdf
                        st.error(f"Could not generate PDF for {selected_mrn_for_pdf}. See logs if available.")
                        # Clear the placeholder if generation failed
                        download_button_placeholder.empty()
        else:
            # Clear the placeholder if no MRN is selected
             download_button_placeholder.empty()


# ===========================
# ⚙️ PROCESS INDENT TAB
# ===========================
with tab_process:
    st.header("Process Indent (Placeholder)")
    st.info("This section will allow authorized users to view submitted indents, allocate stock, mark items as fulfilled, and update the indent status (e.g., Processing, Completed).")
    # Future elements:
    # - Selectbox/Search for Submitted/Processing Indents by MRN
    # - Display Indent Details (Header + Items)
    # - For each item: Input field for 'Fulfilled Quantity', button to 'Allocate Stock'
    #   - Allocation should check available stock
    #   - Record a stock transaction (Type: INDENT_FULFILL)
    #   - Update 'fulfilled_qty' in 'indent_items' table
    # - Button to update overall Indent Status (e.g., 'Mark as Processing', 'Mark as Completed')
    # - Potentially link to PO generation if stock is insufficient.

