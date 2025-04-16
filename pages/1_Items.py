import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple

# Import shared functions and engine from the main app file
# Assumes main file is named item_manager_app.py in the parent directory
try:
    from item_manager_app import (
        connect_db,
        get_all_items_with_stock,
        get_item_details,
        add_new_item,
        update_item_details,
        deactivate_item,
        reactivate_item
    )
except ImportError:
    st.error("Could not import functions from item_manager_app.py. Ensure it's in the parent directory.")
    st.stop()


# --- Initialize Session State ---
# Ensure state variables needed for this page exist
if 'item_to_edit_id' not in st.session_state: st.session_state.item_to_edit_id = None
if 'edit_form_values' not in st.session_state: st.session_state.edit_form_values = None
if 'show_inactive' not in st.session_state: st.session_state.show_inactive = False

# --- Page Content ---
st.header("Item Management")

# Establish DB connection for this page
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed on this page.")
    st.stop()
else:
    # --- Fetch Data ---
    # Fetch data once, including inactive status based on checkbox state
    items_df_with_stock = get_all_items_with_stock(db_engine, include_inactive=st.session_state.show_inactive)

    # Prepare item options list for dropdowns (used in Manage tab)
    if not items_df_with_stock.empty and 'item_id' in items_df_with_stock.columns and 'name' in items_df_with_stock.columns:
        item_options_list: List[Tuple[str, int]] = [
            (f"{row['name']}{'' if row['is_active'] else ' (Inactive)'}", row['item_id'])
            for index, row in items_df_with_stock.dropna(subset=['name']).iterrows()
        ]
        item_options_list.sort()
    else:
        item_options_list = []

    # --- Define Tabs ---
    tab_view, tab_add, tab_manage = st.tabs([
        "📊 View Items",
        "➕ Add New Item",
        "✏️ Edit / Manage Selected"
    ])

    # --- Tab 1: View Items ---
    with tab_view:
        st.subheader("View Options")
        st.checkbox("Show Deactivated Items?", key="show_inactive", value=st.session_state.show_inactive)
        st.divider()

        # Low Stock Report
        st.subheader("⚠️ Low Stock Items")
        if not items_df_with_stock.empty:
            active_items_df = items_df_with_stock[items_df_with_stock['is_active']].copy()
            if not active_items_df.empty:
                active_items_df['current_stock'] = pd.to_numeric(active_items_df['current_stock'], errors='coerce').fillna(0)
                active_items_df['reorder_point'] = pd.to_numeric(active_items_df['reorder_point'], errors='coerce').fillna(0)
                low_stock_df = active_items_df[(active_items_df['reorder_point'] > 0) & (active_items_df['current_stock'] <= active_items_df['reorder_point'])].copy()
                if low_stock_df.empty: st.info("No active items are currently at or below their reorder point.")
                else:
                    st.warning("The following active items need attention:")
                    st.dataframe(low_stock_df, use_container_width=True, hide_index=True, column_config={"item_id": "ID", "name": "Item Name", "unit": "Unit", "category": "Category", "sub_category": "Sub-Category", "permitted_departments": "Permitted Depts", "reorder_point": "Reorder Lvl", "current_stock": "Current Stock", "notes": None, "is_active": None}, column_order=[col for col in ["item_id", "name", "current_stock", "reorder_point", "unit", "category", "sub_category", "permitted_departments"] if col in low_stock_df.columns])
            else: st.info("No active items found to check stock levels.")
        else: st.info("No item data available to check stock levels.")
        st.divider()

        # Full Item List Display
        st.subheader("Full Item List" + (" (Including Deactivated)" if st.session_state.show_inactive else " (Active Only)"))
        if items_df_with_stock.empty and 'name' not in items_df_with_stock.columns: st.info("No items found.")
        else: st.dataframe(items_df_with_stock, use_container_width=True, hide_index=True, column_config={"item_id": st.column_config.NumberColumn("ID", width="small"), "name": st.column_config.TextColumn("Item Name", width="medium"), "unit": st.column_config.TextColumn("Unit", width="small"), "category": st.column_config.TextColumn("Category"), "sub_category": st.column_config.TextColumn("Sub-Category"), "permitted_departments": st.column_config.TextColumn("Permitted Depts", width="medium"), "reorder_point": st.column_config.NumberColumn("Reorder Lvl", width="small", format="%d"), "current_stock": st.column_config.NumberColumn("Current Stock", width="small", help="Calculated from transactions."), "notes": st.column_config.TextColumn("Notes", width="large"), "is_active": st.column_config.CheckboxColumn("Active?", width="small", disabled=True)}, column_order=[col for col in ["item_id", "name", "category", "sub_category", "unit", "current_stock", "reorder_point", "permitted_departments", "is_active", "notes"] if col in items_df_with_stock.columns])

    # --- Tab 2: Add New Item ---
    with tab_add:
        # Removed the expander, form is directly in the tab
        with st.form("new_item_form", clear_on_submit=True):
            st.subheader("Enter New Item Details:")
            new_name = st.text_input("Item Name*")
            new_unit = st.text_input("Unit (e.g., Kg, Pcs, Ltr)")
            new_category = st.text_input("Category")
            new_sub_category = st.text_input("Sub-Category")
            new_permitted_departments = st.text_input("Permitted Departments (Comma-separated or All)")
            new_reorder_point = st.number_input("Reorder Point", min_value=0, value=0, step=1)
            new_notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save New Item")
            if submitted:
                if not new_name: st.warning("Item Name is required.")
                else:
                    item_data = {"name": new_name.strip(), "unit": new_unit.strip() or None, "category": new_category.strip() or "Uncategorized", "sub_category": new_sub_category.strip() or "General", "permitted_departments": new_permitted_departments.strip() or None, "reorder_point": new_reorder_point, "notes": new_notes.strip() or None}
                    # Call imported function
                    success = add_new_item(db_engine, item_data)
                    if success: st.success(f"Item '{new_name}' added!"); get_all_items_with_stock.clear(); st.rerun()

    # --- Tab 3: Edit/Manage Selected Item ---
    with tab_manage:
        st.subheader("Select Item to Manage")
        edit_options = [("--- Select ---", None)] + item_options_list # Use list prepared earlier

        # Callback function to load item details when selectbox changes
        def load_item_for_edit():
            selected_option = st.session_state.item_to_edit_select; item_id_to_load = selected_option[1] if selected_option else None
            if item_id_to_load:
                # Call imported function
                details = get_item_details(db_engine, item_id_to_load)
                st.session_state.item_to_edit_id = item_id_to_load if details else None; st.session_state.edit_form_values = details if details else None
            else: st.session_state.item_to_edit_id = None; st.session_state.edit_form_values = None

        # Determine current index for selectbox
        current_edit_id = st.session_state.get('item_to_edit_id')
        try: current_index = [i for i, opt in enumerate(edit_options) if opt[1] == current_edit_id][0] if current_edit_id is not None else 0
        except IndexError: current_index = 0

        # Selectbox
        selected_item_tuple = st.selectbox(
            "Select Item:", options=edit_options, format_func=lambda x: x[0], key="item_to_edit_select",
            on_change=load_item_for_edit, index=current_index, label_visibility="collapsed"
        )

        # Conditionally display Edit form OR Reactivate button
        if st.session_state.item_to_edit_id is not None and st.session_state.edit_form_values is not None:
            current_details = st.session_state.edit_form_values; item_is_active = current_details.get('is_active', True)

            st.divider() # Separate selection from action form/buttons

            if item_is_active:
                # Show Edit Form and Deactivate Button for ACTIVE items
                with st.form("edit_item_form"):
                    st.subheader(f"Editing Item: {current_details.get('name', '')} (ID: {st.session_state.item_to_edit_id})"); edit_name = st.text_input("Item Name*", value=current_details.get('name', ''), key="edit_name"); edit_unit = st.text_input("Unit", value=current_details.get('unit', ''), key="edit_unit"); edit_category = st.text_input("Category", value=current_details.get('category', ''), key="edit_category"); edit_sub_category = st.text_input("Sub-Category", value=current_details.get('sub_category', ''), key="edit_sub_category"); edit_permitted_departments = st.text_input("Permitted Departments", value=current_details.get('permitted_departments', ''), key="edit_permitted_departments"); reorder_val = current_details.get('reorder_point', 0); edit_reorder_point = st.number_input("Reorder Point", min_value=0, value=int(reorder_val) if pd.notna(reorder_val) else 0, step=1, key="edit_reorder_point"); edit_notes = st.text_area("Notes", value=current_details.get('notes', ''), key="edit_notes")
                    update_submitted = st.form_submit_button("Update Item Details")
                    if update_submitted:
                        if not edit_name: st.warning("Item Name cannot be empty.")
                        else:
                            updated_data = {"name": st.session_state.edit_name.strip(), "unit": st.session_state.edit_unit.strip() or None, "category": st.session_state.edit_category.strip() or "Uncategorized", "sub_category": st.session_state.edit_sub_category.strip() or "General", "permitted_departments": st.session_state.edit_permitted_departments.strip() or None, "reorder_point": st.session_state.edit_reorder_point, "notes": st.session_state.edit_notes.strip() or None}
                            # Call imported function
                            update_success = update_item_details(db_engine, st.session_state.item_to_edit_id, updated_data)
                            if update_success: st.success(f"Item '{st.session_state.edit_name}' updated!"); get_all_items_with_stock.clear(); st.session_state.item_to_edit_id = None; st.session_state.edit_form_values = None; st.rerun()

                # Deactivate Button (outside the edit form, but only shown when active item selected)
                st.subheader("Deactivate Item"); st.warning("⚠️ Deactivating removes item from active lists.")
                if st.button("🗑️ Deactivate This Item", key="deactivate_button", type="secondary"):
                    item_name_to_deactivate = current_details.get('name', 'this item')
                    # Call imported function
                    deactivate_success = deactivate_item(db_engine, st.session_state.item_to_edit_id)
                    if deactivate_success: st.success(f"Item '{item_name_to_deactivate}' deactivated!"); get_all_items_with_stock.clear(); st.session_state.item_to_edit_id = None; st.session_state.edit_form_values = None; st.rerun()
                    else: st.error("Failed to deactivate item.")
            else:
                # Show Reactivate Button for INACTIVE items
                st.info(f"Item **'{current_details.get('name', '')}'** (ID: {st.session_state.item_to_edit_id}) is currently deactivated.")
                if st.button("✅ Reactivate This Item", key="reactivate_button"):
                    # Call imported function
                    reactivate_success = reactivate_item(db_engine, st.session_state.item_to_edit_id)
                    if reactivate_success: st.success(f"Item '{current_details.get('name', '')}' reactivated!"); get_all_items_with_stock.clear(); st.session_state.item_to_edit_id = None; st.session_state.edit_form_values = None; st.rerun()
                    else: st.error("Failed to reactivate item.")
        else:
             st.info("Select an item from the dropdown above to manage it.")
