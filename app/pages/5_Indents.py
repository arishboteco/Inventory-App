# app/pages/5_Indents.py
import os
import sys
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import urllib.parse
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import traceback

st.set_page_config(page_title="Indents", layout="wide")

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_CUR_DIR, os.pardir, os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from app.db.database_utils import connect_db
    from app.services import item_service
    from app.services import indent_service
    from app.auth.auth import get_current_user_id
    from app.core.constants import (
        ALL_INDENT_STATUSES,
        STATUS_SUBMITTED,
        STATUS_PROCESSING,
        STATUS_COMPLETED,
        STATUS_CANCELLED,
        ITEM_STATUS_FULLY_ISSUED,
        ITEM_STATUS_CANCELLED_ITEM,
        # Import UI constants
        PLACEHOLDER_SELECT_ITEM,
        PLACEHOLDER_SELECT_INDENT_PROCESS,
        PLACEHOLDER_SELECT_MRN_PDF,
        FILTER_ALL_DEPARTMENTS,
        FILTER_ALL_STATUSES,
        PLACEHOLDER_SELECT_DEPARTMENT_FIRST,
        PLACEHOLDER_NO_ITEMS_FOR_DEPARTMENT,
        PLACEHOLDER_NO_ITEMS_AVAILABLE,  # If applicable for item lists
        PLACEHOLDER_ERROR_LOADING_ITEMS,  # If applicable
    )
    from app.ui.theme import load_css, format_status_badge, render_sidebar_logo
    from app.ui.navigation import render_sidebar_nav
    from app.ui import show_success, show_error
    from app.ui.choices import build_item_choice_label
except ImportError as e:
    show_error(
        "Import error in 5_Indents.py: "
        f"{e}. Please ensure all service files and utility modules are correctly placed and named."
    )
    st.stop()
except Exception as e:
    show_error(f"An unexpected error occurred during an import in 5_Indents.py: {e}")
    st.stop()

# --- Session State Initialization ---
# Using imported constants for placeholder values
pg5_placeholder_select_item_tuple = (PLACEHOLDER_SELECT_ITEM, -1)
pg5_placeholder_indent_process_tuple = (PLACEHOLDER_SELECT_INDENT_PROCESS, None, None)

# Create Indent Section States
if "pg5_create_indent_rows" not in st.session_state:
    st.session_state.pg5_create_indent_rows = [
        {
            "id": 0,
            "item_id": None,
            "requested_qty": 1.0,
            "notes": "",
            "last_ordered": None,
            "median_qty": None,
            "category": None,
            "sub_category": None,
            "current_stock": None,
            "unit": None,
        }
    ]
    st.session_state.pg5_create_indent_next_id = 1
if "pg5_selected_department_for_create_indent" not in st.session_state:
    st.session_state.pg5_selected_department_for_create_indent = None
if "pg5_num_lines_to_add_value" not in st.session_state:
    st.session_state.pg5_num_lines_to_add_value = 1
if "pg5_last_created_mrn_for_print" not in st.session_state:
    st.session_state.pg5_last_created_mrn_for_print = None
if "pg5_last_submitted_indent_details" not in st.session_state:
    st.session_state.pg5_last_submitted_indent_details = None
if "pg5_pdf_bytes_for_download" not in st.session_state:
    st.session_state.pg5_pdf_bytes_for_download = None
if "pg5_pdf_filename_for_download" not in st.session_state:
    st.session_state.pg5_pdf_filename_for_download = None

# Process Indent Section States
if "pg5_process_indent_selected_tuple" not in st.session_state:
    st.session_state.pg5_process_indent_selected_tuple = pg5_placeholder_indent_process_tuple
if "pg5_process_indent_items_df" not in st.session_state:
    st.session_state.pg5_process_indent_items_df = pd.DataFrame()
if "pg5_process_indent_issue_quantities_defaults" not in st.session_state:
    st.session_state.pg5_process_indent_issue_quantities_defaults = {}
if "pg5_process_indent_user_id" not in st.session_state:
    st.session_state.pg5_process_indent_user_id = get_current_user_id()


INDENT_SECTIONS_PG5 = {
    "create": "➕ Create Indent",
    "view": "📄 View Indents",
    "process": "⚙️ Process Indent",
}
INDENT_SECTION_KEYS_PG5 = list(INDENT_SECTIONS_PG5.keys())
INDENT_SECTION_DISPLAY_NAMES_PG5 = list(INDENT_SECTIONS_PG5.values())
if "pg5_active_indent_section" not in st.session_state:
    st.session_state.pg5_active_indent_section = INDENT_SECTION_KEYS_PG5[0]

# Standardized Session State Keys for Create Indent Header (using pg5_ prefix)
PG5_CREATE_INDENT_DEPT_SESS_KEY = "pg5_create_indent_dept"
PG5_CREATE_INDENT_REQ_BY_SESS_KEY = "pg5_create_indent_req_by"
PG5_CREATE_INDENT_DATE_REQ_SESS_KEY = "pg5_create_indent_date_req"
PG5_CREATE_INDENT_NOTES_SESS_KEY = "pg5_create_indent_header_notes"
PG5_CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY = "pg5_create_indent_header_reset_signal"

for key, default_val in [
    (PG5_CREATE_INDENT_DEPT_SESS_KEY, ""),
    (PG5_CREATE_INDENT_REQ_BY_SESS_KEY, ""),
    (PG5_CREATE_INDENT_DATE_REQ_SESS_KEY, date.today() + timedelta(days=1)),
    (PG5_CREATE_INDENT_NOTES_SESS_KEY, ""),
    (PG5_CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY, False),
]:
    if key not in st.session_state:
        st.session_state[key] = default_val

load_css()
render_sidebar_logo()
render_sidebar_nav()

st.title("📝 Material Indents Management")
st.write(
    "Create new material requests (indents), view their status, process, and download details."
)
st.divider()

db_engine = connect_db()
if not db_engine:
    show_error("Database connection failed. Indent management functionality is unavailable.")
    st.stop()


@st.cache_data(ttl=300, show_spinner="Loading item & department data...")
def fetch_indent_page_data_pg5(_engine):  # Page-specific function
    if _engine is None:
        return (
            pd.DataFrame(
                columns=[
                    "item_id",
                    "name",
                    "unit",
                    "category",
                    "sub_category",
                    "permitted_departments",
                    "current_stock",
                ]
            ),
            [],
        )

    items_df_pg5 = item_service.get_all_items_with_stock(_engine, include_inactive=False)
    required_cols_pg5 = [
        "item_id",
        "name",
        "unit",
        "category",
        "sub_category",
        "permitted_departments",
        "current_stock",
    ]

    if not all(col in items_df_pg5.columns for col in required_cols_pg5):
        missing_pg5 = [col for col in required_cols_pg5 if col not in items_df_pg5.columns]
        print(
            f"ERROR [5_Indents.fetch_indent_page_data_pg5]: Required columns missing: {', '.join(missing_pg5)}."
        )
        return pd.DataFrame(columns=required_cols_pg5), []

    return items_df_pg5[required_cols_pg5].copy(), item_service.get_distinct_departments_from_items(
        _engine
    )


all_active_items_df_pg5, distinct_departments_pg5 = fetch_indent_page_data_pg5(
    db_engine
)  # Page-specific vars


# --- generate_indent_pdf function (keep as is, no UI constants needed inside it) ---
# ... (generate_indent_pdf function code as previously corrected) ...
def generate_indent_pdf(indent_header: Dict, indent_items: List[Dict]) -> Optional[bytes]:
    """Generates a PDF document for the given indent details."""
    if not indent_header or indent_items is None:
        print(
            "ERROR [5_Indents.generate_indent_pdf]: Missing indent header or items data for PDF generation."
        )
        st.toast("Cannot generate PDF: Missing critical indent data.", icon="🚨")
        return None
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=10)
        pdf.set_margins(left=8, top=8, right=8)
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(
            0,
            6,
            "Material Indent Request",
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

        pdf.set_font("Helvetica", "I", 7)
        generated_time_str = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        pdf.cell(0, 4, generated_time_str, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 8.5)
        header_details_list = [
            ("MRN:", indent_header.get("mrn", "N/A")),
            ("Department:", indent_header.get("department", "N/A")),
            ("Requested By:", indent_header.get("requested_by", "N/A")),
            ("Date Submitted:", indent_header.get("date_submitted", "N/A")),
            ("Date Required:", indent_header.get("date_required", "N/A")),
            ("Status:", indent_header.get("status", "N/A")),
        ]

        max_label_w = 0
        for label, _ in header_details_list:
            max_label_w = max(max_label_w, pdf.get_string_width(label) + 1)

        gap_between_pairs = 3
        available_width_for_values = (
            (pdf.w - pdf.l_margin - pdf.r_margin) - (max_label_w * 2) - gap_between_pairs
        )
        col_width_val = available_width_for_values / 2

        line_height_header_details = 4

        for i in range(0, len(header_details_list), 2):
            current_y_pos = pdf.get_y()
            pdf.set_font("Helvetica", "", 8.5)
            pdf.cell(
                max_label_w,
                line_height_header_details,
                header_details_list[i][0],
                align="L",
            )
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.cell(
                col_width_val,
                line_height_header_details,
                str(header_details_list[i][1]),
                align="L",
            )

            if i + 1 < len(header_details_list):
                pdf.set_xy(
                    pdf.l_margin + max_label_w + col_width_val + gap_between_pairs,
                    current_y_pos,
                )
                pdf.set_font("Helvetica", "", 8.5)
                pdf.cell(
                    max_label_w,
                    line_height_header_details,
                    header_details_list[i + 1][0],
                    align="L",
                )
                pdf.set_font("Helvetica", "B", 8.5)
                pdf.cell(
                    col_width_val,
                    line_height_header_details,
                    str(header_details_list[i + 1][1]),
                    align="L",
                )
            pdf.ln(line_height_header_details)

        if indent_header.get("notes"):
            pdf.ln(0.5)
            pdf.set_font("Helvetica", "I", 7.5)
            pdf.multi_cell(
                0,
                3,
                f"Indent Notes: {indent_header['notes']}",
                border=0,
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )

        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 7.5)
        col_widths = {"sno": 8, "name": 72, "unit": 18, "qty": 20, "notes": 70}

        pdf.set_fill_color(220, 220, 220)
        table_header_height = 4.5
        for key_pdf, header_text_pdf in [
            ("sno", "SNo"),
            ("name", "Item Name"),
            ("unit", "UoM"),
            ("qty", "Req Qty"),
            ("notes", "Item Notes"),
        ]:
            align_pdf = "C" if key_pdf in ["sno", "unit"] else ("R" if key_pdf == "qty" else "L")
            pdf.cell(
                col_widths[key_pdf],
                table_header_height,
                header_text_pdf,
                border=1,
                align=align_pdf,
                fill=True,
                new_x=XPos.RIGHT if key_pdf != "notes" else XPos.LMARGIN,
                new_y=YPos.NEXT if key_pdf == "notes" else YPos.TOP,
            )

        pdf.set_font("Helvetica", "", 7.5)
        base_line_height_items = 3.5

        if not indent_items:
            pdf.cell(
                sum(col_widths.values()),
                4,
                "No items found for this indent.",
                border=1,
                align="C",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
        else:
            item_serial_number_pdf = 0
            current_category_pdf = None
            current_sub_category_pdf = None

            for item_pdf in indent_items:
                item_cat_pdf = item_pdf.get("item_category", "Uncategorized")
                item_subcat_pdf = item_pdf.get("item_sub_category", "General")

                if item_cat_pdf != current_category_pdf:
                    current_category_pdf = item_cat_pdf
                    current_sub_category_pdf = None
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_fill_color(230, 230, 250)
                    pdf.cell(
                        sum(col_widths.values()),
                        5,
                        f"Category: {current_category_pdf}",
                        border=1,
                        new_x=XPos.LMARGIN,
                        new_y=YPos.NEXT,
                        fill=True,
                        align="L",
                    )

                if item_subcat_pdf != current_sub_category_pdf:
                    current_sub_category_pdf = item_subcat_pdf
                    pdf.set_font("Helvetica", "BI", 7.5)
                    pdf.set_x(pdf.l_margin + 3)
                    pdf.cell(
                        sum(col_widths.values()) - 3,
                        4,
                        f"Sub-Category: {current_sub_category_pdf}",
                        border="LRB",
                        new_x=XPos.LMARGIN,
                        new_y=YPos.NEXT,
                        fill=False,
                        align="L",
                    )

                pdf.set_font("Helvetica", "", 7.5)
                item_serial_number_pdf += 1

                sno_str = str(item_serial_number_pdf)
                name_str = item_pdf.get("item_name", "N/A") or "N/A"
                unit_str = str(item_pdf.get("item_unit", "N/A"))
                try:
                    qty_str = f"{float(item_pdf.get('requested_qty', 0)):.2f}"
                except (ValueError, TypeError):
                    qty_str = "Invalid"
                notes_str = item_pdf.get("item_notes", "") or ""

                max_lines = 1
                temp_x_for_calc = pdf.get_x()

                if col_widths["name"] > 0:
                    name_content_lines = pdf.multi_cell(
                        w=col_widths["name"],
                        h=base_line_height_items,
                        text=name_str,
                        border=0,
                        dry_run=True,
                        output="LINES",
                        align="L",
                    )
                    max_lines = max(max_lines, len(name_content_lines))
                pdf.set_x(temp_x_for_calc)

                if col_widths["notes"] > 0:
                    notes_content_lines = pdf.multi_cell(
                        w=col_widths["notes"],
                        h=base_line_height_items,
                        text=notes_str,
                        border=0,
                        dry_run=True,
                        output="LINES",
                        align="L",
                    )
                    max_lines = max(max_lines, len(notes_content_lines))
                pdf.set_x(temp_x_for_calc)

                effective_row_height = max_lines * base_line_height_items + (max_lines - 1) * 0.5

                row_start_y = pdf.get_y()
                current_x_pos = pdf.l_margin

                pdf.set_xy(current_x_pos, row_start_y)
                pdf.multi_cell(
                    col_widths["sno"],
                    effective_row_height,
                    sno_str,
                    border="LRB",
                    align="C",
                    max_line_height=base_line_height_items,
                )
                current_x_pos += col_widths["sno"]

                pdf.set_xy(current_x_pos, row_start_y)
                pdf.multi_cell(
                    col_widths["name"],
                    base_line_height_items,
                    name_str,
                    border="RB",
                    align="L",
                    max_line_height=base_line_height_items,
                )
                current_x_pos += col_widths["name"]

                pdf.set_xy(current_x_pos, row_start_y)
                pdf.multi_cell(
                    col_widths["unit"],
                    effective_row_height,
                    unit_str,
                    border="RB",
                    align="C",
                    max_line_height=base_line_height_items,
                )
                current_x_pos += col_widths["unit"]

                pdf.set_xy(current_x_pos, row_start_y)
                pdf.multi_cell(
                    col_widths["qty"],
                    effective_row_height,
                    qty_str,
                    border="RB",
                    align="R",
                    max_line_height=base_line_height_items,
                )
                current_x_pos += col_widths["qty"]

                pdf.set_xy(current_x_pos, row_start_y)
                pdf.multi_cell(
                    col_widths["notes"],
                    base_line_height_items,
                    notes_str,
                    border="RB",
                    align="L",
                    max_line_height=base_line_height_items,
                )

                pdf.set_y(row_start_y + effective_row_height)

        return bytes(pdf.output())

    except Exception as e_pdf:
        print(
            f"ERROR [5_Indents.generate_indent_pdf]: Failed to generate PDF: {e_pdf}\n{traceback.format_exc()}"
        )
        st.toast(f"Failed to generate PDF: {e_pdf}", icon="🚨")
        return None


# --- Callbacks (using pg5_ prefix for session state keys) ---
def add_single_indent_row_logic_pg5():
    new_id = st.session_state.pg5_create_indent_next_id
    st.session_state.pg5_create_indent_rows.append(
        {
            "id": new_id,
            "item_id": None,
            "requested_qty": 1.0,
            "notes": "",
            "last_ordered": None,
            "median_qty": None,
            "category": None,
            "sub_category": None,
            "current_stock": None,
            "unit": None,
        }
    )
    st.session_state.pg5_create_indent_next_id += 1


def add_multiple_indent_lines_callback_pg5():
    num_lines = st.session_state.get("pg5_create_indent_num_lines_input", 1)
    try:
        num_to_add = int(num_lines)
        if num_to_add < 1:
            num_to_add = 1
        if num_to_add > 10:
            num_to_add = 10
    except (ValueError, TypeError):
        num_to_add = 1
    for _ in range(num_to_add):
        add_single_indent_row_logic_pg5()
    st.session_state.pg5_num_lines_to_add_value = 1


def remove_indent_row_callback_pg5(row_id_to_remove):
    idx_to_remove = next(
        (
            i
            for i, r in enumerate(st.session_state.pg5_create_indent_rows)
            if r["id"] == row_id_to_remove
        ),
        -1,
    )
    if idx_to_remove != -1:
        if len(st.session_state.pg5_create_indent_rows) > 1:
            st.session_state.pg5_create_indent_rows.pop(idx_to_remove)
        else:
            st.toast("Cannot remove the last item row.", icon="⚠️")


def add_suggested_item_callback_pg5(item_id_to_add, item_name_to_add, unit_to_add):
    if any(row.get("item_id") == item_id_to_add for row in st.session_state.pg5_create_indent_rows):
        st.toast(f"'{item_name_to_add}' is already in the indent list.", icon="ℹ️")
        return

    empty_row_idx = next(
        (
            i
            for i, r in enumerate(st.session_state.pg5_create_indent_rows)
            if r.get("item_id") is None or r.get("item_id") == -1
        ),
        -1,
    )
    current_department = st.session_state.get(PG5_CREATE_INDENT_DEPT_SESS_KEY)
    history = item_service.get_item_order_history_details(
        db_engine, item_id_to_add, current_department
    )

    item_master_detail_row_df_pg5 = all_active_items_df_pg5[
        all_active_items_df_pg5["item_id"] == item_id_to_add
    ]
    category_val, sub_category_val, current_stock_val, unit_val_from_master = (
        "N/A",
        "N/A",
        None,
        unit_to_add,
    )

    if not item_master_detail_row_df_pg5.empty:
        item_master_row_pg5 = item_master_detail_row_df_pg5.iloc[0]
        category_val = item_master_row_pg5["category"]
        sub_category_val = item_master_row_pg5["sub_category"]
        current_stock_val = item_master_row_pg5.get("current_stock")
        unit_val_from_master = item_master_row_pg5.get("unit", unit_to_add)

    new_row_data_pg5 = {
        "item_id": item_id_to_add,
        "requested_qty": 1.0,
        "notes": "",
        "last_ordered": history.get("last_ordered_date"),
        "median_qty": history.get("median_quantity"),
        "category": category_val,
        "sub_category": sub_category_val,
        "current_stock": current_stock_val,
        "unit": unit_val_from_master,
    }

    if history.get("median_quantity") and history.get("median_quantity") > 0:
        new_row_data_pg5["requested_qty"] = float(history.get("median_quantity"))

    if empty_row_idx != -1:
        st.session_state.pg5_create_indent_rows[empty_row_idx].update(new_row_data_pg5)
        st.toast(f"Added '{item_name_to_add}' to row {empty_row_idx + 1}.", icon="👍")
    else:
        new_id_pg5 = st.session_state.pg5_create_indent_next_id
        st.session_state.pg5_create_indent_rows.append({"id": new_id_pg5, **new_row_data_pg5})
        st.session_state.pg5_create_indent_next_id += 1
        st.toast(f"Added '{item_name_to_add}' as a new line.", icon="➕")  # Corrected icon


def update_row_item_details_callback_pg5(row_index, item_selectbox_key_arg, item_options_dict_arg):
    selected_display_name_pg5 = st.session_state[item_selectbox_key_arg]
    item_id_val_pg5 = item_options_dict_arg.get(
        selected_display_name_pg5, -1
    )  # Default to placeholder if not found

    category_val_pg5, sub_category_val_pg5, current_stock_val_pg5, unit_val_pg5 = (
        None,
        None,
        None,
        None,
    )
    last_ordered_pg5, median_qty_pg5 = None, None
    requested_qty_pg5 = 1.0  # Default

    if item_id_val_pg5 is not None and item_id_val_pg5 != -1:  # Valid item selected
        item_master_row_df_pg5 = all_active_items_df_pg5[
            all_active_items_df_pg5["item_id"] == item_id_val_pg5
        ]
        if not item_master_row_df_pg5.empty:
            item_master_row_pg5 = item_master_row_df_pg5.iloc[0]
            category_val_pg5 = item_master_row_pg5["category"]
            sub_category_val_pg5 = item_master_row_pg5["sub_category"]
            current_stock_val_pg5 = item_master_row_pg5.get("current_stock", 0)
            unit_val_pg5 = item_master_row_pg5.get("unit", "N/A")

        dept_for_history_pg5 = st.session_state.get(PG5_CREATE_INDENT_DEPT_SESS_KEY)
        history_pg5 = item_service.get_item_order_history_details(
            db_engine, item_id_val_pg5, dept_for_history_pg5
        )
        last_ordered_pg5 = history_pg5.get("last_ordered_date")
        median_qty_pg5 = history_pg5.get("median_quantity")
        if median_qty_pg5 and median_qty_pg5 > 0:
            requested_qty_pg5 = float(median_qty_pg5)

    st.session_state.pg5_create_indent_rows[row_index].update(
        {
            "item_id": item_id_val_pg5 if item_id_val_pg5 != -1 else None,
            "category": category_val_pg5,
            "sub_category": sub_category_val_pg5,
            "current_stock": current_stock_val_pg5,
            "unit": unit_val_pg5,
            "last_ordered": last_ordered_pg5,
            "median_qty": median_qty_pg5,
            "requested_qty": requested_qty_pg5,
        }
    )


def set_active_indent_section_callback_pg5():
    selected_display_name_pg5 = st.session_state.pg5_indent_section_radio_key
    new_active_section_pg5 = INDENT_SECTION_KEYS_PG5[0]
    for key, display_name in INDENT_SECTIONS_PG5.items():
        if display_name == selected_display_name_pg5:
            new_active_section_pg5 = key
            break
    st.session_state.pg5_active_indent_section = new_active_section_pg5

    if new_active_section_pg5 != "process":
        st.session_state.pg5_process_indent_selected_tuple = pg5_placeholder_indent_process_tuple
        st.session_state.pg5_process_indent_items_df = pd.DataFrame()
        st.session_state.pg5_process_indent_issue_quantities_defaults = {}

    if new_active_section_pg5 != "create":
        st.session_state.pg5_last_created_mrn_for_print = None
        st.session_state.pg5_last_submitted_indent_details = None
        if "pg5_pdf_bytes_for_download" in st.session_state:
            del st.session_state.pg5_pdf_bytes_for_download
        if "pg5_pdf_filename_for_download" in st.session_state:
            del st.session_state.pg5_pdf_filename_for_download
    # else:
    # st.session_state[PG5_CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY] = True # Reset create form if switching to it


def on_process_indent_select_change_pg5():
    st.session_state.pg5_process_indent_items_df = pd.DataFrame()
    st.session_state.pg5_process_indent_issue_quantities_defaults = {}


def create_indent_submission_form_pg5(item_options_dict_pg5):
    """Render the final submit form for creating an indent."""
    with st.form("pg5_create_indent_final_submit_form", clear_on_submit=False):
        submitted_final_button_pg5 = st.form_submit_button(
            "📝 Submit Indent Request", type="primary", use_container_width=True
        )
        if submitted_final_button_pg5:
            header_data_submit_pg5 = {
                "department": st.session_state.get(PG5_CREATE_INDENT_DEPT_SESS_KEY),
                "requested_by": st.session_state.get(PG5_CREATE_INDENT_REQ_BY_SESS_KEY, "").strip(),
                "date_required": st.session_state.get(PG5_CREATE_INDENT_DATE_REQ_SESS_KEY),
                "notes": st.session_state.get(PG5_CREATE_INDENT_NOTES_SESS_KEY, "").strip() or None,
                "status": STATUS_SUBMITTED,
            }

            is_valid_pg5 = True
            items_to_submit_list_pg5 = []
            seen_item_ids_in_form_pg5 = set()
            if not header_data_submit_pg5["department"]:
                show_error("Department required.")
                is_valid_pg5 = False

            if not header_data_submit_pg5["requested_by"]:
                show_error("Requested By required.")
                is_valid_pg5 = False

            current_item_options_for_validation_pg5 = (
                item_options_dict_pg5 if isinstance(item_options_dict_pg5, dict) else {}
            )

            for i_r_pg5, r_data_pg5 in enumerate(st.session_state.pg5_create_indent_rows):
                item_id_v_pg5 = r_data_pg5.get("item_id")
                qty_v_pg5 = r_data_pg5.get("requested_qty")
                notes_v_pg5 = r_data_pg5.get("notes")
                item_name_val_pg5 = pg5_placeholder_select_item_tuple[0]
                if item_id_v_pg5 and item_id_v_pg5 != -1:
                    item_name_val_pg5 = next(
                        (
                            name
                            for name, id_val in current_item_options_for_validation_pg5.items()
                            if id_val == item_id_v_pg5
                        ),
                        f"Item ID {item_id_v_pg5}",
                    )

                if item_id_v_pg5 is None or item_id_v_pg5 == -1:
                    show_error(f"Row {i_r_pg5+1}: Select item.")
                    is_valid_pg5 = False
                    continue
                if item_id_v_pg5 in seen_item_ids_in_form_pg5:
                    show_error(f"Row {i_r_pg5+1}: Item '{item_name_val_pg5}' duplicated.")
                    is_valid_pg5 = False

                try:
                    if not (isinstance(qty_v_pg5, (float, int)) and float(qty_v_pg5) > 0):
                        show_error(
                            f"Row {i_r_pg5+1}: Qty for '{item_name_val_pg5}' > 0. Got: {qty_v_pg5}"
                        )
                        is_valid_pg5 = False
                except Exception:
                    show_error(
                        f"Row {i_r_pg5+1}: Invalid Qty for '{item_name_val_pg5}'. Got: {qty_v_pg5}"
                    )
                    is_valid_pg5 = False

                if is_valid_pg5 and item_id_v_pg5 not in seen_item_ids_in_form_pg5:
                    items_to_submit_list_pg5.append(
                        {
                            "item_id": item_id_v_pg5,
                            "requested_qty": float(qty_v_pg5),
                            "notes": (notes_v_pg5.strip() if isinstance(notes_v_pg5, str) else None)
                            or None,
                        }
                    )
                if item_id_v_pg5 != -1:
                    seen_item_ids_in_form_pg5.add(item_id_v_pg5)

            if not items_to_submit_list_pg5 and is_valid_pg5:
                show_error("Indent needs at least one valid item.")
                is_valid_pg5 = False

            if is_valid_pg5:
                new_mrn_pg5 = indent_service.generate_mrn(db_engine)
                if new_mrn_pg5:
                    header_data_submit_pg5["mrn"] = new_mrn_pg5
                    success_pg5, message_pg5 = indent_service.create_indent(
                        db_engine, header_data_submit_pg5, items_to_submit_list_pg5
                    )
                    if success_pg5:
                        st.session_state.pg5_last_created_mrn_for_print = new_mrn_pg5
                        (
                            hd_summary_pg5,
                            itms_summary_pg5,
                        ) = indent_service.get_indent_details_for_pdf(db_engine, new_mrn_pg5)
                        st.session_state.pg5_last_submitted_indent_details = (
                            {"header": hd_summary_pg5, "items": itms_summary_pg5}
                            if hd_summary_pg5 and itms_summary_pg5 is not None
                            else None
                        )

                        st.session_state.pg5_create_indent_rows = [
                            {
                                "id": 0,
                                "item_id": None,
                                "requested_qty": 1.0,
                                "notes": "",
                                "last_ordered": None,
                                "median_qty": None,
                                "category": None,
                                "sub_category": None,
                                "current_stock": None,
                                "unit": None,
                            }
                        ]
                        st.session_state.pg5_create_indent_next_id = 1
                        st.session_state[PG5_CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY] = True

                        fetch_indent_page_data_pg5.clear()
                        indent_service.get_indents.clear()
                        item_service.get_item_order_history_details.clear()
                        item_service.get_suggested_items_for_department.clear()
                        st.rerun()
                    else:
                        show_error(f"Failed to create indent: {message_pg5}")
                else:
                    show_error("Failed to generate MRN.")


def process_indent_form_pg5(
    selected_indent_id_pg5, selected_mrn_pg5, items_df_for_processing_disp_pg5
):
    """Render the issue quantities form for processing an indent."""
    with st.form(f"pg5_process_indent_form_submit_{selected_indent_id_pg5}", clear_on_submit=False):
        for (
            index_proc_item_pg5,
            row_proc_item_disp_pg5,
        ) in items_df_for_processing_disp_pg5.iterrows():
            indent_item_id_proc_pg5 = row_proc_item_disp_pg5["indent_item_id"]
            issue_qty_key_proc_pg5 = f"pg5_issue_qty_input_{indent_item_id_proc_pg5}"

            item_display_cols_proc_pg5 = st.columns([3, 1, 1, 1, 1.5, 1.5, 1.5, 2])
            item_display_cols_proc_pg5[0].write(
                f"{row_proc_item_disp_pg5['item_name']} ({row_proc_item_disp_pg5['item_unit']})"
            )
            item_display_cols_proc_pg5[1].write(f"{row_proc_item_disp_pg5['requested_qty']:.2f}")
            item_display_cols_proc_pg5[2].write(f"{row_proc_item_disp_pg5['issued_qty']:.2f}")
            item_display_cols_proc_pg5[3].write(
                f"{row_proc_item_disp_pg5['qty_remaining_to_issue']:.2f}"
            )
            item_display_cols_proc_pg5[4].write(f"{row_proc_item_disp_pg5['stock_on_hand']:.2f}")
            item_display_cols_proc_pg5[5].caption(row_proc_item_disp_pg5["item_status"])

            qty_remaining_calc_pg5 = float(
                row_proc_item_disp_pg5.get("qty_remaining_to_issue", 0.0)
            )
            stock_available_calc_pg5 = float(row_proc_item_disp_pg5.get("stock_on_hand", 0.0))
            max_issuable_qty_calc_pg5 = min(qty_remaining_calc_pg5, stock_available_calc_pg5)
            effective_max_val_input_pg5 = max(0.0, max_issuable_qty_calc_pg5)
            is_disabled_input_pg5 = (
                row_proc_item_disp_pg5["item_status"]
                in [ITEM_STATUS_FULLY_ISSUED, ITEM_STATUS_CANCELLED_ITEM]
                or max_issuable_qty_calc_pg5 <= 0
            )
            default_issue_qty_val_pg5 = 0.0
            if not is_disabled_input_pg5:
                default_issue_qty_val_pg5 = float(
                    st.session_state.pg5_process_indent_issue_quantities_defaults.get(
                        indent_item_id_proc_pg5, 0.0
                    )
                )
                default_issue_qty_val_pg5 = min(
                    default_issue_qty_val_pg5, effective_max_val_input_pg5
                )

            item_display_cols_proc_pg5[6].number_input(
                "Qty to Issue Now",
                min_value=0.0,
                max_value=effective_max_val_input_pg5,
                value=default_issue_qty_val_pg5,
                step=0.01,
                format="%.2f",
                key=issue_qty_key_proc_pg5,
                label_visibility="collapsed",
                disabled=is_disabled_input_pg5,
                help=f"Max issuable: {effective_max_val_input_pg5:.2f}",
            )
            item_display_cols_proc_pg5[7].caption(row_proc_item_disp_pg5.get("item_notes") or "---")
            st.caption("")

        st.divider()
        st.session_state.pg5_process_indent_user_id = get_current_user_id()
        st.text_input(
            "Processed by",
            value=st.session_state.pg5_process_indent_user_id,
            key=f"pg5_process_user_id_input_{selected_indent_id_pg5}",
            disabled=True,
        )

        submit_issue_button_pg5 = st.form_submit_button(
            "💾 Issue Quantities & Update Status", type="primary", use_container_width=True
        )
        if submit_issue_button_pg5:
            items_to_submit_list_proc_pg5: List[Dict[str, Any]] = []
            has_items_with_qty_pg5 = False
            for _, item_row_s_pg5 in items_df_for_processing_disp_pg5.iterrows():
                ii_id_s_pg5 = item_row_s_pg5["indent_item_id"]
                i_id_s_pg5 = item_row_s_pg5["item_id"]
                current_issue_qty_key_s_pg5 = f"pg5_issue_qty_input_{ii_id_s_pg5}"
                qty_val_form_s_pg5 = st.session_state.get(current_issue_qty_key_s_pg5, 0.0)
                try:
                    qty_to_issue_s_pg5 = float(qty_val_form_s_pg5)
                    if qty_to_issue_s_pg5 > 0:
                        items_to_submit_list_proc_pg5.append(
                            {
                                "indent_item_id": ii_id_s_pg5,
                                "item_id": i_id_s_pg5,
                                "qty_to_issue_now": qty_to_issue_s_pg5,
                            }
                        )
                        has_items_with_qty_pg5 = True
                except (ValueError, TypeError):
                    show_error(f"Invalid quantity for {item_row_s_pg5['item_name']}.")
                    items_to_submit_list_proc_pg5 = []
                    break

            if not has_items_with_qty_pg5 and not items_to_submit_list_proc_pg5:
                st.info("No quantities specified for issuance.")
            elif items_to_submit_list_proc_pg5:
                with st.spinner(f"Processing indent {selected_mrn_pg5}..."):
                    success_p_pg5, message_p_pg5 = indent_service.process_indent_issuance(
                        db_engine,
                        selected_indent_id_pg5,
                        items_to_submit_list_proc_pg5,
                        get_current_user_id().strip(),
                        selected_mrn_pg5,
                    )
                if success_p_pg5:
                    show_success(
                        f"{message_p_pg5} Use the sidebar to create a purchase order."
                    )
                    st.session_state.pg5_process_indent_selected_tuple = (
                        pg5_placeholder_indent_process_tuple
                    )
                    st.session_state.pg5_process_indent_items_df = pd.DataFrame()
                    st.session_state.pg5_process_indent_issue_quantities_defaults = {}
                    indent_service.get_indents_for_processing.clear()
                    st.rerun()
                else:
                    show_error(f"Processing Failed: {message_p_pg5}")


st.radio(
    "Indent Actions:",
    options=INDENT_SECTION_DISPLAY_NAMES_PG5,
    index=INDENT_SECTION_KEYS_PG5.index(st.session_state.pg5_active_indent_section),
    key="pg5_indent_section_radio_key",
    on_change=set_active_indent_section_callback_pg5,
    horizontal=True,
)
st.divider()

# --- CREATE INDENT SECTION ---
if st.session_state.pg5_active_indent_section == "create":
    st.subheader(INDENT_SECTIONS_PG5["create"])
    if st.session_state.get(PG5_CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY, False):
        st.session_state[PG5_CREATE_INDENT_DEPT_SESS_KEY] = ""
        st.session_state[PG5_CREATE_INDENT_REQ_BY_SESS_KEY] = ""
        st.session_state[PG5_CREATE_INDENT_DATE_REQ_SESS_KEY] = date.today() + timedelta(days=1)
        st.session_state[PG5_CREATE_INDENT_NOTES_SESS_KEY] = ""
        st.session_state.pg5_selected_department_for_create_indent = None
        st.session_state[PG5_CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY] = False

    if st.session_state.get("pg5_last_created_mrn_for_print"):
        # ... (Success message and PDF/WhatsApp section - use pg5_ prefixed session state keys) ...
        # This section seems okay, just ensure all st.session_state access uses pg5_ prefixes if they were changed.
        mrn_to_print_pg5 = st.session_state.pg5_last_created_mrn_for_print  # Use pg5_ variable
        show_success(
            f"Indent **{mrn_to_print_pg5}** was created successfully! Use the sidebar to create a purchase order."
        )
        if st.session_state.get("pg5_last_submitted_indent_details"):
            summary_header_pg5 = st.session_state.pg5_last_submitted_indent_details["header"]
            summary_items_pg5 = st.session_state.pg5_last_submitted_indent_details["items"]
            st.write("Submitted Items:")
            summary_df_data_pg5 = [
                {
                    "Item Name": itm.get("item_name", "N/A"),
                    "Qty": itm.get("requested_qty", 0),
                    "Unit": itm.get("item_unit", "N/A"),
                    "Notes": itm.get("item_notes", ""),
                }
                for itm in summary_items_pg5
            ]
            summary_df_pg5 = pd.DataFrame(summary_df_data_pg5)
            st.dataframe(
                summary_df_pg5,
                hide_index=True,
                use_container_width=True,
                column_config={"Qty": st.column_config.NumberColumn(format="%.2f")},
            )

        pdf_dl_col_pg5, whatsapp_col_pg5 = st.columns(2)
        with pdf_dl_col_pg5:
            pdf_btn_placeholder_pg5 = st.empty()
            if st.session_state.get("pg5_pdf_bytes_for_download") and st.session_state.get(
                "pg5_pdf_filename_for_download", ""
            ).endswith(f"{mrn_to_print_pg5}.pdf"):
                pdf_btn_placeholder_pg5.download_button(
                    label=f"📥 Download PDF ({mrn_to_print_pg5})",
                    data=st.session_state.pg5_pdf_bytes_for_download,
                    file_name=st.session_state.pg5_pdf_filename_for_download,
                    mime="application/pdf",
                    key=f"pg5_dl_new_indent_{mrn_to_print_pg5.replace('-', '_')}",
                    on_click=lambda: st.session_state.update(
                        {
                            "pg5_pdf_bytes_for_download": None,
                            "pg5_pdf_filename_for_download": None,
                        }
                    ),
                    use_container_width=True,
                )
            else:
                if pdf_btn_placeholder_pg5.button(
                    f"📄 Generate PDF ({mrn_to_print_pg5})",
                    key=f"pg5_print_new_indent_btn_{mrn_to_print_pg5.replace('-', '_')}",
                    use_container_width=True,
                ):
                    with st.spinner(f"Generating PDF for {mrn_to_print_pg5}..."):
                        hd_pg5, itms_pg5 = indent_service.get_indent_details_for_pdf(
                            db_engine, mrn_to_print_pg5
                        )
                        if hd_pg5 and itms_pg5 is not None:
                            pdf_b_pg5 = generate_indent_pdf(hd_pg5, itms_pg5)
                            if pdf_b_pg5:
                                st.session_state.pg5_pdf_bytes_for_download = pdf_b_pg5
                                st.session_state.pg5_pdf_filename_for_download = (
                                    f"Indent_{mrn_to_print_pg5}.pdf"
                                )
                                st.rerun()
                        else:
                            show_error(f"Could not fetch details for PDF: {mrn_to_print_pg5}.")
        with whatsapp_col_pg5:
            if st.session_state.get("pg5_last_submitted_indent_details"):
                header_pg5 = st.session_state.pg5_last_submitted_indent_details["header"]
                wa_text_pg5 = (
                    f"Indent Submitted:\nMRN: {header_pg5.get('mrn', 'N/A')}\nDept: {header_pg5.get('department', 'N/A')}\n"
                    f"By: {header_pg5.get('requested_by', 'N/A')}\nReqd Date: {header_pg5.get('date_required', 'N/A')}\n"
                    f"Items: {len(st.session_state.pg5_last_submitted_indent_details['items'])}"
                )
                encoded_text_pg5 = urllib.parse.quote_plus(wa_text_pg5)
                st.link_button(
                    "✅ Prepare WhatsApp Message",
                    f"https://wa.me/?text={encoded_text_pg5}",
                    use_container_width=True,
                    help="Opens WhatsApp.",
                )
        st.divider()
        if st.button(
            "➕ Create Another Indent",
            key="pg5_create_another_indent_btn",
            use_container_width=True,
            type="primary",
        ):
            st.session_state.pg5_last_created_mrn_for_print = None
            st.session_state.pg5_last_submitted_indent_details = None
            if "pg5_pdf_bytes_for_download" in st.session_state:
                del st.session_state.pg5_pdf_bytes_for_download
            if "pg5_pdf_filename_for_download" in st.session_state:
                del st.session_state.pg5_pdf_filename_for_download
            st.session_state.pg5_create_indent_rows = [
                {
                    "id": 0,
                    "item_id": None,
                    "requested_qty": 1.0,
                    "notes": "",
                    "last_ordered": None,
                    "median_qty": None,
                    "category": None,
                    "sub_category": None,
                    "current_stock": None,
                    "unit": None,
                }
            ]
            st.session_state.pg5_create_indent_next_id = 1
            st.session_state[PG5_CREATE_INDENT_HEADER_RESET_SIGNAL_SESS_KEY] = True
            st.rerun()
    else:
        head_col1_pg5, head_col2_pg5 = st.columns(2)
        with head_col1_pg5:
            pg5_dept_widget_key = "pg5_create_indent_dept_widget"
            current_dept_val_pg5 = st.session_state.get(PG5_CREATE_INDENT_DEPT_SESS_KEY, "")
            dept_options_pg5 = [""] + distinct_departments_pg5
            dept_idx_pg5 = (
                dept_options_pg5.index(current_dept_val_pg5)
                if current_dept_val_pg5 in dept_options_pg5
                else 0
            )

            selected_dept_pg5 = st.selectbox(
                "Requesting Department*",
                options=dept_options_pg5,
                index=dept_idx_pg5,
                format_func=lambda x: "Select Department..." if x == "" else x,
                key=pg5_dept_widget_key,  # Widget specific key
                on_change=lambda: st.session_state.update(
                    {
                        PG5_CREATE_INDENT_DEPT_SESS_KEY: st.session_state[pg5_dept_widget_key],
                        "pg5_selected_department_for_create_indent": (
                            st.session_state[pg5_dept_widget_key]
                            if st.session_state[pg5_dept_widget_key]
                            else None
                        ),
                    }
                ),
            )
            # Ensure session state for department value is updated if selectbox changes it via key directly
            if st.session_state.get(PG5_CREATE_INDENT_DEPT_SESS_KEY) != selected_dept_pg5:
                st.session_state[PG5_CREATE_INDENT_DEPT_SESS_KEY] = selected_dept_pg5
                st.session_state.pg5_selected_department_for_create_indent = (
                    selected_dept_pg5 if selected_dept_pg5 else None
                )

            pg5_req_by_widget_key = "pg5_create_indent_req_by_widget"
            st.session_state[PG5_CREATE_INDENT_REQ_BY_SESS_KEY] = st.text_input(
                "Requested By (Your Name/ID)*",
                value=st.session_state.get(PG5_CREATE_INDENT_REQ_BY_SESS_KEY, ""),
                key=pg5_req_by_widget_key,
            )
        with head_col2_pg5:
            pg5_date_req_widget_key = "pg5_create_indent_date_req_widget"
            st.session_state[PG5_CREATE_INDENT_DATE_REQ_SESS_KEY] = st.date_input(
                "Date Required By*",
                value=st.session_state.get(
                    PG5_CREATE_INDENT_DATE_REQ_SESS_KEY,
                    date.today() + timedelta(days=1),
                ),
                min_value=date.today(),
                key=pg5_date_req_widget_key,
            )
            st.text_input(
                "Initial Status",
                value=STATUS_SUBMITTED,
                disabled=True,
                key="pg5_create_indent_status_disp",
            )

        pg5_header_notes_widget_key = "pg5_create_indent_header_notes_widget"
        st.session_state[PG5_CREATE_INDENT_NOTES_SESS_KEY] = st.text_area(
            "Overall Indent Notes (Optional)",
            value=st.session_state.get(PG5_CREATE_INDENT_NOTES_SESS_KEY, ""),
            key=pg5_header_notes_widget_key,
            placeholder="General notes...",
        )
        st.divider()
        st.subheader("🛍️ Requested Items")

        current_dept_for_suggestions_pg5 = st.session_state.get(
            "pg5_selected_department_for_create_indent"
        )
        if current_dept_for_suggestions_pg5:
            # ... (Suggested items logic - use pg5_ prefixed vars and keys) ...
            suggested_items_pg5 = item_service.get_suggested_items_for_department(
                db_engine, current_dept_for_suggestions_pg5, top_n=5
            )
            if suggested_items_pg5:
                st.caption("✨ Quick Add (based on recent requests from this department):")
                items_in_current_indent_ids_pg5 = {
                    row.get("item_id")
                    for row in st.session_state.pg5_create_indent_rows
                    if row.get("item_id")
                }
                valid_suggestions_pg5 = [
                    sugg
                    for sugg in suggested_items_pg5
                    if sugg["item_id"] not in items_in_current_indent_ids_pg5
                ]
                if valid_suggestions_pg5:
                    sugg_cols_pg5 = st.columns(min(len(valid_suggestions_pg5), 5))
                    for i_sugg_pg5, sugg_item_pg5 in enumerate(valid_suggestions_pg5[:5]):
                        sugg_cols_pg5[i_sugg_pg5].button(
                            f"+ {sugg_item_pg5['item_name']}",
                            key=f"pg5_suggest_item_{sugg_item_pg5['item_id']}",
                            on_click=add_suggested_item_callback_pg5,
                            args=(
                                sugg_item_pg5["item_id"],
                                sugg_item_pg5["item_name"],
                                sugg_item_pg5["unit"],
                            ),
                            help=f"Add {sugg_item_pg5['item_name']} ({sugg_item_pg5['unit']})",
                            use_container_width=True,
                        )
                elif items_in_current_indent_ids_pg5 and any(
                    row.get("item_id") for row in st.session_state.pg5_create_indent_rows
                ):
                    st.caption(
                        "Frequent items are already in your list or no other frequent items found."
                    )
                else:
                    st.caption("No frequent items found for this department recently.")
                st.caption("")

        # Item options dictionary construction using constants
        item_options_dict_pg5: Dict[str, Optional[int]] = {
            pg5_placeholder_select_item_tuple[0]: pg5_placeholder_select_item_tuple[1]
        }
        if st.session_state.get("pg5_selected_department_for_create_indent"):
            selected_dept_for_filter_pg5 = (
                st.session_state.pg5_selected_department_for_create_indent
            )
            if not all_active_items_df_pg5.empty:
                try:
                    available_items_df_pg5 = all_active_items_df_pg5[
                        all_active_items_df_pg5["permitted_departments"]
                        .fillna("")
                        .astype(str)
                        .str.lower()
                        .apply(
                            lambda depts_str: (
                                selected_dept_for_filter_pg5.strip().lower()
                                in [d.strip().lower() for d in depts_str.split(",")]
                                if depts_str
                                else False
                            )
                        )
                    ].copy()
                    if available_items_df_pg5.empty:
                        item_options_dict_pg5.update({PLACEHOLDER_NO_ITEMS_FOR_DEPARTMENT: -2})
                    else:
                        item_options_dict_pg5.update(
                            {
                                build_item_choice_label(r): r["item_id"]
                                for _, r in available_items_df_pg5.sort_values("name").iterrows()
                            }
                        )
                except Exception as e_item_filter_pg5:
                    print(
                        f"ERROR [5_Indents.item_filtering_create]: Error filtering items: {e_item_filter_pg5}"
                    )
                    item_options_dict_pg5.update({PLACEHOLDER_ERROR_LOADING_ITEMS: -3})
            else:
                item_options_dict_pg5.update({PLACEHOLDER_NO_ITEMS_AVAILABLE: -4})
        else:
            item_options_dict_pg5 = {PLACEHOLDER_SELECT_DEPARTMENT_FIRST: -5}

        h_cols_pg5 = st.columns([4, 2, 3, 1])
        h_cols_pg5[0].markdown("**Item**")
        h_cols_pg5[1].markdown("**Req. Qty**")
        h_cols_pg5[2].markdown("**Notes**")
        h_cols_pg5[3].markdown("**Action**")
        st.divider()

        # Item rows display using pg5_ prefixed session state and keys
        for i_loop_item_rows_pg5, row_state_pg5 in enumerate(
            st.session_state.pg5_create_indent_rows
        ):
            # ... (Item row rendering logic - use pg5_ prefixed vars and unique keys based on row_id_pg5) ...
            # This section is complex, ensure all st.session_state.pg5_create_indent_rows access and widget keys are pg5_ prefixed and unique.
            # Example for one item row input (apply similar pattern for others):
            # item_selectbox_key_row_pg5 = f"pg5_disp_item_select_{row_id_pg5}"
            # default_item_display_name_row_pg5 = pg5_placeholder_select_item_tuple[0]
            # ...
            # with item_cols_display_pg5[0]:
            #     st.selectbox(f"Item (Row {i_loop_item_rows_pg5+1})", ..., key=item_selectbox_key_row_pg5, ...)
            # ...
            row_id_pg5 = row_state_pg5["id"]
            item_cols_display_pg5 = st.columns([4, 2, 3, 1])
            item_selectbox_key_row_pg5 = f"pg5_disp_item_select_{row_id_pg5}"
            default_item_display_name_row_pg5 = pg5_placeholder_select_item_tuple[0]
            if row_state_pg5.get("item_id") is not None:
                default_item_display_name_row_pg5 = next(
                    (
                        name
                        for name, id_val in item_options_dict_pg5.items()
                        if id_val == row_state_pg5["item_id"]
                    ),
                    default_item_display_name_row_pg5,
                )
            try:
                current_item_idx_row_pg5 = list(item_options_dict_pg5.keys()).index(
                    default_item_display_name_row_pg5
                )
            except ValueError:
                current_item_idx_row_pg5 = 0

            with item_cols_display_pg5[0]:
                st.selectbox(
                    f"Item_R{i_loop_item_rows_pg5+1}",
                    options=list(item_options_dict_pg5.keys()),
                    index=current_item_idx_row_pg5,
                    key=item_selectbox_key_row_pg5,
                    label_visibility="collapsed",
                    on_change=update_row_item_details_callback_pg5,
                    args=(
                        i_loop_item_rows_pg5,
                        item_selectbox_key_row_pg5,
                        item_options_dict_pg5,
                    ),
                )
                # ... (Display item details caption) ...
                current_row_data_pg5 = st.session_state.pg5_create_indent_rows[i_loop_item_rows_pg5]
                if (
                    current_row_data_pg5.get("item_id")
                    and current_row_data_pg5.get("item_id") != -1
                ):
                    info_parts_pg5 = []
                    if current_row_data_pg5.get("category"):
                        info_parts_pg5.append(f"Cat: {current_row_data_pg5['category']}")
                    # ... (other info parts) ...
                    if current_row_data_pg5.get("current_stock") is not None:
                        unit_disp_pg5 = current_row_data_pg5.get("unit", "")
                        info_parts_pg5.append(
                            f"Stock: {float(current_row_data_pg5['current_stock']):.2f} {unit_disp_pg5}"
                        )
                    if current_row_data_pg5.get("last_ordered"):
                        info_parts_pg5.append(f"Last ord: {current_row_data_pg5['last_ordered']}")
                    if info_parts_pg5:
                        st.caption(" | ".join(info_parts_pg5))

            with item_cols_display_pg5[1]:
                qty_key_for_row_disp_pg5 = f"pg5_disp_item_qty_{row_id_pg5}"
                current_qty_for_row_disp_pg5 = float(
                    st.session_state.pg5_create_indent_rows[i_loop_item_rows_pg5].get(
                        "requested_qty", 1.0
                    )
                )

                def on_qty_change_callback_pg5(idx_pg5, key_arg_pg5):
                    st.session_state.pg5_create_indent_rows[idx_pg5][
                        "requested_qty"
                    ] = st.session_state[key_arg_pg5]

                st.number_input(
                    f"Qty_R{i_loop_item_rows_pg5+1}",
                    value=current_qty_for_row_disp_pg5,
                    min_value=0.01,
                    step=0.1,
                    format="%.2f",
                    key=qty_key_for_row_disp_pg5,
                    label_visibility="collapsed",
                    on_change=on_qty_change_callback_pg5,
                    args=(i_loop_item_rows_pg5, qty_key_for_row_disp_pg5),
                )
                # ... (Median qty warning/info) ...
                median_qty_row_disp_pg5 = st.session_state.pg5_create_indent_rows[
                    i_loop_item_rows_pg5
                ].get("median_qty")
                actual_qty_row_disp_pg5 = st.session_state.pg5_create_indent_rows[
                    i_loop_item_rows_pg5
                ].get("requested_qty", 0.0)
                if (
                    median_qty_row_disp_pg5
                    and median_qty_row_disp_pg5 > 0
                    and actual_qty_row_disp_pg5 > 0
                ):
                    if actual_qty_row_disp_pg5 > median_qty_row_disp_pg5 * 3:
                        st.warning(f"High! (Avg:~{median_qty_row_disp_pg5:.1f})", icon="❗")
                    elif actual_qty_row_disp_pg5 < median_qty_row_disp_pg5 / 3:
                        st.info(f"Low (Avg:~{median_qty_row_disp_pg5:.1f})", icon="ℹ️")

            with item_cols_display_pg5[2]:
                notes_key_for_row_disp_pg5 = f"pg5_disp_item_notes_{row_id_pg5}"

                def on_notes_change_callback_pg5(idx_pg5, key_arg_pg5):
                    st.session_state.pg5_create_indent_rows[idx_pg5]["notes"] = st.session_state[
                        key_arg_pg5
                    ]

                st.text_input(
                    f"Notes_R{i_loop_item_rows_pg5+1}",
                    value=st.session_state.pg5_create_indent_rows[i_loop_item_rows_pg5].get(
                        "notes", ""
                    ),
                    key=notes_key_for_row_disp_pg5,
                    label_visibility="collapsed",
                    placeholder="Optional",
                    on_change=on_notes_change_callback_pg5,
                    args=(i_loop_item_rows_pg5, notes_key_for_row_disp_pg5),
                )
            with item_cols_display_pg5[3]:
                if len(st.session_state.pg5_create_indent_rows) > 1:
                    item_cols_display_pg5[3].button(
                        "➖",
                        key=f"pg5_disp_remove_row_{row_id_pg5}",
                        on_click=remove_indent_row_callback_pg5,
                        args=(row_id_pg5,),
                        help="Remove line",
                    )
                else:
                    item_cols_display_pg5[3].write("")
            st.caption("")

        add_lines_cols_pg5 = st.columns([2, 1.2])
        with add_lines_cols_pg5[0]:
            st.number_input(
                "Lines to add:",
                value=st.session_state.pg5_num_lines_to_add_value,
                min_value=1,
                max_value=10,
                step=1,
                key="pg5_create_indent_num_lines_input",
                help="Specify how many new blank item lines to add.",
            )
        with add_lines_cols_pg5[1]:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            st.button(
                "➕ Add Lines",
                on_click=add_multiple_indent_lines_callback_pg5,
                key="pg5_add_multi_lines_btn",
                use_container_width=True,
            )
        st.divider()
        create_indent_submission_form_pg5(item_options_dict_pg5)

# --- VIEW INDENTS SECTION ---
elif st.session_state.pg5_active_indent_section == "view":
    st.subheader(INDENT_SECTIONS_PG5["view"])
    view_filter_cols_pg5 = st.columns([1, 1, 1, 2])
    with view_filter_cols_pg5[0]:
        mrn_filter_pg5 = st.text_input(
            "Search by MRN:",
            key="pg5_view_indent_mrn_filter",
            placeholder="e.g., MRN-...",
        )
    with view_filter_cols_pg5[1]:
        dept_options_view_pg5 = [FILTER_ALL_DEPARTMENTS] + distinct_departments_pg5
        dept_filter_val_pg5 = st.selectbox(
            "Filter by Department:",
            options=dept_options_view_pg5,
            key="pg5_view_indent_dept_filter",
        )
    with view_filter_cols_pg5[2]:
        status_options_view_pg5 = [FILTER_ALL_STATUSES] + ALL_INDENT_STATUSES
        status_filter_val_pg5 = st.selectbox(
            "Filter by Status:",
            options=status_options_view_pg5,
            key="pg5_view_indent_status_filter",
        )
    with view_filter_cols_pg5[3]:
        date_col1_pg5, date_col2_pg5 = st.columns(2)
        with date_col1_pg5:
            date_start_filter_val_pg5 = st.date_input(
                "Submitted From:", value=None, key="pg5_view_indent_date_start"
            )
        with date_col2_pg5:
            date_end_filter_val_pg5 = st.date_input(
                "Submitted To:", value=None, key="pg5_view_indent_date_end"
            )

    date_start_str_arg_pg5 = (
        date_start_filter_val_pg5.strftime("%Y-%m-%d") if date_start_filter_val_pg5 else None
    )
    date_end_str_arg_pg5 = (
        date_end_filter_val_pg5.strftime("%Y-%m-%d") if date_end_filter_val_pg5 else None
    )
    dept_arg_pg5 = dept_filter_val_pg5 if dept_filter_val_pg5 != FILTER_ALL_DEPARTMENTS else None
    status_arg_pg5 = status_filter_val_pg5 if status_filter_val_pg5 != FILTER_ALL_STATUSES else None
    mrn_arg_pg5 = mrn_filter_pg5.strip() if mrn_filter_pg5 else None

    indents_df_pg5 = indent_service.get_indents(
        db_engine,
        mrn_filter=mrn_arg_pg5,
        dept_filter=dept_arg_pg5,
        status_filter=status_arg_pg5,
        date_start_str=date_start_str_arg_pg5,
        date_end_str=date_end_str_arg_pg5,
    )
    st.divider()
    if indents_df_pg5.empty:
        st.info("ℹ️ No indents found matching your criteria.")
    else:
        # ... (Display DataFrame - use pg5_ prefixed vars) ...
        # ... (PDF Download Section - use pg5_ prefixed vars, PLACEHOLDER_SELECT_MRN_PDF, and unique keys) ...
        show_success(f"Found {len(indents_df_pg5)} indent(s).")
        # ... (DataFrame display logic, ensure column names match what get_indents returns) ...
        # (The display logic was okay, just needs variable renaming if any done above)
        display_df_pg5 = indents_df_pg5.copy()
        date_cols_for_view_pg5 = [
            "date_required",
            "date_submitted",
            "date_processed",
            "created_at",
            "updated_at",
        ]
        for col_v_pg5 in date_cols_for_view_pg5:
            if col_v_pg5 in display_df_pg5.columns:
                display_df_pg5[col_v_pg5] = (
                    pd.to_datetime(display_df_pg5[col_v_pg5], errors="coerce").dt.strftime(
                        "%Y-%m-%d %H:%M"
                    )
                    if col_v_pg5 in ["date_submitted", "created_at", "updated_at", "date_processed"]
                    else pd.to_datetime(display_df_pg5[col_v_pg5], errors="coerce").dt.strftime(
                        "%Y-%m-%d"
                    )
                )

        if "status" in display_df_pg5.columns:
            display_df_pg5["status_display"] = display_df_pg5["status"].apply(format_status_badge)

        cols_to_display_order_pg5 = [
            "mrn",
            "date_submitted",
            "department",
            "requested_by",
            "date_required",
            "status_display",
            "item_count",
            "indent_notes",
            "processed_by_user_id",
            "date_processed",
        ]
        final_cols_for_df_pg5 = [
            col for col in cols_to_display_order_pg5 if col in display_df_pg5.columns
        ]

        st.dataframe(
            display_df_pg5[final_cols_for_df_pg5],
            use_container_width=True,
            hide_index=True,
            column_config={  # ... (column configs as before) ...
                "indent_id": None,
                "status": None,
                "mrn": st.column_config.TextColumn("MRN"),
                "date_submitted": st.column_config.TextColumn("Submitted On"),
                "department": "Department",
                "requested_by": "Requestor",
                "date_required": st.column_config.TextColumn("Required By"),
                "status_display": st.column_config.TextColumn("Status"),
                "item_count": st.column_config.NumberColumn("No. of Items", format="%d"),
                "indent_notes": st.column_config.TextColumn("Indent Notes"),
                "processed_by_user_id": st.column_config.TextColumn("Processed By"),
                "date_processed": st.column_config.TextColumn("Processed On"),
            },
        )

        st.divider()
        st.subheader("📄 Download Indent as PDF")
        st.caption("Select an MRN from the list above (if any) to generate its PDF.")
        if not indents_df_pg5.empty:
            available_mrns_for_pdf_pg5 = [PLACEHOLDER_SELECT_MRN_PDF] + sorted(
                indents_df_pg5["mrn"].unique().tolist()
            )
            selected_mrn_for_pdf_pg5_key = "pg5_pdf_mrn_select_key"  # Unique key

            current_pdf_selection_idx_pg5 = 0
            # Try to keep selection if PDF was just generated for it
            if st.session_state.get("pg5_pdf_filename_for_download"):
                try:
                    mrn_from_filename_pg5 = st.session_state.pg5_pdf_filename_for_download.split(
                        "_", 1
                    )[1].rsplit(".", 1)[0]
                    if mrn_from_filename_pg5 in available_mrns_for_pdf_pg5:
                        current_pdf_selection_idx_pg5 = available_mrns_for_pdf_pg5.index(
                            mrn_from_filename_pg5
                        )
                except IndexError:
                    pass

            selected_mrn_for_pdf_pg5 = st.selectbox(
                "Choose MRN:",
                options=available_mrns_for_pdf_pg5,
                index=current_pdf_selection_idx_pg5,
                key=selected_mrn_for_pdf_pg5_key,
            )

            if selected_mrn_for_pdf_pg5 != PLACEHOLDER_SELECT_MRN_PDF:
                if not (
                    st.session_state.get("pg5_pdf_bytes_for_download")
                    and st.session_state.get("pg5_pdf_filename_for_download", "").endswith(
                        f"{selected_mrn_for_pdf_pg5}.pdf"
                    )
                ):
                    if st.button(
                        "⚙️ Generate PDF",
                        key=f"pg5_generate_pdf_btn_{selected_mrn_for_pdf_pg5.replace('-', '_')}",
                    ):
                        with st.spinner(f"Generating PDF for {selected_mrn_for_pdf_pg5}..."):
                            (
                                header_details_pg5,
                                items_details_pg5,
                            ) = indent_service.get_indent_details_for_pdf(
                                db_engine, selected_mrn_for_pdf_pg5
                            )
                            if header_details_pg5 and items_details_pg5 is not None:
                                pdf_bytes_pg5 = generate_indent_pdf(
                                    header_details_pg5, items_details_pg5
                                )
                                if pdf_bytes_pg5:
                                    st.session_state.pg5_pdf_bytes_for_download = pdf_bytes_pg5
                                    st.session_state.pg5_pdf_filename_for_download = (
                                        f"Indent_{selected_mrn_for_pdf_pg5}.pdf"
                                    )
                                    st.rerun()
                            else:
                                show_error(
                                    f"Could not fetch details to generate PDF for MRN {selected_mrn_for_pdf_pg5}."
                                )

                if st.session_state.get("pg5_pdf_bytes_for_download") and st.session_state.get(
                    "pg5_pdf_filename_for_download", ""
                ).endswith(f"{selected_mrn_for_pdf_pg5}.pdf"):
                    st.download_button(
                        label=f"📥 Download PDF for {selected_mrn_for_pdf_pg5}",
                        data=st.session_state.pg5_pdf_bytes_for_download,
                        file_name=st.session_state.pg5_pdf_filename_for_download,
                        mime="application/pdf",
                        key=f"pg5_final_dl_btn_{selected_mrn_for_pdf_pg5.replace('-', '_')}",
                    )


# --- PROCESS INDENT SECTION ---
elif st.session_state.pg5_active_indent_section == "process":
    st.subheader(INDENT_SECTIONS_PG5["process"])
    indents_to_process_df_pg5 = indent_service.get_indents_for_processing(db_engine)

    indent_options_list_pg5 = [pg5_placeholder_indent_process_tuple]
    if not indents_to_process_df_pg5.empty:
        for _, row_p_pg5 in indents_to_process_df_pg5.iterrows():
            date_submitted_str_pg5 = (
                pd.to_datetime(row_p_pg5["date_submitted"]).strftime("%d-%b-%y")
                if pd.notna(row_p_pg5.get("date_submitted"))
                else "N/A"
            )
            display_name_pg5 = (
                f"{row_p_pg5['mrn']} ({row_p_pg5['department']}) - Sub: {date_submitted_str_pg5}"
            )
            indent_options_list_pg5.append(
                (display_name_pg5, row_p_pg5["indent_id"], row_p_pg5["mrn"])
            )

    current_selected_tuple_proc_pg5 = st.session_state.get(
        "pg5_process_indent_selected_tuple", pg5_placeholder_indent_process_tuple
    )
    current_selected_index_proc_pg5 = 0
    for i_proc_pg5, option_tuple_p_pg5 in enumerate(indent_options_list_pg5):
        if option_tuple_p_pg5[1] == current_selected_tuple_proc_pg5[1]:
            current_selected_index_proc_pg5 = i_proc_pg5
            break

    selected_tuple_widget_pg5 = st.selectbox(
        "Select Indent (MRN) to Process:",
        options=indent_options_list_pg5,
        index=current_selected_index_proc_pg5,
        format_func=lambda x_opt_pg5: x_opt_pg5[0],
        key="pg5_process_indent_select_widget",
        on_change=on_process_indent_select_change_pg5,
    )
    if st.session_state.pg5_process_indent_selected_tuple != selected_tuple_widget_pg5:
        st.session_state.pg5_process_indent_selected_tuple = selected_tuple_widget_pg5
        st.rerun()  # Rerun to load items for newly selected indent

    selected_indent_id_pg5 = st.session_state.pg5_process_indent_selected_tuple[1]
    selected_mrn_pg5 = st.session_state.pg5_process_indent_selected_tuple[2]
    st.divider()

    if selected_indent_id_pg5:
        # ... (Process Indent Display & Form logic - use pg5_ prefixed vars and unique keys) ...
        # This section is also complex and needs careful application of pg5_ prefixes and unique keys.
        # The fix for StreamlitValueAboveMaxError should already be in effect here from previous steps.
        # Key area: ensure the form key and widget keys within the loop are unique.
        # e.g., form key: f"pg5_process_indent_form_{selected_indent_id_pg5}"
        # e.g., issue_qty_key: f"pg5_issue_qty_input_{indent_item_id_proc}"
        st.markdown(f"#### Processing Indent: **{selected_mrn_pg5}**")

        refetch_items_proc_pg5 = True
        if (
            not st.session_state.pg5_process_indent_items_df.empty
            and "indent_id_for_check" in st.session_state.pg5_process_indent_items_df.columns
            and not st.session_state.pg5_process_indent_items_df.empty
            and st.session_state.pg5_process_indent_items_df.iloc[0]["indent_id_for_check"]
            == selected_indent_id_pg5
        ):
            refetch_items_proc_pg5 = False

        if refetch_items_proc_pg5:
            fetched_items_df_pg5 = indent_service.get_indent_items_for_display(
                db_engine, selected_indent_id_pg5
            )
            if not fetched_items_df_pg5.empty:
                fetched_items_df_pg5["indent_id_for_check"] = selected_indent_id_pg5
            st.session_state.pg5_process_indent_items_df = fetched_items_df_pg5
            st.session_state.pg5_process_indent_issue_quantities_defaults = {
                row_item_df_pg5["indent_item_id"]: 0.0
                for _, row_item_df_pg5 in fetched_items_df_pg5.iterrows()
            }

        items_df_for_processing_disp_pg5 = st.session_state.pg5_process_indent_items_df

        if not items_df_for_processing_disp_pg5.empty:
            header_cols_proc_pg5 = st.columns([3, 1, 1, 1, 1.5, 1.5, 1.5, 2])
            headers_text_list_pg5 = [
                "Item (Unit)",
                "Req.",
                "Issued",
                "Pend.",
                "Stock",
                "Status",
                "Issue Now*",
                "Notes",
            ]
            for col_header_pg5, header_txt_pg5 in zip(header_cols_proc_pg5, headers_text_list_pg5):
                col_header_pg5.markdown(f"**{header_txt_pg5}**")
            process_indent_form_pg5(
                selected_indent_id_pg5,
                selected_mrn_pg5,
                items_df_for_processing_disp_pg5,
            )

            # Other Actions (Mark as Completed / Cancel Indent) - Placed correctly outside the form
            st.markdown("---")
            st.markdown("##### Other Actions for this Indent:")
            action_cols_proc_pg5 = st.columns(2)
            with action_cols_proc_pg5[0]:
                if st.button(
                    "✅ Mark Indent as Completed",
                    key=f"pg5_mark_completed_{selected_indent_id_pg5}",
                    use_container_width=True,
                ):
                    # ... (logic using pg5_process_indent_user_id)
                    user_id_for_action_pg5 = get_current_user_id()
                    # ... (call indent_service.mark_indent_completed) ...
                    with st.spinner(f"Marking {selected_mrn_pg5} as completed..."):
                        s_mark, m_mark = indent_service.mark_indent_completed(
                            db_engine,
                            selected_indent_id_pg5,
                            user_id_for_action_pg5,
                            selected_mrn_pg5,
                        )
                        if s_mark:
                            show_success(m_mark)
                            st.session_state.pg5_process_indent_selected_tuple = (
                                pg5_placeholder_indent_process_tuple
                            )
                            st.rerun()  # Simplified reset
                        else:
                            show_error(f"Failed: {m_mark}")

            with action_cols_proc_pg5[1]:
                if st.button(
                    "❌ Cancel Entire Indent",
                    key=f"pg5_cancel_indent_{selected_indent_id_pg5}",
                    type="secondary",
                    use_container_width=True,
                ):
                    # ... (logic using pg5_process_indent_user_id) ...
                    user_id_for_action_pg5 = get_current_user_id()
                    # ... (call indent_service.cancel_entire_indent) ...
                    with st.spinner(f"Cancelling {selected_mrn_pg5}..."):
                        s_cancel, m_cancel = indent_service.cancel_entire_indent(
                            db_engine,
                            selected_indent_id_pg5,
                            user_id_for_action_pg5,
                            selected_mrn_pg5,
                        )
                        if s_cancel:
                            show_success(m_cancel)
                            st.session_state.pg5_process_indent_selected_tuple = (
                                pg5_placeholder_indent_process_tuple
                            )
                            st.rerun()  # Simplified reset
                        else:
                            show_error(f"Failed: {m_cancel}")

        elif selected_indent_id_pg5:
            st.info(
                f"No items found for Indent MRN {selected_mrn_pg5} to process, or it's already processed/cancelled."
            )
    else:
        st.info("Select an indent from the dropdown above to start processing.")
