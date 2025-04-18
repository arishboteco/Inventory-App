# pages/5_Indents.py – Fix for strip error during submission + PDF + Drilldown

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
        fetch_data,
        get_all_items_with_stock,
        generate_mrn,
        create_indent,
        get_indents,
        get_distinct_departments_from_items,
        generate_indent_pdf,      # <-- Import PDF function
        get_indent_items,         # <-- Import function to get items
        ALL_INDENT_STATUSES,
        STATUS_SUBMITTED
    )
except ImportError as e:
    st.error(f"Import error from item_manager_app.py: {e}. Check file location and content.")
    st.stop()
except Exception as e:
    st.error(f"Unexpected error during import: {e}")
    st.stop()

# --- Constants ---
# DEPARTMENTS list removed, using dynamic list fetched below

# --- Page Setup ---
st.set_page_config(layout="wide")
st.header("🛒 Material Indents")
db_engine = connect_db()
if not db_engine: st.error("Database connection failed."); st.stop()

# --- Session State Initialization ---
if 'create_indent_rows' not in st.session_state: st.session_state.create_indent_rows = [{'id': 0}]
if 'create_indent_next_row_id' not in st.session_state: st.session_state.create_indent_next_row_id = 1
if 'create_indent_selected_department' not in st.session_state: st.session_state.create_indent_selected_department = None
if 'show_indent_summary' not in st.session_state: st.session_state.show_indent_summary = False
if 'last_submitted_indent_header' not in st.session_state: st.session_state.last_submitted_indent_header = None
if 'last_submitted_indent_items' not in st.session_state: st.session_state.last_submitted_indent_items = None
if 'view_selected_mrn' not in st.session_state: st.session_state.view_selected_mrn = None # For drilldown

# --- Fetch Data needed across Tabs (Cached) ---
@st.cache_data(ttl=120)
def fetch_indent_page_data(_engine):
    items = get_all_items_with_stock(_engine, include_inactive=False)
    dynamic_departments = get_distinct_departments_from_items(_engine)
    indent_info_df = fetch_data(_engine, "SELECT DISTINCT status, department FROM indents")
    statuses = ["All"] + sorted(indent_info_df['status'].unique().tolist()) if not indent_info_df.empty else ["All"]
    view_departments = ["All"] + sorted(indent_info_df['department'].unique().tolist()) if not indent_info_df.empty else ["All"]
    create_depts = dynamic_departments if dynamic_departments else []
    return items, create_depts, statuses, view_departments

items_df, create_dept_options, view_status_options, view_dept_options = fetch_indent_page_data(db_engine)

# --- Callbacks for Create Indent ---
def add_indent_row():
    new_row_id = st.session_state.create_indent_next_row_id; st.session_state.create_indent_rows.append({'id': new_row_id}); st.session_state.create_indent_next_row_id += 1
def remove_indent_row(row_id):
    st.session_state.create_indent_rows = [r for r in st.session_state.create_indent_rows if r['id'] != row_id]; keys_to_remove = [k for k in st.session_state if k.startswith(f"create_item_{row_id}_")];
    for k in keys_to_remove: del st.session_state[k]
def department_changed(): st.session_state.create_indent_selected_department = st.session_state.get('create_indent_department_select')

# --- Tabs ---
tab_create, tab_view, tab_process = st.tabs(["📝 Create New Indent", "📊 View Indents", "⚙️ Process Indent (Future)"])

# ============================
# 📝 CREATE NEW INDENT TAB
# ============================
with tab_create:
    if st.session_state.get('show_indent_summary', False):
        # Display Summary Section
        st.subheader("✅ Indent Submitted Successfully!"); header_data = st.session_state.get('last_submitted_indent_header', {}); items_data = st.session_state.get('last_submitted_indent_items', [])
        if not header_data: st.warning("Could not retrieve details.")
        else:
            st.success(f"Indent **{header_data.get('mrn', 'N/A')}** has been submitted.")
            cols_summary = st.columns(2)
            with cols_summary[0]: st.markdown(f"**MRN:** {header_data.get('mrn', 'N/A')}<br>**Department:** {header_data.get('department', 'N/A')}<br>**Requested By:** {header_data.get('requested_by', 'N/A')}", unsafe_allow_html=True)
            with cols_summary[1]: st.markdown(f"**Date Required:** {header_data.get('date_required', 'N/A')}<br>**Status:** {header_data.get('status', 'N/A')}", unsafe_allow_html=True)
            if header_data.get('notes'): st.markdown(f"**Indent Notes:**\n> {header_data.get('notes')}")
            st.markdown("**Submitted Items:**")
            if not items_data: st.info("No items recorded.")
            else:
                summary_df = pd.DataFrame(items_data); st.dataframe(summary_df, column_order=["item_name", "item_unit", "requested_qty", "notes"], column_config={"item_id": None, "item_name": st.column_config.TextColumn("Item Name", width="large"), "item_unit": st.column_config.TextColumn("Unit", width="small"), "requested_qty": st.column_config.NumberColumn("Requested Qty", format="%.2f", width="small"), "notes": st.column_config.TextColumn("Item Notes", width="medium")}, hide_index=True, use_container_width=True)

            # PDF Download Button Block
            try:
                header_data_for_pdf = header_data.copy()
                if 'date_submitted' not in header_data_for_pdf:
                     header_data_for_pdf['date_submitted'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                elif isinstance(header_data_for_pdf['date_submitted'], (datetime, date)):
                     header_data_for_pdf['date_submitted'] = header_data_for_pdf['date_submitted'].strftime('%Y-%m-%d %H:%M')
                pdf_bytes = generate_indent_pdf(header_data_for_pdf, items_data)
                st.download_button(label="📄 Download Indent PDF", data=pdf_bytes, file_name=f"{header_data.get('mrn', 'indent')}.pdf", mime="application/pdf", key="download_pdf_btn_final")
            except NameError: st.error("PDF function missing. Check item_manager_app.py.")
            except ImportError: st.error("FPDF library missing. Install `fpdf2`.")
            except Exception as pdf_e: st.error(f"Could not generate PDF: {pdf_e}")

        st.divider()
        if st.button("➕ Create Another Indent / Clear Summary", key="clear_summary_btn"):
            st.session_state.show_indent_summary = False;
            if 'last_submitted_indent_header' in st.session_state: del st.session_state['last_submitted_indent_header']
            if 'last_submitted_indent_items' in st.session_state: del st.session_state['last_submitted_indent_items']
            st.rerun()
    else:
        # Display Create Form
        st.subheader("Create a New Material Request");
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            # Get values from widgets - they return "" if empty, not None usually
            with col1: requested_by = st.text_input("Requested By*", key="create_indent_requested_by_input")
            with col2:
                if not create_dept_options: st.warning("No departments found."); selected_dept = None
                else:
                    current_dept_val = st.session_state.create_indent_selected_department
                    try: dept_index = create_dept_options.index(current_dept_val) if current_dept_val in create_dept_options else 0
                    except ValueError: dept_index = 0
                    selected_dept = st.selectbox("Requesting Department*", create_dept_options, key='create_indent_department_select', index=dept_index, on_change=department_changed, placeholder="Select department...")
                    if selected_dept != st.session_state.create_indent_selected_department: st.session_state.create_indent_selected_department = selected_dept
                current_selected_dept = st.session_state.create_indent_selected_department
            with col3: date_required = st.date_input("Date Required*", datetime.now().date() + timedelta(days=1), key="create_indent_date_required_input")
            notes_header = st.text_area("Indent Notes (Optional)", key="create_indent_notes_header_input", height=75)

        st.subheader("Indent Items"); filtered_items_df = pd.DataFrame()
        if current_selected_dept and not items_df.empty:
            def is_dept_permitted(p): return False if pd.isna(p) or not isinstance(p,str) or not p.strip() else current_selected_dept in [d.strip() for d in p.split(',') if d.strip()]
            mask = items_df['permitted_departments'].apply(is_dept_permitted); filtered_items_df = items_df[mask].copy()

        item_rows_data = [];
        if not filtered_items_df.empty:
            item_options = filtered_items_df[['item_id', 'name', 'unit']].to_dict('records'); item_display_options = {item['item_id']: f"{item['name']} ({item['unit']})" for item in item_options}; item_unit_map = {item['item_id']: item['unit'] for item in item_options}
            header_cols = st.columns([3, 1, 1, 3, 1]); header_cols[0].write("**Item**"); header_cols[1].write("**Unit**"); header_cols[2].write("**Req. Qty***"); header_cols[3].write("**Item Notes**"); header_cols[4].write("**Action**"); st.markdown("---")
            for i, row_state in enumerate(st.session_state.create_indent_rows):
                row_id = row_state['id']; key_base = f"create_item_{row_id}"; cols = st.columns([3, 1, 1, 3, 1])
                with cols[0]:
                    current_item_selection = st.session_state.get(f"{key_base}_select", None); valid_item_ids = list(item_display_options.keys())
                    try: item_index = valid_item_ids.index(current_item_selection) if current_item_selection in valid_item_ids else None
                    except ValueError: item_index = None
                    selected_item_id = st.selectbox(f"Item##{key_base}_select", options=valid_item_ids, format_func=lambda x: item_display_options.get(x, "Select..."), label_visibility="collapsed", key=f"{key_base}_select", index=item_index, placeholder="Select item...")
                with cols[1]: unit = item_unit_map.get(selected_item_id, ""); st.text_input(f"Unit##{key_base}_unit", value=unit, key=f"{key_base}_unit_display", disabled=True, label_visibility="collapsed")
                with cols[2]: requested_qty = st.number_input(f"Qty##{key_base}_qty", min_value=0.01, step=1.0, value=float(st.session_state.get(f"{key_base}_qty", 1.0)), format="%.2f", label_visibility="collapsed", key=f"{key_base}_qty")
                with cols[3]: item_notes = st.text_input(f"Notes##{key_base}_notes", key=f"{key_base}_notes", label_visibility="collapsed")
                with cols[4]: disable_remove = len(st.session_state.create_indent_rows) <= 1; st.button("➖", key=f"{key_base}_remove", on_click=remove_indent_row, args=(row_id,), disabled=disable_remove, help="Remove item row")
                if selected_item_id: item_rows_data.append({'item_id': selected_item_id, 'requested_qty': requested_qty, 'notes': item_notes.strip() or None, 'row_id': row_id})
        else:
            if current_selected_dept: st.warning(f"No active items found permitted for department: '{current_selected_dept}'.")
            else: st.warning("Please select a requesting department.")

        st.markdown("---"); col_add, col_submit = st.columns([1, 10])
        with col_add: st.button("➕ Add Item", key="create_indent_add_item_btn", on_click=add_indent_row, disabled=filtered_items_df.empty)
        with col_submit:
            can_submit = bool(item_rows_data and requested_by and current_selected_dept and date_required)
            submit_indent = st.button("✅ Submit Indent", key="create_indent_submit_btn", type="primary", disabled=not can_submit)

        # Indent Submission Logic
        if submit_indent:
            is_valid = True; validation_errors = [] # Validation logic... (as before)
            # Ensure requested_by is not None or just whitespace before proceeding
            if not requested_by or not requested_by.strip():
                 validation_errors.append("'Requested By' cannot be empty."); is_valid = False
            if not current_selected_dept: validation_errors.append("'Department' required."); is_valid = False
            if not date_required: validation_errors.append("'Date Required' required."); is_valid = False
            if not item_rows_data: validation_errors.append("At least one item required."); is_valid = False
            else: # Item validation
                seen_item_ids=set();
                for idx,d in enumerate(item_rows_data):
                    if not d.get('item_id'): is_valid=False
                    elif d['item_id'] in seen_item_ids: item_name=item_display_options.get(d['item_id'],f"ID {d['item_id']}"); validation_errors.append(f"Row {idx+1}: Item '{item_name}' duplicated."); is_valid=False
                    else: seen_item_ids.add(d['item_id'])
                    if not d.get('requested_qty') or d['requested_qty']<=0: item_name=item_display_options.get(d['item_id'],f"ID {d['item_id']}"); validation_errors.append(f"Row {idx+1}: Qty for '{item_name}' must be > 0."); is_valid=False

            # --- Submission ---
            if not is_valid: st.error("Validation failed:\n" + "\n".join(f"- {e}" for e in validation_errors))
            else:
                with st.spinner("Submitting Indent..."):
                    try:
                        new_mrn = generate_mrn(db_engine)
                        if not new_mrn: st.error("Failed to generate MRN.")
                        else:
                            date_required_str = date_required.strftime('%Y-%m-%d')
                            # *** MODIFIED SECTION START: Safer data prep ***
                            # Ensure .strip() is called safely
                            req_by_cleaned = requested_by.strip() # Already validated not empty/None above
                            notes_cleaned = notes_header.strip() if notes_header else None # Handle potential None for notes

                            indent_header_data = {
                                'mrn': new_mrn,
                                'requested_by': req_by_cleaned, # Use cleaned value
                                'department': current_selected_dept,
                                'date_required': date_required_str,
                                'notes': notes_cleaned, # Use cleaned value
                                'status': STATUS_SUBMITTED
                            }
                            # *** MODIFIED SECTION END ***

                            items_submitted_details = [{'item_id': item['item_id'], 'item_name': item_display_options.get(item['item_id'], f"ID {item['item_id']}"), 'item_unit': item_unit_map.get(item['item_id'], ""), 'requested_qty': item['requested_qty'], 'notes': item['notes']} for item in item_rows_data]
                            items_to_submit_backend = [{'item_id': item['item_id'], 'requested_qty': item['requested_qty'], 'notes': item['notes']} for item in items_submitted_details]

                            # Call backend function
                            success, message = create_indent(db_engine, indent_header_data, items_to_submit_backend)

                            if success: # Store state and rerun for summary view
                                st.session_state.last_submitted_indent_header = indent_header_data; st.session_state.last_submitted_indent_items = items_submitted_details; st.session_state.show_indent_summary = True
                                # Clear form state
                                st.session_state.create_indent_rows = [{'id': 0}]; st.session_state.create_indent_next_row_id = 1; st.session_state.create_indent_selected_department = None
                                if 'create_indent_requested_by_input' in st.session_state: del st.session_state['create_indent_requested_by_input']
                                if 'create_indent_department_select' in st.session_state: del st.session_state['create_indent_department_select']
                                if 'create_indent_notes_header_input' in st.session_state: del st.session_state['create_indent_notes_header_input']
                                keys_to_clear = [k for k in st.session_state if k.startswith("create_item_")];
                                for k in keys_to_clear: del st.session_state[k]
                                fetch_indent_page_data.clear(); st.rerun()
                            else: st.error(f"Failed create indent: {message}")
                    except Exception as e: st.error(f"An unexpected error occurred during submission: {e}")


# ============================
# 📊 VIEW INDENTS TAB (Includes Item Drilldown)
# ============================
with tab_view:
    st.subheader("View Submitted Indents"); st.write("Apply filters:")
    col_flt1, col_flt2 = st.columns([1, 3])
    with col_flt1:
        mrn_filter = st.text_input("MRN Filter", key="view_mrn_filter")
        dept_filter = st.selectbox("Department Filter", options=view_dept_options, index=0, key="view_dept_filter")
        status_filter = st.selectbox("Status Filter", options=view_status_options, index=0, key="view_status_filter")
    with col_flt2:
        filter_date_from_obj = st.date_input("Submitted From", value=None, key="view_date_from_obj_final", help="Leave blank for no start date")
        filter_date_to_obj = st.date_input("Submitted To", value=None, key="view_date_to_obj_final", help="Leave blank for no end date")

    indents_df = pd.DataFrame()
    if filter_date_from_obj and filter_date_to_obj and filter_date_from_obj > filter_date_to_obj: st.warning("Start date cannot be after end date.")
    else:
        date_start_str_arg = filter_date_from_obj.strftime('%Y-%m-%d') if filter_date_from_obj else None; date_end_str_arg = filter_date_to_obj.strftime('%Y-%m-%d') if filter_date_to_obj else None
        dept_arg = dept_filter if dept_filter != "All" else None; status_arg = status_filter if status_filter != "All" else None; mrn_arg = mrn_filter.strip() if mrn_filter else None
        indents_df = get_indents(db_engine, mrn_filter=mrn_arg, dept_filter=dept_arg, status_filter=status_arg, date_start_str=date_start_str_arg, date_end_str=date_end_str_arg)

    st.divider()
    if indents_df.empty: st.info("No indents found matching filters.")
    else:
        st.success(f"Found {len(indents_df)} indent(s).")
        if 'mrn' in indents_df.columns and 'indent_id' in indents_df.columns:
             mrn_options = pd.Series(indents_df.indent_id.values,index=indents_df.mrn).to_dict()
             mrn_display_list = ["Select MRN to view items..."] + sorted(list(mrn_options.keys()), reverse=True)
        else: st.error("Missing 'mrn' or 'indent_id' column."); mrn_options = {}; mrn_display_list = ["Select MRN..."]

        expected_view_cols = ["mrn", "date_submitted", "department", "requested_by", "date_required", "status", "item_count", "indent_notes"]
        actual_view_cols = [col for col in expected_view_cols if col in indents_df.columns]
        st.dataframe(indents_df, use_container_width=True, hide_index=True, column_order=actual_view_cols,
            column_config={"indent_id": None, "mrn": st.column_config.TextColumn("MRN", width="medium"), "requested_by": st.column_config.TextColumn("Requested By", width="small"),"department": st.column_config.TextColumn("Department", width="small"), "date_required": st.column_config.DateColumn("Date Required", format="YYYY-MM-DD", width="small"), "date_submitted": st.column_config.DatetimeColumn("Submitted On", format="YYYY-MM-DD HH:mm", width="medium"), "status": st.column_config.TextColumn("Status", width="small"), "item_count": st.column_config.NumberColumn("# Items", width="small"), "indent_notes": st.column_config.TextColumn("Indent Notes", width="large")})

        # Section to View Items for Selected Indent
        if mrn_options:
            st.divider(); st.subheader("View Indent Items")
            current_selection = st.session_state.get('view_selected_mrn', mrn_display_list[0])
            if current_selection not in mrn_display_list: current_selection = mrn_display_list[0]
            selected_mrn = st.selectbox("Select MRN from list above:", options=mrn_display_list, key='view_select_mrn_box_final', index=mrn_display_list.index(current_selection))
            st.session_state.view_selected_mrn = selected_mrn

            if selected_mrn != mrn_display_list[0]:
                selected_indent_id = mrn_options.get(selected_mrn)
                if selected_indent_id:
                    with st.spinner(f"Loading items for {selected_mrn}..."):
                        items_in_indent_df = get_indent_items(db_engine, selected_indent_id) # Call backend
                        if items_in_indent_df.empty: st.info(f"No items found for MRN {selected_mrn}.")
                        else:
                            st.dataframe(items_in_indent_df, use_container_width=True, hide_index=True, column_order=["item_name", "item_unit", "requested_qty", "fulfilled_qty", "notes"],
                                column_config={"indent_item_id": None, "item_id": None, "item_name": st.column_config.TextColumn("Item Name", width="large"), "item_unit": st.column_config.TextColumn("Unit", width="small"), "requested_qty": st.column_config.NumberColumn("Requested", format="%.2f", width="small"), "fulfilled_qty": st.column_config.NumberColumn("Fulfilled", format="%.2f", width="small"), "notes": st.column_config.TextColumn("Item Notes", width="medium")})
                else: st.warning("Could not find details for selected MRN.")

# ============================
# ⚙️ PROCESS INDENT TAB
# ============================
with tab_process:
    st.subheader("Process Indent (Future Implementation)"); st.info("This section will allow viewing indent details, marking items as fulfilled, and updating indent status.")

