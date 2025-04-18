# pages/5_Indents.py
# Integrates with consolidated backend and includes PDF generation locally.
# Fix: Removed unnecessary st.form wrapper in Create Indent tab.
# Fix: Correctly reset state after successful indent creation.
# Fix: Updated fpdf2 usage to resolve DeprecationWarnings and RuntimeError.
# Fix: Explicitly convert PDF output to bytes for st.download_button.

# ─── Ensure repo root is on sys.path ─────────────────────────────────
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
# ────────────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple, Set
import time
import numpy as np
from fpdf import FPDF
from fpdf.enums import XPos, YPos # <-- Import new enums for positioning

# --- Imports from consolidated backend (item_manager_app.py) ---
try:
    from item_manager_app import (
        connect_db,
        fetch_data, # Used by fetch_indent_page_data
        get_all_items_with_stock, # Used by fetch_indent_page_data
        generate_mrn,             # For creating indents
        create_indent,            # For creating indents
        get_indents,              # For viewing indents
        get_distinct_departments_from_items, # For dropdowns
        get_indent_details_for_pdf, # <-- New function for PDF data
        ALL_INDENT_STATUSES,      # Constants
        STATUS_SUBMITTED
    )
except ImportError as e:
    st.error(f"Import error from item_manager_app.py: {e}. Ensure it's in the parent directory.")
    st.stop()
except Exception as e:
    st.error(f"Unexpected error during import: {e}")
    st.stop()

# --- Page Config ---
st.set_page_config(layout="wide", page_title="Indents", page_icon="📝")
st.title("📝 Material Indents")
st.write("Create, view, and manage material requests (indents).")

# --- Database Connection ---
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
    # Use the backend function which is already cached
    items_df = get_all_items_with_stock(_engine, include_inactive=False)
    # Select only necessary columns if needed, or use the full df
    items_df_filtered = items_df[['item_id', 'name', 'unit', 'permitted_departments']].copy()

    # Fetch distinct departments using the function from main app
    departments = get_distinct_departments_from_items(_engine)

    return items_df_filtered, departments

# --- PDF Generation Utility (Updated fpdf2 usage & explicit bytes conversion) ---
def generate_indent_pdf(indent_header: Dict, indent_items: List[Dict]) -> Optional[bytes]:
    """Generates a PDF document for a submitted indent using FPDF2."""
    if not indent_header or indent_items is None: # items can be an empty list
         st.error("Cannot generate PDF: Missing indent header or items data.")
         return None

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)

        # Title
        pdf.cell(0, 10, "Material Indent Request", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Updated ln=True
        pdf.ln(10)

        # Header Info - Use a consistent label width
        pdf.set_font("Helvetica", "", 11)
        label_width = pdf.get_string_width("Date Required: ") + 2 # Estimate label width

        def add_header_line(label, value):
            pdf.set_font("Helvetica", "", 11)
            pdf.cell(label_width, 7, label)
            pdf.set_font("Helvetica", "B", 11) # Bold for value
            pdf.cell(0, 7, str(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Updated ln=True

        add_header_line("MRN:", indent_header.get('mrn', 'N/A'))
        add_header_line("Department:", indent_header.get('department', 'N/A'))
        add_header_line("Requested By:", indent_header.get('requested_by', 'N/A'))
        # Dates are pre-formatted strings from get_indent_details_for_pdf
        add_header_line("Date Submitted:", indent_header.get('date_submitted', 'N/A'))
        add_header_line("Date Required:", indent_header.get('date_required', 'N/A'))
        add_header_line("Status:", indent_header.get('status', 'N/A'))


        # Overall Indent Notes
        if indent_header.get('notes'):
            pdf.ln(3) # Small gap before notes
            pdf.set_font("Helvetica", "I", 10)
            # Use multi_cell for notes which handles line breaks properly
            pdf.multi_cell(0, 5, f"Indent Notes: {indent_header['notes']}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(8) # More space before table

        # Items Table Header
        pdf.set_font("Helvetica", "B", 10)
        # Define column widths (total should be around 190 for A4 portrait)
        col_widths = {'sno': 15, 'name': 75, 'unit': 20, 'qty': 25, 'notes': 55}
        pdf.set_fill_color(220, 220, 220) # Light grey background
        pdf.cell(col_widths['sno'], 7, "S.No.", border=1, align='C', fill=True)
        pdf.cell(col_widths['name'], 7, "Item Name", border=1, fill=True)
        pdf.cell(col_widths['unit'], 7, "Unit", border=1, align='C', fill=True)
        pdf.cell(col_widths['qty'], 7, "Req. Qty", border=1, align='C', fill=True)
        pdf.cell(col_widths['notes'], 7, "Item Notes", border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Updated ln=True

        # Items Table Rows
        pdf.set_font("Helvetica", "", 9) # Smaller font for table content
        pdf.set_fill_color(255, 255, 255) # Reset fill color
        fill = False # Alternate row colors
        if not indent_items:
             pdf.cell(sum(col_widths.values()), 7, "No items found in this indent.", border=1, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Updated ln=True
        else:
            for i, item in enumerate(indent_items):
                # Handle potential line breaks in name/notes
                line_height = 5 # Adjust line height
                notes_str = item.get('item_notes', '') or '' # Ensure string, default empty
                item_name_str = item.get('item_name', 'N/A') or 'N/A'

                # Calculate max lines needed based on potential wrapping (simple estimate)
                # FPDF's multi_cell handles wrapping, but we need height consistency
                # A more robust way involves calculating lines needed for each cell
                # For simplicity, let's use a fixed height or estimate based on notes length
                num_lines = max(1, len(notes_str) // (col_widths['notes'] // 2) + 1) # Rough estimate
                row_height = line_height * num_lines

                # Store Y position before drawing cells in this row
                start_y = pdf.get_y()

                pdf.cell(col_widths['sno'], row_height, str(i + 1), border=1, align='C', fill=fill)

                # Use multi_cell for name to allow wrapping if needed
                x_after_sno = pdf.get_x()
                pdf.multi_cell(col_widths['name'], line_height, item_name_str, border=1, align='L', fill=fill, new_x=XPos.LEFT, new_y=YPos.TOP) # Draw name
                pdf.set_y(start_y) # Reset Y to top of row
                pdf.set_x(x_after_sno + col_widths['name']) # Move X after name cell

                pdf.cell(col_widths['unit'], row_height, item.get('item_unit', 'N/A'), border=1, align='C', fill=fill)
                pdf.cell(col_widths['qty'], row_height, f"{item.get('requested_qty', 0):.2f}", border=1, align='R', fill=fill) # Format quantity

                # Use multi_cell for notes
                x_after_qty = pdf.get_x()
                pdf.multi_cell(col_widths['notes'], line_height, notes_str, border=1, align='L', fill=fill, new_x=XPos.LEFT, new_y=YPos.TOP) # Draw notes
                pdf.set_y(start_y) # Reset Y to top of row
                pdf.set_x(x_after_qty + col_widths['notes']) # Move X after notes cell

                pdf.ln(row_height) # Move down by the calculated row height
                fill = not fill # Alternate fill color

        # --- Footer (Optional) ---
        pdf.set_y(-15) # Position 1.5 cm from bottom
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align='C', new_x=XPos.RIGHT, new_y=YPos.TOP) # Updated ln=0

        # Output as bytes (explicitly convert bytearray to bytes)
        pdf_output_data = pdf.output()
        return bytes(pdf_output_data) # <-- *** EXPLICIT CONVERSION ***

    except Exception as e:
        st.error(f"Failed to generate PDF: {e}")
        return None


# --- Load Data ---
# Pass the connected engine to the cached data fetching function
all_active_items_df, distinct_departments = fetch_indent_page_data(db_engine)

# --- Initialize Session State for Dynamic Rows ---
if 'create_indent_rows' not in st.session_state:
    # Start with one empty row represented as a dictionary
    st.session_state.create_indent_rows = [{'id': 0, 'item_id': None, 'requested_qty': 1.0, 'notes': ''}]
    st.session_state.create_indent_next_id = 1
if 'selected_department_for_create' not in st.session_state:
     st.session_state.selected_department_for_create = None


# --- Define Callbacks for Dynamic Rows ---
def add_indent_row():
    new_id = st.session_state.create_indent_next_id
    st.session_state.create_indent_rows.append({'id': new_id, 'item_id': None, 'requested_qty': 1.0, 'notes': ''})
    st.session_state.create_indent_next_id += 1

def remove_indent_row(row_id_to_remove):
    # Find the index of the row with the matching unique id
    index_to_remove = -1
    for i, row in enumerate(st.session_state.create_indent_rows):
        if row['id'] == row_id_to_remove:
            index_to_remove = i
            break

    if index_to_remove != -1:
        if len(st.session_state.create_indent_rows) > 1: # Prevent removing the last row
            st.session_state.create_indent_rows.pop(index_to_remove)
        else:
            st.warning("Cannot remove the last item row.")
    else:
        st.warning(f"Could not find row with ID {row_id_to_remove} to remove.") # Should not happen


# --- Tabs for Indent Management ---
tab_create, tab_view, tab_process = st.tabs([
    "➕ Create Indent",
    "📄 View Indents",
    "⚙️ Process Indent (Placeholder)"
])

# ===========================
# ➕ CREATE INDENT TAB
# ===========================
with tab_create:
    st.subheader("Create New Material Indent")

    # --- Header Information (No longer wrapped in st.form) ---
    col1, col2 = st.columns(2)
    with col1:
        department = st.selectbox(
            "Requesting Department*",
            options=distinct_departments,
            index=None, # Default to no selection
            placeholder="Select Department...",
            key="create_dept", # Key to read value later
            help="Select the department requesting the items."
        )
        # Update session state for dynamic item filtering
        # This happens automatically when the user selects an option
        st.session_state.selected_department_for_create = department

    with col2:
        requested_by = st.text_input("Requested By*", placeholder="Your Name/ID", key="create_req_by", help="Enter the name or ID of the person requesting.")

    col3, col4 = st.columns(2)
    with col3:
        # Set default date value directly in the widget
        date_required = st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today(), key="create_date_req", help="Select the date when items are needed.")
    with col4:
        st.text_input("Status", value=STATUS_SUBMITTED, disabled=True, key="create_status") # Read-only status

    header_notes = st.text_area("Overall Indent Notes (Optional)", key="create_header_notes", placeholder="Add any general notes for this indent.")

    # --- Display Available Items based on Department Selection ---
    st.divider()
    st.subheader("Indent Items")

    if st.session_state.selected_department_for_create:
        selected_dept = st.session_state.selected_department_for_create
        if not all_active_items_df.empty:
            try:
                # Filter items where permitted_departments (string) contains the selected department
                # Handle potential NaN/None, case-insensitivity, and whitespace
                available_items_df = all_active_items_df[
                    all_active_items_df['permitted_departments'].fillna('').astype(str).str.split(',')
                    .apply(lambda depts: selected_dept.strip().lower() in [d.strip().lower() for d in depts] if isinstance(depts, list) else False)
                ].copy()

                if available_items_df.empty:
                    st.warning(f"No active items found permitted for the '{selected_dept}' department. Check item configurations.")
                    item_options_dict = {"Select Item...": None} # Dictionary: {display_name: item_id}
                else:
                    # Create dictionary for selectbox options: {display_name: item_id}
                    item_options_dict = {"Select Item...": None}
                    item_options_dict.update({
                        f"{row['name']} ({row['unit']})": row['item_id']
                        for index, row in available_items_df.sort_values('name').iterrows()
                    })

            except Exception as e:
                st.error(f"Error filtering items by department: {e}")
                item_options_dict = {"Error loading items": None}
                available_items_df = pd.DataFrame() # Ensure empty on error
        else: # all_active_items_df is empty
            st.warning("No active items found in the system.")
            item_options_dict = {"No Items Available": None}
            available_items_df = pd.DataFrame()
    else:
        st.info("Select a department above to see available items.")
        item_options_dict = {"Select Department First": None}
        available_items_df = pd.DataFrame()

    # --- Dynamic Item Rows ---
    # Use a container to manage the layout of dynamic rows
    item_rows_container = st.container()
    items_to_submit = [] # List to hold validated item data for submission

    with item_rows_container:
        # Keep track of selected item IDs in this submission to prevent duplicates
        current_indent_item_ids = set()

        for i, row_state in enumerate(st.session_state.create_indent_rows):
            row_id = row_state['id'] # Unique ID for this row instance
            cols = st.columns([4, 2, 3, 1]) # Adjust column ratios

            with cols[0]: # Item Selection
                # Find current display value based on stored item_id
                current_display_value = next((name for name, id_val in item_options_dict.items() if id_val == row_state['item_id']), "Select Item...")

                selected_display_name = cols[0].selectbox(
                    f"Item*",
                    options=list(item_options_dict.keys()), # Pass list of names
                    index=list(item_options_dict.keys()).index(current_display_value), # Find index of current value
                    key=f"item_select_{row_id}", # Use unique row ID in key
                    label_visibility="collapsed",
                )
                # Update the item_id in the session state based on the selected name
                selected_item_id = item_options_dict.get(selected_display_name)
                st.session_state.create_indent_rows[i]['item_id'] = selected_item_id

                 # Display unit if item is selected and found
                if selected_item_id is not None and not available_items_df.empty:
                     item_details = available_items_df[available_items_df['item_id'] == selected_item_id]
                     if not item_details.empty:
                         st.caption(f"Unit: {item_details.iloc[0]['unit']}")
                     else:
                          st.caption("Unit: N/A") # Should not happen if item_options_dict is correct

            with cols[1]: # Quantity
                st.session_state.create_indent_rows[i]['requested_qty'] = cols[1].number_input(
                    "Quantity*", min_value=0.01,
                    value=float(row_state['requested_qty']), step=1.0,
                    key=f"item_qty_{row_id}", label_visibility="collapsed"
                )
            with cols[2]: # Item Notes
                st.session_state.create_indent_rows[i]['notes'] = cols[2].text_input(
                    "Item Notes", value=row_state['notes'],
                    placeholder="Optional notes for this item",
                    key=f"item_notes_{row_id}", label_visibility="collapsed"
                )
            with cols[3]: # Remove Button
                if len(st.session_state.create_indent_rows) > 1:
                    cols[3].button("➖", key=f"remove_row_{row_id}", on_click=remove_indent_row, args=(row_id,), help="Remove this item")

    # --- Add Row Button ---
    st.button("➕ Add Another Item", on_click=add_indent_row)

    st.divider()

    # --- Submit Button (Processes everything) ---
    if st.button("Submit Indent", type="primary", key="submit_indent_button"):
        # --- Validation ---
        valid = True
        items_to_submit = []
        seen_item_ids = set()

        # Get header values from widget state using keys
        header_data = {
            "department": st.session_state.get("create_dept"),
            "requested_by": st.session_state.get("create_req_by", "").strip(),
            "date_required": st.session_state.get("create_date_req"),
            "notes": st.session_state.get("create_header_notes", "").strip() or None,
            "status": STATUS_SUBMITTED # Default status
        }

        if not header_data["department"]:
            st.error("Requesting Department is required.")
            valid = False
        if not header_data["requested_by"]:
            st.error("Requested By is required and cannot be empty.")
            valid = False
        if not header_data["date_required"]: # Should always have a value due to default
            st.error("Date Required is required.")
            valid = False

        # Validate item rows from session state
        for i, row in enumerate(st.session_state.create_indent_rows):
            item_id = row.get('item_id')
            qty = row.get('requested_qty')

            if item_id is None:
                st.error(f"Row {i+1}: Please select an item.")
                valid = False
                continue # Skip further checks for this row

            if item_id in seen_item_ids:
                 # Find item name for error message
                 item_name = next((name for name, id_val in item_options_dict.items() if id_val == item_id), f"ID {item_id}")
                 st.error(f"Row {i+1}: Item '{item_name}' is duplicated. Please combine quantities or remove duplicate rows.")
                 valid = False
                 # Do not add to items_to_submit, but continue validation

            if not isinstance(qty, (int, float)) or qty <= 0:
                st.error(f"Row {i+1}: Quantity must be a positive number (is {qty}).")
                valid = False

            if item_id is not None and item_id not in seen_item_ids: # Only add valid, non-duplicate items
                 if valid: # Add only if row itself is valid
                     items_to_submit.append({
                         "item_id": item_id,
                         "requested_qty": float(qty),
                         "notes": row.get('notes', '').strip() or None
                     })
                 seen_item_ids.add(item_id) # Add to seen even if row had other errors to catch duplicates

        if not items_to_submit and valid: # Check if list is empty even if header was valid
             st.error("Indent must contain at least one valid item row.")
             valid = False

        # --- Submission ---
        if valid:
            st.info("Generating MRN and submitting indent...")
            # 1. Generate MRN (using non-cached function)
            new_mrn = generate_mrn(db_engine)

            if new_mrn:
                header_data["mrn"] = new_mrn # Add generated MRN to header data
                # 2. Call create_indent (using non-cached function)
                success, message = create_indent(
                    engine=db_engine,
                    indent_data=header_data,
                    items_data=items_to_submit
                )

                if success:
                    st.success(f"Indent '{new_mrn}' created successfully!")
                    # Clear *only custom* form state after successful submission
                    # Let st.rerun handle resetting the widgets themselves
                    st.session_state.create_indent_rows = [{'id': 0, 'item_id': None, 'requested_qty': 1.0, 'notes': ''}]
                    st.session_state.create_indent_next_id = 1
                    st.session_state.selected_department_for_create = None # Reset department filter state

                    st.balloons()
                    time.sleep(1) # Short pause
                    st.rerun() # Rerun to reset the form visually and clear selections

                else:
                    # Error message is already shown by create_indent via st.error
                    st.error(f"Failed to create indent: {message}") # Display specific message from backend
            else:
                st.error("Failed to generate MRN. Cannot create indent.")
        else:
            st.warning("Please fix the errors above before submitting.")


# ===========================
# 📄 VIEW INDENTS TAB
# ===========================
with tab_view:
    st.subheader("View Existing Indents")

    # --- Filters ---
    view_cols = st.columns([1, 1, 1, 2])
    with view_cols[0]:
        mrn_filter = st.text_input("Filter by MRN", key="view_mrn_filter")
    with view_cols[1]:
        dept_filter = st.selectbox(
            "Filter by Department", options=["All"] + distinct_departments,
            key="view_dept_filter"
        )
    with view_cols[2]:
        status_filter = st.selectbox(
            "Filter by Status", options=["All"] + ALL_INDENT_STATUSES,
            key="view_status_filter"
        )
    with view_cols[3]:
        # Date Range Filter - Use string format for cache key
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            date_start_filter = st.date_input("Submitted From", value=None, key="view_date_start")
        with date_col2:
            date_end_filter = st.date_input("Submitted To", value=None, key="view_date_end")

    # --- Fetch Data based on Filters ---
    # Convert dates to strings *before* passing to the cached function
    date_start_str_arg = date_start_filter.strftime('%Y-%m-%d') if date_start_filter else None
    date_end_str_arg = date_end_filter.strftime('%Y-%m-%d') if date_end_filter else None

    dept_arg = dept_filter if dept_filter != "All" else None
    status_arg = status_filter if status_filter != "All" else None
    mrn_arg = mrn_filter.strip() if mrn_filter else None

    # Call get_indents (cached function uses _engine convention)
    indents_df = get_indents(
        db_engine, # Pass engine directly
        mrn_filter=mrn_arg,
        dept_filter=dept_arg,
        status_filter=status_arg,
        date_start_str=date_start_str_arg,
        date_end_str=date_end_str_arg
    )

    st.divider()
    # --- Display Results ---
    if indents_df.empty:
         st.info("No indents found matching the selected criteria.")
    else:
        st.success(f"Found {len(indents_df)} indent(s).")
        # Format dates for display just before showing dataframe
        display_df = indents_df.copy()
        if 'date_required' in display_df.columns:
            display_df['date_required'] = pd.to_datetime(display_df['date_required'], errors='coerce').dt.strftime('%Y-%m-%d')
        if 'date_submitted' in display_df.columns:
            display_df['date_submitted'] = pd.to_datetime(display_df['date_submitted'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_order=["mrn", "date_submitted", "department", "requested_by", "date_required", "status", "item_count", "indent_notes"],
             column_config={
                "indent_id": None, # Hide internal ID
                "mrn": st.column_config.TextColumn("MRN", width="medium", help="Material Request Number"),
                "date_submitted": st.column_config.TextColumn("Submitted", width="medium"), # Already formatted as string
                "department": st.column_config.TextColumn("Department", width="medium"),
                "requested_by": st.column_config.TextColumn("Requestor", width="medium"),
                "date_required": st.column_config.TextColumn("Required By", width="small"), # Already formatted as string
                "status": st.column_config.TextColumn("Status", width="small"),
                "item_count": st.column_config.NumberColumn("Items", format="%d", width="small", help="Number of unique items in the indent"),
                "indent_notes": st.column_config.TextColumn("Notes", width="large"),
            }
        )

        # --- PDF Download Section ---
        st.divider()
        st.subheader("Download Indent as PDF")

        if not indents_df.empty:
            # Get list of MRNs from the original dataframe (before display formatting)
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
                    with st.spinner(f"Fetching details and generating PDF for {selected_mrn_for_pdf}..."):
                        # 1. Fetch data using the new backend function (non-cached)
                        header_details, items_details = get_indent_details_for_pdf(db_engine, selected_mrn_for_pdf)

                        if header_details and items_details is not None: # Check both header and items list (can be empty)
                            # 2. Generate PDF using the local function
                            pdf_bytes = generate_indent_pdf(header_details, items_details)

                            if pdf_bytes:
                                # 3. Display download button
                                download_button_placeholder.download_button(
                                    label=f"Download PDF for {selected_mrn_for_pdf}",
                                    data=pdf_bytes, # Should be bytes now
                                    file_name=f"indent_{selected_mrn_for_pdf}.pdf",
                                    mime="application/pdf",
                                    key="download_pdf_btn_final" # Use a distinct key
                                )
                                st.success("PDF generated. Click button above to download.")
                            else:
                                # Error message shown by generate_indent_pdf
                                download_button_placeholder.empty() # Clear placeholder on failure
                        else:
                            # Error message shown by get_indent_details_for_pdf
                            st.error(f"Could not fetch details for MRN {selected_mrn_for_pdf}.")
                            download_button_placeholder.empty() # Clear placeholder
            else:
                 download_button_placeholder.empty() # Clear if no MRN selected
        else:
             st.info("No indents available to download.")


# ===========================
# ⚙️ PROCESS INDENT TAB
# ===========================
with tab_process:
    st.header("Process Indent (Placeholder)")
    st.info("This section will allow authorized users to view submitted indents, allocate stock, mark items as fulfilled, and update the indent status (e.g., Processing, Completed).")
    # Future elements outlined in previous thoughts remain relevant here.

