# pages/5_Indents.py
# Rebuilt from user-provided base: Form + Two-Step Dept Confirmation
# Implements multi-item entry using dynamic rows managed by callbacks.

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Any, Optional, Dict, List, Tuple
import time
import numpy as np

# --- Imports and Error Handling ---
try:
    from item_manager_app import (
        connect_db, get_all_items_with_stock, generate_mrn, create_indent
    )
    if 'get_indents' not in locals(): get_indents = lambda **kwargs: pd.DataFrame()
except ImportError as e:
    st.error(f"Import Error from item_manager_app.py: {e}.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import: {e}")
    st.stop()

# --- Constants ---
DEPARTMENTS = ["Kitchen", "Bar", "Housekeeping", "Admin", "Maintenance", "Service"]
# Static Keys for header widgets
KEY_DEPT = "indent_form_dept"
KEY_REQ_BY = "indent_form_req_by"
KEY_REQ_DATE = "indent_form_req_date"
KEY_NOTES = "indent_form_notes"
KEY_FORM = "new_indent_form_cb" # cb for callback version

# --- Session State Initialization ---
def init_form_state():
    """Initializes session state variables for this page."""
    # Control flags for two-step process
    if 'indent_dept_confirmed' not in st.session_state: st.session_state.indent_dept_confirmed = False
    if 'indent_selected_dept' not in st.session_state: st.session_state.indent_selected_dept = None

    # State for dynamic item rows
    if 'form_item_list' not in st.session_state:
        # List stores dicts: {"key": unique_int, "item_tuple": (name, id)|None, "qty": float}
        st.session_state.form_item_list = [{"key": 0, "item_tuple": None, "qty": 1.0}]
    if 'form_next_item_key' not in st.session_state:
        st.session_state.form_next_item_key = 1 # Counter for unique widget keys

    # State for item options/lookup based on confirmed department
    if 'form_item_options' not in st.session_state: st.session_state.form_item_options = []
    if 'form_item_unit_map' not in st.session_state: st.session_state.form_item_unit_map = {}

    # Ensure keys for header widgets exist (optional, but good practice)
    if KEY_DEPT not in st.session_state: st.session_state[KEY_DEPT] = None
    if KEY_REQ_BY not in st.session_state: st.session_state[KEY_REQ_BY] = ""
    if KEY_REQ_DATE not in st.session_state: st.session_state[KEY_REQ_DATE] = date.today() + timedelta(days=1)
    if KEY_NOTES not in st.session_state: st.session_state[KEY_NOTES] = ""

# Call initialization
init_form_state()


# --- Callback Functions for Row Management ---
def add_item_row():
    """Appends a new blank item row structure to the session state list."""
    new_key = st.session_state.form_next_item_key
    st.session_state.form_item_list.append({"key": new_key, "item_tuple": None, "qty": 1.0})
    st.session_state.form_next_item_key += 1

def remove_item_row(row_key_to_remove):
    """Removes an item row from the session state list based on its unique key."""
    st.session_state.form_item_list = [
        item_dict for item_dict in st.session_state.form_item_list
        if item_dict["key"] != row_key_to_remove
    ]
    # Add a default row back if the list becomes empty (optional, keeps one row always)
    if not st.session_state.form_item_list:
         add_item_row()

# --- Reset Function ---
def reset_form_state():
    """Resets the form state, including dynamic rows."""
    st.session_state.indent_dept_confirmed = False
    st.session_state.indent_selected_dept = None
    st.session_state.form_item_list = [{"key": 0, "item_tuple": None, "qty": 1.0}]
    st.session_state.form_next_item_key = 1
    st.session_state.form_item_options = []
    st.session_state.form_item_unit_map = {}
    # Let clear_on_submit handle basic widget clearing if possible
    # Or explicitly clear if clear_on_submit=False is needed later
    # st.session_state.pop(KEY_DEPT, None)
    # st.session_state.pop(KEY_REQ_BY, None)
    # st.session_state.pop(KEY_REQ_DATE, None)
    # st.session_state.pop(KEY_NOTES, None)


# --- Helper function for validation ---
def is_valid_item_tuple_form(val):
    if val is None: return False
    try:
        return isinstance(val, tuple) and len(val) == 2 and isinstance(int(val[1]), int)
    except (TypeError, ValueError, IndexError): return False

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

        # Use clear_on_submit=True - should clear basic widgets after successful submit logic
        with st.form(KEY_FORM, clear_on_submit=True):
            confirm_dept_button = False
            submit_indent_button = False
            change_dept_button = False

            # --- Step 1: Select Department ---
            st.markdown("**Step 1: Select Department**")
            dept_selectbox_val = st.selectbox(
                "Requesting Department*", options=DEPARTMENTS,
                index=DEPARTMENTS.index(st.session_state.indent_selected_dept) if st.session_state.indent_selected_dept in DEPARTMENTS else None,
                placeholder="Select department...", key=KEY_DEPT,
                disabled=st.session_state.indent_dept_confirmed
            )

            if not st.session_state.indent_dept_confirmed:
                confirm_dept_button = st.form_submit_button("Confirm Department & Load Items")
            if st.session_state.indent_dept_confirmed:
                 change_dept_button = st.form_submit_button("Change Department", type="secondary")

            st.divider()

            # --- Step 2: Load Items & Complete Form (Conditional Display) ---
            can_add_items = False
            if st.session_state.indent_dept_confirmed:
                st.markdown(f"**Step 2: Add Items for {st.session_state.indent_selected_dept} Department**")

                # Load items if options aren't already loaded for the confirmed dept
                if not st.session_state.form_item_options:
                    with st.spinner(f"Loading items for {st.session_state.indent_selected_dept}..."):
                        filtered_items_df = get_all_items_with_stock(db_engine, include_inactive=False, department=st.session_state.indent_selected_dept)
                    if not filtered_items_df.empty and 'item_id' in filtered_items_df.columns and 'name' in filtered_items_df.columns:
                        temp_options = []
                        temp_map = {}
                        filtered_items_df['item_id'] = pd.to_numeric(filtered_items_df['item_id'], errors='coerce').fillna(-1).astype(int)
                        valid_items = filtered_items_df[filtered_items_df['item_id'] != -1]
                        for i, r in valid_items.iterrows():
                            display_name = f"{r['name']} ({r.get('unit', 'N/A')})"
                            temp_options.append((display_name, r['item_id']))
                            temp_map[r['item_id']] = r.get('unit', '')
                        st.session_state.form_item_options = temp_options
                        st.session_state.form_item_unit_map = temp_map
                        can_add_items = True # Set flag only if items loaded
                    else:
                         st.warning(f"No active items permitted for '{st.session_state.indent_selected_dept}'.", icon="⚠️")
                         st.session_state.form_item_options = []
                         st.session_state.form_item_unit_map = {}
                else:
                     # Options already loaded for this dept
                     can_add_items = bool(st.session_state.form_item_options)

                # --- Display Other Header Inputs ---
                c2, c3 = st.columns(2)
                with c2: st.text_input("Requested By*", placeholder="Enter name", key=KEY_REQ_BY)
                with c3: st.date_input("Date Required*", value=date.today() + timedelta(days=1), min_value=date.today(), key=KEY_REQ_DATE)

                st.markdown("**Add Items to Request:**")
                if not can_add_items:
                     st.warning(f"No items available to add for {st.session_state.indent_selected_dept}.")
                else:
                    # --- Dynamic Item Rows ---
                    # Retrieve current item list from state
                    current_item_list = st.session_state.form_item_list
                    for i, item_dict in enumerate(current_item_list):
                        item_key = item_dict["key"]
                        row_cols = st.columns([4, 2, 1]) # Adjust ratios as needed
                        with row_cols[0]:
                            st.selectbox(
                                f"Item #{i+1}", options=st.session_state.form_item_options,
                                format_func=lambda x: x[0] if isinstance(x, tuple) else "Select...", # Show display name
                                key=f"item_select_{item_key}", # Unique key per row
                                index=None, # Start empty unless loading existing data
                                label_visibility="collapsed"
                            )
                        with row_cols[1]:
                            st.number_input(
                                f"Qty {i+1}", min_value=0.01, step=0.1, format="%.2f",
                                key=f"item_qty_{item_key}", # Unique key per row
                                value=item_dict.get("qty", 1.0), # Use value from state if exists
                                label_visibility="collapsed"
                            )
                        with row_cols[2]:
                            # Use standard button with callback for removal
                            st.button(
                                "➖", key=f"remove_{item_key}",
                                on_click=remove_item_row, args=(item_key,), # Pass key to remove
                                help="Remove this item row",
                                disabled=(len(current_item_list) <= 1) # Don't allow removing the last row
                            )

                    # --- Add Item Button ---
                    # Use standard button with callback
                    st.button("➕ Add Item Row", on_click=add_item_row, disabled=not can_add_items)

                st.divider()
                st.text_area("Notes / Remarks", placeholder="Any special instructions?", key=KEY_NOTES)

                # --- Final Submit Button ---
                # This is the only st.form_submit_button
                submit_indent_button = st.form_submit_button(
                    "Submit Full Indent Request",
                    disabled=not can_add_items, # Disable if no items can be added
                    type="primary"
                )

            # --- Logic after the form definition ---
            # This runs ONLY when a st.form_submit_button is clicked

            if change_dept_button:
                 # Reset everything if changing department
                 reset_form_state()
                 # No rerun needed here, form submission handles rerun

            elif confirm_dept_button:
                # Logic for the first step submission
                if not dept_selectbox_val:
                    st.warning("Please select a department first.")
                else:
                    # Store selected dept and set confirmed flag
                    st.session_state.indent_selected_dept = dept_selectbox_val
                    st.session_state.indent_dept_confirmed = True
                    # Reset item list for the new department confirmation
                    st.session_state.form_item_list = [{"key": 0, "item_tuple": None, "qty": 1.0}]
                    st.session_state.form_next_item_key = 1
                    st.session_state.form_item_options = [] # Force reload
                    st.session_state.form_item_unit_map = {}
                    # No rerun needed here, form submission handles rerun

            elif submit_indent_button:
                # This runs only when the final submit button is clicked
                if not st.session_state.indent_dept_confirmed:
                     st.error("Department not confirmed.") # Should not happen normally
                else:
                    # Get header values from state
                    current_req_by = st.session_state.get(KEY_REQ_BY, "").strip()
                    current_req_date = st.session_state.get(KEY_REQ_DATE, date.today())
                    current_notes = st.session_state.get(KEY_NOTES, "").strip()
                    current_dept = st.session_state.indent_selected_dept

                    # --- Process item rows from session state ---
                    item_list = []
                    processed_item_ids = set()
                    duplicate_found = False
                    invalid_row_found = False

                    for item_dict in st.session_state.form_item_list:
                        item_key = item_dict["key"]
                        selected_item = st.session_state.get(f"item_select_{item_key}")
                        quantity = st.session_state.get(f"item_qty_{item_key}")

                        # Validate row
                        if is_valid_item_tuple_form(selected_item) and quantity is not None and pd.to_numeric(quantity, errors='coerce') > 0:
                            item_id = selected_item[1]
                            qty_float = float(quantity)

                            # Check for duplicates
                            if item_id in processed_item_ids:
                                duplicate_found = True
                                break # Stop processing on first duplicate
                            processed_item_ids.add(item_id)
                            item_list.append({"item_id": item_id, "requested_qty": qty_float, "notes": ""})
                        elif selected_item is not None or quantity is not None:
                             # Row has some input but is invalid (ignore empty rows)
                             if selected_item is not None or (quantity is not None and pd.to_numeric(quantity, errors='coerce') != 1.0): # Ignore default qty if item is None
                                invalid_row_found = True
                                # Don't break, just note it happened

                    # --- Final Validation ---
                    if not current_dept: st.warning("Select Department.", icon="⚠️") # Should be set if confirmed
                    elif not current_req_by: st.warning("Enter Requester.", icon="⚠️")
                    elif not item_list and invalid_row_found: st.warning("Found rows with invalid item/quantity.", icon="⚠️")
                    elif not item_list: st.warning("Add at least one valid item row with quantity > 0.", icon="⚠️")
                    elif duplicate_found: st.warning("Duplicate items found. Please remove or combine rows.", icon="⚠️")
                    else:
                        # --- Prepare & Execute Backend Call ---
                         mrn = generate_mrn(engine=db_engine)
                         if not mrn: st.error("Failed to generate MRN.")
                         else:
                            indent_header = {
                                "mrn": mrn, "requested_by": current_req_by,
                                "department": current_dept, "date_required": current_req_date,
                                "status": "Submitted", "notes": current_notes
                            }
                            success = create_indent(engine=db_engine, indent_details=indent_header, item_list=item_list)
                            if success:
                                st.success(f"Indent '{mrn}' submitted!", icon="✅")
                                # Reset state - clear_on_submit=True handles basic widgets
                                # We only need to reset our custom list state
                                reset_form_state() # Call reset
                                # No rerun needed, clear_on_submit=True should handle it
                            else:
                                st.error("Failed to submit Indent.", icon="❌")
                                # Data remains in widgets due to clear_on_submit=True only happening on success? Test this.
                                # If data doesn't clear on failure, may need clear_on_submit=False and manual reset + rerun

    # --- Tabs 2 & 3 ---
    with tab_view: st.subheader("View Indents"); st.info("To be implemented.")
    with tab_process: st.subheader("Process Indents"); st.info("To be implemented.")

```

**Key Changes:**

1.  **State for Items:** Uses `st.session_state.form_item_list` (a list of dictionaries) to store the data for each item row. Each dictionary has a unique `key` for widget identification. `st.session_state.form_next_item_key` generates these unique keys.
2.  **Callbacks:**
    * `add_item_row`: Appends a new blank item structure to `st.session_state.form_item_list` and increments the key counter. Attached to the "➕ Add Item Row" `st.button`.
    * `remove_item_row(row_key_to_remove)`: Removes the item with the matching key from `st.session_state.form_item_list`. Attached to the "➖" `st.button` next to each row.
    * These buttons are standard `st.button` (not submit buttons) and modify state via callbacks, triggering a rerun to update the UI without submitting the whole form.
3.  **UI Loop:** The code loops through `st.session_state.form_item_list` to dynamically generate the `st.selectbox`, `st.number_input`, and remove button for each item row, using the unique keys.
4.  **Final Submission:** The main `st.form_submit_button("Submit Full Indent Request")` remains. Its logic (`elif submit_indent_button:`) now iterates through `st.session_state.form_item_list`, reads the corresponding widget values from `st.session_state` using their unique keys (e.g., `st.session_state.get(f"item_select_{item_dict['key']}")`), validates the data, and builds the final `item_list` for the backend.
5.  **Reset:** The `reset_form_state` function resets the custom list state and flags. We are trying `clear_on_submit=True` on the main form again, hoping it works correctly now that row management uses callbacks. If not, we may need `clear_on_submit=False` and a manual reset + `st.rerun`.

This approach keeps your preferred form structure but uses callbacks for dynamic row management, which is the standard Streamlit way to handle such interactions within a form. Please **replace the file content entirely**, **Save, Commit, Push, Reboot, Hard Refresh**, and test carefully, trying adding and removing rows before final submissi
