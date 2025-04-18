# pages/1_Items.py – full file with import-path fix and _engine fix

# ─── Ensure repo root is on sys.path ─────────────────────────────────
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
# ────────────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Tuple, Optional
import math

# Back‑end imports
try:
    from item_manager_app import (
        connect_db,
        get_all_items_with_stock, # Will receive _engine fix
        get_item_details,         # Does not need fix (not cached)
        add_new_item,             # Does not need fix (not cached)
        update_item_details,      # Does not need fix (not cached)
        deactivate_item,          # Does not need fix (not cached)
        reactivate_item,          # Does not need fix (not cached)
    )
except ImportError as e:
    st.error(f"Import error from item_manager_app.py: {e}. Ensure it's in the parent directory and the path fix is working.")
    st.stop()
except Exception as e:
    st.error(f"Unexpected error during import: {e}")
    st.stop()

# ─────────────────────────────────────────────────────────
# Session‑state defaults
# ─────────────────────────────────────────────────────────
if "item_to_edit_id" not in st.session_state:
    st.session_state.item_to_edit_id = None
if "edit_form_values" not in st.session_state:
    st.session_state.edit_form_values = None
if "show_inactive" not in st.session_state:
    st.session_state.show_inactive = False

# ─────────────────────────────────────────────────────────
# Helper function to fetch items for display (cached)
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=60) # Short cache as data changes often
def fetch_items_for_display(_engine, show_inactive: bool) -> pd.DataFrame: # MODIFIED: _engine
    """Cached fetch using the main app's function."""
    # Pass _engine to the backend function which now expects _engine
    return get_all_items_with_stock(_engine, include_inactive=show_inactive) # MODIFIED: Call with _engine

# ─────────────────────────────────────────────────────────
# Page Setup & DB Connection
# ─────────────────────────────────────────────────────────
st.set_page_config(layout="wide")
st.header("📦 Item Master Management")

engine = connect_db() # Keep original name for the connection variable
if not engine:
    st.error("Database connection failed. Cannot manage items.")
    st.stop()

# ─────────────────────────────────────────────────────────
# ADD NEW ITEM Section
# ─────────────────────────────────────────────────────────
with st.expander("➕ Add New Item", expanded=False):
    with st.form("add_item_form", clear_on_submit=True):
        st.subheader("Enter New Item Details:")
        name = st.text_input("Item Name*", help="Unique name for the item.")
        unit = st.text_input("Unit*", help="e.g., KG, LTR, PCS, BTL")
        category = st.text_input("Category", value="Uncategorized")
        sub_category = st.text_input("Sub-Category", value="General")
        permitted_departments = st.text_input(
            "Permitted Departments",
            help="Comma-separated list of departments allowed to request this item (e.g., Kitchen, Bar)"
        )
        reorder_point = st.number_input("Reorder Point", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        initial_stock = st.number_input("Initial Stock", min_value=0.0, value=0.0, step=1.0, format="%.2f", help="Enter starting stock quantity if known.")
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("💾 Add Item")
        if submitted:
            is_valid = True
            if not name:
                st.warning("Item Name is required.")
                is_valid = False
            if not unit:
                st.warning("Unit is required.")
                is_valid = False

            if is_valid:
                item_data = {
                    "name": name.strip(),
                    "unit": unit.strip(),
                    "category": category.strip() or "Uncategorized",
                    "sub_category": sub_category.strip() or "General",
                    "permitted_departments": permitted_departments.strip() or None,
                    "reorder_point": float(reorder_point),
                    "current_stock": float(initial_stock), # Set initial stock
                    "notes": notes.strip() or None,
                    "is_active": True
                }
                # Pass the original 'engine' variable to non-cached functions
                success, message = add_new_item(engine, item_data)
                if success:
                    st.success(message)
                    fetch_items_for_display.clear() # Clear this page's cache
                    st.rerun() # Rerun to refresh view table
                else:
                    st.error(message)

# ─────────────────────────────────────────────────────────
# VIEW / EDIT / DEACTIVATE Section
# ─────────────────────────────────────────────────────────
st.divider()
st.subheader("🔍 View & Manage Existing Items")

# --- Filters ---
show_inactive_items = st.toggle(
    "Show Inactive Items",
    value=st.session_state.show_inactive,
    key="show_inactive_toggle"
)
st.session_state.show_inactive = show_inactive_items # Update session state

# --- Fetch Data for Dropdown and Table ---
# Pass the original 'engine' variable here; fetch_items_for_display receives it as _engine
items_df_display = fetch_items_for_display(engine, st.session_state.show_inactive)

if items_df_display.empty:
    st.info("No items found." if not st.session_state.show_inactive else "No active items found. Toggle 'Show Inactive Items' to see all.")
else:
    # --- Item Selection Dropdown ---
    item_options = items_df_display[['item_id', 'name', 'unit', 'is_active']].copy()
    item_options['display_name'] = item_options.apply(lambda row: f"{row['name']} ({row['unit']})" + (" [Inactive]" if not row['is_active'] else ""), axis=1)
    item_dict = pd.Series(item_options.item_id.values, index=item_options.display_name).to_dict()

    # Find index of currently selected item if it exists
    current_selection_id = st.session_state.get('item_to_edit_id')
    selected_display_name = next((name for name, id_ in item_dict.items() if id_ == current_selection_id), None)

    def load_item_for_edit():
        """Callback to load selected item details into session state for editing."""
        selected_name = st.session_state.item_select_key
        if selected_name and selected_name in item_dict:
            st.session_state.item_to_edit_id = item_dict[selected_name]
            # Pass original 'engine' variable to non-cached function
            details = get_item_details(engine, st.session_state.item_to_edit_id)
            st.session_state.edit_form_values = details
        else:
            st.session_state.item_to_edit_id = None
            st.session_state.edit_form_values = None

    st.selectbox(
        "Select Item to View/Edit",
        options=item_dict.keys(),
        index=list(item_dict.keys()).index(selected_display_name) if selected_display_name else 0,
        key="item_select_key",
        on_change=load_item_for_edit,
        placeholder="Choose an item..."
    )

    # --- Display Item Table ---
    st.dataframe(
        items_df_display,
        use_container_width=True,
        hide_index=True,
        column_order=["name", "unit", "category", "sub_category", "current_stock", "reorder_point", "permitted_departments", "is_active", "notes", "item_id"],
        column_config={
            "item_id": st.column_config.NumberColumn("ID", width="small"),
            "name": "Item Name",
            "unit": st.column_config.TextColumn("Unit", width="small"),
            "category": "Category",
            "sub_category": "Sub-Category",
            "current_stock": st.column_config.NumberColumn("Stock", format="%.2f", width="small"),
            "reorder_point": st.column_config.NumberColumn("Reorder Pt", format="%.2f", width="small"),
            "permitted_departments": "Permitted Depts",
            "is_active": st.column_config.CheckboxColumn("Active?", width="small"),
            "notes": "Notes"
        }
    )

    # --- Edit/Deactivate Form ---
    if st.session_state.item_to_edit_id and st.session_state.edit_form_values:
        st.divider()
        st.subheader(f"Edit Item: {st.session_state.edit_form_values.get('name', 'N/A')}")

        current_values = st.session_state.edit_form_values
        is_currently_active = current_values.get('is_active', False)

        if is_currently_active: # Only allow editing active items fully
            with st.form("edit_item_form"):
                st.caption(f"Item ID: {st.session_state.item_to_edit_id} | Current Stock: {current_values.get('current_stock', 0):.2f} (Stock cannot be edited here)")
                e_name = st.text_input("Item Name*", value=current_values.get('name', ''))
                e_unit = st.text_input("Unit*", value=current_values.get('unit', ''))
                e_category = st.text_input("Category", value=current_values.get('category', ''))
                e_sub_category = st.text_input("Sub-Category", value=current_values.get('sub_category', ''))
                e_permitted = st.text_input(
                    "Permitted Departments",
                    value=current_values.get('permitted_departments', '') or '', # Ensure empty string if None
                    help="Comma-separated list (e.g., Kitchen, Bar)"
                )
                e_rp = st.number_input("Reorder Point", min_value=0.0, value=float(current_values.get('reorder_point', 0.0)), step=1.0, format="%.2f")
                e_notes = st.text_area("Notes", value=current_values.get('notes', '') or '') # Ensure empty string if None

                submitted_edit = st.form_submit_button("💾 Update Item")
                if submitted_edit:
                    is_valid_edit = True
                    if not e_name: st.warning("Item Name is required."); is_valid_edit = False
                    if not e_unit: st.warning("Unit is required."); is_valid_edit = False

                    if is_valid_edit:
                        update_data = {
                            "name": e_name.strip(),
                            "unit": e_unit.strip(),
                            "category": e_category.strip() or "Uncategorized",
                            "sub_category": e_sub_category.strip() or "General",
                            "permitted_departments": e_permitted.strip() or None,
                            "reorder_point": float(e_rp),
                            "notes": e_notes.strip() or None,
                        }
                        # Pass original 'engine' variable to non-cached function
                        ok, msg = update_item_details(engine, st.session_state.item_to_edit_id, update_data)
                        if ok:
                            st.success(msg)
                            # Clear relevant session state and rerun
                            st.session_state.item_to_edit_id = None
                            st.session_state.edit_form_values = None
                            fetch_items_for_display.clear() # Clear display cache
                            st.rerun()
                        else:
                            st.error(msg)

            # --- Deactivate Button (Outside Edit Form, but linked to selected item) ---
            st.divider()
            st.subheader("Deactivate Item")
            if st.button("🗑️ Deactivate"):
                # Pass original 'engine' variable to non-cached function
                if deactivate_item(engine, st.session_state.item_to_edit_id):
                    st.success("Item deactivated.")
                    # Clear state and rerun
                    st.session_state.item_to_edit_id = None
                    st.session_state.edit_form_values = None
                    fetch_items_for_display.clear()
                    st.rerun()
                else:
                    st.error("Failed to deactivate item.")

        else: # Item is currently inactive
            st.info("This item is currently deactivated. You can reactivate it below.")
            if st.button("✅ Reactivate"):
                 # Pass original 'engine' variable to non-cached function
                if reactivate_item(engine, st.session_state.item_to_edit_id):
                    st.success("Item reactivated.")
                    # Clear state and rerun
                    st.session_state.item_to_edit_id = None
                    st.session_state.edit_form_values = None
                    fetch_items_for_display.clear()
                    st.rerun()
                else:
                    st.error("Failed to reactivate item.")
    else:
        st.info("Select an item from the dropdown above to view details or manage.")