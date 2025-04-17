# pages/5_Indents.py
import streamlit as st
import pandas as pd
# Updated import to include timedelta
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time # For potential MRN generation or unique keys

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
if 'indent_reset_trigger' not in st.session_state: st.session_state.indent_reset_trigger = 0

# Function to reset the indent creation state
def reset_indent_form_state():
    st.session_state.indent_dept_confirmed = False
    st.session_state.indent_selected_dept = None
    st.session_state.indent_items_df = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
    )
    st.session_state.indent_reset_trigger += 1
    widget_keys_to_clear = [
        f"indent_req_dept_{st.session_state.indent_reset_trigger-1}",
        f"indent_req_by_{st.session_state.indent_reset_trigger-1}",
        f"indent_req_date_{st.session_state.indent_reset_trigger-1}",
        f"indent_notes_{st.session_state.indent_reset_trigger-1}",
        f"indent_item_editor_{st.session_state.indent_reset_trigger-1}",
    ]
    for key in widget_keys_to_clear:
        st.session_state.pop(key, None)

# --- Page Content ---
st.header("🛒 Material Indents")

db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed on this page.")
    st.stop()
else:
    tab_create, tab_view, tab_process = st.tabs([
        "📝 Create New Indent", "📊 View Indents", "⚙️ Process Indent (Future)"
    ])

    with tab_create:
        st.subheader("Create a New Material Request")
        form_key = f"new_indent_form_{st.session_state.indent_reset_trigger}"

        with st.form(form_key, clear_on_submit=False):
            confirm_dept_button = False
            submit_indent_button = False
            change_dept_button = False

            st.markdown("**Step 1: Select Department**")
            current_selected_dept = st.session_state.get('indent_selected_dept', None)
            dept_key = f"indent_req_dept_{st.session_state.indent_reset_trigger}"
            req_by_key = f"indent_req_by_{st.session_state.indent_reset_trigger}"
            req_date_key = f"indent_req_date_{st.session_state.indent_reset_trigger}"
            editor_key = f"indent_item_editor_{st.session_state.indent_reset_trigger}"
            notes_key = f"indent_notes_{st.session_state.indent_reset_trigger}"

            dept_selectbox_val = st.selectbox(
                "Requesting Department*", options=DEPARTMENTS,
                index=DEPARTMENTS.index(current_selected_dept) if current_selected_dept in DEPARTMENTS else None,
                placeholder="Select department...", key=dept_key,
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
                with c2: st.text_input("Requested By*", placeholder="Enter name", key=req_by_key)
                with c3: st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today(), key=req_date_key)

                st.markdown("**Add Items to Request:**")
                if not items_loaded_successfully:
                    st.info("No items available.")
                else:
                     edited_df = st.data_editor(
                        st.session_state.indent_items_df, key=editor_key, num_rows="dynamic", use_container_width=True,
                        column_config={
                            "Item": st.column_config.SelectboxColumn("Select Item*", help="Choose item", width="large", options=item_options_list, required=True),
                            "Quantity": st.column_config.NumberColumn("Quantity*", help="Enter quantity", min_value=0.01, format="%.2f", step=0.1, required=True),
                            "Unit": st.column_config.TextColumn("Unit", help="Auto-filled", disabled=True, width="small"),
                        }, hide_index=True,
                     )
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
                st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=notes_key)
                submit_indent_button = st.form_submit_button("Submit Full Indent Request", disabled=not items_loaded_successfully, type="primary")

            # --- Logic after the form definition ---
            if change_dept_button:
                 reset_indent_form_state()
                 st.rerun()

            elif confirm_dept_button:
                selected_dept_val = dept_selectbox_val
                if not selected_dept_val: st.warning("Please select department first.")
                else:
                    st.session_state.indent_selected_dept = selected_dept_val
                    st.session_state.indent_dept_confirmed = True
                    st.session_state.indent_items_df = pd.DataFrame([{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"])
                    st.rerun()

            elif submit_indent_button:
                # --- START DEBUGGING ---
                st.write("--- DEBUG: Inside submit_indent_button Logic ---")
                st.write(f"Checking key: {req_by_key}")
                st.write(f"Value in state for {req_by_key}: {st.session_state.get(req_by_key)}")
                st.write(f"Checking key: {req_date_key}")
                st.write(f"Value in state for {req_date_key}: {st.session_state.get(req_date_key)}")
                st.write(f"Checking key: {notes_key}")
                st.write(f"Value in state for {notes_key}: {st.session_state.get(notes_key)}")
                st.write(f"Confirmed Dept: {st.session_state.indent_selected_dept}")
                st.write("--- END DEBUGGING ---")
                # --- END DEBUGGING ---

                if not st.session_state.indent_dept_confirmed:
                     st.error("Department not confirmed.") # Should not happen if button logic is correct
                else:
                    current_req_by = st.session_state.get(req_by_key, "").strip()
                    current_req_date = st.session_state.get(req_date_key, date.today())
                    current_notes = st.session_state.get(notes_key, "").strip()
                    items_df_to_validate = st.session_state.indent_items_df.copy()

                    items_df_final = items_df_to_validate[items_df_to_validate['Item'].apply(lambda x: isinstance(x, tuple))]
                    items_df_final = items_df_final.dropna(subset=['Item', 'Quantity'])
                    items_df_final = items_df_final[items_df_final['Quantity'] > 0]

                    if not current_req_by: st.warning("Enter Requester Name/ID.", icon="⚠️")
                    elif items_df_final.empty: st.warning("Add valid item(s).", icon="⚠️")
                    elif items_df_final['Item'].apply(lambda x: x[1]).duplicated().any(): st.warning("Duplicate items found.", icon="⚠️")
                    else:
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
                            if success: st.success(f"Indent '{mrn}' submitted!", icon="✅"); reset_indent_form_state()
                            else: st.error("Failed to submit Indent.", icon="❌")

    # --- Tab 2: View Indents ---
    with tab_view: st.subheader("View Submitted Indents"); st.info("To be implemented.")
    # --- Tab 3: Process Indent ---
    with tab_process: st.subheader("Process Submitted Indents"); st.info("To be implemented.")
