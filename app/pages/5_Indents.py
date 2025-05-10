# app/pages/5_Indents.py
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple, Set
import time
import urllib.parse
from fpdf import FPDF
from fpdf.enums import XPos, YPos

try:
    from app.db.database_utils import connect_db, fetch_data
    from app.services import item_service
    from app.services import indent_service
    from app.core.constants import ALL_INDENT_STATUSES, STATUS_SUBMITTED, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_CANCELLED
except ImportError as e:
    st.error(f"Import error in 5_Indents.py: {e}. Please ensure all service files and utility modules are correctly placed and named.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during an import in 5_Indents.py: {e}")
    st.stop()

# --- Session State Initialization ---
placeholder_option_stock = ("-- Select Item --", -1)

# For Create Indent dynamic rows
if 'create_indent_rows' not in st.session_state:
    st.session_state.create_indent_rows = [{'id': 0, 'item_id': None, 'requested_qty': 1.0, 'notes': '', 'last_ordered': None, 'median_qty': None, 'category': None, 'sub_category': None}]
    st.session_state.create_indent_next_id = 1
if 'selected_department_for_create_indent' not in st.session_state:
     st.session_state.selected_department_for_create_indent = None
if "num_lines_to_add_indent_widget" not in st.session_state:
    st.session_state.num_lines_to_add_indent_widget = 1

# For "Print after create" feature
if 'last_created_mrn_for_print' not in st.session_state: st.session_state.last_created_mrn_for_print = None
if 'last_submitted_indent_details' not in st.session_state: st.session_state.last_submitted_indent_details = None
if 'pdf_bytes_for_download' not in st.session_state: st.session_state.pdf_bytes_for_download = None
if 'pdf_filename_for_download' not in st.session_state: st.session_state.pdf_filename_for_download = None

# For section navigation (radio buttons)
INDENT_SECTIONS = {"create": "➕ Create Indent", "view": "📄 View Indents", "process": "⚙️ Process Indent"}
INDENT_SECTION_KEYS = list(INDENT_SECTIONS.keys())
INDENT_SECTION_DISPLAY_NAMES = list(INDENT_SECTIONS.values())
if 'active_indent_section' not in st.session_state:
    st.session_state.active_indent_section = INDENT_SECTION_KEYS[0]

# For Create Indent Header Form Fields Persistency & Reset
# Using v15 for this iteration to ensure key freshness
CREATE_INDENT_DEPT_SESS_KEY = "sess_create_indent_dept_v15"
CREATE_INDENT_REQ_BY_SESS_KEY = "sess_create_indent_req_by_val_v15"
CREATE_INDENT_DATE_REQ_SESS_KEY = "sess_create_indent_date_req_val_v15"
CREATE_INDENT_NOTES_SESS_KEY = "sess_create_indent_header_notes_val_v15"
CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY = "sess_create_indent_header_reset_signal_v15"

for key, default_val in [
    (CREATE_INDENT_DEPT_SESS_KEY, ""), 
    (CREATE_INDENT_REQ_BY_SESS_KEY, ""),
    (CREATE_INDENT_DATE_REQ_SESS_KEY, date.today() + timedelta(days=1)),
    (CREATE_INDENT_NOTES_SESS_KEY, ""),
    (CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY, False)
]:
    if key not in st.session_state:
        st.session_state[key] = default_val

# --- Page Config & Title ---
st.title("📝 Material Indents Management")
st.write("Create new material requests (indents), view their status, and download details.")
st.divider()

db_engine = connect_db()
if not db_engine: st.error("Database connection failed."); st.stop()

@st.cache_data(ttl=300, show_spinner="Loading item & department data...")
def fetch_indent_page_data(_engine):
    if _engine is None: return pd.DataFrame(columns=['item_id', 'name', 'unit', 'category', 'sub_category', 'permitted_departments']), []
    items_df = item_service.get_all_items_with_stock(_engine, include_inactive=False)
    required_cols = ['item_id', 'name', 'unit', 'category', 'sub_category', 'permitted_departments']
    if not all(col in items_df.columns for col in required_cols):
        st.error("Required columns (incl. category/sub_category) missing from items_df in fetch_indent_page_data.")
        return pd.DataFrame(columns=required_cols), []
    return items_df[required_cols].copy(), item_service.get_distinct_departments_from_items(_engine)

all_active_items_df, distinct_departments = fetch_indent_page_data(db_engine)

def generate_indent_pdf(indent_header: Dict, indent_items: List[Dict]) -> Optional[bytes]:
    # ... (Your existing, working PDF generation code with Category/Sub-Category grouping) ...
    if not indent_header or indent_items is None:
         st.error("Cannot generate PDF: Missing indent header or items data.")
         return None
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Material Indent Request", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(10); pdf.set_font("Helvetica", "", 11)
        label_width = pdf.get_string_width("Date Required: ") + 2 
        def add_header_line(label, value):
            pdf.set_font("Helvetica", "", 11); pdf.cell(label_width, 7, label)
            pdf.set_font("Helvetica", "B", 11); pdf.cell(0, 7, str(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        add_header_line("MRN:", indent_header.get('mrn', 'N/A')); add_header_line("Department:", indent_header.get('department', 'N/A'))
        add_header_line("Requested By:", indent_header.get('requested_by', 'N/A')); add_header_line("Date Submitted:", indent_header.get('date_submitted', 'N/A'))
        add_header_line("Date Required:", indent_header.get('date_required', 'N/A')); add_header_line("Status:", indent_header.get('status', 'N/A'))
        if indent_header.get('notes'):
            pdf.ln(3); pdf.set_font("Helvetica", "I", 10) 
            pdf.multi_cell(0, 5, f"Indent Notes: {indent_header['notes']}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(8); pdf.set_font("Helvetica", "B", 10)
        col_widths = {'sno': 10, 'name': 80, 'unit': 20, 'qty': 25, 'notes': 55} 
        pdf.set_fill_color(220, 220, 220)
        for key_pdf, header_text_pdf in [('sno',"S.No."), ('name',"Item Name"), ('unit',"Unit"), ('qty',"Req. Qty"), ('notes',"Item Notes")]:
            align_pdf = 'C' if key_pdf in ['sno', 'unit'] else ('R' if key_pdf == 'qty' else 'L')
            pdf.cell(col_widths[key_pdf], 7, header_text_pdf, border=1, align=align_pdf, fill=True, new_x=XPos.RIGHT if key_pdf != 'notes' else XPos.LMARGIN, new_y=YPos.NEXT if key_pdf == 'notes' else YPos.TOP)
        pdf.set_font("Helvetica", "", 9); current_category_pdf = None; current_sub_category_pdf = None; item_serial_number_pdf = 0
        if not indent_items: pdf.cell(sum(col_widths.values()), 7, "No items.", border=1, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            for item_pdf in indent_items: 
                item_cat_pdf = item_pdf.get('item_category', 'Uncategorized'); item_subcat_pdf = item_pdf.get('item_sub_category', 'General')
                if item_cat_pdf != current_category_pdf:
                    current_category_pdf = item_cat_pdf; current_sub_category_pdf = None 
                    pdf.set_font("Helvetica", "B", 10); pdf.set_fill_color(230,230,250)
                    pdf.cell(0, 7, f"Category: {current_category_pdf}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, align='L')
                if item_subcat_pdf != current_sub_category_pdf:
                    current_sub_category_pdf = item_subcat_pdf
                    pdf.set_font("Helvetica", "BI", 9); pdf.set_fill_color(240,240,240) 
                    pdf.cell(5); pdf.cell(0, 6, f"Sub-Category: {current_sub_category_pdf}", border="LRB", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=False, align='L')
                pdf.set_font("Helvetica", "", 9); item_serial_number_pdf += 1
                notes_str_pdf = item_pdf.get('item_notes', '') or ''; item_name_str_pdf = item_pdf.get('item_name', 'N/A') or 'N/A'
                line_height_pdf = 5
                name_lines_pdf = pdf.get_string_width(item_name_str_pdf)//col_widths['name']+1 if col_widths['name'] > 0 else 1
                notes_lines_pdf = pdf.get_string_width(notes_str_pdf)//col_widths['notes']+1 if col_widths['notes'] > 0 else 1
                num_lines_pdf = int(max(1, name_lines_pdf, notes_lines_pdf)); row_height_pdf = line_height_pdf * num_lines_pdf
                start_y_item_pdf = pdf.get_y()
                pdf.cell(col_widths['sno'], row_height_pdf, str(item_serial_number_pdf), border='LRB', align='C')
                x_before_name_pdf = pdf.get_x()
                pdf.multi_cell(col_widths['name'], line_height_pdf, item_name_str_pdf, border='RB', align='L', new_x=XPos.LEFT, new_y=YPos.TOP)
                pdf.set_xy(x_before_name_pdf + col_widths['name'], start_y_item_pdf)
                pdf.cell(col_widths['unit'], row_height_pdf, str(item_pdf.get('item_unit', 'N/A')), border='RB', align='C')
                pdf.cell(col_widths['qty'], row_height_pdf, f"{item_pdf.get('requested_qty', 0):.2f}", border='RB', align='R')
                x_before_notes_pdf = pdf.get_x()
                pdf.multi_cell(col_widths['notes'], line_height_pdf, notes_str_pdf, border='RB', align='L', new_x=XPos.LEFT, new_y=YPos.TOP)
                pdf.ln(row_height_pdf)
        pdf.set_y(-15); pdf.set_font("Helvetica", "I", 8); pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align='C')
        return bytes(pdf.output())
    except Exception as e_pdf: st.error(f"Failed to generate PDF: {e_pdf}"); return None

# --- Callbacks ---
def add_single_indent_row_logic():
    new_id = st.session_state.create_indent_next_id
    st.session_state.create_indent_rows.append({'id': new_id, 'item_id': None, 'requested_qty': 1.0, 'notes': '', 'last_ordered': None, 'median_qty': None, 'category': None, 'sub_category': None})
    st.session_state.create_indent_next_id += 1

def add_multiple_indent_lines_callback():
    num_lines = st.session_state.get("num_lines_to_add_indent_widget", 1)
    for _ in range(int(num_lines)): add_single_indent_row_logic()

def remove_indent_row_callback(row_id_to_remove):
    idx_to_remove = next((i for i, r in enumerate(st.session_state.create_indent_rows) if r['id'] == row_id_to_remove), -1)
    if idx_to_remove != -1:
        if len(st.session_state.create_indent_rows) > 1: st.session_state.create_indent_rows.pop(idx_to_remove)
        else: st.warning("Cannot remove last item row.")

def add_suggested_item_callback(item_id_to_add, item_name_to_add, unit_to_add):
    if any(row.get('item_id') == item_id_to_add for row in st.session_state.create_indent_rows):
        st.toast(f"'{item_name_to_add}' is already in the indent list.", icon="ℹ️"); return
    empty_row_idx = next((i for i,r in enumerate(st.session_state.create_indent_rows) if r.get('item_id') is None or r.get('item_id')==-1), -1)
    current_department = st.session_state.get(CREATE_INDENT_DEPT_SESS_KEY)
    history = item_service.get_item_order_history_details(db_engine, item_id_to_add, current_department)
    item_master_detail = all_active_items_df[all_active_items_df['item_id'] == item_id_to_add].iloc[0] if item_id_to_add in all_active_items_df['item_id'].values else {}
    new_row_data = {'item_id': item_id_to_add, 'requested_qty': 1.0, 'notes': '',
                    'last_ordered': history.get('last_ordered_date'), 
                    'median_qty': history.get('median_quantity'),
                    'category': item_master_detail.get('category', 'N/A'),
                    'sub_category': item_master_detail.get('sub_category', 'N/A')}
    if history.get('median_quantity') and history.get('median_quantity') > 0:
        new_row_data['requested_qty'] = float(history.get('median_quantity'))
    if empty_row_idx != -1:
        st.session_state.create_indent_rows[empty_row_idx].update(new_row_data)
        st.toast(f"Added '{item_name_to_add}' to row {empty_row_idx + 1}.", icon="👍")
    else:
        new_id = st.session_state.create_indent_next_id
        st.session_state.create_indent_rows.append({'id': new_id, **new_row_data})
        st.session_state.create_indent_next_id += 1
        st.toast(f"Added '{item_name_to_add}' as a new line.", icon="👍")

def update_row_item_details_callback(row_index, item_selectbox_key_arg, item_options_dict_arg):
    selected_display_name = st.session_state[item_selectbox_key_arg]
    item_id_val = item_options_dict_arg.get(selected_display_name)
    category_val, sub_category_val = "N/A", "N/A"
    if item_id_val and item_id_val != -1:
        item_master_row = all_active_items_df[all_active_items_df['item_id'] == item_id_val]
        if not item_master_row.empty: # Corrected .empty
            category_val = item_master_row.iloc[0]['category']
            sub_category_val = item_master_row.iloc[0]['sub_category']
    st.session_state.create_indent_rows[row_index].update({
        'item_id': item_id_val, 'category': category_val, 'sub_category': sub_category_val
    })
    if item_id_val and item_id_val != -1:
        dept_for_history = st.session_state.get(CREATE_INDENT_DEPT_SESS_KEY)
        history = item_service.get_item_order_history_details(db_engine, item_id_val, dept_for_history)
        st.session_state.create_indent_rows[row_index].update({
            'last_ordered': history.get('last_ordered_date'), 'median_qty': history.get('median_quantity')
        })
        if history.get('median_quantity') and history.get('median_quantity') > 0:
            st.session_state.create_indent_rows[row_index]['requested_qty'] = float(history.get('median_quantity'))
    else:
        st.session_state.create_indent_rows[row_index].update({'last_ordered': None, 'median_qty': None, 'category': None, 'sub_category': None})

def set_active_indent_section_callback():
    selected_display_name = st.session_state.indent_section_radio_key_v15 # Unique key
    for key, display_name in INDENT_SECTIONS.items():
        if display_name == selected_display_name:
            st.session_state.active_indent_section = key
            if key != "create":
                st.session_state.last_created_mrn_for_print = None
                if "pdf_bytes_for_download" in st.session_state: del st.session_state.pdf_bytes_for_download
                if "pdf_filename_for_download" in st.session_state: del st.session_state.pdf_filename_for_download
            break
st.radio("Indent Actions:", options=INDENT_SECTION_DISPLAY_NAMES,
         index=INDENT_SECTION_KEYS.index(st.session_state.active_indent_section),
         key="indent_section_radio_key_v15", on_change=set_active_indent_section_callback, horizontal=True)
st.markdown("---")

# ===========================
# CREATE INDENT SECTION
# ===========================
if st.session_state.active_indent_section == "create":
    st.subheader("📝 Create New Material Indent Request")
    if st.session_state.get(CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY, False):
        st.session_state[CREATE_INDENT_DEPT_SESS_KEY] = ""
        st.session_state[CREATE_INDENT_REQ_BY_SESS_KEY] = ""
        st.session_state[CREATE_INDENT_DATE_REQ_SESS_KEY] = date.today() + timedelta(days=1)
        st.session_state[CREATE_INDENT_NOTES_SESS_KEY] = ""
        st.session_state.selected_department_for_create_indent = None
        st.session_state[CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY] = False

    if st.session_state.get("last_created_mrn_for_print"):
        mrn_to_print = st.session_state.last_created_mrn_for_print
        st.success(f"Indent **{mrn_to_print}** was created successfully!")
        if st.session_state.get("last_submitted_indent_details"):
            summary_header = st.session_state.last_submitted_indent_details['header']
            summary_items = st.session_state.last_submitted_indent_details['items']
            st.write("Submitted Items:")
            summary_df_data = [{'Item Name': itm.get('item_name', 'N/A'), 'Qty': itm.get('requested_qty', 0),
                                'Unit': itm.get('item_unit', 'N/A'), 'Notes': itm.get('item_notes', '')} for itm in summary_items]
            summary_df = pd.DataFrame(summary_df_data)
            st.dataframe(summary_df, hide_index=True, use_container_width=True, column_config={"Qty": st.column_config.NumberColumn(format="%.2f")})
        pdf_dl_col, whatsapp_col = st.columns(2)
        with pdf_dl_col:
            pdf_btn_placeholder = st.empty()
            if st.session_state.get("pdf_bytes_for_download"):
                pdf_btn_placeholder.download_button(label=f"📥 Download PDF ({mrn_to_print})",data=st.session_state.pdf_bytes_for_download,
                                                    file_name=st.session_state.pdf_filename_for_download,mime="application/pdf",
                                                    key=f"dl_new_indent_final_v15_{mrn_to_print.replace('-', '_')}",
                                                    on_click=lambda: st.session_state.update({"pdf_bytes_for_download": None, "pdf_filename_for_download": None}),use_container_width=True )
            else:
                if pdf_btn_placeholder.button(f"📄 Generate PDF ({mrn_to_print})",key=f"print_new_indent_btn_v15_{mrn_to_print.replace('-', '_')}",use_container_width=True):
                    with st.spinner(f"Generating PDF for {mrn_to_print}..."):
                        hd, itms = indent_service.get_indent_details_for_pdf(db_engine, mrn_to_print)
                        if hd and itms is not None:
                            pdf_b = generate_indent_pdf(hd, itms)
                            if pdf_b: st.session_state.pdf_bytes_for_download = pdf_b; st.session_state.pdf_filename_for_download = f"Indent_{mrn_to_print}.pdf"; st.rerun()
                        else: st.error(f"Could not fetch details for PDF: {mrn_to_print}.")
        with whatsapp_col:
            if st.session_state.get("last_submitted_indent_details"):
                header = st.session_state.last_submitted_indent_details['header']
                wa_text = (f"Indent Submitted:\nMRN: {header.get('mrn', 'N/A')}\nDept: {header.get('department', 'N/A')}\n"
                           f"By: {header.get('requested_by', 'N/A')}\nReqd Date: {header.get('date_required', 'N/A')}\n"
                           f"Items: {len(st.session_state.last_submitted_indent_details['items'])}")
                encoded_text = urllib.parse.quote_plus(wa_text)
                st.link_button("✅ Prepare WhatsApp Message", f"https://wa.me/?text={encoded_text}", use_container_width=True, help="Opens WhatsApp.")
        st.divider()
        if st.button("➕ Create Another Indent", key="create_another_indent_btn_v15", use_container_width=True):
            st.session_state.last_created_mrn_for_print = None; st.session_state.last_submitted_indent_details = None
            if "pdf_bytes_for_download" in st.session_state: del st.session_state.pdf_bytes_for_download
            if "pdf_filename_for_download" in st.session_state: del st.session_state.pdf_filename_for_download
            st.session_state.create_indent_rows = [{'id':0,'item_id':None,'requested_qty':1.0,'notes':'','last_ordered':None,'median_qty':None, 'category':None, 'sub_category':None}]
            st.session_state.create_indent_next_id = 1
            st.session_state[CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY] = True; st.rerun()
    else: 
        head_col1, head_col2 = st.columns(2)
        with head_col1:
            dept_widget_key = "create_indent_dept_widget_v15"
            st.selectbox("Requesting Department*", options=[""] + distinct_departments,
                         index=([""] + distinct_departments).index(st.session_state.get(CREATE_INDENT_DEPT_SESS_KEY,"")) if st.session_state.get(CREATE_INDENT_DEPT_SESS_KEY,"") in ([""]+distinct_departments) else 0,
                         format_func=lambda x: "Select Department..." if x=="" else x, key=dept_widget_key,
                         on_change=lambda: st.session_state.update({CREATE_INDENT_DEPT_SESS_KEY:st.session_state[dept_widget_key], 'selected_department_for_create_indent':st.session_state[dept_widget_key] if st.session_state[dept_widget_key] else None}))
            if 'selected_department_for_create_indent' not in st.session_state: st.session_state.selected_department_for_create_indent = st.session_state.get(CREATE_INDENT_DEPT_SESS_KEY) if st.session_state.get(CREATE_INDENT_DEPT_SESS_KEY) else None
            req_by_widget_key = "create_indent_req_by_widget_v15"
            st.session_state[CREATE_INDENT_REQ_BY_SESS_KEY] = st.text_input("Requested By (Your Name/ID)*", value=st.session_state.get(CREATE_INDENT_REQ_BY_SESS_KEY,""), key=req_by_widget_key)
        with head_col2:
            date_req_widget_key = "create_indent_date_req_widget_v15"
            st.session_state[CREATE_INDENT_DATE_REQ_SESS_KEY] = st.date_input("Date Required By*", value=st.session_state.get(CREATE_INDENT_DATE_REQ_SESS_KEY, date.today()+timedelta(days=1)), min_value=date.today(), key=date_req_widget_key)
            st.text_input("Initial Status", value=STATUS_SUBMITTED, disabled=True, key="create_indent_status_disp_v15")
        header_notes_widget_key = "create_indent_header_notes_widget_v15"
        st.session_state[CREATE_INDENT_NOTES_SESS_KEY] = st.text_area("Overall Indent Notes (Optional)", value=st.session_state.get(CREATE_INDENT_NOTES_SESS_KEY,""), key=header_notes_widget_key, placeholder="General notes...")
        st.divider()
        st.subheader("🛍️ Requested Items")
        current_dept_for_suggestions = st.session_state.get('selected_department_for_create_indent')
        if current_dept_for_suggestions:
            suggested_items = item_service.get_suggested_items_for_department(db_engine, current_dept_for_suggestions, top_n=5)
            if suggested_items:
                st.caption("✨ Quick Add (based on recent requests from this department):")
                items_in_current_indent_ids = {row.get('item_id') for row in st.session_state.create_indent_rows if row.get('item_id')}
                valid_suggestions = [sugg for sugg in suggested_items if sugg['item_id'] not in items_in_current_indent_ids]
                if valid_suggestions:
                    sugg_cols = st.columns(min(len(valid_suggestions), 5)) 
                    for i_sugg, sugg_item in enumerate(valid_suggestions):
                        sugg_cols[i_sugg].button(f"+ {sugg_item['item_name']}", key=f"suggest_item_v15_{sugg_item['item_id']}", 
                                            on_click=add_suggested_item_callback, args=(sugg_item['item_id'], sugg_item['item_name'], sugg_item['unit']),
                                            help=f"Add {sugg_item['item_name']} ({sugg_item['unit']})", use_container_width=True)
                elif items_in_current_indent_ids and len(st.session_state.create_indent_rows) > 0 and st.session_state.create_indent_rows[0].get('item_id') is not None : st.caption("Frequent items are already in your list or no other frequent items found.")
                else: st.caption("No frequent items found for this department recently.")
                st.caption("") 
        if st.session_state.selected_department_for_create_indent:
            selected_dept_for_filter = st.session_state.selected_department_for_create_indent
            if not all_active_items_df.empty:
                try:
                    available_items_df = all_active_items_df[all_active_items_df['permitted_departments'].fillna('').astype(str).str.split(',').apply(lambda dl: selected_dept_for_filter.strip().lower() in [d.strip().lower() for d in dl] if isinstance(dl, list) else False)].copy()
                    item_options_dict = {placeholder_option_stock[0]: placeholder_option_stock[1]} 
                    if available_items_df.empty: item_options_dict.update({"-- No items for this department --": None})
                    else: item_options_dict.update({ f"{r['name']} ({r['unit']})": r['item_id'] for _, r in available_items_df.sort_values('name').iterrows()})
                except Exception as e: st.error(f"Error filtering items: {e}"); item_options_dict = {"Error loading items": None}
            else: st.warning("No active items in system."); item_options_dict = {"No items available": None}
        else: st.info("Select a requesting department above to add items."); item_options_dict = {"-- Select Department First --": None}

        h_cols = st.columns([4,2,3,1]); h_cols[0].markdown("**Item**"); h_cols[1].markdown("**Req. Qty**"); h_cols[2].markdown("**Notes**"); h_cols[3].markdown("**Action**"); st.divider()
        
        for i_loop_item_rows, row_state in enumerate(st.session_state.create_indent_rows): # Unique loop var
            row_id = row_state['id']
            item_cols_display = st.columns([4,2,3,1])
            item_selectbox_key_row = f"disp_item_select_v15_{row_id}" # Unique key
            default_item_display_name_row = list(item_options_dict.keys())[0]
            if row_state.get('item_id') is not None: default_item_display_name_row = next((name for name, id_val in item_options_dict.items() if id_val == row_state['item_id']), default_item_display_name_row)
            try: current_item_idx_row = list(item_options_dict.keys()).index(default_item_display_name_row)
            except ValueError: current_item_idx_row = 0
            
            with item_cols_display[0]:
                st.selectbox(f"Item (Row {i_loop_item_rows+1})", options=list(item_options_dict.keys()), index=current_item_idx_row,
                                           key=item_selectbox_key_row, label_visibility="collapsed",
                                           on_change=update_row_item_details_callback, args=(i_loop_item_rows, item_selectbox_key_row, item_options_dict))
                current_item_id_for_row_disp = st.session_state.create_indent_rows[i_loop_item_rows].get('item_id')
                if current_item_id_for_row_disp and current_item_id_for_row_disp != -1:
                    info_parts = []
                    item_cat_info = st.session_state.create_indent_rows[i_loop_item_rows].get('category')
                    if item_cat_info and item_cat_info != "N/A": info_parts.append(f"Cat: {item_cat_info}")
                    item_subcat_info = st.session_state.create_indent_rows[i_loop_item_rows].get('sub_category')
                    if item_subcat_info and item_subcat_info != "N/A": info_parts.append(f"Sub: {item_subcat_info}")
                    last_ord_info_disp = st.session_state.create_indent_rows[i_loop_item_rows].get('last_ordered')
                    if last_ord_info_disp: info_parts.append(f"Last ord: {last_ord_info_disp}")
                    if info_parts: st.caption(" | ".join(info_parts)) # Horizontal display
            
            with item_cols_display[1]:
                qty_key_for_row_disp = f"disp_item_qty_v15_{row_id}" # Unique key
                current_qty_for_row_disp = float(st.session_state.create_indent_rows[i_loop_item_rows].get('requested_qty', 1.0))
                def on_qty_change_callback(idx, key_arg): st.session_state.create_indent_rows[idx]['requested_qty'] = st.session_state[key_arg]
                st.number_input(f"Qty(R{i_loop_item_rows+1})", value=current_qty_for_row_disp, min_value=0.01, step=0.1, format="%.2f", 
                                                  key=qty_key_for_row_disp, label_visibility="collapsed",
                                                  on_change=on_qty_change_callback, args=(i_loop_item_rows, qty_key_for_row_disp))
                median_qty_row_disp = st.session_state.create_indent_rows[i_loop_item_rows].get('median_qty'); actual_qty_row_disp = st.session_state.create_indent_rows[i_loop_item_rows]['requested_qty']
                if median_qty_row_disp and median_qty_row_disp > 0 and actual_qty_row_disp > 0:
                    if actual_qty_row_disp > median_qty_row_disp*3: st.warning(f"High! (Avg:~{median_qty_row_disp:.1f})",icon="❗")
                    elif actual_qty_row_disp < median_qty_row_disp/3: st.info(f"Low (Avg:~{median_qty_row_disp:.1f})",icon="ℹ️")

            with item_cols_display[2]:
                notes_key_for_row_disp = f"disp_item_notes_v15_{row_id}" # Unique key
                def on_notes_change_callback(idx, key_arg): st.session_state.create_indent_rows[idx]['notes'] = st.session_state[key_arg]
                st.text_input(f"Notes(R{i_loop_item_rows+1})", value=st.session_state.create_indent_rows[i_loop_item_rows].get('notes',''), 
                                                key=notes_key_for_row_disp, label_visibility="collapsed", placeholder="Optional",
                                                on_change=on_notes_change_callback, args=(i_loop_item_rows, notes_key_for_row_disp))
            with item_cols_display[3]:
                if len(st.session_state.create_indent_rows)>1: item_cols_display[3].button("➖",key=f"disp_remove_row_v15_{row_id}",on_click=remove_indent_row_callback,args=(row_id,),help="Remove line") # Unique key
                else: item_cols_display[3].write("") 
            st.caption("") 

        add_lines_col_label, add_lines_col_input, add_lines_col_button = st.columns([1.2, 1, 1.8]) 
        with add_lines_col_label: st.markdown("<div style='padding-top: 28px;'>Add more lines:</div>", unsafe_allow_html=True) 
        with add_lines_col_input: st.number_input("Number of lines",value=st.session_state.num_lines_to_add_indent_widget,min_value=1,max_value=10,step=1,key="num_lines_to_add_widget_v8", label_visibility="collapsed") # Unique key
        with add_lines_col_button: st.button("➕ Add Lines",on_click=add_multiple_indent_lines_callback,key="add_multi_lines_btn_v15", use_container_width=True) # Unique key
        st.divider()
        
        with st.form("create_indent_final_submit_form_v15", clear_on_submit=False): # Unique key
            submitted_final_button = st.form_submit_button("📝 Submit Indent Request", type="primary", use_container_width=True)
            if submitted_final_button:
                # ... (Validation and Submission Logic - same as your last working version)
                header_data_submit = {"department": st.session_state.get(CREATE_INDENT_DEPT_SESS_KEY),"requested_by": st.session_state.get(CREATE_INDENT_REQ_BY_SESS_KEY, "").strip(),
                                      "date_required": st.session_state.get(CREATE_INDENT_DATE_REQ_SESS_KEY),"notes": st.session_state.get(CREATE_INDENT_NOTES_SESS_KEY, "").strip() or None,
                                      "status": STATUS_SUBMITTED}
                valid = True; items_to_submit_list = []; seen_item_ids_in_form = set()
                if not header_data_submit["department"]: st.error("Department required."); valid = False
                if not header_data_submit["requested_by"]: st.error("Requested By required."); valid = False
                for i_r, r_data in enumerate(st.session_state.create_indent_rows):
                    item_id_v = r_data.get('item_id'); qty_v = r_data.get('requested_qty'); notes_v = r_data.get('notes')
                    if item_id_v is None or item_id_v == -1 : st.error(f"Row {i_r+1}: Select item."); valid=False; continue
                    if item_id_v in seen_item_ids_in_form: 
                        item_name_val = "Item"; temp_item_options_dict_submit = item_options_dict if 'item_options_dict' in locals() else {}
                        for name_lookup, id_lookup in temp_item_options_dict_submit.items():
                            if id_lookup == item_id_v: item_name_val = name_lookup; break
                        st.error(f"Row {i_r+1}: Item '{item_name_val}' duplicated."); valid=False
                    if not (isinstance(qty_v, (float, int)) and qty_v > 0) : st.error(f"Row {i_r+1}: Qty > 0. Got: {qty_v}"); valid=False
                    if valid and item_id_v not in seen_item_ids_in_form: items_to_submit_list.append({"item_id":item_id_v, "requested_qty":float(qty_v), "notes":(notes_v or "").strip() or None})
                    if item_id_v != -1: seen_item_ids_in_form.add(item_id_v)
                if not items_to_submit_list and valid: st.error("Indent needs items."); valid=False
                if valid:
                    new_mrn = indent_service.generate_mrn(db_engine)
                    if new_mrn:
                        header_data_submit["mrn"] = new_mrn
                        success, message = indent_service.create_indent(db_engine, header_data_submit, items_to_submit_list)
                        if success:
                            st.session_state.last_created_mrn_for_print = new_mrn
                            hd_summary, itms_summary = indent_service.get_indent_details_for_pdf(db_engine, new_mrn)
                            st.session_state.last_submitted_indent_details = {"header": hd_summary, "items": itms_summary} if hd_summary and itms_summary is not None else None
                            st.session_state.create_indent_rows = [{'id': 0, 'item_id': None, 'requested_qty': 1.0, 'notes': '', 'last_ordered': None, 'median_qty': None, 'category':None, 'sub_category':None}]
                            st.session_state.create_indent_next_id = 1
                            st.session_state[CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY] = True
                            fetch_indent_page_data.clear(); indent_service.get_indents.clear()
                            item_service.get_item_order_history_details.clear(); item_service.get_suggested_items_for_department.clear()
                            st.rerun() 
                        else: st.error(f"Failed to create indent: {message}")
                    else: st.error("Failed to generate MRN.")
                else: st.warning("Fix errors before submitting.")

# ===========================
# VIEW INDENTS SECTION 
# ===========================
elif st.session_state.active_indent_section == "view":
    # ... (Your existing "View Indents" code with unique widget keys like _v15) ...
    st.subheader("📄 View Existing Material Indents")
    view_filter_cols = st.columns([1, 1, 1, 2]) 
    with view_filter_cols[0]: mrn_filter = st.text_input("Search by MRN:", key="view_indent_mrn_filter_v15", placeholder="e.g., MRN-...")
    with view_filter_cols[1]:
        dept_options_view = ["All Departments"] + distinct_departments
        dept_filter_val = st.selectbox("Filter by Department:", options=dept_options_view, key="view_indent_dept_filter_v15")
    with view_filter_cols[2]:
        status_options_view = ["All Statuses"] + ALL_INDENT_STATUSES
        status_filter_val = st.selectbox("Filter by Status:", options=status_options_view, key="view_indent_status_filter_v15")
    with view_filter_cols[3]:
        date_col1, date_col2 = st.columns(2)
        with date_col1: date_start_filter_val = st.date_input("Submitted From:", value=None, key="view_indent_date_start_v15")
        with date_col2: date_end_filter_val = st.date_input("Submitted To:", value=None, key="view_indent_date_end_v15")
    date_start_str_arg = date_start_filter_val.strftime('%Y-%m-%d') if date_start_filter_val else None
    date_end_str_arg = date_end_filter_val.strftime('%Y-%m-%d') if date_end_filter_val else None
    dept_arg = dept_filter_val if dept_filter_val != "All Departments" else None
    status_arg = status_filter_val if status_filter_val != "All Statuses" else None
    mrn_arg = mrn_filter.strip() if mrn_filter else None
    indents_df = indent_service.get_indents(db_engine, mrn_filter=mrn_arg, dept_filter=dept_arg, status_filter=status_arg, date_start_str=date_start_str_arg, date_end_str=date_end_str_arg)
    st.divider()
    if indents_df.empty: st.info("No indents found.")
    else:
        st.success(f"Found {len(indents_df)} indent(s).")
        display_df = indents_df.copy()
        if 'date_required' in display_df.columns: display_df['date_required'] = pd.to_datetime(display_df['date_required'], errors='coerce').dt.strftime('%Y-%m-%d')
        if 'date_submitted' in display_df.columns: display_df['date_submitted'] = pd.to_datetime(display_df['date_submitted'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
        status_emoji_map = {STATUS_SUBMITTED: "📬 Submitted", STATUS_PROCESSING: "⚙️ Processing", STATUS_COMPLETED: "✅ Completed", STATUS_CANCELLED: "❌ Cancelled"}
        if 'status' in display_df.columns: display_df['status_display'] = display_df['status'].map(status_emoji_map).fillna(display_df['status'])
        st.dataframe(display_df, use_container_width=True, hide_index=True,
                     column_order=["mrn", "date_submitted", "department", "requested_by", "date_required", "status_display", "item_count", "indent_notes"],
                     column_config={"indent_id": None, "status": None, "mrn": st.column_config.TextColumn("MRN"), "date_submitted": st.column_config.TextColumn("Submitted On"),
                                    "department": "Department", "requested_by": "Requestor", "date_required": st.column_config.TextColumn("Required By"),
                                    "status_display": st.column_config.TextColumn("Status"), "item_count": st.column_config.NumberColumn("No. of Items", format="%d"),
                                    "indent_notes": st.column_config.TextColumn("Indent Notes")})
        st.divider(); st.subheader("📄 Download Indent as PDF")
        st.caption("Select an MRN from the list above to generate its PDF.")
        if not indents_df.empty:
            available_mrns_for_pdf = ["-- Select MRN for PDF --"] + indents_df['mrn'].tolist()
            selected_mrn_for_pdf = st.selectbox("Choose MRN:", options=available_mrns_for_pdf, key="pdf_mrn_select_v15") 
            if selected_mrn_for_pdf != "-- Select MRN for PDF --":
                if st.button("⚙️ Generate PDF", key="generate_pdf_indent_btn_v15"): 
                    with st.spinner(f"Generating PDF for {selected_mrn_for_pdf}..."):
                        header_details, items_details = indent_service.get_indent_details_for_pdf(db_engine, selected_mrn_for_pdf)
                        if header_details and items_details is not None:
                            pdf_bytes = generate_indent_pdf(header_details, items_details)
                            if pdf_bytes:
                                st.session_state.pdf_bytes_for_download = pdf_bytes
                                st.session_state.pdf_filename_for_download = f"Indent_{selected_mrn_for_pdf}.pdf"
                                st.rerun() 
                        else: st.error(f"Could not fetch details for PDF: MRN {selected_mrn_for_pdf}.")
            if "pdf_bytes_for_download" in st.session_state and st.session_state.pdf_bytes_for_download and st.session_state.get("pdf_filename_for_download","").endswith(f"{selected_mrn_for_pdf}.pdf"):
                st.download_button(label=f"📥 Download PDF for {selected_mrn_for_pdf}", data=st.session_state.pdf_bytes_for_download,
                                   file_name=st.session_state.pdf_filename_for_download, mime="application/pdf",
                                   key=f"final_dl_btn_v14_{selected_mrn_for_pdf.replace('-','_')}",
                                   on_click=lambda: st.session_state.update({"pdf_bytes_for_download":None, "pdf_filename_for_download":None}))

# ===========================
# PROCESS INDENT SECTION (Placeholder)
# ===========================
elif st.session_state.active_indent_section == "process":
    st.subheader("⚙️ Process Material Indents")
    st.info("This section is under development.")