# pages/5_Indents.py
import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime, date
import time # For potential MRN generation or unique keys

# Import shared functions and engine from the main app file
# We will need to ADD NEW functions like create_indent, get_indents, etc., to item_manager_app.py
try:
    from item_manager_app import (
        connect_db,
        get_all_items_with_stock, # Needed for item selection
        # --- Functions to be added to item_manager_app.py ---
        # generate_mrn,
        # create_indent,
        # get_indents,
        # get_indent_details,
        # update_indent_status,
        # fulfill_indent_item, # This might call record_stock_transaction internally
        # get_departments # Optional: if departments are stored in DB
    )
    # Placeholder for functions not yet created - prevents immediate error
    # We'll replace these with actual imports once defined in the main app
    if 'create_indent' not in locals(): create_indent = lambda **kwargs: False
    if 'generate_mrn' not in locals(): generate_mrn = lambda **kwargs: f"MRN-{int(time.time())}" # Dummy MRN
    if 'get_indents' not in locals(): get_indents = lambda **kwargs: pd.DataFrame() # Dummy empty DF

except ImportError as e:
    st.error(f"Could not import functions from item_manager_app.py: {e}. Ensure it's in the parent directory and necessary functions are defined.")
    st.stop()

# --- Constants (Example Departments - Adapt as needed) ---
DEPARTMENTS = ["Kitchen", "Bar", "Housekeeping", "Admin", "Maintenance", "Service"]
# Consider fetching from a table if dynamic departments are needed

# --- Initialize Session State ---
if 'indent_items_df' not in st.session_state:
    # Initialize dataframe for st.data_editor in the "Create" tab
    st.session_state.indent_items_df = pd.DataFrame(
        [
            {"Item": None, "Quantity": 1.0, "Unit": ""}
        ],
        columns=["Item", "Quantity", "Unit"] # Add other columns if needed
    )

# --- Page Content ---
st.set_page_config(layout="wide") # Use wide layout for potentially large tables/editors
st.header("🛒 Material Indents")

# Establish DB connection for this page
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed on this page.")
    st.stop()
else:
    # --- Fetch Data Needed Across Tabs ---
    # Get active items for selection dropdowns
    active_items_df = get_all_items_with_stock(db_engine, include_inactive=False)
    if active_items_df.empty:
        st.warning("No active items found in the database. Cannot create indents.", icon="⚠️")
        # Provide link to item management?
        st.stop()

    # Create list for selectbox [(display_name, item_id), ...]
    item_options_list: List[Tuple[str, int]] = []
    item_unit_map = {} # Dictionary to map item_id to unit for display
    if 'item_id' in active_items_df.columns and 'name' in active_items_df.columns:
        item_options_list = [
            (f"{row['name']} ({row.get('unit', 'N/A')})", row['item_id'])
            for index, row in active_items_df.iterrows()
        ]
        item_unit_map = {row['item_id']: row.get('unit', '') for index, row in active_items_df.iterrows()}

    # --- Define Tabs ---
    tab_create, tab_view, tab_process = st.tabs([
        "📝 Create New Indent",
        "📊 View Indents",
        "⚙️ Process Indent (Future)"
    ])

    # --- Tab 1: Create New Indent ---
    with tab_create:
        st.subheader("Create a New Material Request")

        # Use a form to batch input
        with st.form("new_indent_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                req_dept = st.selectbox("Requesting Department*", options=DEPARTMENTS, index=None, placeholder="Select department...")
            with c2:
                req_by = st.text_input("Requested By*", placeholder="Enter your name or ID")
            with c3:
                req_date = st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today())

            st.divider()
            st.markdown("**Add Items to Request:**")

            # Use st.data_editor for adding/editing items
            # We need to handle updates carefully if using session state
            edited_df = st.data_editor(
                st.session_state.indent_items_df,
                key="indent_item_editor", # Assign a key
                num_rows="dynamic", # Allow adding/deleting rows
                use_container_width=True,
                column_config={
                    "Item": st.column_config.SelectboxColumn(
                        "Select Item*",
                        help="Choose the item you need",
                        width="large",
                        options=item_options_list, # Use list of (display, value) tuples
                        format_func=lambda x: x[0] if isinstance(x, tuple) else x, # Show only display name
                        required=True,
                    ),
                    "Quantity": st.column_config.NumberColumn(
                        "Quantity*",
                        help="Enter the quantity needed",
                        min_value=0.01,
                        format="%.2f", # Format to 2 decimal places
                        step=0.1,
                        required=True,
                    ),
                     "Unit": st.column_config.TextColumn(
                        "Unit",
                        help="Unit of Measure (auto-filled)",
                        disabled=True, # Make read-only
                        width="small",
                    ),
                },
                hide_index=True,
            )

            # Update Units automatically based on Item selection
            # This part needs careful handling as data_editor state is tricky
            # A possible approach: Process the dataframe after editing
            processed_rows = []
            valid_items = True
            for i, row in edited_df.iterrows():
                 selected_option = row["Item"]
                 item_id = None
                 if isinstance(selected_option, tuple):
                     item_id = selected_option[1] # Get the item_id from the tuple
                 elif selected_option is not None: # Handle potential direct value if config changes
                     # Find item_id based on display name (less robust)
                     pass # Or raise error if format is wrong

                 if item_id:
                     row["Unit"] = item_unit_map.get(item_id, '')
                     processed_rows.append(row)
                 elif row['Quantity'] or selected_option: # If user entered qty but no item
                     valid_items = False # Mark as invalid if item missing but other data present

            # Update the session state DataFrame for the next render
            # Use the processed data if valid, otherwise keep original/edited
            if valid_items:
                 st.session_state.indent_items_df = pd.DataFrame(processed_rows)
            else:
                 # Maybe keep the edited_df to show errors or revert? For now, keep edited.
                 st.session_state.indent_items_df = edited_df


            st.divider()
            req_notes = st.text_area("Notes / Remarks", placeholder="Any special instructions?")

            # Submit Button
            submitted = st.form_submit_button("Submit Indent Request")

            if submitted:
                # --- Validation ---
                items_to_submit = st.session_state.indent_items_df.dropna(subset=['Item']) # Drop rows where Item is None
                items_to_submit = items_to_submit[items_to_submit['Quantity'] > 0] # Ensure quantity > 0

                if not req_dept:
                    st.warning("Please select the Requesting Department.", icon="⚠️")
                elif not req_by.strip():
                    st.warning("Please enter the Requester's Name/ID.", icon="⚠️")
                elif items_to_submit.empty:
                     st.warning("Please add at least one item with a valid quantity.", icon="⚠️")
                # Add check for duplicate items? (Optional)
                # Add check if any item selection is invalid? (Data editor should handle required)
                else:
                    # --- Prepare Data for Backend ---
                    # Generate MRN (using placeholder function for now)
                    mrn = generate_mrn(engine=db_engine) # Needs implementation

                    indent_header = {
                        "mrn": mrn,
                        "requested_by": req_by.strip(),
                        "department": req_dept,
                        "date_required": req_date,
                        "status": "Submitted", # Initial status
                        "notes": req_notes.strip()
                    }

                    # Convert DataFrame rows to list of dictionaries for items
                    item_list = []
                    for _, row in items_to_submit.iterrows():
                        selected_item_tuple = row['Item'] # This is (display_name, item_id)
                        item_list.append({
                            "item_id": selected_item_tuple[1], # Extract item_id
                            "requested_qty": row['Quantity'],
                            "notes": "" # Add line item notes later if needed
                        })

                    # --- Call Backend Function (using placeholder) ---
                    st.write("--- Data to be submitted ---") # Debug output
                    st.json({"header": indent_header, "items": item_list}) # Debug output

                    # success = create_indent(
                    #     engine=db_engine,
                    #     indent_details=indent_header,
                    #     item_list=item_list
                    # ) # Needs implementation

                    # Mock success for now
                    success = True
                    time.sleep(1) # Simulate processing

                    if success:
                        st.success(f"Indent Request '{mrn}' submitted successfully!", icon="✅")
                        # Clear the items dataframe in session state for the next form
                        st.session_state.indent_items_df = pd.DataFrame([{"Item": None, "Quantity": 1.0, "Unit": ""}], columns=["Item", "Quantity", "Unit"])
                        # Rerun is handled by clear_on_submit=True
                    else:
                        st.error("Failed to submit Indent Request.", icon="❌")
                        # Keep form data by not clearing session state? Or maybe just items?


    # --- Tab 2: View Indents ---
    with tab_view:
        st.subheader("View Submitted Indents")
        st.info("Filtering and display of indents will be implemented here.")

        # Placeholder for filters
        # col1, col2, col3, col4 = st.columns(4)
        # with col1: filter_mrn = st.text_input("Filter by MRN")
        # with col2: filter_dept = st.multiselect("Filter by Department", options=DEPARTMENTS)
        # with col3: filter_status = st.multiselect("Filter by Status", options=["Submitted", "Processing", "Completed", "Cancelled"])
        # with col4: filter_date = st.date_input("Filter by Date Required", value=[None, None])

        # Fetch and display indents (using placeholder function)
        # indents_df = get_indents(engine=db_engine, ...) # Needs implementation
        # st.dataframe(indents_df)


    # --- Tab 3: Process Indent ---
    with tab_process:
        st.subheader("Process Submitted Indents")
        st.info("Functionality to approve, fulfill (issue stock), and update indent status will be built here.")
        # This tab would likely involve:
        # 1. Selecting an indent (e.g., by MRN).
        # 2. Displaying its details.
        # 3. Form/buttons to update status.
        # 4. Form/editor to enter fulfilled quantities for each item.
        # 5. Logic to call `fulfill_indent_item` which updates stock transactions.
