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
if 'indent_dept_confirmed' not in st.session_state: st.session_state.indent_dept_confirmed = False
if 'indent_selected_dept' not in st.session_state: st.session_state.indent_selected_dept = None
if 'indent_items_df_nofilter' not in st.session_state:
    st.session_state.indent_items_df_nofilter = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )

# --- Corrected Reset Function ---
def reset_indent_form_state_nofilter():
    # --- ADD THIS DEBUG LINE ---
    st.write("--- Executing CORRECT reset_indent_form_state_nofilter ---")
    # --- END ADD DEBUG LINE ---
    st.session_state.indent_dept_confirmed = False
    st.session_state.indent_selected_dept = None
    # Reset data editor state DataFrame
    st.session_state.indent_items_df_nofilter = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )
    # NO direct setting of widget keys

# --- Page Content ---
st.header("🛒 Material Indents")
db_engine = connect_db()
# ... (rest of the code remains exactly the same as the previous version with st.data_editor) ...
# ... (find the block starting around line 235) ...

            # --- Form Submission Logic ---
            if submit_button:
                dept_val = st.session_state.get(KEY_DEPT)
                req_by_val = st.session_state.get(KEY_REQ_BY, "").strip()
                req_date_val = st.session_state.get(KEY_REQ_DATE, date.today())
                notes_val = st.session_state.get(KEY_NOTES, "").strip()
                # --- Process items DIRECTLY from edited_df ---
                items_df_to_validate = edited_df.copy() # Use editor's direct output

                # --- Validation using MORE ROBUST check ---
                def is_valid_item_tuple(val): # Ensure helper is defined or imported if needed
                     if val is None: return False
                     return isinstance(val, tuple) and len(val) == 2 and isinstance(val[1], int)

                items_df_validated_items = items_df_to_validate[items_df_to_validate['Item'].apply(is_valid_item_tuple)]
                items_df_validated_items['Quantity'] = pd.to_numeric(items_df_validated_items['Quantity'], errors='coerce')
                items_df_validated_items = items_df_validated_items.dropna(subset=['Quantity'])
                items_df_final = items_df_validated_items[items_df_validated_items['Quantity'] > 0]

                # --- Optional Debugging ---
                # st.write("DEBUG: Final Validated Item Rows (`items_df_final`):")
                # st.dataframe(items_df_final)
                # --- End Debugging ---

                # --- Run Checks ---
                if not dept_val: st.warning("Select Department.", icon="⚠️")
                elif not req_by_val: st.warning("Enter Requester.", icon="⚠️")
                elif items_df_final.empty:
                    st.warning("Add valid item(s) with quantity > 0.", icon="⚠️")
                    st.write("Debug: Raw `edited_df` at submission:")
                    st.dataframe(edited_df) # Keep this debug active
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
                            reset_indent_form_state_nofilter() # Call the reset function
                            # clear_on_submit=True handles other fields
                        else:
                            st.error("Failed to submit Indent.", icon="❌")

# ... (rest of the code for tabs 2 & 3) ...
