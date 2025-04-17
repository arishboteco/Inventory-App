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
        get_all_items_with_stock,
        generate_mrn,
        create_indent,
        get_indents,
        ALL_INDENT_STATUSES
    )
except ImportError as e:
    st.error(f"Import Error from item_manager_app.py: {e}")
    st.stop()
except Exception as e:
    st.error(f"Unexpected error: {e}")
    st.stop()

# --- Constants ---
DEPARTMENTS = ["Kitchen", "Bar", "Housekeeping", "Admin", "Maintenance", "Service"]
STATE_PREFIX = "indent_loop_v1_"
KEY_DEPT = f"{STATE_PREFIX}dept"
KEY_REQ_BY = f"{STATE_PREFIX}req_by"
KEY_REQ_DATE = f"{STATE_PREFIX}req_date"
KEY_NOTES = f"{STATE_PREFIX}notes"
KEY_ITEM_LIST = f"{STATE_PREFIX}item_list"
KEY_NEXT_ITEM_ROW_KEY = f"{STATE_PREFIX}next_row_key"
KEY_ITEM_OPTIONS = f"{STATE_PREFIX}item_options"
KEY_CURRENT_DEPT = f"{STATE_PREFIX}current_dept"
KEY_VIEW_MRN = f"{STATE_PREFIX}view_mrn"
KEY_VIEW_DEPT = f"{STATE_PREFIX}view_dept"
KEY_VIEW_STATUS = f"{STATE_PREFIX}view_status"
KEY_VIEW_DATE = f"{STATE_PREFIX}view_date"

# --- Initialize Session State ---
def init_state():
    if KEY_ITEM_LIST not in st.session_state:
        st.session_state[KEY_ITEM_LIST] = [{"row_key": 0}]
        st.session_state[f"item_select_0"] = None
        st.session_state[f"item_qty_0"] = 1.0
    if KEY_NEXT_ITEM_ROW_KEY not in st.session_state: st.session_state[KEY_NEXT_ITEM_ROW_KEY] = 1
    if KEY_ITEM_OPTIONS not in st.session_state: st.session_state[KEY_ITEM_OPTIONS] = []
    if KEY_CURRENT_DEPT not in st.session_state: st.session_state[KEY_CURRENT_DEPT] = None
    if KEY_DEPT not in st.session_state: st.session_state[KEY_DEPT] = None
    if KEY_REQ_BY not in st.session_state: st.session_state[KEY_REQ_BY] = ""
    if KEY_REQ_DATE not in st.session_state: st.session_state[KEY_REQ_DATE] = date.today() + timedelta(days=1)
    if KEY_NOTES not in st.session_state: st.session_state[KEY_NOTES] = ""
    if KEY_VIEW_MRN not in st.session_state: st.session_state[KEY_VIEW_MRN] = ""
    if KEY_VIEW_DEPT not in st.session_state: st.session_state[KEY_VIEW_DEPT] = []
    if KEY_VIEW_STATUS not in st.session_state: st.session_state[KEY_VIEW_STATUS] = []
    if KEY_VIEW_DATE not in st.session_state: st.session_state[KEY_VIEW_DATE] = (None, None)

init_state()

# --- Page Content ---
st.header("🛒 Material Indents")
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed.")
    st.stop()

tab_create, tab_view, tab_process = st.tabs([
    "📝 Create New Indent", "📊 View Indents", "⚙️ Process Indent (Future)"
])

# ----------------------------
# 📊 VIEW INDENTS TAB
# ----------------------------
with tab_view:
    st.subheader("📋 View Submitted Indents")

    with st.expander("🔎 Filters", expanded=True):
        col1, col2 = st.columns([2, 2])
        with col1:
            mrn_filter = st.text_input("Search by MRN", key=KEY_VIEW_MRN)
            status_filter = st.multiselect("Status", options=ALL_INDENT_STATUSES, key=KEY_VIEW_STATUS)
        with col2:
            dept_filter = st.multiselect("Department", options=DEPARTMENTS, key=KEY_VIEW_DEPT)
            date_range = st.date_input("Submission Date Range", value=(None, None), key=KEY_VIEW_DATE)

        start_date, end_date = None, None
        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            start_date, end_date = date_range
            if isinstance(start_date, date) and end_date is None: end_date = start_date
            if isinstance(end_date, date) and start_date is None: start_date = end_date

    try:
        indents_df = get_indents(
            db_engine,
            mrn_filter=mrn_filter,
            dept_filter=dept_filter or None,
            status_filter=status_filter or None,
            date_start_filter=start_date,
            date_end_filter=end_date
        )
    except Exception as e:
        st.error(f"Failed to fetch indents: {e}")
        indents_df = pd.DataFrame()

    st.divider()
    if indents_df.empty:
        st.info("No indents found matching the selected filters.")
    else:
        st.success(f"Found {len(indents_df)} indent(s).")
        st.dataframe(
            indents_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "indent_id": None,
                "mrn": st.column_config.TextColumn("MRN", width="small", help="Material Request Number"),
                "date_submitted": st.column_config.DatetimeColumn("Submitted", format="YYYY-MM-DD HH:mm", width="medium"),
                "department": st.column_config.TextColumn("Dept.", width="small"),
                "requested_by": st.column_config.TextColumn("Requester", width="medium"),
                "date_required": st.column_config.DateColumn("Date Required", format="YYYY-MM-DD", width="small"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
            },
            column_order=["mrn", "date_submitted", "department", "requested_by", "date_required", "status", "notes"]
        )
