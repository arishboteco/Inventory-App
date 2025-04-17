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
KEY_DEPT = "indent_req_dept"
KEY_REQ_BY = "indent_req_by"
KEY_REQ_DATE = "indent_req_date"
KEY_EDITOR = "indent_item_editor" # Key for data editor
KEY_NOTES = "indent_notes"
KEY_FORM = "new_indent_form"

# --- Initialize Session State ---
if 'indent_dept_confirmed' not in st.session_state: st.session_state.indent_dept_confirmed = False
if 'indent_selected_dept' not in st.session_state: st.session_state.indent_selected_dept = None
# RE-ADD data editor state
if 'indent_items_df' not in st.session_state:
    st.session_state.indent_items_df = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )

# --- Updated Reset Function ---
def reset_indent_form_state():
    st.session_state.indent_dept_confirmed = False
    st.session_state.indent_selected_dept = None
    # Reset data editor state DataFrame
    st.session_state.indent_items_df = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )
    # No need to reset individual widget states explicitly here

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

        with st.form(KEY_FORM, clear_on_submit=False):
            confirm_dept_button = False
            submit_indent_button = False
            change_dept_button = False

            st.markdown("**Step 1: Select Department**")
            current_selected_dept = st.session_state.get('indent_selected_dept', None)

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
            item_unit_map = {} # Needed again for data editor unit lookup

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
                        # Recreate unit map
                        item_unit_map = {r['item_id']: r.get('unit', '') for i, r in filtered_items_df.iterrows()}

                c2, c3 = st.columns(2)
                with c2: st.text_input("Requested By*", placeholder="Enter name", key=KEY_REQ_BY)
                with c3: st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today(), key=KEY_REQ_DATE)

                st.markdown("**Add Items to Request:**")
                if not items_loaded_successfully: st.info("No items available.")
                else:
                     # --- RESTORED DATA EDITOR ---
                     edited_df = st.data_editor(
                        st.session_state.indent_items_df, # Use state DataFrame
                        key=KEY_EDITOR, # Use static key
                        num_rows="dynamic",
                        use_container_width=True,
                        column_config={
                            "Item": st.column_config.SelectboxColumn(
                                "Select Item*", help="Choose item for this department", width="large",
                                options=item_options_list, # Use filtered list
                                required=True,
                            ),
                            "Quantity": st.column_config.NumberColumn(
                                "Quantity*", help="Enter quantity needed", min_value=0.01,
                                format="%.2f", step=0.1, required=True,
                            ),
                             "Unit": st.column_config.TextColumn(
                                "Unit", help="Unit of Measure (auto-filled)", disabled=True, width="small",
                            ),
                        },
                        hide_index=True,
                        disabled=not items_loaded_successfully
                     )
                     # --- Process Edited Dataframe (Unit lookup, etc.) ---
                     # This needs to run to update units and the state DF
                     processed_rows = []
                     if not edited_df.empty:
                         for i, row in edited_df.iterrows():
                            new_row = row.to_dict()
                            selected_option = new_row.get("Item")
                            item_id = None
                            if isinstance(selected_option, tuple):
                                item_id = selected_option[1]
                                new_row["Item"] = selected_option
                                new_row["Unit"] = item_unit_map.get(item_id, '')
                            elif pd.isna(selected_option): new_row["Unit"] = ''
                            else: new_row["Unit"] = ''
                            processed_rows.append(new_row)
                         # Check if processed_rows has content before updating state
                         # Avoid overwriting state if processing fails or yields nothing
                         if processed_rows:
                            st.session_state.indent_items_df = pd.DataFrame(processed_rows)
                         # Optionally handle else case, maybe revert to previous state? For now, do nothing.
                     else: # If edited_df is empty (e.g., user deleted all rows)
                          st.session_state.indent_items_df = pd.DataFrame(
                            [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
                          )
                     # --- END DATA EDITOR RESTORATION ---

                st.divider()
                st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES)
                submit_indent_button = st.form_submit_button("Submit Full Indent Request", disabled=not items_loaded_successfully, type="primary")

            # --- Logic after the form definition ---
            if change_dept_button:
                 reset_indent_form_state()
                 st.rerun()

            elif confirm_dept_button:
                selected_dept_val = st.session_state.get(KEY_DEPT)
                if not selected_dept_val: st.warning("Please select department first.")
                else:
                    st.session_state.indent_selected_dept = selected_dept_val
                    st.session_state.indent_dept_confirmed = True
                    # Reset data editor df when confirming dept
                    st.session_state.indent_items_df = pd.DataFrame(
                        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
                    )
                    st.rerun()

            elif submit_indent_button:
                if not st.session_state.indent_dept_confirmed: st.error("Department not confirmed.")
                else:
                    # --- Get values using static keys ---
                    current_req_by = st.session_state.get(KEY_REQ_BY, "").strip()
                    current_req_date = st.session_state.get(KEY_REQ_DATE, date.today())
                    current_notes = st.session_state.get(KEY_NOTES, "").strip()
                    # --- Process items FROM DATA EDITOR STATE ---
                    items_df_to_validate = st.session_state.indent_items_df.copy()

                    # --- Validation using data editor DF ---
                    items_df_final = items_df_to_validate[items_df_to_validate['Item'].apply(lambda x: isinstance(x, tuple))]
                    items_df_final = items_df_final.dropna(subset=['Item', 'Quantity'])
                    items_df_final = items_df_final[items_df_final['Quantity'] > 0]

                    if not current_req_by: st.warning("Enter Requester Name/ID.", icon="⚠️")
                    elif items_df_final.empty: st.warning("Add at least one valid item with quantity > 0.", icon="⚠️") # Modified message
                    elif items_df_final['Item'].apply(lambda x: x[1]).duplicated().any(): st.warning("Duplicate items found.", icon="⚠️")
                    else:
                         # --- Prepare item_list FROM DATA EDITOR DF ---
                         item_list = [{"item_id": r['Item'][1], "requested_qty": r['Quantity'], "notes": ""} for i, r in items_df_final.iterrows()]

                         mrn = generate_mrn(engine=db_engine)
                         if not mrn: st.error("Failed to generate MRN.")
                         else:
                            indent_header = {
                                "mrn": mrn, "requested_by": current_req_by,
                                "department": st.session_state.indent_selected_dept,
                                "date_required": current_req_date, "status": "Submitted",
                                "notes": current_notes
                            }
                            success = create_indent(engine=db_engine, indent_details=indent_header, item_list=item_list)
                            if success:
                                st.success(f"Indent '{mrn}' submitted!", icon="✅")
                                reset_indent_form_state() # Call reset
                                time.sleep(0.5)
                                st.rerun() # Rerun to clear form visually
                            else: st.error("Failed to submit Indent.", icon="❌")

    # --- Tabs 2 & 3 ---
    with tab_view: st.subheader("View Indents"); st.info("To be implemented.")
    with tab_process: st.subheader("Process Indents"); st.info("To be implemented.")
