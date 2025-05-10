# app/pages/1_Items.py

# Debug prints can be removed now if everything is working, or kept for future debugging
# import sys
# import os
# print(f"--- Debug from 1_Items.py ---")
# print(f"Current Working Directory (from 1_Items.py): {os.getcwd()}")
# print(f"sys.path (from 1_Items.py): {sys.path}")
# print(f"--- End Debug ---")

import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Tuple, Optional
import math

try:
    # Functions that will eventually move to service modules are still imported from app.item_manager_app
    from app.item_manager_app import (
        get_all_items_with_stock,
        get_item_details,
        add_new_item,
        update_item_details,
        deactivate_item,
        reactivate_item,
        get_distinct_departments_from_items # This was in your original main app
    )
    # Import connect_db from its new location
    from app.db.database_utils import connect_db
    # No constants seem to be directly used by this page from app.core.constants
except ImportError as e:
    st.error(f"Import error in 1_Items.py: {e}. Ensure 'INVENTORY-APP' is the root for 'streamlit run app/item_manager_app.py'.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 1_Items.py: {e}")
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
@st.cache_data(ttl=60)
def fetch_items_for_display(_engine, show_inactive: bool) -> pd.DataFrame:
    return get_all_items_with_stock(_engine, include_inactive=show_inactive)

# ─────────────────────────────────────────────────────────
# Page Setup & DB Connection
# ─────────────────────────────────────────────────────────
# st.set_page_config(layout="wide") # Ideally called only once in the main app script
st.header("📦 Item Master Management")

engine = connect_db() # Uses imported connect_db
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
                    "current_stock": float(initial_stock),
                    "notes": notes.strip() or None,
                    "is_active": True
                }
                # Calls add_new_item (currently from app.item_manager_app)
                success, message = add_new_item(engine, item_data)
                if success:
                    st.success(message)
                    fetch_items_for_display.clear() # Clears this page's display cache
                    # The following caches should be cleared by add_new_item itself once it's in item_service.py
                    get_all_items_with_stock.clear()
                    get_distinct_departments_from_items.clear()
                    st.rerun()
                else:
                    st.error(message)

# ─────────────────────────────────────────────────────────
# VIEW / EDIT / DEACTIVATE Section
# ─────────────────────────────────────────────────────────
st.divider()
st.subheader("🔍 View & Manage Existing Items")

show_inactive_items = st.toggle(
    "Show Inactive Items",
    value=st.session_state.show_inactive,
    key="show_inactive_toggle"
)
st.session_state.show_inactive = show_inactive_items

items_df_display = fetch_items_for_display(engine, st.session_state.show_inactive)

if items_df_display.empty:
    st.info("No items found." if not st.session_state.show_inactive else "No active items found. Toggle 'Show Inactive Items' to see all.")
else:
    item_options = items_df_display[['item_id', 'name', 'unit', 'is_active']].copy()
    item_options['display_name'] = item_options.apply(lambda row: f"{row['name']} ({row['unit']})" + (" [Inactive]" if not row['is_active'] else ""), axis=1)
    item_dict = pd.Series(item_options.item_id.values, index=item_options.display_name).to_dict()

    current_selection_id = st.session_state.get('item_to_edit_id')
    selected_display_name = next((name for name, id_ in item_dict.items() if id_ == current_selection_id), None)

    def load_item_for_edit():
        selected_name = st.session_state.item_select_key
        if selected_name and selected_name in item_dict:
            st.session_state.item_to_edit_id = item_dict[selected_name]
            # Calls get_item_details (currently from app.item_manager_app)
            details = get_item_details(engine, st.session_state.item_to_edit_id)
            st.session_state.edit_form_values = details
        else:
            st.session_state.item_to_edit_id = None
            st.session_state.edit_form_values = None

    st.selectbox(
        "Select Item to View/Edit",
        options=list(item_dict.keys()), # Ensure options is a list
        index=list(item_dict.keys()).index(selected_display_name) if selected_display_name else 0,
        key="item_select_key",
        on_change=load_item_for_edit,
        placeholder="Choose an item..."
    )

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

    if st.session_state.item_to_edit_id and st.session_state.edit_form_values:
        st.divider()
        st.subheader(f"Edit Item: {st.session_state.edit_form_values.get('name', 'N/A')}")

        current_values = st.session_state.edit_form_values
        is_currently_active = current_values.get('is_active', False)

        if is_currently_active:
            with st.form("edit_item_form"):
                st.caption(f"Item ID: {st.session_state.item_to_edit_id} | Current Stock: {current_values.get('current_stock', 0):.2f} (Stock cannot be edited here)")
                e_name = st.text_input("Item Name*", value=current_values.get('name', ''))
                e_unit = st.text_input("Unit*", value=current_values.get('unit', ''))
                e_category = st.text_input("Category", value=current_values.get('category', ''))
                e_sub_category = st.text_input("Sub-Category", value=current_values.get('sub_category', ''))
                e_permitted = st.text_input(
                    "Permitted Departments",
                    value=current_values.get('permitted_departments', '') or '',
                    help="Comma-separated list (e.g., Kitchen, Bar)"
                )
                e_rp = st.number_input("Reorder Point", min_value=0.0, value=float(current_values.get('reorder_point', 0.0)), step=1.0, format="%.2f")
                e_notes = st.text_area("Notes", value=current_values.get('notes', '') or '')

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
                        # Calls update_item_details (currently from app.item_manager_app)
                        ok, msg = update_item_details(engine, st.session_state.item_to_edit_id, update_data)
                        if ok:
                            st.success(msg)
                            st.session_state.item_to_edit_id = None
                            st.session_state.edit_form_values = None
                            fetch_items_for_display.clear()
                            get_all_items_with_stock.clear()
                            get_distinct_departments_from_items.clear()
                            # If get_item_details were cached, clear it here too
                            st.rerun()
                        else:
                            st.error(msg)

            st.divider()
            st.subheader("Deactivate Item")
            if st.button("🗑️ Deactivate"):
                # Calls deactivate_item (currently from app.item_manager_app)
                if deactivate_item(engine, st.session_state.item_to_edit_id):
                    st.success("Item deactivated.")
                    st.session_state.item_to_edit_id = None
                    st.session_state.edit_form_values = None
                    fetch_items_for_display.clear()
                    get_all_items_with_stock.clear()
                    get_distinct_departments_from_items.clear()
                    st.rerun()
                else:
                    st.error("Failed to deactivate item.")

        else: # Item is currently inactive
            st.info("This item is currently deactivated. You can reactivate it below.")
            if st.button("✅ Reactivate"):
                # Calls reactivate_item (currently from app.item_manager_app)
                if reactivate_item(engine, st.session_state.item_to_edit_id):
                    st.success("Item reactivated.")
                    st.session_state.item_to_edit_id = None
                    st.session_state.edit_form_values = None
                    fetch_items_for_display.clear()
                    get_all_items_with_stock.clear()
                    get_distinct_departments_from_items.clear()
                    st.rerun()
                else:
                    st.error("Failed to reactivate item.")
    else:
        st.info("Select an item from the dropdown above to view details or manage.")