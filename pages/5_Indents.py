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
             all_items_df['item_id'] = pd.to_numeric(all_items_df['item_id'], errors='coerce').fillna(-1).astype(int)
             all_item_options = [(f"{r['name']} ({r.get('unit', 'N/A')})", r['item_id']) for i, r in all_items_df.iterrows() if r['item_id'] != -1]
             item_unit_map = {r['item_id']: r.get('unit', '') for i, r in all_items_df.iterrows() if r['item_id'] != -1}

        # Use clear_on_submit=True which should clear basic fields
        with st.form(KEY_FORM, clear_on_submit=True): # Indent Level 0 starts here
            # Widgets and logic inside the form should be indented (Level 1)
            st.markdown("**Enter Indent Details:**") # Level 1

            c1, c2, c3 = st.columns(3) # Level 1
            with c1: # Level 1 context manager
                st.selectbox("Requesting Department*", options=DEPARTMENTS, index=None, placeholder="Select...", key=KEY_DEPT) # Level 2
            with c2: # Level 1 context manager
                st.text_input("Requested By*", placeholder="Enter name", key=KEY_REQ_BY) # Level 2
            with c3: # Level 1 context manager
                st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today(), key=KEY_REQ_DATE) # Level 2

            st.divider() # Level 1
            st.markdown("**Add Items to Request:**") # Level 1

            # Assign editor output to variable at Level 1
            edited_df = st.data_editor(
                st.session_state.indent_items_df_nofilter,
                key=KEY_EDITOR, num_rows="dynamic", use_container_width=True,
                column_config={
                    "Item": st.column_config.SelectboxColumn("Select Item*", help="Choose item", width="large", options=all_item_options, required=False),
                    "Quantity": st.column_config.NumberColumn("Quantity*", help="Enter quantity", min_value=0.01, format="%.2f", step=0.1, required=False),
                    "Unit": st.column_config.TextColumn("Unit", help="Auto-filled", disabled=True, width="small"),
                }, hide_index=True, disabled=not all_item_options
            ) # Level 1

            # Unit processing logic is part of the form definition, Level 1
            processed_rows_for_unit_display = []
            if not edited_df.empty:
                for i, row in edited_df.iterrows(): # Level 2
                    new_row = row.to_dict() # Level 3
                    selected_option = new_row.get("Item") # Level 3
                    if is_valid_item_tuple(selected_option): # Level 3
                        item_id = selected_option[1] # Level 4
                        new_row["Unit"] = item_unit_map.get(item_id, '') # Level 4
                    else: # Level 3
                         new_row["Unit"] = '' # Level 4
                    processed_rows_for_unit_display.append(new_row) # Level 3

            st.divider() # Level 1
            st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES) # Level 1

            submit_button = st.form_submit_button("Submit Indent Request", type="primary") # Level 1

            # --- Form Submission Logic ---
            # This IF block must be indented at Level 1, inside the 'with st.form'
            if submit_button:
                # Logic inside the submit handler is indented (Level 2)
                dept_val = st.session_state.get(KEY_DEPT)
                req_by_val = st.session_state.get(KEY_REQ_BY, "").strip()
                req_date_val = st.session_state.get(KEY_REQ_DATE, date.today())
                notes_val = st.session_state.get(KEY_NOTES, "").strip()
                items_df_to_validate = edited_df.copy() # Use editor's direct output

                # --- Validation using MORE ROBUST check --- Level 2
                items_df_validated_items = items_df_to_validate[items_df_to_validate['Item'].apply(is_valid_item_tuple)]
                items_df_validated_items['Quantity'] = pd.to_numeric(items_df_validated_items['Quantity'], errors='coerce')
                items_df_validated_items = items_df_validated_items.dropna(subset=['Quantity'])
                items_df_final = items_df_validated_items[items_df_validated_items['Quantity'] > 0]

                # --- Debugging --- Level 2
                st.write("DEBUG: Final Validated Item Rows (`items_df_final`):")
                st.dataframe(items_df_final)

                # --- Run Checks --- Level 2
                if not dept_val: st.warning("Select Department.", icon="⚠️") # Level 3
                elif not req_by_val: st.warning("Enter Requester.", icon="⚠️") # Level 3
                elif items_df_final.empty: # Level 3
                    st.warning("Add valid item(s) with quantity > 0.", icon="⚠️") # Level 4
                    st.write("Debug: Raw `edited_df` at submission:") # Level 4
                    st.dataframe(edited_df) # Level 4
                elif items_df_final['Item'].apply(lambda x: x[1]).duplicated().any(): st.warning("Duplicate items found.", icon="⚠️") # Level 3
                else: # Level 3
                    # --- Prepare & Execute Backend Call --- Level 4
                    item_list = [{"item_id": r['Item'][1], "requested_qty": r['Quantity'], "notes": ""} for i, r in items_df_final.iterrows()]
                    mrn = generate_mrn(engine=db_engine)
                    if not mrn: # Level 4
                        st.error("Failed to generate MRN.") # Level 5
                    else: # Level 4
                        indent_header = { # Level 5
                            "mrn": mrn, "requested_by": req_by_val,
                            "department": dept_val, "date_required": req_date_val,
                            "status": "Submitted", "notes": notes_val
                        }
                        success = create_indent(engine=db_engine, indent_details=indent_header, item_list=item_list) # Level 5
                        if success: # Level 5
                            st.success(f"Indent '{mrn}' submitted!", icon="✅") # Level 6
                            reset_indent_form_state_nofilter() # Level 6
                        else: # Level 5
                            st.error("Failed to submit Indent.", icon="❌") # Level 6

        # End of 'with st.form' block (Level 0 indentation)

    # --- Tabs 2 & 3 --- (Level 0 indentation)
    with tab_view: st.subheader("View Indents"); st.info("To be implemented.")
    with tab_process: st.subheader("Process Indents"); st.info("To be implemented.")
