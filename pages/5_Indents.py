# pages/5_Indents.py
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time

# --- Page Config (REMOVED) ---

# Import shared functions
try:
    from item_manager_app import (
        connect_db, get_all_items_with_stock, generate_mrn, create_indent,
        # get_indents, get_indent_details, update_indent_status, fulfill_indent_item, get_departments # Future
    )
    if 'get_indents' not in locals(): get_indents = lambda **kwargs: pd.DataFrame()
except ImportError as e:
    st.error(f"Import Error: {e}.")
    st.stop()

# --- Constants ---
DEPARTMENTS = ["Kitchen", "Bar", "Housekeeping", "Admin", "Maintenance", "Service"]
# Static Keys
KEY_DEPT = "indent_req_dept_nofilter"
KEY_REQ_BY = "indent_req_by_nofilter"
KEY_REQ_DATE = "indent_req_date_nofilter"
KEY_EDITOR = "indent_item_editor_nofilter"
KEY_NOTES = "indent_notes_nofilter"
KEY_FORM = "new_indent_form_nofilter"

# --- Initialize Session State ---
if 'indent_items_df_nofilter' not in st.session_state:
    st.session_state.indent_items_df_nofilter = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )

# --- Simplified Reset Function ---
def reset_indent_form_state_nofilter():
    st.session_state.indent_items_df_nofilter = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )

# --- Helper function for validation ---
def is_valid_item_tuple(val):
    """Checks if the value is a tuple representing a valid item selection."""
    # Check if it's a tuple of length 2 and the second element (ID) is an integer
    return isinstance(val, tuple) and len(val) == 2 and isinstance(val[1], int)


# --- Page Content ---
st.header("🛒 Material Indents")
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed.")
    st.stop()
else:
    tab_create, tab_view, tab_process = st.tabs([
        "📝 Create New Indent", "📊 View Indents", "⚙️ Process Indent (Future)"
    ])

    with tab_create:
        st.subheader("Create a New Material Request")
        st.caption("Note: Item list is not filtered by department in this view.")

        all_items_df = get_all_items_with_stock(db_engine, include_inactive=False)
        all_item_options = []
        item_unit_map = {}
        if not all_items_df.empty and 'item_id' in all_items_df.columns and 'name' in all_items_df.columns:
             all_item_options = [(f"{r['name']} ({r.get('unit', 'N/A')})", int(r['item_id'])) for i, r in all_items_df.iterrows()] # Ensure item_id is int
             item_unit_map = {int(r['item_id']): r.get('unit', '') for i, r in all_items_df.iterrows()} # Ensure key is int

        with st.form(KEY_FORM, clear_on_submit=True):
            st.markdown("**Enter Indent Details:**")

            c1, c2, c3 = st.columns(3)
            with c1: st.selectbox("Requesting Department*", options=DEPARTMENTS, index=None, placeholder="Select...", key=KEY_DEPT)
            with c2: st.text_input("Requested By*", placeholder="Enter name", key=KEY_REQ_BY)
            with c3: st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today(), key=KEY_REQ_DATE)

            st.divider()
            st.markdown("**Add Items to Request:**")

            edited_df = st.data_editor(
                st.session_state.indent_items_df_nofilter,
                key=KEY_EDITOR, num_rows="dynamic", use_container_width=True,
                column_config={
                    "Item": st.column_config.SelectboxColumn("Select Item*", help="Choose item", width="large", options=all_item_options, required=False), # Changed required to False temporarily
                    "Quantity": st.column_config.NumberColumn("Quantity*", help="Enter quantity", min_value=0.01, format="%.2f", step=0.1, required=False), # Changed required to False temporarily
                    "Unit": st.column_config.TextColumn("Unit", help="Auto-filled", disabled=True, width="small"),
                }, hide_index=True, disabled=not all_item_options
            )

            # Process units locally - NO state update here
            processed_rows_for_unit_display = []
            if not edited_df.empty:
                for i, row in edited_df.iterrows():
                    new_row = row.to_dict()
                    selected_option = new_row.get("Item")
                    if is_valid_item_tuple(selected_option): # Use new validation func
                        item_id = selected_option[1]
                        new_row["Unit"] = item_unit_map.get(item_id, '')
                    else:
                         new_row["Unit"] = '' # Clear unit if item invalid
                    processed_rows_for_unit_display.append(new_row)
            # We capture edited_df below, no need to update state df here

            st.divider()
            st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES)
            submit_button = st.form_submit_button("Submit Indent Request", type="primary")

            # --- Form Submission Logic ---
            if submit_button:
                dept_val = st.session_state.get(KEY_DEPT)
                req_by_val = st.session_state.get(KEY_REQ_BY, "").strip()
                req_date_val = st.session_state.get(KEY_REQ_DATE, date.today())
                notes_val = st.session_state.get(KEY_NOTES, "").strip()
                # --- Process items DIRECTLY from edited_df ---
                items_df_to_validate = edited_df.copy()

                # --- Validation using MORE ROBUST check ---
                # 1. Filter using the robust tuple check function
                items_df_validated_items = items_df_to_validate[items_df_to_validate['Item'].apply(is_valid_item_tuple)]

                # 2. Drop rows where Quantity is missing (or non-numeric after coerce)
                items_df_validated_items['Quantity'] = pd.to_numeric(items_df_validated_items['Quantity'], errors='coerce')
                items_df_validated_items = items_df_validated_items.dropna(subset=['Quantity'])

                # 3. Filter for Quantity > 0
                items_df_final = items_df_validated_items[items_df_validated_items['Quantity'] > 0]

                # --- Optional Debugging ---
                st.write("DEBUG: Final Validated Item Rows (`items_df_final`):")
                st.dataframe(items_df_final)
                # --- End Debugging ---

                # --- Run Checks ---
                if not dept_val: st.warning("Select Department.", icon="⚠️")
                elif not req_by_val: st.warning("Enter Requester.", icon="⚠️")
                elif items_df_final.empty:
                    st.warning("Add valid item(s) with quantity > 0.", icon="⚠️")
                    # Optionally add more debug about the raw edited_df if needed
                    # st.write("Debug: Raw `edited_df` at submission:")
                    # st.dataframe(edited_df)
                elif items_df_final['Item'].apply(lambda x: x[1]).duplicated().any(): st.warning("Duplicate items found.", icon="⚠️")
                else:
                    # --- Prepare & Execute Backend Call ---
                    item_list = [{"item_id": r['Item'][1], "requested_qty": r['Quantity'], "notes": ""} for i, r in items_df_final.iterrows()]
                    mrn = generate_mrn(engine=db_engine)
                    if not mrn: st.error("Failed to generate MRN.")
                    else:
                        indent_header = {
                            "mrn": mrn, "requested_by": req_by_val,
                            "department": dept_val, "date_required": req_date_val,
                            "status": "Submitted", "notes": notes_val
                        }
                        success = create_indent(engine=db_engine, indent_details=indent_header, item_list=item_list)
                        if success:
                            st.success(f"Indent '{mrn}' submitted!", icon="✅")
                            # Reset data editor state for next time
                            reset_indent_form_state_nofilter()
                            # clear_on_submit=True handles other fields
                        else: st.error("Failed to submit Indent.", icon="❌")

    # --- Tabs 2 & 3 ---
    with tab_view: st.subheader("View Indents"); st.info("To be implemented.")
    with tab_process: st.subheader("Process Indents"); st.info("To be implemented.")
