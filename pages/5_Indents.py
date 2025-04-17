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

# --- Page Setup ---
st.header("🛒 Material Indents")
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed.")
    st.stop()

# --- Tabs ---
tab_create, tab_view, tab_process = st.tabs([
    "📝 Create New Indent", "📊 View Indents", "⚙️ Process Indent (Future)"
])

# ----------------------------
# 📝 CREATE NEW INDENT TAB
# ----------------------------
with tab_create:
    st.subheader("Create a New Material Request")
    selected_dept = st.selectbox("Requesting Department*", options=DEPARTMENTS, placeholder="Select department...")

    item_options = []
    if selected_dept:
        with st.spinner(f"Loading items for {selected_dept}..."):
            filtered_items_df = get_all_items_with_stock(db_engine, include_inactive=False, department=selected_dept)
        if not filtered_items_df.empty:
            filtered_items_df['item_id'] = pd.to_numeric(filtered_items_df['item_id'], errors='coerce').fillna(-1).astype(int)
            valid_items = filtered_items_df[filtered_items_df['item_id'] != -1]
            for _, row in valid_items.iterrows():
                item_options.append((f"{row['name']} ({row.get('unit', 'N/A')})", row['item_id']))

    req_by = st.text_input("Requested By*")
    req_date = st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today())

    st.divider()
    st.markdown("**Add Items to Request:**")
    item_rows = st.session_state.get("item_rows", [{"key": 0}])

    for row in item_rows:
        row_key = row["key"]
        cols = st.columns([4, 2, 1])
        with cols[0]:
            st.selectbox("Item", options=item_options, format_func=lambda x: x[0], key=f"item_{row_key}", label_visibility="collapsed")
        with cols[1]:
            st.number_input("Qty", min_value=0.01, step=0.1, format="%.2f", key=f"qty_{row_key}", label_visibility="collapsed")
        with cols[2]:
            if st.button("➖", key=f"remove_{row_key}"):
                item_rows = [r for r in item_rows if r["key"] != row_key]
                st.session_state["item_rows"] = item_rows
                st.rerun()

    if st.button("➕ Add Item"):
        new_key = max([r["key"] for r in item_rows], default=0) + 1
        item_rows.append({"key": new_key})
        st.session_state["item_rows"] = item_rows
        st.rerun()

    notes = st.text_area("Notes / Remarks")

    if st.button("Submit Indent Request", type="primary"):
        item_list_final = []
        for row in item_rows:
            item = st.session_state.get(f"item_{row['key']}")
            qty = st.session_state.get(f"qty_{row['key']}", 0)
            if item and qty > 0:
                item_list_final.append({"item_id": item[1], "requested_qty": qty, "notes": ""})

        if not selected_dept: st.warning("Select Department.")
        elif not req_by: st.warning("Enter Requester.")
        elif not item_list_final: st.warning("Add at least one valid item row with quantity > 0.")
        else:
            mrn = generate_mrn(engine=db_engine)
            if not mrn: st.error("Failed to generate MRN.")
            else:
                indent_header = {
                    "mrn": mrn,
                    "requested_by": req_by,
                    "department": selected_dept,
                    "date_required": req_date,
                    "status": "Submitted",
                    "notes": notes
                }
                success = create_indent(engine=db_engine, indent_details=indent_header, item_list=item_list_final)
                if success:
                    st.success(f"Indent '{mrn}' submitted!")
                    st.session_state["item_rows"] = [{"key": 0}]
                    st.rerun()

# ----------------------------
# 📊 VIEW INDENTS TAB
# ----------------------------
with tab_view:
    st.subheader("📋 View Submitted Indents")

    DEFAULT_START_DATE = date.today() - timedelta(days=30)
    DEFAULT_END_DATE = date.today()

    with st.expander("🔍 Filter Indents", expanded=True):
        col1, col2 = st.columns([2, 2])
        with col1:
            mrn_filter = st.text_input("Search by MRN")
            status_filter = st.multiselect("Status", options=ALL_INDENT_STATUSES)
        with col2:
            dept_filter = st.multiselect("Department", options=DEPARTMENTS)
            date_range = st.date_input(
                "Submission Date Range",
                value=(DEFAULT_START_DATE, DEFAULT_END_DATE),
                min_value=date(2020, 1, 1),
                max_value=date.today()
            )

    start_date, end_date = None, None
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
        if isinstance(start_date, date) and not isinstance(end_date, date): end_date = start_date
        if isinstance(end_date, date) and not isinstance(start_date, date): start_date = end_date

    indents_df = get_indents(
        db_engine,
        mrn_filter=mrn_filter,
        dept_filter=dept_filter or None,
        status_filter=status_filter or None,
        date_start_filter=start_date,
        date_end_filter=end_date
    )

    st.divider()
    if indents_df.empty:
        st.info("No indents found matching the filters.")
    else:
        st.success(f"Found {len(indents_df)} indent(s).")
        st.dataframe(
            indents_df,
            use_container_width=True,
            hide_index=True,
            column_order=["mrn", "date_submitted", "department", "requested_by", "date_required", "status", "notes"]
        )

# ----------------------------
# ⚙️ PROCESS INDENTS TAB (Placeholder)
# ----------------------------
with tab_process:
    st.subheader("Process Submitted Indents")
    st.info("Functionality to approve, fulfill (issue stock), and update indent status will be built here.")
