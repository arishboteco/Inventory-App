# pages/5_Indents.py
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time
import numpy as np # Import numpy for potential NaN checks if needed

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
# Using data editor state key from this version
if 'indent_items_df_nofilter' not in st.session_state:
    st.session_state.indent_items_df_nofilter = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )

# --- Simplified Reset Function ---
# Resets only the data editor state DF for this version
def reset_indent_form_state_nofilter():
    st.session_state.indent_items_df_nofilter = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )

# --- Helper function for validation (Based on Suggestion) ---
def is_valid_item_tuple(val):
    """Checks if the value is a tuple representing a valid item selection."""
    # Check if it's a tuple of length 2 and the second element (ID) is an integer
    # Added check for None explicitly
    if val is None:
        return False
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
        st.caption("Note: Item list shows all items.")

        all_items_df = get_all_items_with_stock(db_engine, include_inactive=False)
        all_item_options = []
        item_unit_map = {}
        if not all_items_df.empty and 'item_id' in all_items_df.columns and 'name' in all_items_df.columns:
             # Ensure item_id is consistently int for reliable tuple comparison later
             all_items_df['item_id'] = pd.to_numeric(all_items_df['item_id'], errors='coerce').fillna(-1).astype(int)
             all_item_options = [(f"{r['name']} ({r.get('unit', 'N/A')})", r['item_id']) for i, r in all_items_df.iterrows() if r['item_id'] != -1]
             item_unit_map = {r['item_id']: r.get('unit', '') for i, r in all_items_df.iterrows() if r['item_id'] != -1}

        # Use clear_on_submit=True which should clear basic fields
        with st.form(KEY_FORM, clear_on_submit=True):
            st.markdown("**Enter Indent Details:**")

            c1, c2, c3 = st.columns(3)
            with c1: st.selectbox("Requesting Department*", options=DEPARTMENTS, index=None, placeholder="Select...", key=KEY_DEPT)
            with c2: st.text_input("Requested By*", placeholder="Enter name", key=KEY_REQ_BY)
            with c3: st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today(), key=KEY_REQ_DATE)

            st.divider()
            st.markdown("**Add Items to Request:**")

            edited_df = st.data_editor(
                st.session_state.indent_items_df_nofilter, # Display current state
                key=KEY_EDITOR,
                num_rows="dynamic", use_container_width=True,
                column_config={
                    "Item": st.column_config.SelectboxColumn(
                        "Select Item*", help="Choose item", width="large",
                        options=all_item_options, # Use full list of valid (name, int_id) tuples
                        required=False # Set to False, rely on Python validation below
                        ),
                    "Quantity": st.column_config.NumberColumn(
                        "Quantity*", help="Enter quantity", min_value=0.0, # Allow 0 temporarily if needed for empty rows? Let's stick to 0.01
                        format="%.2f", step=0.1, required=False # Set to False, rely on Python validation
                        ),
                    "Unit": st.column_config.TextColumn(
                        "Unit", help="Auto-filled", disabled=True, width="small"
                        ),
                }, hide_index=True, disabled=not all_item_options
            )

            # Process units locally - NO state update here necessary before submit logic
            # We will read and process edited_df directly in submit logic

            st.divider()
            st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES)

            submit_button = st.form_submit_button("Submit Indent Request", type="primary")

            # --- Form Submission Logic ---
            if submit_button:
                dept_val = st.session_state.get(KEY_DEPT)
                req_by_val = st.session_state.get(KEY_REQ_BY, "").strip()
                req_date_val = st.session_state.get(KEY_REQ_DATE, date.today())
                notes_val = st.session_state.get(KEY_NOTES, "").strip()
                # --- Process items DIRECTLY from edited_df using robust validation ---
                items_df_to_validate = edited_df.copy() # Use editor's direct output

                # --- Validation using MORE ROBUST check ---
                # 1. Filter using the robust tuple check function
                items_df_validated_items = items_df_to_validate[items_df_to_validate['Item'].apply(is_valid_item_tuple)]

                # 2. Drop rows where Quantity is missing or non-numeric (and coerce valid ones)
                items_df_validated_items['Quantity'] = pd.to_numeric(items_df_validated_items['Quantity'], errors='coerce')
                items_df_validated_items = items_df_validated_items.dropna(subset=['Quantity'])

                # 3. Filter for Quantity > 0
                items_df_final = items_df_validated_items[items_df_validated_items['Quantity'] > 0]

                # --- Debugging ---
                st.write("DEBUG: Final Validated Item Rows (`items_df_final`):")
                st.dataframe(items_df_final)
                # --- End Debugging ---

                # --- Run Checks ---
                if not dept_val: st.warning("Select Department.", icon="⚠️")
                elif not req_by_val: st.warning("Enter Requester.", icon="⚠️")
                elif items_df_final.empty:
                    st.warning("Add valid item(s) with quantity > 0.", icon="⚠️")
                    # Add extra debug about the raw editor output if needed
                    st.write("Debug: Raw `edited_df` at submission:")
                    st.dataframe(edited_df)
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
                            # Reset editor state DF for next render
                            reset_indent_form_state_nofilter()
                            # clear_on_submit=True handles other fields
                        else:
                            st.error("Failed to submit Indent.", icon="❌")
                            # On failure, data editor might clear due to clear_on_submit=True
                            # Consider setting clear_on_submit=False and handling reset manually if this is an issue

    # --- Tabs 2 & 3 ---
    with tab_view: st.subheader("View Indents"); st.info("To be implemented.")
    with tab_process: st.subheader("Process Indents"); st.info("To be implemented.")
