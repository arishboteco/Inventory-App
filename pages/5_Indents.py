# pages/5_Indents.py
import streamlit as st
import pandas as pd
# Updated import to include timedelta
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time # For potential MRN generation or unique keys

# --- Page Config (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide")

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
# Use unique keys for this page to avoid conflicts if names are reused elsewhere
if 'indent_dept_confirmed' not in st.session_state:
    st.session_state.indent_dept_confirmed = False
if 'indent_selected_dept' not in st.session_state:
    st.session_state.indent_selected_dept = None
if 'indent_items_df' not in st.session_state:
    st.session_state.indent_items_df = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}],
        columns=["Item", "Quantity", "Unit"]
    )
if 'indent_reset_trigger' not in st.session_state:
    st.session_state.indent_reset_trigger = 0 # Used to help reset form

# Function to reset the indent creation state
def reset_indent_form_state():
    st.session_state.indent_dept_confirmed = False
    st.session_state.indent_selected_dept = None
    st.session_state.indent_items_df = pd.DataFrame(
        [{"Item": None, "Quantity": 1.0, "Unit": ""}],
        columns=["Item", "Quantity", "Unit"]
    )
    # Increment trigger to help clear widgets if needed (optional)
    st.session_state.indent_reset_trigger += 1

# --- Page Content ---
st.header("🛒 Material Indents")

# Establish DB connection for this page
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed on this page.")
    st.stop()
else:
    # --- Define Tabs ---
    tab_create, tab_view, tab_process = st.tabs([
        "📝 Create New Indent",
        "📊 View Indents",
        "⚙️ Process Indent (Future)"
    ])

    # --- Tab 1: Create New Indent ---
    with tab_create:
        st.subheader("Create a New Material Request")

        # Key for the form, potentially incorporating reset trigger
        form_key = f"new_indent_form_{st.session_state.indent_reset_trigger}"

        # Use a single form for the multi-step process
        # Set clear_on_submit=False to manage state between steps
        with st.form(form_key, clear_on_submit=False):
            # Initialize button variables BEFORE conditional display
            confirm_dept_button = False
            submit_indent_button = False
            change_dept_button = False # Initialize change button as well

            # --- Step 1: Select Department ---
            st.markdown("**Step 1: Select Department**")
            current_selected_dept = st.session_state.get('indent_selected_dept', None)

            dept_selectbox = st.selectbox(
                "Requesting Department*",
                options=DEPARTMENTS,
                index=DEPARTMENTS.index(current_selected_dept) if current_selected_dept in DEPARTMENTS else None,
                placeholder="Select department...",
                key=f"indent_req_dept_{st.session_state.indent_reset_trigger}", # Use reset trigger in key
                # Disable if department is already confirmed
                disabled=st.session_state.indent_dept_confirmed
            )

            # Display Confirm Dept button only if department not confirmed
            if not st.session_state.indent_dept_confirmed:
                confirm_dept_button = st.form_submit_button(
                    "Confirm Department & Load Items",
                    disabled=not dept_selectbox, # Disable if no department selected
                )

            # Optional: Button to change department after confirmation
            if st.session_state.indent_dept_confirmed:
                 change_dept_button = st.form_submit_button("Change Department", type="secondary")


            st.divider()

            # --- Step 2: Load Items & Complete Form (Conditional Display) ---
            items_loaded_successfully = False
            item_options_list = []
            item_unit_map = {}

            # Only display this section if department is confirmed
            if st.session_state.indent_dept_confirmed:
                st.markdown(f"**Step 2: Add Items for {st.session_state.indent_selected_dept} Department**")

                # Fetch filtered items based on the confirmed department
                # Add spinner for user feedback during fetch
                with st.spinner(f"Loading items for {st.session_state.indent_selected_dept}..."):
                    filtered_items_df = get_all_items_with_stock(
                        db_engine,
                        include_inactive=False,
                        department=st.session_state.indent_selected_dept
                    )

                if filtered_items_df.empty:
                    st.warning(f"No active items found permitted for the '{st.session_state.indent_selected_dept}' department.", icon="⚠️")
                    items_loaded_successfully = False
                else:
                    items_loaded_successfully = True
                    # Build options list for data editor
                    if 'item_id' in filtered_items_df.columns and 'name' in filtered_items_df.columns:
                        item_options_list = [
                            (f"{row['name']} ({row.get('unit', 'N/A')})", row['item_id'])
                            for index, row in filtered_items_df.iterrows()
                        ]
                        item_unit_map = {row['item_id']: row.get('unit', '') for index, row in filtered_items_df.iterrows()}

                # --- Display Rest of Form Fields ---
                c2, c3 = st.columns(2)
                with c2:
                    req_by = st.text_input("Requested By*", placeholder="Enter your name or ID", key=f"indent_req_by_{st.session_state.indent_reset_trigger}")
                with c3:
                    req_date = st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today(), key=f"indent_req_date_{st.session_state.indent_reset_trigger}")

                st.markdown("**Add Items to Request:**")
                if not items_loaded_successfully:
                    st.info("No items available to add for the selected department.")
                    can_add_items = False
                else:
                     can_add_items = True
                     edited_df = st.data_editor(
                        st.session_state.indent_items_df,
                        key=f"indent_item_editor_{st.session_state.indent_reset_trigger}", # Use reset trigger
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
                     )

                     # --- Process Edited Dataframe (Unit lookup, etc.) ---
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
                         st.session_state.indent_items_df = pd.DataFrame(processed_rows)
                     else:
                          st.session_state.indent_items_df = pd.DataFrame(
                            [{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"]
                          )


                st.divider()
                req_notes = st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=f"indent_notes_{st.session_state.indent_reset_trigger}")

                # --- Final Submit Button (Only displayed if dept confirmed) ---
                submit_indent_button = st.form_submit_button(
                    "Submit Full Indent Request",
                    disabled=not items_loaded_successfully, # Disable if no items could be loaded
                    type="primary"
                    )


            # --- Logic after the form definition ---
            # This block executes when ANY submit button inside the form is pressed

            if change_dept_button:
                 # Handle the "Change Department" action
                 reset_indent_form_state() # Reset the entire state
                 st.rerun() # Rerun to show step 1 again

            elif confirm_dept_button:
                # Logic for the first step submission
                if not dept_selectbox:
                    st.warning("Please select a department first.")
                else:
                    st.session_state.indent_selected_dept = dept_selectbox
                    st.session_state.indent_dept_confirmed = True
                    # Reset item editor state when department confirmed
                    st.session_state.indent_items_df = pd.DataFrame(
                        [{"Item": None, "Quantity": 1.0, "Unit": ""}],
                        columns=["Item", "Quantity", "Unit"]
                    )
                    st.rerun() # Rerun to show the second part of the form

            # Check if the final submit button was pressed
            # This variable 'submit_indent_button' now exists (initialized to False)
            # and will be True only if Step 2 was displayed AND its button was clicked.
            elif submit_indent_button: # Use elif to avoid running if change_dept was clicked
                # --- Perform Final Validation ---
                # Ensure we are still in the confirmed state (sanity check)
                if not st.session_state.indent_dept_confirmed:
                     st.error("Department not confirmed. Please confirm department first.")
                else:
                    final_dept = st.session_state.indent_selected_dept # Get confirmed dept
                    final_req_by = req_by # Get value from widget instance
                    final_req_date = req_date # Get value from widget instance

                    items_df_final = st.session_state.indent_items_df.copy()
                    items_df_final = items_df_final[items_df_final['Item'].apply(lambda x: isinstance(x, tuple))]
                    items_df_final = items_df_final.dropna(subset=['Item', 'Quantity'])
                    items_df_final = items_df_final[items_df_final['Quantity'] > 0]

                    if not final_req_by.strip():
                        st.warning("Please enter the Requester's Name/ID.", icon="⚠️")
                    elif items_df_final.empty:
                         st.warning("Please add at least one valid item with a quantity greater than 0.", icon="⚠️")
                    elif items_df_final['Item'].apply(lambda x: x[1]).duplicated().any():
                         st.warning("Duplicate items found. Please combine quantities for each item.", icon="⚠️")
                    else:
                        # --- Prepare Data for Backend ---
                        mrn = generate_mrn(engine=db_engine)
                        if not mrn:
                             st.error("Failed to generate MRN. Cannot submit indent.")
                        else:
                            indent_header = {
                                "mrn": mrn,
                                "requested_by": final_req_by.strip(),
                                "department": final_dept,
                                "date_required": final_req_date,
                                "status": "Submitted",
                                "notes": req_notes.strip() # Get notes value from widget instance
                            }
                            item_list = [
                                {"item_id": row['Item'][1], "requested_qty": row['Quantity'], "notes": ""}
                                for _, row in items_df_final.iterrows()
                            ]

                            # --- Call Backend Function ---
                            success = create_indent(
                                engine=db_engine,
                                indent_details=indent_header,
                                item_list=item_list
                            )

                            if success:
                                st.success(f"Indent Request '{mrn}' submitted successfully!", icon="✅")
                                reset_indent_form_state() # Reset state for next indent
                                # Don't call rerun here, allow success message to show
                                # Form widgets will reset on next interaction due to key change
                            else:
                                st.error("Failed to submit Indent Request.", icon="❌")
                                # State is not reset, user can retry submitting


    # --- Tab 2: View Indents ---
    with tab_view:
        st.subheader("View Submitted Indents")
        st.info("Filtering and display of indents will be implemented here.")
        # (Placeholder for future implementation)


    # --- Tab 3: Process Indent ---
    with tab_process:
        st.subheader("Process Submitted Indents")
        st.info("Functionality to approve, fulfill (issue stock), and update indent status will be built here.")
         # (Placeholder for future implementation)
