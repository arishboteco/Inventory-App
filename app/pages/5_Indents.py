# app/pages/5_Indents.py
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple, Set
import time 
import urllib.parse
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import traceback 

try:
    from app.db.database_utils import connect_db, fetch_data
    from app.services import item_service 
    from app.services import indent_service
    from app.core.constants import (
        ALL_INDENT_STATUSES, STATUS_SUBMITTED, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_CANCELLED,
        ITEM_STATUS_PENDING_ISSUE, ITEM_STATUS_FULLY_ISSUED, ITEM_STATUS_PARTIALLY_ISSUED,
        ITEM_STATUS_CANCELLED_ITEM 
    )
except ImportError as e:
    st.error(f"Import error in 5_Indents.py: {e}. Please ensure all service files and utility modules are correctly placed and named.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during an import in 5_Indents.py: {e}")
    st.stop()

# --- Session State Initialization ---
placeholder_option_stock = ("-- Select Item --", -1) # item_id = -1 to distinguish from None or valid ID
placeholder_option_indent_process = ("-- Select Indent (MRN) to Process --", None, None) # (display_name, indent_id, mrn)

# Create Indent Section States
if 'create_indent_rows' not in st.session_state:
    st.session_state.create_indent_rows = [{'id': 0, 'item_id': None, 'requested_qty': 1.0, 'notes': '',
                                            'last_ordered': None, 'median_qty': None,
                                            'category': None, 'sub_category': None,
                                            'current_stock': None, 'unit': None}] 
    st.session_state.create_indent_next_id = 1
if 'selected_department_for_create_indent' not in st.session_state: # Stores the string department name
     st.session_state.selected_department_for_create_indent = None
if "num_lines_to_add_value" not in st.session_state: # For the number input controlling how many lines to add
    st.session_state.num_lines_to_add_value = 1
if 'last_created_mrn_for_print' not in st.session_state: st.session_state.last_created_mrn_for_print = None
if 'last_submitted_indent_details' not in st.session_state: st.session_state.last_submitted_indent_details = None
if 'pdf_bytes_for_download' not in st.session_state: st.session_state.pdf_bytes_for_download = None
if 'pdf_filename_for_download' not in st.session_state: st.session_state.pdf_filename_for_download = None

# Process Indent Section States
if "process_indent_selected_tuple" not in st.session_state: # Stores the (display_name, indent_id, mrn) tuple
    st.session_state.process_indent_selected_tuple = placeholder_option_indent_process
if "process_indent_items_df" not in st.session_state: # Stores DataFrame of items for the selected indent
    st.session_state.process_indent_items_df = pd.DataFrame()
if "process_indent_issue_quantities_defaults" not in st.session_state: # Stores default values for "Issue Now" fields
    st.session_state.process_indent_issue_quantities_defaults = {}
if "process_indent_user_id" not in st.session_state: # Stores user ID for processing
    st.session_state.process_indent_user_id = ""


INDENT_SECTIONS = {"create": "➕ Create Indent", "view": "📄 View Indents", "process": "⚙️ Process Indent"}
INDENT_SECTION_KEYS = list(INDENT_SECTIONS.keys())
INDENT_SECTION_DISPLAY_NAMES = list(INDENT_SECTIONS.values())
if 'active_indent_section' not in st.session_state:
    st.session_state.active_indent_section = INDENT_SECTION_KEYS[0] # Default to "create"

# Standardized Session State Keys for Create Indent Header (as per previous discussions)
CREATE_INDENT_DEPT_SESS_KEY = "ss_indent_create_dept_v18" # Using 'ss' prefix
CREATE_INDENT_REQ_BY_SESS_KEY = "ss_indent_create_req_by_v18"
CREATE_INDENT_DATE_REQ_SESS_KEY = "ss_indent_create_date_req_v18"
CREATE_INDENT_NOTES_SESS_KEY = "ss_indent_create_header_notes_v18"
CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY = "ss_indent_create_header_reset_signal_v18"

# Initialize these standardized keys
for key, default_val in [
    (CREATE_INDENT_DEPT_SESS_KEY, ""), # Empty string for selectbox default
    (CREATE_INDENT_REQ_BY_SESS_KEY, ""),
    (CREATE_INDENT_DATE_REQ_SESS_KEY, date.today() + timedelta(days=1)), # Default to tomorrow
    (CREATE_INDENT_NOTES_SESS_KEY, ""),
    (CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY, False) # Signal to reset header fields
]:
    if key not in st.session_state:
        st.session_state[key] = default_val

st.title("📝 Material Indents Management")
st.write("Create new material requests (indents), view their status, process, and download details.")
st.divider()

db_engine = connect_db()
if not db_engine: 
    st.error("Database connection failed. Indent management functionality is unavailable.")
    st.stop()

@st.cache_data(ttl=300, show_spinner="Loading item & department data...")
def fetch_indent_page_data(_engine):
    """Fetches active items and distinct department names for indent creation."""
    if _engine is None: 
        # Return empty structures with expected columns to prevent downstream errors
        return pd.DataFrame(columns=['item_id', 'name', 'unit', 'category', 'sub_category', 'permitted_departments', 'current_stock']), []
    
    items_df = item_service.get_all_items_with_stock(_engine, include_inactive=False) # Only active items for new indents
    required_cols = ['item_id', 'name', 'unit', 'category', 'sub_category', 'permitted_departments', 'current_stock']
    
    # Ensure all required columns are present
    if not all(col in items_df.columns for col in required_cols):
        missing = [col for col in required_cols if col not in items_df.columns]
        # Log error to console and return empty structure
        print(f"ERROR [5_Indents.fetch_indent_page_data]: Required columns missing from items_df: {', '.join(missing)}.")
        return pd.DataFrame(columns=required_cols), []
        
    return items_df[required_cols].copy(), item_service.get_distinct_departments_from_items(_engine)

all_active_items_df, distinct_departments = fetch_indent_page_data(db_engine)

def generate_indent_pdf(indent_header: Dict, indent_items: List[Dict]) -> Optional[bytes]:
    """Generates a PDF document for the given indent details."""
    if not indent_header or indent_items is None: # indent_items can be an empty list for an indent with no items
         print("ERROR [5_Indents.generate_indent_pdf]: Missing indent header or items data for PDF generation.")
         st.toast("Cannot generate PDF: Missing critical indent data.", icon="🚨")
         return None
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=10) 
        pdf.set_margins(left=8, top=8, right=8)    
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 13) 
        pdf.cell(0, 6, "Material Indent Request", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT) 

        pdf.set_font("Helvetica", "I", 7) 
        generated_time_str = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        pdf.cell(0, 4, generated_time_str, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT) 
        pdf.ln(2) 

        pdf.set_font("Helvetica", "", 8.5) 
        header_details_list = [
            ("MRN:", indent_header.get('mrn', 'N/A')),
            ("Department:", indent_header.get('department', 'N/A')),
            ("Requested By:", indent_header.get('requested_by', 'N/A')),
            ("Date Submitted:", indent_header.get('date_submitted', 'N/A')), # Expecting formatted date string
            ("Date Required:", indent_header.get('date_required', 'N/A')),   # Expecting formatted date string
            ("Status:", indent_header.get('status', 'N/A')),
        ]
        
        max_label_w = 0
        for label, _ in header_details_list:
            max_label_w = max(max_label_w, pdf.get_string_width(label) + 1)

        gap_between_pairs = 3 
        available_width_for_values = (pdf.w - pdf.l_margin - pdf.r_margin) - (max_label_w * 2) - gap_between_pairs
        col_width_val = available_width_for_values / 2
        
        line_height_header_details = 4 

        for i in range(0, len(header_details_list), 2):
            current_y_pos = pdf.get_y()
            pdf.set_font("Helvetica", "", 8.5)
            pdf.cell(max_label_w, line_height_header_details, header_details_list[i][0], align='L')
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.cell(col_width_val, line_height_header_details, str(header_details_list[i][1]), align='L')

            if i + 1 < len(header_details_list):
                pdf.set_xy(pdf.l_margin + max_label_w + col_width_val + gap_between_pairs, current_y_pos)
                pdf.set_font("Helvetica", "", 8.5)
                pdf.cell(max_label_w, line_height_header_details, header_details_list[i+1][0], align='L')
                pdf.set_font("Helvetica", "B", 8.5)
                pdf.cell(col_width_val, line_height_header_details, str(header_details_list[i+1][1]), align='L')
            pdf.ln(line_height_header_details)

        if indent_header.get('notes'):
            pdf.ln(0.5) 
            pdf.set_font("Helvetica", "I", 7.5) 
            pdf.multi_cell(0, 3, f"Indent Notes: {indent_header['notes']}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT) 

        pdf.ln(2) 

        pdf.set_font("Helvetica", "B", 7.5) 
        col_widths = {'sno': 8, 'name': 72, 'unit': 18, 'qty': 20, 'notes': 70} 
        
        pdf.set_fill_color(220, 220, 220) # Light grey for table header
        table_header_height = 4.5
        for key_pdf, header_text_pdf in [('sno',"SNo"), ('name',"Item Name"), ('unit',"UoM"), ('qty',"Req Qty"), ('notes',"Item Notes")]:
            align_pdf = 'C' if key_pdf in ['sno', 'unit'] else ('R' if key_pdf == 'qty' else 'L')
            pdf.cell(col_widths[key_pdf], table_header_height, header_text_pdf, border=1, align=align_pdf, fill=True,
                     new_x=XPos.RIGHT if key_pdf != 'notes' else XPos.LMARGIN,
                     new_y=YPos.NEXT if key_pdf == 'notes' else YPos.TOP)

        pdf.set_font("Helvetica", "", 7.5) 
        base_line_height_items = 3.5 

        if not indent_items: # If items list is empty
            pdf.cell(sum(col_widths.values()), 4, "No items found for this indent.", border=1, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            item_serial_number_pdf = 0
            current_category_pdf = None # For grouping
            current_sub_category_pdf = None # For grouping

            for item_pdf in indent_items:
                item_cat_pdf = item_pdf.get('item_category', 'Uncategorized')
                item_subcat_pdf = item_pdf.get('item_sub_category', 'General')

                # Category Header
                if item_cat_pdf != current_category_pdf:
                    current_category_pdf = item_cat_pdf
                    current_sub_category_pdf = None # Reset sub-category when category changes
                    pdf.set_font("Helvetica", "B", 8) 
                    pdf.set_fill_color(230,230,250) # Light purple for category header
                    pdf.cell(sum(col_widths.values()), 5, f"Category: {current_category_pdf}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, align='L')

                # Sub-Category Header (indented)
                if item_subcat_pdf != current_sub_category_pdf:
                    current_sub_category_pdf = item_subcat_pdf
                    pdf.set_font("Helvetica", "BI", 7.5) # Bold Italic for sub-category
                    pdf.set_x(pdf.l_margin + 3) # Indent sub-category header
                    pdf.cell(sum(col_widths.values()) - 3, 4, f"Sub-Category: {current_sub_category_pdf}", border="LRB", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=False, align='L')
                
                pdf.set_font("Helvetica", "", 7.5) # Reset font for item rows
                item_serial_number_pdf += 1
                
                sno_str = str(item_serial_number_pdf)
                name_str = item_pdf.get('item_name', 'N/A') or 'N/A' # Ensure not None
                unit_str = str(item_pdf.get('item_unit', 'N/A'))
                try:
                    qty_str = f"{float(item_pdf.get('requested_qty', 0)):.2f}"
                except (ValueError, TypeError):
                    qty_str = "Invalid"
                notes_str = item_pdf.get('item_notes', '') or '' # Ensure not None

                # Multi-cell logic for name and notes to handle wrapping
                max_lines = 1 # Default to 1 line
                temp_x_for_calc = pdf.get_x() # Store current x to reset after dry_run for multi_cell
                
                # Calculate lines for name
                if col_widths['name'] > 0: # Check to prevent error if width is zero
                    name_content_lines = pdf.multi_cell(w=col_widths['name'], h=base_line_height_items, text=name_str, border=0, dry_run=True, output='LINES', align='L')
                    max_lines = max(max_lines, len(name_content_lines))
                pdf.set_x(temp_x_for_calc) # Reset x position

                # Calculate lines for notes
                if col_widths['notes'] > 0:
                   notes_content_lines = pdf.multi_cell(w=col_widths['notes'], h=base_line_height_items, text=notes_str, border=0, dry_run=True, output='LINES', align='L')
                   max_lines = max(max_lines, len(notes_content_lines))
                pdf.set_x(temp_x_for_calc) # Reset x position

                effective_row_height = max_lines * base_line_height_items + (max_lines -1) * 0.5 # Add small gap for multi-lines

                row_start_y = pdf.get_y()
                current_x_pos = pdf.l_margin

                # SNo
                pdf.set_xy(current_x_pos, row_start_y)
                pdf.multi_cell(col_widths['sno'], effective_row_height, sno_str, border='LRB', align='C', max_line_height=base_line_height_items)
                current_x_pos += col_widths['sno']
                
                # Item Name (uses base_line_height_items for each line within the multi_cell)
                pdf.set_xy(current_x_pos, row_start_y)
                pdf.multi_cell(col_widths['name'], base_line_height_items, name_str, border='RB', align='L', max_line_height=base_line_height_items)
                current_x_pos += col_widths['name']
                
                # UoM
                pdf.set_xy(current_x_pos, row_start_y)
                pdf.multi_cell(col_widths['unit'], effective_row_height, unit_str, border='RB', align='C', max_line_height=base_line_height_items)
                current_x_pos += col_widths['unit']
                
                # Req Qty
                pdf.set_xy(current_x_pos, row_start_y)
                pdf.multi_cell(col_widths['qty'], effective_row_height, qty_str, border='RB', align='R', max_line_height=base_line_height_items)
                current_x_pos += col_widths['qty']
                
                # Item Notes
                pdf.set_xy(current_x_pos, row_start_y)
                pdf.multi_cell(col_widths['notes'], base_line_height_items, notes_str, border='RB', align='L', max_line_height=base_line_height_items)
                
                # Set Y for next row, ensuring it's below the tallest cell in current row
                pdf.set_y(row_start_y + effective_row_height)

        return bytes(pdf.output())

    except Exception as e_pdf:
        print(f"ERROR [5_Indents.generate_indent_pdf]: Failed to generate PDF: {e_pdf}\n{traceback.format_exc()}")
        st.toast(f"Failed to generate PDF: {e_pdf}", icon="🚨")
        return None

# --- Callbacks for Create Indent ---
def add_single_indent_row_logic():
    """Adds a single new blank row to the indent creation form."""
    new_id = st.session_state.create_indent_next_id
    st.session_state.create_indent_rows.append({
        'id': new_id, 'item_id': None, 'requested_qty': 1.0, 'notes': '',
        'last_ordered': None, 'median_qty': None,
        'category': None, 'sub_category': None,
        'current_stock': None, 'unit': None # Store unit for display consistency
    })
    st.session_state.create_indent_next_id += 1

def add_multiple_indent_lines_callback():
    """Callback to add multiple indent lines based on user input."""
    num_lines = st.session_state.get("create_indent_num_lines_input_v19", 1) # Unique key
    try:
        num_to_add = int(num_lines)
        if num_to_add < 1: num_to_add = 1
        if num_to_add > 10: num_to_add = 10 # Limit to prevent excessive rows
    except (ValueError, TypeError):
        num_to_add = 1
        
    for _ in range(num_to_add): 
        add_single_indent_row_logic()
    st.session_state.num_lines_to_add_value = 1 # Reset the input field's driving value

def remove_indent_row_callback(row_id_to_remove: int):
    """Removes a specific row from the indent creation form by its unique ID."""
    idx_to_remove = next((i for i, r in enumerate(st.session_state.create_indent_rows) if r['id'] == row_id_to_remove), -1)
    if idx_to_remove != -1:
        if len(st.session_state.create_indent_rows) > 1: 
            st.session_state.create_indent_rows.pop(idx_to_remove)
        else: 
            st.toast("Cannot remove the last item row. Add another before removing.", icon="⚠️")

def add_suggested_item_callback(item_id_to_add: int, item_name_to_add: str, unit_to_add: str):
    """Adds a suggested item to the indent form, filling an empty row or adding a new one."""
    if any(row.get('item_id') == item_id_to_add for row in st.session_state.create_indent_rows):
        st.toast(f"'{item_name_to_add}' is already in the indent list.", icon="ℹ️")
        return

    empty_row_idx = next((i for i,r in enumerate(st.session_state.create_indent_rows) if r.get('item_id') is None or r.get('item_id') == -1), -1)
    current_department = st.session_state.get(CREATE_INDENT_DEPT_SESS_KEY) # Use standardized key
    history = item_service.get_item_order_history_details(db_engine, item_id_to_add, current_department)

    item_master_detail_row_df = all_active_items_df[all_active_items_df['item_id'] == item_id_to_add]
    category_val, sub_category_val, current_stock_val = "N/A", "N/A", None
    unit_val_from_master = unit_to_add # Default to unit passed

    if not item_master_detail_row_df.empty:
        item_master_row = item_master_detail_row_df.iloc[0]
        category_val = item_master_row.get('category', "N/A")
        sub_category_val = item_master_row.get('sub_category', "N/A")
        current_stock_val = item_master_row.get('current_stock')
        unit_val_from_master = item_master_row.get('unit', unit_to_add) # Prefer master unit

    new_row_data = {'item_id': item_id_to_add, 'requested_qty': 1.0, 'notes': '',
                    'last_ordered': history.get('last_ordered_date'),
                    'median_qty': history.get('median_quantity'),
                    'category': category_val, 'sub_category': sub_category_val,
                    'current_stock': current_stock_val, 'unit': unit_val_from_master}

    if history.get('median_quantity') and history.get('median_quantity') > 0:
        new_row_data['requested_qty'] = float(history.get('median_quantity'))

    if empty_row_idx != -1: # Fill the first empty row found
        st.session_state.create_indent_rows[empty_row_idx].update(new_row_data)
        st.toast(f"Added '{item_name_to_add}' to an existing empty row.", icon="👍")
    else: # Add as a new row if no empty rows
        new_id = st.session_state.create_indent_next_id
        st.session_state.create_indent_rows.append({'id': new_id, **new_row_data})
        st.session_state.create_indent_next_id += 1
        st.toast(f"Added '{item_name_to_add}' as a new line.", icon="➕")

def update_row_item_details_callback(row_index: int, item_selectbox_key_arg: str, item_options_dict_arg: Dict):
    """Callback when an item is selected in a row's selectbox. Updates row details."""
    selected_display_name = st.session_state[item_selectbox_key_arg]
    item_id_val = item_options_dict_arg.get(selected_display_name, -1) # Default to placeholder ID if not found
    
    # Initialize details to clear out old ones if placeholder selected
    category_val, sub_category_val, current_stock_val, unit_val = None, None, None, None
    last_ordered_val, median_qty_val = None, None
    requested_qty_val = 1.0 # Default requested quantity

    if item_id_val is not None and item_id_val != -1: # If a valid item is selected
        item_master_row_df = all_active_items_df[all_active_items_df['item_id'] == item_id_val]
        if not item_master_row_df.empty:
            item_master_row = item_master_row_df.iloc[0]
            category_val = item_master_row.get('category')
            sub_category_val = item_master_row.get('sub_category')
            current_stock_val = item_master_row.get('current_stock')
            unit_val = item_master_row.get('unit')

        dept_for_history = st.session_state.get(CREATE_INDENT_DEPT_SESS_KEY)
        history = item_service.get_item_order_history_details(db_engine, item_id_val, dept_for_history)
        last_ordered_val = history.get('last_ordered_date')
        median_qty_val = history.get('median_quantity')
        if median_qty_val and median_qty_val > 0:
            requested_qty_val = float(median_qty_val) # Default to median if available

    # Update the specific row in session state
    st.session_state.create_indent_rows[row_index].update({
        'item_id': item_id_val if item_id_val != -1 else None, # Store None if placeholder
        'category': category_val, 'sub_category': sub_category_val,
        'current_stock': current_stock_val, 'unit': unit_val,
        'last_ordered': last_ordered_val, 'median_qty': median_qty_val,
        'requested_qty': requested_qty_val # Update requested_qty based on median or default
    })

# --- Callbacks for Page Navigation / Section Change ---
def set_active_indent_section_callback():
    """Sets the active indent section and resets states for other sections."""
    selected_display_name = st.session_state.indent_section_radio_key_v19 # Unique key
    new_active_section = INDENT_SECTION_KEYS[0] # Default
    for key, display_name in INDENT_SECTIONS.items():
        if display_name == selected_display_name:
            new_active_section = key
            break
    st.session_state.active_indent_section = new_active_section
    
    # Reset states for sections not being activated
    if new_active_section != "process":
        st.session_state.process_indent_selected_tuple = placeholder_option_indent_process
        st.session_state.process_indent_items_df = pd.DataFrame()
        st.session_state.process_indent_issue_quantities_defaults = {}
    
    if new_active_section != "create":
        st.session_state.last_created_mrn_for_print = None
        st.session_state.last_submitted_indent_details = None
        if "pdf_bytes_for_download" in st.session_state: del st.session_state.pdf_bytes_for_download
        if "pdf_filename_for_download" in st.session_state: del st.session_state.pdf_filename_for_download
    # else: # If switching to create, ensure form is reset if coming from another section
    #     st.session_state[CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY] = True


def on_process_indent_select_change():
    """Callback when a new indent is selected for processing. Resets item details."""
    # This is called when the selectbox for "Select Indent (MRN)" changes.
    # We need to fetch new items for the newly selected indent.
    st.session_state.process_indent_items_df = pd.DataFrame() # Clear old items
    st.session_state.process_indent_issue_quantities_defaults = {} # Clear old default quantities

# --- Main Page UI ---
st.radio(
    "Indent Actions:", 
    options=INDENT_SECTION_DISPLAY_NAMES,
    index=INDENT_SECTION_KEYS.index(st.session_state.active_indent_section),
    key="indent_section_radio_key_v19", # Unique key
    on_change=set_active_indent_section_callback, 
    horizontal=True
)
st.divider()

# ===========================
# CREATE INDENT SECTION
# ===========================
if st.session_state.active_indent_section == "create":
    st.subheader(INDENT_SECTIONS["create"])
    
    # Handle reset signal for header fields
    if st.session_state.get(CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY, False):
        st.session_state[CREATE_INDENT_DEPT_SESS_KEY] = ""
        st.session_state[CREATE_INDENT_REQ_BY_SESS_KEY] = ""
        st.session_state[CREATE_INDENT_DATE_REQ_SESS_KEY] = date.today() + timedelta(days=1)
        st.session_state[CREATE_INDENT_NOTES_SESS_KEY] = ""
        st.session_state.selected_department_for_create_indent = None # Also reset this
        st.session_state[CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY] = False # Consume the signal

    # Display success message and download options if an indent was just created
    if st.session_state.get("last_created_mrn_for_print"):
        mrn_to_print = st.session_state.last_created_mrn_for_print
        st.success(f"Indent **{mrn_to_print}** was created successfully!")
        
        if st.session_state.get("last_submitted_indent_details"):
            summary_items = st.session_state.last_submitted_indent_details.get('items', [])
            if summary_items: # Only show if items exist
                st.write("Submitted Items:")
                summary_df_data = [{'Item Name': itm.get('item_name', 'N/A'), 
                                    'Qty': itm.get('requested_qty', 0),
                                    'Unit': itm.get('item_unit', 'N/A'), 
                                    'Notes': itm.get('item_notes', '')} for itm in summary_items]
                summary_df = pd.DataFrame(summary_df_data)
                st.dataframe(summary_df, hide_index=True, use_container_width=True, 
                               column_config={"Qty": st.column_config.NumberColumn(format="%.2f")})

        pdf_dl_col, whatsapp_col = st.columns(2)
        with pdf_dl_col:
            pdf_btn_placeholder = st.empty() # For dynamic button update
            if st.session_state.get("pdf_bytes_for_download") and st.session_state.get("pdf_filename_for_download","").endswith(f"{mrn_to_print}.pdf"):
                pdf_btn_placeholder.download_button(
                    label=f"📥 Download PDF ({mrn_to_print})",
                    data=st.session_state.pdf_bytes_for_download,
                    file_name=st.session_state.pdf_filename_for_download,
                    mime="application/pdf",
                    key=f"dl_new_indent_final_v19_{mrn_to_print.replace('-', '_')}",
                    on_click=lambda: st.session_state.update({"pdf_bytes_for_download": None, "pdf_filename_for_download": None}), # Clear after click
                    use_container_width=True
                )
            else: # Show generate button if PDF not ready or for different MRN
                if pdf_btn_placeholder.button(f"📄 Generate PDF ({mrn_to_print})",key=f"print_new_indent_btn_v19_{mrn_to_print.replace('-', '_')}",use_container_width=True):
                    with st.spinner(f"Generating PDF for {mrn_to_print}..."):
                        hd, itms = indent_service.get_indent_details_for_pdf(db_engine, mrn_to_print)
                        if hd and itms is not None: # itms can be empty list
                            pdf_b = generate_indent_pdf(hd, itms)
                            if pdf_b: 
                                st.session_state.pdf_bytes_for_download = pdf_b
                                st.session_state.pdf_filename_for_download = f"Indent_{mrn_to_print}.pdf"
                                st.rerun() # Rerun to show download button
                        else: 
                            st.error(f"Could not fetch details to generate PDF for MRN {mrn_to_print}.")
        with whatsapp_col:
            if st.session_state.get("last_submitted_indent_details"):
                header = st.session_state.last_submitted_indent_details.get('header', {})
                items_count = len(st.session_state.last_submitted_indent_details.get('items', []))
                wa_text = (f"Indent Submitted:\n"
                           f"MRN: {header.get('mrn', 'N/A')}\n"
                           f"Dept: {header.get('department', 'N/A')}\n"
                           f"By: {header.get('requested_by', 'N/A')}\n"
                           f"Reqd Date: {header.get('date_required', 'N/A')}\n"
                           f"No. of Items: {items_count}")
                encoded_text = urllib.parse.quote_plus(wa_text)
                st.link_button("✅ Prepare WhatsApp Message", f"https://wa.me/?text={encoded_text}", use_container_width=True, help="Opens WhatsApp with a pre-filled message.")
        
        st.divider()
        if st.button("➕ Create Another Indent", key="create_another_indent_btn_v19", use_container_width=True, type="primary"):
            # Reset all creation-related states for a fresh form
            st.session_state.last_created_mrn_for_print = None
            st.session_state.last_submitted_indent_details = None
            if "pdf_bytes_for_download" in st.session_state: del st.session_state.pdf_bytes_for_download
            if "pdf_filename_for_download" in st.session_state: del st.session_state.pdf_filename_for_download
            st.session_state.create_indent_rows = [{'id': 0, 'item_id': None, 'requested_qty': 1.0, 'notes': '',
                                                    'last_ordered': None, 'median_qty': None,
                                                    'category':None, 'sub_category':None,
                                                    'current_stock': None, 'unit': None}]
            st.session_state.create_indent_next_id = 1
            st.session_state[CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY] = True # Signal to reset header fields
            st.rerun()
    else: # Normal indent creation form
        # --- Indent Header ---
        head_col1, head_col2 = st.columns(2)
        with head_col1:
            dept_widget_key = "create_indent_dept_widget_v19" # Unique key
            # Ensure current department value is valid for selectbox options
            current_dept_val = st.session_state.get(CREATE_INDENT_DEPT_SESS_KEY, "")
            dept_options_with_empty = [""] + distinct_departments # Add empty option for placeholder
            dept_idx = 0
            if current_dept_val in dept_options_with_empty:
                dept_idx = dept_options_with_empty.index(current_dept_val)

            selected_dept = st.selectbox(
                "Requesting Department*", 
                options=dept_options_with_empty,
                index=dept_idx,
                format_func=lambda x: "Select Department..." if x == "" else x, 
                key=dept_widget_key,
                on_change=lambda: st.session_state.update({
                    CREATE_INDENT_DEPT_SESS_KEY: st.session_state[dept_widget_key], 
                    'selected_department_for_create_indent': st.session_state[dept_widget_key] if st.session_state[dept_widget_key] else None
                })
            )
            # Update session state if not already done by on_change (e.g., initial load)
            if st.session_state.get(CREATE_INDENT_DEPT_SESS_KEY) != selected_dept :
                 st.session_state[CREATE_INDENT_DEPT_SESS_KEY] = selected_dept
                 st.session_state.selected_department_for_create_indent = selected_dept if selected_dept else None


            req_by_widget_key = "create_indent_req_by_widget_v19" # Unique key
            st.session_state[CREATE_INDENT_REQ_BY_SESS_KEY] = st.text_input(
                "Requested By (Your Name/ID)*", 
                value=st.session_state.get(CREATE_INDENT_REQ_BY_SESS_KEY,""), 
                key=req_by_widget_key
            )
        with head_col2:
            date_req_widget_key = "create_indent_date_req_widget_v19" # Unique key
            st.session_state[CREATE_INDENT_DATE_REQ_SESS_KEY] = st.date_input(
                "Date Required By*", 
                value=st.session_state.get(CREATE_INDENT_DATE_REQ_SESS_KEY, date.today()+timedelta(days=1)), 
                min_value=date.today(), 
                key=date_req_widget_key
            )
            st.text_input("Initial Status", value=STATUS_SUBMITTED, disabled=True, key="create_indent_status_disp_v19_fixed") # Unique key
        
        header_notes_widget_key = "create_indent_header_notes_widget_v19" # Unique key
        st.session_state[CREATE_INDENT_NOTES_SESS_KEY] = st.text_area(
            "Overall Indent Notes (Optional)", 
            value=st.session_state.get(CREATE_INDENT_NOTES_SESS_KEY,""), 
            key=header_notes_widget_key, 
            placeholder="General notes, urgency, etc."
        )
        st.divider()

        # --- Indent Items ---
        st.subheader("🛍️ Requested Items")
        
        # Suggested items based on department
        current_dept_for_suggestions = st.session_state.get('selected_department_for_create_indent')
        if current_dept_for_suggestions:
            suggested_items = item_service.get_suggested_items_for_department(db_engine, current_dept_for_suggestions, top_n=5)
            if suggested_items:
                st.caption("✨ Quick Add (based on recent requests from this department):")
                items_in_current_indent_ids = {row.get('item_id') for row in st.session_state.create_indent_rows if row.get('item_id')}
                valid_suggestions = [sugg for sugg in suggested_items if sugg['item_id'] not in items_in_current_indent_ids]
                
                if valid_suggestions:
                    sugg_cols = st.columns(min(len(valid_suggestions), 5)) # Max 5 columns for suggestions
                    for i_sugg, sugg_item in enumerate(valid_suggestions[:5]): # Limit to 5 suggestions displayed
                        sugg_cols[i_sugg].button(
                            f"+ {sugg_item['item_name']}", 
                            key=f"suggest_item_v19_{sugg_item['item_id']}", # Unique key
                            on_click=add_suggested_item_callback, 
                            args=(sugg_item['item_id'], sugg_item['item_name'], sugg_item['unit']),
                            help=f"Add {sugg_item['item_name']} ({sugg_item['unit']})", 
                            use_container_width=True
                        )
                elif items_in_current_indent_ids and any(row.get('item_id') for row in st.session_state.create_indent_rows):
                     st.caption("Frequent items might already be in your list or no other frequent items found.")
                else: st.caption("No frequent items found for this department recently, or items are already added.")
                st.caption("") # Adds a little space
        
        # Item selection dropdown options based on department
        item_options_dict: Dict[str, Optional[int]] = {placeholder_option_stock[0]: placeholder_option_stock[1]} # Type hint
        if st.session_state.get('selected_department_for_create_indent'): # Use .get for safety
            selected_dept_for_filter = st.session_state.selected_department_for_create_indent
            if not all_active_items_df.empty:
                try:
                    # Filter items based on permitted_departments string (case-insensitive)
                    available_items_df = all_active_items_df[
                        all_active_items_df['permitted_departments'].fillna('').astype(str).str.lower().apply(
                            lambda depts_str: selected_dept_for_filter.strip().lower() in [d.strip().lower() for d in depts_str.split(',')] if depts_str else False
                        )
                    ].copy()

                    if available_items_df.empty:
                        item_options_dict.update({"-- No items permitted for this department --": -2}) # Use a different sentinel value
                    else:
                        item_options_dict.update({ 
                            f"{r['name']} ({r['unit']})": r['item_id'] 
                            for _, r in available_items_df.sort_values('name').iterrows()
                        })
                except Exception as e_item_filter: 
                    print(f"ERROR [5_Indents.item_filtering]: Error filtering items: {e_item_filter}")
                    item_options_dict.update({"Error loading items": -3}) # Sentinel for error
            else: # No active items in the system at all
                st.warning("No active items found in the system to add to the indent.")
                item_options_dict.update({"No items available": -4})
        else: # Department not selected yet
            st.info("ℹ️ Select a requesting department above to see and add items.")
            item_options_dict = {"-- Select Department First --": -5} # Placeholder if no dept selected

        # Item rows display
        h_cols = st.columns([4,2,3,1]); 
        h_cols[0].markdown("**Item**"); h_cols[1].markdown("**Req. Qty**"); 
        h_cols[2].markdown("**Notes**"); h_cols[3].markdown("**Action**"); 
        st.divider()

        for i_loop_item_rows, row_state in enumerate(st.session_state.create_indent_rows):
            row_id = row_state['id']
            item_cols_display = st.columns([4,2,3,1]) # Columns for each item row
            
            # Item Selectbox
            item_selectbox_key_row = f"disp_item_select_v19_{row_id}" # Unique key
            # Determine default item for selectbox
            default_item_display_name_row = placeholder_option_stock[0] # Default to placeholder
            if row_state.get('item_id') is not None and row_state.get('item_id') != -1 :
                # Find the display name matching the stored item_id
                default_item_display_name_row = next(
                    (name for name, id_val in item_options_dict.items() if id_val == row_state['item_id']), 
                    placeholder_option_stock[0] # Fallback to placeholder if not found (e.g. item became inactive/unpermitted)
                )
            try: # Determine index for selectbox
                current_item_idx_row = list(item_options_dict.keys()).index(default_item_display_name_row)
            except ValueError: 
                current_item_idx_row = 0 # Default to first option (placeholder) if key not found
                if row_state.get('item_id') is not None and row_state.get('item_id') != -1: # If a valid item was stored but not found in options
                    st.session_state.create_indent_rows[i_loop_item_rows]['item_id'] = None # Reset if item becomes invalid

            with item_cols_display[0]:
                st.selectbox(
                    f"Item (Row {i_loop_item_rows+1})", 
                    options=list(item_options_dict.keys()), 
                    index=current_item_idx_row,
                    key=item_selectbox_key_row, 
                    label_visibility="collapsed",
                    on_change=update_row_item_details_callback, 
                    args=(i_loop_item_rows, item_selectbox_key_row, item_options_dict)
                )
                # Display item details below selectbox
                current_row_data_for_disp = st.session_state.create_indent_rows[i_loop_item_rows]
                current_item_id_for_disp = current_row_data_for_disp.get('item_id')
                if current_item_id_for_disp and current_item_id_for_disp != -1: # If a valid item is selected
                    info_parts = []
                    if current_row_data_for_disp.get('category'): info_parts.append(f"Cat: {current_row_data_for_disp['category']}")
                    if current_row_data_for_disp.get('sub_category'): info_parts.append(f"Sub: {current_row_data_for_disp['sub_category']}")
                    if current_row_data_for_disp.get('current_stock') is not None : 
                        unit_disp = current_row_data_for_disp.get('unit', '')
                        info_parts.append(f"Stock: {float(current_row_data_for_disp['current_stock']):.2f} {unit_disp}")
                    if current_row_data_for_disp.get('last_ordered'): info_parts.append(f"Last ord: {current_row_data_for_disp['last_ordered']}")
                    if info_parts: st.caption(" | ".join(info_parts))

            # Requested Quantity Input
            with item_cols_display[1]:
                qty_key_for_row_disp = f"disp_item_qty_v19_{row_id}" # Unique key
                current_qty_val = float(st.session_state.create_indent_rows[i_loop_item_rows].get('requested_qty', 1.0))
                def on_qty_change_callback(idx_arg, key_arg): # Inner callback for quantity change
                    st.session_state.create_indent_rows[idx_arg]['requested_qty'] = st.session_state[key_arg]
                st.number_input(
                    f"Qty(R{i_loop_item_rows+1})", value=current_qty_val, 
                    min_value=0.01, step=0.1, format="%.2f",
                    key=qty_key_for_row_disp, label_visibility="collapsed",
                    on_change=on_qty_change_callback, args=(i_loop_item_rows, qty_key_for_row_disp)
                )
                # Median quantity comparison (visual aid)
                median_qty_row_disp = st.session_state.create_indent_rows[i_loop_item_rows].get('median_qty')
                actual_qty_row_disp = st.session_state.create_indent_rows[i_loop_item_rows].get('requested_qty', 0.0)
                if median_qty_row_disp and median_qty_row_disp > 0 and actual_qty_row_disp > 0:
                    if actual_qty_row_disp > median_qty_row_disp * 3: st.warning(f"High! (Avg:~{median_qty_row_disp:.1f})",icon="❗")
                    elif actual_qty_row_disp < median_qty_row_disp / 3: st.info(f"Low (Avg:~{median_qty_row_disp:.1f})",icon="ℹ️")
            
            # Item Notes Input
            with item_cols_display[2]:
                notes_key_for_row_disp = f"disp_item_notes_v19_{row_id}" # Unique key
                def on_notes_change_callback(idx_arg, key_arg): # Inner callback for notes change
                    st.session_state.create_indent_rows[idx_arg]['notes'] = st.session_state[key_arg]
                st.text_input(
                    f"Notes(R{i_loop_item_rows+1})", 
                    value=st.session_state.create_indent_rows[i_loop_item_rows].get('notes',''),
                    key=notes_key_for_row_disp, label_visibility="collapsed", placeholder="Optional item specific notes",
                    on_change=on_notes_change_callback, args=(i_loop_item_rows, notes_key_for_row_disp)
                )
            
            # Remove Row Button
            with item_cols_display[3]:
                if len(st.session_state.create_indent_rows) > 1: 
                    item_cols_display[3].button(
                        "➖", key=f"disp_remove_row_v19_{row_id}", # Unique key
                        on_click=remove_indent_row_callback, args=(row_id,),
                        help="Remove this item line"
                    )
                else: item_cols_display[3].write("") # Placeholder if only one row
            st.caption("") # Small space below each item row

        # Add multiple lines
        add_lines_cols = st.columns([2, 1.2])
        with add_lines_cols[0]:
            st.number_input(
                "Lines to add:",
                min_value=1, max_value=10, step=1,
                key="create_indent_num_lines_input_v19", # Unique key (was v18)
                # Use session state for value to persist if form validation fails and reruns
                value = st.session_state.num_lines_to_add_value, 
                help="Specify how many new blank item lines to add (1-10)."
            )
        with add_lines_cols[1]:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True) # Align button vertically
            st.button(
                "➕ Add Lines",
                on_click=add_multiple_indent_lines_callback, # Uses value from the number_input
                key="add_multi_lines_btn_v19", # Unique key (was v18)
                use_container_width=True
            )
        st.divider()

        # Form Submission
        with st.form("create_indent_final_submit_form_v19", clear_on_submit=False): # Unique key
            submitted_final_button = st.form_submit_button("📝 Submit Indent Request", type="primary", use_container_width=True)
            if submitted_final_button:
                # Gather header data from session state using standardized keys
                header_data_submit = {
                    "department": st.session_state.get(CREATE_INDENT_DEPT_SESS_KEY),
                    "requested_by": st.session_state.get(CREATE_INDENT_REQ_BY_SESS_KEY, "").strip(),
                    "date_required": st.session_state.get(CREATE_INDENT_DATE_REQ_SESS_KEY),
                    "notes": st.session_state.get(CREATE_INDENT_NOTES_SESS_KEY, "").strip() or None, # Ensure None if empty
                    "status": STATUS_SUBMITTED # Default status
                }
                
                is_valid_submission = True # Flag for overall validity
                items_to_submit_list: List[Dict[str,Any]] = [] # Type hint
                seen_item_ids_in_form: Set[Optional[int]] = set() # Type hint for set of item IDs

                # Validate header
                if not header_data_submit["department"]: 
                    st.error("Requesting Department is required."); is_valid_submission = False
                if not header_data_submit["requested_by"]: 
                    st.error("Requested By (Your Name/ID) is required."); is_valid_submission = False
                
                # Validate items
                if not st.session_state.create_indent_rows:
                    st.error("At least one item must be added to the indent."); is_valid_submission = False
                
                for i_r, r_data in enumerate(st.session_state.create_indent_rows):
                    item_id_v = r_data.get('item_id')
                    qty_v = r_data.get('requested_qty')
                    notes_v = r_data.get('notes', "") # Default to empty string for notes if missing

                    # Find item name for error messages
                    item_name_val = "Selected Item" # Default name
                    if item_id_v and item_id_v != -1:
                        item_name_val = next((name for name, id_val in item_options_dict.items() if id_val == item_id_v), f"Item ID {item_id_v}")


                    if item_id_v is None or item_id_v == -1: 
                        st.error(f"Row {i_r+1}: Please select a valid item."); is_valid_submission=False; continue # Skip to next item if this one is invalid
                    
                    if item_id_v in seen_item_ids_in_form:
                        st.error(f"Row {i_r+1}: Item '{item_name_val}' is duplicated in the indent. Please remove duplicate lines."); is_valid_submission=False
                    
                    try:
                        qty_float = float(qty_v)
                        if qty_float <= 0:
                            st.error(f"Row {i_r+1}: Requested quantity for '{item_name_val}' must be greater than 0. Got: {qty_v}"); is_valid_submission=False
                    except (ValueError, TypeError):
                        st.error(f"Row {i_r+1}: Invalid quantity for '{item_name_val}'. Please enter a number. Got: {qty_v}"); is_valid_submission=False
                    
                    if is_valid_submission and item_id_v not in seen_item_ids_in_form: # Add to list if valid and not duplicate
                        items_to_submit_list.append({
                            "item_id": item_id_v, 
                            "requested_qty": float(qty_v), 
                            "notes": (notes_v.strip() if isinstance(notes_v, str) else None) or None # Clean notes
                        })
                    if item_id_v != -1 : seen_item_ids_in_form.add(item_id_v) # Add to seen set

                if not items_to_submit_list and is_valid_submission: # If all validations passed but no items somehow
                    st.error("Indent must contain at least one valid item to submit."); is_valid_submission = False
                
                # Final submission if all valid
                if is_valid_submission:
                    new_mrn = indent_service.generate_mrn(db_engine)
                    if new_mrn:
                        header_data_submit["mrn"] = new_mrn
                        success, message = indent_service.create_indent(db_engine, header_data_submit, items_to_submit_list)
                        if success:
                            st.session_state.last_created_mrn_for_print = new_mrn
                            # Fetch details for summary and PDF generation *after* successful creation
                            hd_summary, itms_summary = indent_service.get_indent_details_for_pdf(db_engine, new_mrn)
                            st.session_state.last_submitted_indent_details = {"header": hd_summary, "items": itms_summary} if hd_summary and itms_summary is not None else None
                            
                            # Reset form state for next indent
                            st.session_state.create_indent_rows = [{'id': 0, 'item_id': None, 'requested_qty': 1.0, 'notes': '',
                                                                    'last_ordered': None, 'median_qty': None,
                                                                    'category':None, 'sub_category':None,
                                                                    'current_stock': None, 'unit': None}]
                            st.session_state.create_indent_next_id = 1
                            st.session_state[CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY] = True # Signal to reset header fields
                            
                            # Clear caches that might be affected
                            fetch_indent_page_data.clear()
                            indent_service.get_indents.clear() # For view page
                            item_service.get_item_order_history_details.clear() # If median qty calculation depends on this
                            item_service.get_suggested_items_for_department.clear()
                            st.rerun() # Rerun to display success message and clear form
                        else: 
                            st.error(f"Failed to create indent: {message}") # Display error from service
                    else: 
                        st.error("Failed to generate MRN. Please try again.")
                # No else here; warnings/errors for invalid fields already displayed

# ===========================
# VIEW INDENTS SECTION
# ===========================
elif st.session_state.active_indent_section == "view":
    st.subheader(INDENT_SECTIONS["view"])
    view_filter_cols = st.columns([1.5, 1.5, 1.5, 2.5]) # Adjusted column ratios
    with view_filter_cols[0]: 
        mrn_filter_key = "view_indent_mrn_filter_v19" # Unique key
        mrn_filter = st.text_input("Search by MRN:", key=mrn_filter_key, placeholder="e.g., MRN-...")
    with view_filter_cols[1]:
        dept_options_view = ["All Departments"] + distinct_departments
        dept_filter_key = "view_indent_dept_filter_v19" # Unique key
        dept_filter_val = st.selectbox("Filter by Department:", options=dept_options_view, key=dept_filter_key)
    with view_filter_cols[2]:
        status_options_view = ["All Statuses"] + ALL_INDENT_STATUSES
        status_filter_key = "view_indent_status_filter_v19" # Unique key
        status_filter_val = st.selectbox("Filter by Status:", options=status_options_view, key=status_filter_key)
    with view_filter_cols[3]:
        date_col1, date_col2 = st.columns(2)
        with date_col1: date_start_filter_val = st.date_input("Submitted From:", value=None, key="view_indent_date_start_v19_unique") # Unique key
        with date_col2: date_end_filter_val = st.date_input("Submitted To:", value=None, key="view_indent_date_end_v19_unique") # Unique key
    
    # Prepare arguments for service call
    date_start_str_arg = date_start_filter_val.strftime('%Y-%m-%d') if date_start_filter_val else None
    date_end_str_arg = date_end_filter_val.strftime('%Y-%m-%d') if date_end_filter_val else None
    dept_arg = dept_filter_val if dept_filter_val != "All Departments" else None
    status_arg = status_filter_val if status_filter_val != "All Statuses" else None
    mrn_arg = mrn_filter.strip() if mrn_filter else None
    
    indents_df = indent_service.get_indents(
        db_engine, mrn_filter=mrn_arg, dept_filter=dept_arg, 
        status_filter=status_arg, date_start_str=date_start_str_arg, date_end_str=date_end_str_arg
    )
    st.divider()

    if indents_df.empty: 
        st.info("ℹ️ No indents found matching your criteria.")
    else:
        st.success(f"Found {len(indents_df)} indent(s).")
        display_df_view = indents_df.copy()
        
        # Format dates for display
        date_cols_for_view = ['date_required', 'date_submitted', 'date_processed', 'created_at', 'updated_at']
        for col_v in date_cols_for_view:
            if col_v in display_df_view.columns:
                display_df_view[col_v] = pd.to_datetime(display_df_view[col_v], errors='coerce').dt.strftime('%Y-%m-%d %H:%M') \
                                        if col_v in ['date_submitted', 'created_at', 'updated_at', 'date_processed'] \
                                        else pd.to_datetime(display_df_view[col_v], errors='coerce').dt.strftime('%Y-%m-%d')
        
        status_emoji_map = {STATUS_SUBMITTED: "📬 Submitted", STATUS_PROCESSING: "⚙️ Processing", 
                            STATUS_COMPLETED: "✅ Completed", STATUS_CANCELLED: "❌ Cancelled"}
        if 'status' in display_df_view.columns: 
            display_df_view['status_display'] = display_df_view['status'].map(status_emoji_map).fillna(display_df_view['status'])
        
        cols_to_display_order = ["mrn", "date_submitted", "department", "requested_by", "date_required", 
                                 "status_display", "item_count", "indent_notes", "processed_by_user_id", "date_processed"]
        
        # Filter out columns that might not exist if schema varies or for cleaner display
        final_cols_for_df = [col for col in cols_to_display_order if col in display_df_view.columns]

        st.dataframe(
            display_df_view[final_cols_for_df], 
            use_container_width=True, hide_index=True,
            column_config={
                "indent_id": None, "status": None, # Hide raw status if status_display is used
                "mrn": st.column_config.TextColumn("MRN", help="Material Request Number"), 
                "date_submitted": st.column_config.TextColumn("Submitted On"),
                "department": "Department", 
                "requested_by": "Requestor", 
                "date_required": st.column_config.TextColumn("Required By"),
                "status_display": st.column_config.TextColumn("Status"), 
                "item_count": st.column_config.NumberColumn("No. of Items", format="%d"),
                "indent_notes": st.column_config.TextColumn("Indent Notes"),
                "processed_by_user_id": st.column_config.TextColumn("Processed By"),
                "date_processed": st.column_config.TextColumn("Processed On")
            }
        )
        st.divider()
        
        # PDF Download Section
        st.subheader("📄 Download Indent as PDF")
        st.caption("Select an MRN from the list above (if any) to generate its PDF.")
        if not indents_df.empty:
            available_mrns_for_pdf = ["-- Select MRN for PDF --"] + sorted(indents_df['mrn'].unique().tolist())
            selected_mrn_for_pdf_key = "pdf_mrn_select_v19_unique" # Unique key
            
            # Preserve selection if PDF was generated for it
            current_pdf_selection_idx = 0
            if st.session_state.get("pdf_filename_for_download"):
                try:
                    # Extract MRN from filename e.g. "Indent_MRN-202301-00001.pdf" -> "MRN-202301-00001"
                    mrn_from_filename = st.session_state.pdf_filename_for_download.split('_',1)[1].rsplit('.',1)[0]
                    if mrn_from_filename in available_mrns_for_pdf:
                        current_pdf_selection_idx = available_mrns_for_pdf.index(mrn_from_filename)
                except IndexError: pass # Filename format might not match

            selected_mrn_for_pdf = st.selectbox("Choose MRN:", options=available_mrns_for_pdf, index=current_pdf_selection_idx, key=selected_mrn_for_pdf_key)
            
            if selected_mrn_for_pdf != "-- Select MRN for PDF --":
                # Generate PDF button (only if not already generated for this MRN)
                if not (st.session_state.get("pdf_bytes_for_download") and 
                        st.session_state.get("pdf_filename_for_download","").endswith(f"{selected_mrn_for_pdf}.pdf")):
                    if st.button("⚙️ Generate PDF", key=f"generate_pdf_indent_btn_v19_{selected_mrn_for_pdf.replace('-', '_')}"): # Unique key
                        with st.spinner(f"Generating PDF for {selected_mrn_for_pdf}..."):
                            header_details, items_details = indent_service.get_indent_details_for_pdf(db_engine, selected_mrn_for_pdf)
                            if header_details and items_details is not None: # items_details can be empty list
                                pdf_bytes = generate_indent_pdf(header_details, items_details)
                                if pdf_bytes:
                                    st.session_state.pdf_bytes_for_download = pdf_bytes
                                    st.session_state.pdf_filename_for_download = f"Indent_{selected_mrn_for_pdf}.pdf"
                                    st.rerun() # Rerun to make download button visible
                                # else: error already shown by generate_indent_pdf via toast
                            else: 
                                st.error(f"Could not fetch details to generate PDF for MRN {selected_mrn_for_pdf}.")
                
                # Download button (if PDF is ready for the selected MRN)
                if (st.session_state.get("pdf_bytes_for_download") and 
                    st.session_state.get("pdf_filename_for_download","").endswith(f"{selected_mrn_for_pdf}.pdf")):
                    st.download_button(
                        label=f"📥 Download PDF for {selected_mrn_for_pdf}", 
                        data=st.session_state.pdf_bytes_for_download,
                        file_name=st.session_state.pdf_filename_for_download, 
                        mime="application/pdf",
                        key=f"final_dl_btn_v19_{selected_mrn_for_pdf.replace('-', '_')}", # Unique key
                        # No on_click clear here, let it persist until another PDF is generated or section changes
                    )

# ===========================
# PROCESS INDENT SECTION
# ===========================
elif st.session_state.active_indent_section == "process":
    st.subheader(INDENT_SECTIONS["process"])

    indents_to_process_df = indent_service.get_indents_for_processing(db_engine)
    
    indent_options_list = [placeholder_option_indent_process] # Start with placeholder
    if not indents_to_process_df.empty:
        for _, row_proc in indents_to_process_df.iterrows():
            # Ensure date_submitted is datetime before formatting
            date_submitted_str = pd.to_datetime(row_proc['date_submitted']).strftime('%d-%b-%y') if pd.notna(row_proc.get('date_submitted')) else 'N/A'
            display_name = f"{row_proc['mrn']} ({row_proc['department']}) - Sub: {date_submitted_str}"
            indent_options_list.append((display_name, row_proc['indent_id'], row_proc['mrn']))

    # Determine current selection index for selectbox
    current_selected_tuple_for_process = st.session_state.get("process_indent_selected_tuple", placeholder_option_indent_process)
    current_selected_index_proc = 0 # Default to placeholder
    for i_proc_opt, option_tuple_proc in enumerate(indent_options_list):
        if option_tuple_proc[1] == current_selected_tuple_for_process[1]: # Match by indent_id
            current_selected_index_proc = i_proc_opt
            break
            
    selected_tuple_from_widget = st.selectbox(
        "Select Indent (MRN) to Process:",
        options=indent_options_list,
        index=current_selected_index_proc,
        format_func=lambda x_opt: x_opt[0], # Display only the name part of the tuple
        key="process_indent_select_widget_v19", # Unique key
        on_change=on_process_indent_select_change # Resets item df and defaults
    )
    # Update session state if selection changed via UI
    if st.session_state.process_indent_selected_tuple != selected_tuple_from_widget:
        st.session_state.process_indent_selected_tuple = selected_tuple_from_widget
        # on_process_indent_select_change will handle clearing items_df,
        # but a rerun might be needed to fetch new data immediately.
        st.rerun() 
    
    selected_indent_id = st.session_state.process_indent_selected_tuple[1]
    selected_mrn = st.session_state.process_indent_selected_tuple[2]

    st.divider()

    if selected_indent_id: # If a valid indent is selected
        st.markdown(f"#### Processing Indent: **{selected_mrn}**")
        
        # Fetch or use cached indent items for display
        # Check if items_df needs to be refetched (if indent changes or df is empty)
        refetch_items_for_processing = True
        if not st.session_state.process_indent_items_df.empty and \
           'indent_id_for_check' in st.session_state.process_indent_items_df.columns and \
           not st.session_state.process_indent_items_df.empty and \
           st.session_state.process_indent_items_df.iloc[0]['indent_id_for_check'] == selected_indent_id:
            refetch_items_for_processing = False

        if refetch_items_for_processing:
            fetched_items_df = indent_service.get_indent_items_for_display(db_engine, selected_indent_id)
            if not fetched_items_df.empty:
                fetched_items_df['indent_id_for_check'] = selected_indent_id # Add check column
            st.session_state.process_indent_items_df = fetched_items_df
            # Reset default quantities when new indent items are loaded
            st.session_state.process_indent_issue_quantities_defaults = {
                row_item_df['indent_item_id']: 0.0 for _, row_item_df in fetched_items_df.iterrows()
            }
        
        items_df_for_processing_display = st.session_state.process_indent_items_df

        if not items_df_for_processing_display.empty:
            st.markdown("**Indent Items:**")
            
            header_cols_proc = st.columns([3, 1, 1, 1, 1.5, 1.5, 1.5, 2])
            headers_proc = ["Item (Unit)", "Req.", "Issued", "Pend.", "Stock", "Status", "Issue Now*", "Notes"]
            for col_p, header_text_p in zip(header_cols_proc, headers_proc):
                col_p.markdown(f"**{header_text_p}**")
            
            # Form for issuing quantities
            with st.form("process_indent_form_submit_v19_2", clear_on_submit=False): # Unique key
                for index_proc_item, row_proc_item_disp in items_df_for_processing_display.iterrows():
                    indent_item_id_proc = row_proc_item_disp['indent_item_id']
                    issue_qty_key_proc = f"issue_qty_input_v19_2_{indent_item_id_proc}" # Unique key

                    item_display_cols_proc = st.columns([3, 1, 1, 1, 1.5, 1.5, 1.5, 2])
                    
                    item_display_cols_proc[0].write(f"{row_proc_item_disp['item_name']} ({row_proc_item_disp['item_unit']})")
                    item_display_cols_proc[1].write(f"{row_proc_item_disp['requested_qty']:.2f}")
                    item_display_cols_proc[2].write(f"{row_proc_item_disp['issued_qty']:.2f}")
                    item_display_cols_proc[3].write(f"{row_proc_item_disp['qty_remaining_to_issue']:.2f}")
                    item_display_cols_proc[4].write(f"{row_proc_item_disp['stock_on_hand']:.2f}")
                    item_display_cols_proc[5].caption(row_proc_item_disp['item_status'])

                    qty_remaining_calc = float(row_proc_item_disp.get('qty_remaining_to_issue', 0.0))
                    stock_available_calc = float(row_proc_item_disp.get('stock_on_hand', 0.0))
                    max_issuable_qty_calc = min(qty_remaining_calc, stock_available_calc)
                    
                    effective_max_val_input = max(0.0, max_issuable_qty_calc) # Ensure max_value is not negative

                    is_disabled_input = row_proc_item_disp['item_status'] in [ITEM_STATUS_FULLY_ISSUED, ITEM_STATUS_CANCELLED_ITEM] or max_issuable_qty_calc <= 0
                    
                    default_issue_qty_val = 0.0
                    if not is_disabled_input:
                         default_issue_qty_val = float(st.session_state.process_indent_issue_quantities_defaults.get(indent_item_id_proc, 0.0))
                         default_issue_qty_val = min(default_issue_qty_val, effective_max_val_input) # Clamp default by max

                    item_display_cols_proc[6].number_input(
                        "Qty to Issue Now", 
                        min_value=0.0, 
                        max_value=effective_max_val_input, # Corrected max_value
                        value=default_issue_qty_val,
                        step=0.01, format="%.2f",
                        key=issue_qty_key_proc, 
                        label_visibility="collapsed",
                        disabled=is_disabled_input,
                        help=f"Max issuable for this item: {effective_max_val_input:.2f}"
                    )
                    item_display_cols_proc[7].caption(row_proc_item_disp.get('item_notes') or "---")
                    st.caption("") 

                st.divider()
                st.session_state.process_indent_user_id = st.text_input(
                    "Processed by (Your Name/ID)*", 
                    value=st.session_state.get("process_indent_user_id", ""),
                    key="process_user_id_input_v19_unique" # Unique key
                )

                # Submit button for the form
                submit_issue_button = st.form_submit_button("💾 Issue Quantities & Update Status", type="primary", use_container_width=True)

                if submit_issue_button:
                    if not st.session_state.process_indent_user_id.strip():
                        st.warning("Please enter 'Processed by' User ID.")
                    else:
                        items_to_submit_list_proc: List[Dict[str,Any]] = []
                        has_items_with_qty_to_issue = False
                        for _, item_row_submit in items_df_for_processing_display.iterrows():
                            ii_id_submit = item_row_submit['indent_item_id']
                            i_id_submit = item_row_submit['item_id']
                            current_issue_qty_key_submit = f"issue_qty_input_v19_2_{ii_id_submit}" # Match key
                            
                            qty_val_from_form = st.session_state.get(current_issue_qty_key_submit, 0.0)
                            try:
                                qty_to_issue_val_submit = float(qty_val_from_form)
                                if qty_to_issue_val_submit > 0: # Only process if qty > 0
                                    items_to_submit_list_proc.append({
                                        "indent_item_id": ii_id_submit,
                                        "item_id": i_id_submit,
                                        "qty_to_issue_now": qty_to_issue_val_submit
                                    })
                                    has_items_with_qty_to_issue = True
                            except (ValueError, TypeError) as e_qty_parse:
                                st.error(f"Invalid quantity '{qty_val_from_form}' for item {item_row_submit['item_name']}. Please correct.")
                                items_to_submit_list_proc = [] # Invalidate the submission
                                has_items_with_qty_to_issue = False
                                break 
                        
                        if not has_items_with_qty_to_issue and not items_to_submit_list_proc: 
                            st.info("No quantities were specified for issuance. If you intend to only change the indent status (e.g., mark as completed), use the buttons below this form.")
                        elif items_to_submit_list_proc: # Only proceed if there are valid items to submit
                            with st.spinner(f"Processing indent {selected_mrn}..."):
                                success_proc, message_proc = indent_service.process_indent_issuance(
                                    db_engine, selected_indent_id, items_to_submit_list_proc,
                                    st.session_state.process_indent_user_id.strip(), selected_mrn
                                )
                                if success_proc:
                                    st.success(message_proc)
                                    st.session_state.process_indent_selected_tuple = placeholder_option_indent_process
                                    st.session_state.process_indent_items_df = pd.DataFrame()
                                    st.session_state.process_indent_issue_quantities_defaults = {}
                                    indent_service.get_indents_for_processing.clear() # Clear cache
                                    st.rerun()
                                else:
                                    st.error(f"Indent Processing Failed: {message_proc}")
            
            # Other Actions (Mark as Completed / Cancel Indent) - Should be OUTSIDE the form
            st.markdown("---") 
            st.markdown("##### Other Actions for this Indent:")

            action_cols_proc = st.columns(2)
            with action_cols_proc[0]:
                if st.button("✅ Mark Indent as Completed", key=f"mark_completed_v19_{selected_indent_id}", use_container_width=True):
                    user_id_for_action = st.session_state.get("process_indent_user_id","").strip()
                    if not user_id_for_action:
                        st.warning("Please enter 'Processed by' User ID (in the form above) before marking as completed.")
                    else:
                        with st.spinner(f"Marking indent {selected_mrn} as completed..."):
                            success_mark, msg_mark = indent_service.mark_indent_completed(
                                db_engine, selected_indent_id, user_id_for_action, selected_mrn
                            )
                            if success_mark:
                                st.success(msg_mark)
                                st.session_state.process_indent_selected_tuple = placeholder_option_indent_process
                                st.session_state.process_indent_items_df = pd.DataFrame()
                                st.session_state.process_indent_issue_quantities_defaults = {}
                                indent_service.get_indents_for_processing.clear()
                                st.rerun()
                            else: st.error(f"Failed to mark as completed: {msg_mark}")
            
            with action_cols_proc[1]:
                if st.button("❌ Cancel Entire Indent", key=f"cancel_indent_v19_{selected_indent_id}", type="secondary", use_container_width=True):
                    user_id_for_action = st.session_state.get("process_indent_user_id","").strip()
                    if not user_id_for_action:
                        st.warning("Please enter 'Processed by' User ID (in the form above) before cancelling.")
                    else:
                        # Consider adding a confirmation dialog for destructive actions like cancel
                        # e.g. if st.confirm("Are you sure you want to cancel this entire indent? This action cannot be undone."):
                        with st.spinner(f"Cancelling indent {selected_mrn}..."):
                            success_cancel, msg_cancel = indent_service.cancel_entire_indent(
                                db_engine, selected_indent_id, user_id_for_action, selected_mrn
                            )
                            if success_cancel:
                                st.success(msg_cancel)
                                st.session_state.process_indent_selected_tuple = placeholder_option_indent_process
                                st.session_state.process_indent_items_df = pd.DataFrame()
                                st.session_state.process_indent_issue_quantities_defaults = {}
                                indent_service.get_indents_for_processing.clear()
                                st.rerun()
                            else: st.error(f"Failed to cancel indent: {msg_cancel}")

        elif selected_indent_id: 
            st.info(f"No items found for Indent MRN {selected_mrn} to process, or it might have already been fully processed/cancelled.")
    else: # No indent selected for processing
        st.info("Select an indent from the dropdown above to start processing.")