# pages/5_Indents.py
import streamlit as st
import pandas as pd
# Updated import to include timedelta
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time

# --- Page Config (REMOVED FROM HERE) ---

# Import shared functions and engine from the main app file
try:
    from item_manager_app import (
        connect_db,
        get_all_items_with_stock, # Will be used with department filter
        generate_mrn,
        create_indent,
        # --- Functions to be added later ---
        # get_indents,
        # get_indent_details,
        # update_indent_status,
        # fulfill_indent_item,
        # get_departments
    )
    # Placeholder for functions not yet created
    if 'get_indents' not in locals(): get_indents = lambda **kwargs: pd.DataFrame()

except ImportError as e:
    st.error(f"Could not import functions from item_manager_app.py: {e}.")
    st.stop()

# --- Constants ---
DEPARTMENTS = ["Kitchen", "Bar", "Housekeeping", "Admin", "Maintenance", "Service"]

# --- Initialize Session State for Indent Page ---
if 'indent_dept_confirmed' not in st.session_state: st.session_state.indent_dept_confirmed = False
if 'indent_selected_dept' not in st.session_state: st.session_state.indent_selected_dept = None
if 'indent_items_df' not in st.session_state:
    st.session_state.indent_items_df = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )
# REMOVED: indent_reset_trigger

# --- Static Keys ---
# Define keys centrally
KEY_DEPT = "indent_req_dept"
KEY_REQ_BY = "indent_req_by"
KEY_REQ_DATE = "indent_req_date"
KEY_EDITOR = "indent_item_editor"
KEY_NOTES = "indent_notes"
KEY_FORM = "new_indent_form" # Static key for the form

# Function to reset the indent creation state
def reset_indent_form_state():
    st.session_state.indent_dept_confirmed = False
    st.session_state.indent_selected_dept = None
    st.session_state.indent_items_df = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )
    # Explicitly reset widget values in state using static keys
    st.session_state[KEY_DEPT] = None # Or appropriate default like ""
    st.session_state[KEY_REQ_BY] = ""
    st.session_state[KEY_REQ_DATE] = date.today() + timedelta(days=1) # Reset to default date
    st.session_state[KEY_NOTES] = ""
    # Data editor state is reset via indent_items_df above
    # We might need st.rerun() after calling this if not called from within form logic

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

        # Use static form key
        with st.form(KEY_FORM, clear_on_submit=False):
            confirm_dept_button = False
            submit_indent_button = False
            change_dept_button = False

            st.markdown("**Step 1: Select Department**")
            current_selected_dept = st.session_state.get('indent_selected_dept', None)

            # Use static keys for widgets
            dept_selectbox_val = st.selectbox(
                "Requesting Department*", options=DEPARTMENTS,
                index=DEPARTMENTS.index(current_selected_dept) if current_selected_dept in DEPARTMENTS else None,
                placeholder="Select department...", key=KEY_DEPT,
                disabled=st.session_state.indent_dept_confirmed
            )

            if not st.session_state.indent_dept_confirmed:
                confirm_dept_button = st.form_submit_button("Confirm Department & Load Items")

            if st.session_state.indent_dept_confirmed:
                 change_dept_button = st.form_submit_button("Change Department", type="secondary")

            st.divider()

            items_loaded_successfully = False
            item_options_list = []
            item_unit_map = {}

            if st.session_state.indent_dept_confirmed:
                st.markdown(f"**Step 2: Add Items for {st.session_state.indent_selected_dept} Department**")
                with st.spinner(f"Loading items for {st.session_state.indent_selected_dept}..."):
                    filtered_items_df = get_all_items_with_stock(
                        db_engine, include_inactive=False,
                        department=st.session_state.indent_selected_dept
                    )
                if filtered_items_df.empty:
                    st.warning(f"No active items permitted for '{st.session_state.indent_selected_dept}'.", icon="⚠️")
                else:
                    items_loaded_successfully = True
                    if 'item_id' in filtered_items_df.columns and 'name' in filtered_items_df.columns:
                        item_options_list = [(f"{r['name']} ({r.get('unit', 'N/A')})", r['item_id']) for i, r in filtered_items_df.iterrows()]
                        item_unit_map = {r['item_id']: r.get('unit', '') for i, r in filtered_items_df.iterrows()}

                c2, c3 = st.columns(2)
                with c2: st.text_input("Requested By*", placeholder="Enter name", key=KEY_REQ_BY)
                with c3: st.date_input("Date Required*", value=st.session_state.get(KEY_REQ_DATE, date.today() + timedelta(days=1)), min_value=date.today(), key=KEY_REQ_DATE) # Use state value if available

                st.markdown("**Add Items to Request:**")
                if not items_loaded_successfully:
                    st.info("No items available.")
                else:
                     edited_df = st.data_editor(
                        st.session_state.indent_items_df, key=KEY_EDITOR, num_rows="dynamic", use_container_width=True,
                        column_config={
                            "Item": st.column_config.SelectboxColumn("Select Item*", help="Choose item", width="large", options=item_options_list, required=True),
                            "Quantity": st.column_config.NumberColumn("Quantity*", help="Enter quantity", min_value=0.01, format="%.2f", step=0.1, required=True),
                            "Unit": st.column_config.TextColumn("Unit", help="Auto-filled", disabled=True, width="small"),
                        }, hide_index=True,
                     )
                     # Process edited data editor state for unit lookup
                     processed_rows = []
                     if not edited_df.empty:
                         for i, row in edited_df.iterrows():
                            new_row = row.to_dict()
                            selected_option = new_row.get("Item")
                            item_id = None
                            if isinstance(selected_option, tuple): item_id = selected_option[1]; new_row["Item"] = selected_option; new_row["Unit"] = item_unit_map.get(item_id, '')
                            elif pd.isna(selected_option): new_row["Unit"] = ''
                            else: new_row["Unit"] = ''
                            processed_rows.append(new_row)
                         if processed_rows: st.session_state.indent_items_df = pd.DataFrame(processed_rows)
                         else: st.session_state.indent_items_df = pd.DataFrame([{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"])
                     else: st.session_state.indent_items_df = pd.DataFrame([{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"])

                st.divider()
                st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES)
                submit_indent_button = st.form_submit_button("Submit Full Indent Request", disabled=not items_loaded_successfully, type="primary")

            # --- Logic after the form definition ---
            if change_dept_button:
                 reset_indent_form_state()
                 st.rerun()

            elif confirm_dept_button:
                # Use static key to get value
                selected_dept_val = st.session_state.get(KEY_DEPT)
                if not selected_dept_val: st.warning("Please select department first.")
                else:
                    st.session_state.indent_selected_dept = selected_dept_val
                    st.session_state.indent_dept_confirmed = True
                    st.session_state.indent_items_df = pd.DataFrame([{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"])
                    st.rerun()

            elif submit_indent_button:
                if not st.session_state.indent_dept_confirmed:
                     st.error("Department not confirmed.")
                else:
                    # --- Get final values directly from session_state using STATIC keys ---
                    current_req_by = st.session_state.get(KEY_REQ_BY, "").strip()
                    current_req_date = st.session_state.get(KEY_REQ_DATE, date.today())
                    current_notes = st.session_state.get(KEY_NOTES, "").strip()
                    items_df_to_validate = st.session_state.indent_items_df.copy()

                    # --- Perform Final Validation ---
                    items_df_final = items_df_to_validate[items_df_to_validate['Item'].apply(lambda x: isinstance(x, tuple))]
                    items_df_final = items_df_final.dropna(subset=['Item', 'Quantity'])
                    items_df_final = items_df_final[items_df_final['Quantity'] > 0]

                    if not current_req_by: st.warning("Enter Requester Name/ID.", icon="⚠️")
                    elif items_df_final.empty: st.warning("Add valid item(s).", icon="⚠️")
                    elif items_df_final['Item'].apply(lambda x: x[1]).duplicated().any(): st.warning("Duplicate items found.", icon="⚠️")
                    else:
                        # --- Prepare & Execute Backend Call ---
                         mrn = generate_mrn(engine=db_engine)
                         if not mrn: st.error("Failed to generate MRN.")
                         else:
                            indent_header = {
                                "mrn": mrn, "requested_by": current_req_by,
                                "department": st.session_state.indent_selected_dept,
                                "date_required": current_req_date, "status": "Submitted",
                                "notes": current_notes
                            }
                            item_list = [{"item_id": r['Item'][1], "requested_qty": r['Quantity'], "notes": ""} for i, r in items_df_final.iterrows()]
                            success = create_indent(engine=db_engine, indent_details=indent_header, item_list=item_list)

                            if success:
                                st.success(f"Indent '{mrn}' submitted!", icon="✅")
                                # Call reset which now sets defaults for static keys
                                reset_indent_form_state()
                                # Need to rerun to clear form fields after successful reset
                                time.sleep(0.5) # Short delay might help ensure state updates propagate
                                st.rerun()
                            else: st.error("Failed to submit Indent.", icon="❌")

    # --- Tab 2: View Indents ---
    with tab_view: st.subheader("View Submitted Indents"); st.info("To be implemented.")
    # --- Tab 3: Process Indent ---
    with tab_process: st.subheader("Process Submitted Indents"); st.info("To be implemented.")
