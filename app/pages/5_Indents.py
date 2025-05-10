# app/pages/5_Indents.py

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple, Set # Ensure all necessary typing imports
import time
import numpy as np # Used in your original file
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Import shared functions and constants
try:
    # Import connect_db and fetch_data from their new location
    from app.db.database_utils import connect_db, fetch_data
    # Functions still temporarily in app.item_manager_app
    from app.item_manager_app import (
        # fetch_data was here, now imported from database_utils
        get_all_items_with_stock,
        generate_mrn,
        create_indent,
        get_indents,
        get_distinct_departments_from_items,
        get_indent_details_for_pdf,
    )
    # Import constants from their new location
    from app.core.constants import ALL_INDENT_STATUSES, STATUS_SUBMITTED
except ImportError as e:
    st.error(f"Import error in 5_Indents.py: {e}. Ensure 'INVENTORY-APP' is the root for 'streamlit run app/item_manager_app.py'.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 5_Indents.py: {e}")
    st.stop()

# --- Page Config ---
# st.set_page_config(layout="wide", page_title="Indents", page_icon="📝") # Ideally called only once
st.title("📝 Material Indents")
st.write("Create, view, and manage material requests (indents).")

db_engine = connect_db() # Uses imported connect_db
if not db_engine:
    st.error("Database connection failed. Cannot load Indent Management page.")
    st.stop()

# --- Helper Functions Specific to this Page ---
@st.cache_data(ttl=300, show_spinner="Loading item data...")
def fetch_indent_page_data(_engine):
    if _engine is None:
        return pd.DataFrame(), []

    # Uses get_all_items_with_stock (imported from app.item_manager_app)
    items_df = get_all_items_with_stock(_engine, include_inactive=False)
    items_df_filtered = items_df[['item_id', 'name', 'unit', 'permitted_departments']].copy()

    # Uses get_distinct_departments_from_items (imported from app.item_manager_app)
    departments = get_distinct_departments_from_items(_engine)
    return items_df_filtered, departments

# --- PDF Generation Utility (Your existing function) ---
def generate_indent_pdf(indent_header: Dict, indent_items: List[Dict]) -> Optional[bytes]:
    if not indent_header or indent_items is None:
         st.error("Cannot generate PDF: Missing indent header or items data.")
         return None
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Material Indent Request", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(10)
        pdf.set_font("Helvetica", "", 11)
        label_width = pdf.get_string_width("Date Required: ") + 2
        def add_header_line(label, value):
            pdf.set_font("Helvetica", "", 11)
            pdf.cell(label_width, 7, label)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, str(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        add_header_line("MRN:", indent_header.get('mrn', 'N/A'))
        add_header_line("Department:", indent_header.get('department', 'N/A'))
        add_header_line("Requested By:", indent_header.get('requested_by', 'N/A'))
        add_header_line("Date Submitted:", indent_header.get('date_submitted', 'N/A'))
        add_header_line("Date Required:", indent_header.get('date_required', 'N/A'))
        add_header_line("Status:", indent_header.get('status', 'N/A'))
        if indent_header.get('notes'):
            pdf.ln(3)
            pdf.set_font("Helvetica", "I", 10)
            pdf.multi_cell(0, 5, f"Indent Notes: {indent_header['notes']}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(8)
        pdf.set_font("Helvetica", "B", 10)
        col_widths = {'sno': 15, 'name': 75, 'unit': 20, 'qty': 25, 'notes': 55}
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(col_widths['sno'], 7, "S.No.", border=1, align='C', fill=True)
        pdf.cell(col_widths['name'], 7, "Item Name", border=1, fill=True)
        pdf.cell(col_widths['unit'], 7, "Unit", border=1, align='C', fill=True)
        pdf.cell(col_widths['qty'], 7, "Req. Qty", border=1, align='C', fill=True)
        pdf.cell(col_widths['notes'], 7, "Item Notes", border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_fill_color(255, 255, 255)
        fill = False
        if not indent_items:
             pdf.cell(sum(col_widths.values()), 7, "No items found in this indent.", border=1, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            for i, item in enumerate(indent_items):
                line_height = 5
                notes_str = item.get('item_notes', '') or ''
                item_name_str = item.get('item_name', 'N/A') or 'N/A'
                start_y = pdf.get_y()
                pdf.cell(col_widths['sno'], line_height * max(1, len(notes_str) // (col_widths['notes'] // 2) +1), str(i + 1), border=1, align='C', fill=fill) # Adjusted height logic inline
                x_after_sno = pdf.get_x()
                pdf.multi_cell(col_widths['name'], line_height, item_name_str, border=1, align='L', fill=fill, new_x=XPos.LEFT, new_y=YPos.TOP)
                pdf.set_y(start_y)
                pdf.set_x(x_after_sno + col_widths['name'])
                pdf.cell(col_widths['unit'], line_height * max(1, len(notes_str) // (col_widths['notes'] // 2) +1), item.get('item_unit', 'N/A'), border=1, align='C', fill=fill) # Adjusted height logic inline
                pdf.cell(col_widths['qty'], line_height * max(1, len(notes_str) // (col_widths['notes'] // 2) +1), f"{item.get('requested_qty', 0):.2f}", border=1, align='R', fill=fill) # Adjusted height logic inline
                x_after_qty = pdf.get_x()
                pdf.multi_cell(col_widths['notes'], line_height, notes_str, border=1, align='L', fill=fill, new_x=XPos.LEFT, new_y=YPos.TOP)
                pdf.set_y(start_y)
                pdf.set_x(x_after_qty + col_widths['notes'])
                pdf.ln(line_height * max(1, len(notes_str) // (col_widths['notes'] // 2) +1)) # Adjusted height logic inline
                fill = not fill
        pdf.set_y(-15)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf_output_data = pdf.output()
        return bytes(pdf_output_data)
    except Exception as e:
        st.error(f"Failed to generate PDF: {e}")
        return None

# --- Load Data ---
all_active_items_df, distinct_departments = fetch_indent_page_data(db_engine)

# --- Initialize Session State for Dynamic Rows ---
if 'create_indent_rows' not in st.session_state:
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
    index_to_remove = -1
    for i, row in enumerate(st.session_state.create_indent_rows):
        if row['id'] == row_id_to_remove:
            index_to_remove = i
            break
    if index_to_remove != -1:
        if len(st.session_state.create_indent_rows) > 1:
            st.session_state.create_indent_rows.pop(index_to_remove)
        else:
            st.warning("Cannot remove the last item row.")
    else:
        st.warning(f"Could not find row with ID {row_id_to_remove} to remove.")

# --- Tabs for Indent Management ---
tab_create, tab_view, tab_process = st.tabs([
    "➕ Create Indent", "📄 View Indents", "⚙️ Process Indent (Placeholder)"
])

# ===========================
# ➕ CREATE INDENT TAB (Your existing logic)
# ===========================
with tab_create:
    st.subheader("Create New Material Indent")
    col1, col2 = st.columns(2)
    with col1:
        department = st.selectbox(
            "Requesting Department*", options=distinct_departments, index=None,
            placeholder="Select Department...", key="create_dept",
            help="Select the department requesting the items."
        )
        st.session_state.selected_department_for_create = department
    with col2:
        requested_by = st.text_input("Requested By*", placeholder="Your Name/ID", key="create_req_by", help="Enter the name or ID of the person requesting.")
    col3, col4 = st.columns(2)
    with col3:
        date_required = st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today(), key="create_date_req", help="Select the date when items are needed.")
    with col4:
        st.text_input("Status", value=STATUS_SUBMITTED, disabled=True, key="create_status") # Imported constant
    header_notes = st.text_area("Overall Indent Notes (Optional)", key="create_header_notes", placeholder="Add any general notes for this indent.")
    st.divider()
    st.subheader("Indent Items")
    if st.session_state.selected_department_for_create:
        selected_dept = st.session_state.selected_department_for_create
        if not all_active_items_df.empty:
            try:
                available_items_df = all_active_items_df[
                    all_active_items_df['permitted_departments'].fillna('').astype(str).str.split(',')
                    .apply(lambda depts: selected_dept.strip().lower() in [d.strip().lower() for d in depts] if isinstance(depts, list) else False)
                ].copy()
                if available_items_df.empty:
                    st.warning(f"No active items permitted for '{selected_dept}'. Check item configurations.")
                    item_options_dict = {"Select Item...": None}
                else:
                    item_options_dict = {"Select Item...": None}
                    item_options_dict.update({
                        f"{row['name']} ({row['unit']})": row['item_id']
                        for index, row in available_items_df.sort_values('name').iterrows()
                    })
            except Exception as e:
                st.error(f"Error filtering items by department: {e}")
                item_options_dict = {"Error loading items": None}; available_items_df = pd.DataFrame()
        else:
            st.warning("No active items in system."); item_options_dict = {"No Items Available": None}; available_items_df = pd.DataFrame()
    else:
        st.info("Select department to see items."); item_options_dict = {"Select Department First": None}; available_items_df = pd.DataFrame()

    item_rows_container = st.container()
    items_to_submit = []
    with item_rows_container:
        current_indent_item_ids = set()
        for i, row_state in enumerate(st.session_state.create_indent_rows):
            row_id = row_state['id']
            cols = st.columns([4, 2, 3, 1])
            with cols[0]:
                current_display_value = next((name for name, id_val in item_options_dict.items() if id_val == row_state['item_id']), "Select Item...")
                selected_display_name = cols[0].selectbox(
                    f"Item*", options=list(item_options_dict.keys()),
                    index=list(item_options_dict.keys()).index(current_display_value),
                    key=f"item_select_{row_id}", label_visibility="collapsed",
                )
                selected_item_id = item_options_dict.get(selected_display_name)
                st.session_state.create_indent_rows[i]['item_id'] = selected_item_id
                if selected_item_id is not None and not available_items_df.empty:
                     item_details_df = available_items_df[available_items_df['item_id'] == selected_item_id] # Renamed to avoid conflict
                     if not item_details_df.empty: st.caption(f"Unit: {item_details_df.iloc[0]['unit']}")
                     else: st.caption("Unit: N/A")
            with cols[1]:
                st.session_state.create_indent_rows[i]['requested_qty'] = cols[1].number_input(
                    "Quantity*", min_value=0.01, value=float(row_state['requested_qty']),
                    step=1.0, key=f"item_qty_{row_id}", label_visibility="collapsed"
                )
            with cols[2]:
                st.session_state.create_indent_rows[i]['notes'] = cols[2].text_input(
                    "Item Notes", value=row_state['notes'], placeholder="Optional notes",
                    key=f"item_notes_{row_id}", label_visibility="collapsed"
                )
            with cols[3]:
                if len(st.session_state.create_indent_rows) > 1:
                    cols[3].button("➖", key=f"remove_row_{row_id}", on_click=remove_indent_row, args=(row_id,), help="Remove item")
    st.button("➕ Add Another Item", on_click=add_indent_row)
    st.divider()
    if st.button("Submit Indent", type="primary", key="submit_indent_button"):
        valid = True; items_to_submit = []; seen_item_ids = set()
        header_data = {
            "department": st.session_state.get("create_dept"),
            "requested_by": st.session_state.get("create_req_by", "").strip(),
            "date_required": st.session_state.get("create_date_req"),
            "notes": st.session_state.get("create_header_notes", "").strip() or None,
            "status": STATUS_SUBMITTED # Imported constant
        }
        if not header_data["department"]: st.error("Requesting Department required."); valid = False
        if not header_data["requested_by"]: st.error("Requested By required."); valid = False
        if not header_data["date_required"]: st.error("Date Required required."); valid = False
        for i, row in enumerate(st.session_state.create_indent_rows):
            item_id = row.get('item_id'); qty = row.get('requested_qty')
            if item_id is None: st.error(f"Row {i+1}: Select an item."); valid = False; continue
            if item_id in seen_item_ids:
                 item_name = next((name for name, id_val in item_options_dict.items() if id_val == item_id), f"ID {item_id}")
                 st.error(f"Row {i+1}: Item '{item_name}' duplicated."); valid = False
            if not isinstance(qty, (int, float)) or qty <= 0: st.error(f"Row {i+1}: Quantity must be positive."); valid = False
            if item_id is not None and item_id not in seen_item_ids and valid: # Check valid for current row before adding
                 items_to_submit.append({"item_id": item_id, "requested_qty": float(qty), "notes": row.get('notes', '').strip() or None})
            if item_id is not None: seen_item_ids.add(item_id) # Add to seen even if row had other errors
        if not items_to_submit and valid: st.error("Indent must have at least one valid item."); valid = False
        if valid:
            st.info("Generating MRN and submitting indent...")
            new_mrn = generate_mrn(db_engine) # Imported from app.item_manager_app
            if new_mrn:
                header_data["mrn"] = new_mrn
                # Calls create_indent (imported from app.item_manager_app)
                success, message = create_indent(engine=db_engine, indent_data=header_data, items_data=items_to_submit)
                if success:
                    st.success(f"Indent '{new_mrn}' created successfully!")
                    st.session_state.create_indent_rows = [{'id': 0, 'item_id': None, 'requested_qty': 1.0, 'notes': ''}]
                    st.session_state.create_indent_next_id = 1
                    st.session_state.selected_department_for_create = None
                    st.balloons(); time.sleep(1); st.rerun()
                else: st.error(f"Failed to create indent: {message}")
            else: st.error("Failed to generate MRN. Cannot create indent.")
        else: st.warning("Please fix errors before submitting.")

# ===========================
# 📄 VIEW INDENTS TAB (Your existing logic)
# ===========================
with tab_view:
    st.subheader("View Existing Indents")
    view_cols = st.columns([1, 1, 1, 2])
    with view_cols[0]: mrn_filter = st.text_input("Filter by MRN", key="view_mrn_filter")
    with view_cols[1]: dept_filter = st.selectbox("Filter by Department", options=["All"] + distinct_departments, key="view_dept_filter")
    with view_cols[2]: status_filter = st.selectbox("Filter by Status", options=["All"] + ALL_INDENT_STATUSES, key="view_status_filter") # Imported constant
    with view_cols[3]:
        date_col1, date_col2 = st.columns(2)
        with date_col1: date_start_filter = st.date_input("Submitted From", value=None, key="view_date_start")
        with date_col2: date_end_filter = st.date_input("Submitted To", value=None, key="view_date_end")
    date_start_str_arg = date_start_filter.strftime('%Y-%m-%d') if date_start_filter else None
    date_end_str_arg = date_end_filter.strftime('%Y-%m-%d') if date_end_filter else None
    dept_arg = dept_filter if dept_filter != "All" else None
    status_arg = status_filter if status_filter != "All" else None
    mrn_arg = mrn_filter.strip() if mrn_filter else None
    # Calls get_indents (imported from app.item_manager_app)
    indents_df = get_indents(
        db_engine, mrn_filter=mrn_arg, dept_filter=dept_arg, status_filter=status_arg,
        date_start_str=date_start_str_arg, date_end_str=date_end_str_arg
    )
    st.divider()
    if indents_df.empty: st.info("No indents found matching criteria.")
    else:
        st.success(f"Found {len(indents_df)} indent(s).")
        display_df = indents_df.copy()
        if 'date_required' in display_df.columns: display_df['date_required'] = pd.to_datetime(display_df['date_required'], errors='coerce').dt.strftime('%Y-%m-%d')
        if 'date_submitted' in display_df.columns: display_df['date_submitted'] = pd.to_datetime(display_df['date_submitted'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(
            display_df, use_container_width=True, hide_index=True,
            column_order=["mrn", "date_submitted", "department", "requested_by", "date_required", "status", "item_count", "indent_notes"],
            column_config={
                "indent_id": None, "mrn": st.column_config.TextColumn("MRN", width="medium"),
                "date_submitted": st.column_config.TextColumn("Submitted", width="medium"),
                "department": st.column_config.TextColumn("Department", width="medium"),
                "requested_by": st.column_config.TextColumn("Requestor", width="medium"),
                "date_required": st.column_config.TextColumn("Required By", width="small"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "item_count": st.column_config.NumberColumn("Items", format="%d", width="small"),
                "indent_notes": st.column_config.TextColumn("Notes", width="large"),
            }
        )
        st.divider(); st.subheader("Download Indent as PDF")
        if not indents_df.empty:
            available_mrns = ["Select MRN..."] + indents_df['mrn'].tolist()
            selected_mrn_for_pdf = st.selectbox("Choose MRN to download:", options=available_mrns, key="pdf_mrn_select")
            download_button_placeholder = st.empty()
            if selected_mrn_for_pdf != "Select MRN...":
                if st.button("Generate PDF", key="generate_pdf_btn"):
                    with st.spinner(f"Generating PDF for {selected_mrn_for_pdf}..."):
                        # Calls get_indent_details_for_pdf (imported from app.item_manager_app)
                        header_details, items_details = get_indent_details_for_pdf(db_engine, selected_mrn_for_pdf)
                        if header_details and items_details is not None:
                            pdf_bytes = generate_indent_pdf(header_details, items_details)
                            if pdf_bytes:
                                download_button_placeholder.download_button(
                                    label=f"Download PDF for {selected_mrn_for_pdf}", data=pdf_bytes,
                                    file_name=f"indent_{selected_mrn_for_pdf}.pdf", mime="application/pdf",
                                    key="download_pdf_btn_final"
                                )
                                st.success("PDF ready. Click download button.")
                            else: download_button_placeholder.empty()
                        else: st.error(f"Could not fetch details for MRN {selected_mrn_for_pdf}."); download_button_placeholder.empty()
            else: download_button_placeholder.empty()
        else: st.info("No indents to download.")

# ===========================
# ⚙️ PROCESS INDENT TAB (Your existing placeholder)
# ===========================
with tab_process:
    st.header("Process Indent (Placeholder)")
    st.info("This section will allow authorized users to view submitted indents, allocate stock, mark items as fulfilled, and update the indent status (e.g., Processing, Completed).")