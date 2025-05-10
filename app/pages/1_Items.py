# app/pages/1_Items.py
import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Tuple, Optional
import math

try:
    from app.db.database_utils import connect_db
    from app.services import item_service # For all item-related functions
except ImportError as e:
    st.error(f"Import error in 1_Items.py: {e}. Ensure 'INVENTORY-APP' is the root for 'streamlit run app/item_manager_app.py'.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 1_Items.py: {e}")
    st.stop()

# Session state
if "item_to_edit_id" not in st.session_state: st.session_state.item_to_edit_id = None
if "edit_form_values" not in st.session_state: st.session_state.edit_form_values = None
if "show_inactive" not in st.session_state: st.session_state.show_inactive = False

@st.cache_data(ttl=60)
def fetch_items_for_display(_engine, show_inactive: bool) -> pd.DataFrame:
    return item_service.get_all_items_with_stock(_engine, include_inactive=show_inactive)

# Page Setup
st.header("📦 Item Master Management")
st.write("Manage your inventory items: add new items, edit existing ones, and view stock levels.")
st.divider()

engine = connect_db()
if not engine:
    st.error("Database connection failed. Cannot manage items.")
    st.stop()

# ADD NEW ITEM Section
with st.expander("➕ Add New Inventory Item", expanded=False):
    with st.form("add_item_form", clear_on_submit=True):
        st.subheader("Enter New Item Details")

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Item Name*", help="Unique name for the inventory item (e.g., 'Roma Tomatoes', 'Basmati Rice XL').")
            unit = st.text_input("Unit of Measure (UoM)*", help="e.g., KG, LTR, PCS, BTL, Pack of 12")
            category = st.text_input("Category", value="Uncategorized", help="e.g., Vegetables, Grains, Dairy, Beverages.")
            sub_category = st.text_input("Sub-Category", value="General", help="e.g., Leafy Greens, Rice, Milk, Soft Drinks.")
        with col2:
            permitted_departments = st.text_input(
                "Permitted Departments",
                help="Comma-separated list of departments allowed to request this item (e.g., Kitchen, Bar, Service)"
            )
            reorder_point = st.number_input("Reorder At", min_value=0.0, value=0.0, step=0.1, format="%.2f", help="Stock level at which to reorder.")
            initial_stock = st.number_input("Initial Stock Quantity", min_value=0.0, value=0.0, step=0.1, format="%.2f", help="Current stock on hand. Will create an initial stock transaction.")

        notes = st.text_area("Notes / Description", placeholder="Optional: any specific details about the item, brand, storage instructions, etc.")

        submitted = st.form_submit_button("💾 Add Item to Master")
        if submitted:
            is_valid = True
            if not name: st.warning("Item Name is required."); is_valid = False
            if not unit: st.warning("Unit of Measure (UoM) is required."); is_valid = False
            if is_valid:
                item_data = {"name": name.strip(), "unit": unit.strip(), "category": category.strip() or "Uncategorized",
                             "sub_category": sub_category.strip() or "General",
                             "permitted_departments": permitted_departments.strip() or None,
                             "reorder_point": float(reorder_point), "current_stock": float(initial_stock),
                             "notes": notes.strip() or None, "is_active": True}
                success, message = item_service.add_new_item(engine, item_data)
                if success:
                    st.success(message)
                    fetch_items_for_display.clear()
                    # item_service.add_new_item already clears its dependent caches in item_service
                    st.rerun()
                else: st.error(message)

st.divider()
st.subheader("🔍 View & Manage Existing Items")

col_toggle, _ = st.columns([1,3]) # Use underscore for unused column variable
with col_toggle:
    show_inactive_items = st.toggle(
        "Show Inactive Items",
        value=st.session_state.show_inactive,
        key="show_inactive_toggle_items"
    )
    st.session_state.show_inactive = show_inactive_items

items_df_display = fetch_items_for_display(engine, st.session_state.show_inactive)

if items_df_display.empty:
    st.info("No items found matching your criteria." if st.session_state.show_inactive else "No active items found. Toggle 'Show Inactive Items' to see all.")
else:
    st.write(f"Displaying {len(items_df_display)} item(s):")
    item_options_for_select = items_df_display[['item_id', 'name', 'unit', 'is_active']].copy()
    item_options_for_select['display_name'] = item_options_for_select.apply(
        lambda r: f"{r['name']} ({r['unit']})" + (" [Inactive]" if not r['is_active'] else ""), axis=1
    )
    item_dict_for_select = pd.Series(item_options_for_select.item_id.values, index=item_options_for_select.display_name).to_dict()
    
    # To handle the selectbox index correctly if the list of items changes (e.g. after add/deactivate)
    # we re-evaluate selected_display_name and its index each time.
    current_selection_id = st.session_state.get('item_to_edit_id')
    select_options_list = list(item_dict_for_select.keys())
    selected_display_name = next((name for name, id_ in item_dict_for_select.items() if id_ == current_selection_id), None)
    
    current_index = 0
    if selected_display_name and selected_display_name in select_options_list:
        current_index = select_options_list.index(selected_display_name)
    elif select_options_list: # Default to first item if previous selection is gone
        selected_display_name = select_options_list[0]
        # Optionally auto-load the first item if no specific item was being edited
        # if st.session_state.item_to_edit_id is None and item_dict_for_select.get(selected_display_name):
        #    st.session_state.item_to_edit_id = item_dict_for_select[selected_display_name]
        #    st.session_state.edit_form_values = item_service.get_item_details(engine, st.session_state.item_to_edit_id)

    def load_item_for_edit_ux(): # UX stands for User Experience, just a naming choice
        selected_name_from_widget = st.session_state.item_select_key_details # Use the key of the selectbox
        if selected_name_from_widget and selected_name_from_widget in item_dict_for_select:
            item_id_to_load = item_dict_for_select[selected_name_from_widget]
            st.session_state.item_to_edit_id = item_id_to_load
            st.session_state.edit_form_values = item_service.get_item_details(engine, item_id_to_load)
        else: # No selection or invalid selection
            st.session_state.item_to_edit_id = None
            st.session_state.edit_form_values = None
        # No st.rerun() here, let Streamlit handle the natural flow after on_change

    st.selectbox(
        "Select Item to View/Edit Details:",
        options=select_options_list,
        index=current_index,
        key="item_select_key_details",
        on_change=load_item_for_edit_ux,
        placeholder="Choose an item to see/edit details below..."
    )
    
    # Trigger initial load if an item_id is in session state but form_values are not (e.g., after rerun)
    if st.session_state.item_to_edit_id and not st.session_state.edit_form_values:
        st.session_state.edit_form_values = item_service.get_item_details(engine, st.session_state.item_to_edit_id)


    st.dataframe(
        items_df_display,
        use_container_width=True,
        hide_index=True,
        column_order=["name", "unit", "category", "sub_category", "current_stock", "reorder_point", "permitted_departments", "is_active", "notes", "item_id"],
        column_config={
            "item_id": st.column_config.NumberColumn("ID", width="small", help="Unique Item Identifier"),
            "name": st.column_config.TextColumn("Item Name", help="Name of the inventory item"),
            "unit": st.column_config.TextColumn("UoM", width="small", help="Unit of Measure (e.g., KG, PCS)"),
            "category": "Category", "sub_category": "Sub-Category",
            "current_stock": st.column_config.NumberColumn("Stock on Hand", format="%.2f", width="small"),
            "reorder_point": st.column_config.NumberColumn("Reorder At", format="%.2f", width="small"),
            "permitted_departments": st.column_config.TextColumn("Permitted Depts", help="Departments allowed to request this item"),
            "is_active": st.column_config.CheckboxColumn("Active?", width="small", help="Is this item currently in use?"),
            "notes": st.column_config.TextColumn("Notes / Description")
        }
    )

    # --- This is the Edit/Deactivate/Reactivate section ---
    if st.session_state.item_to_edit_id and st.session_state.edit_form_values:
        st.divider()
        current_values_for_edit = st.session_state.edit_form_values # Use a different variable name
        st.subheader(f"📝 Edit Details for: {current_values_for_edit.get('name', 'N/A')}")
        is_currently_active = current_values_for_edit.get('is_active', False)

        if is_currently_active:
            with st.form("edit_item_form_actual"): # Ensure unique form key
                st.caption(f"Item ID: {st.session_state.item_to_edit_id} | Current Stock: {current_values_for_edit.get('current_stock', 0):.2f} (Stock cannot be edited here. Use Stock Movements page.)")
                
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    e_name = st.text_input("Item Name*", value=current_values_for_edit.get('name', ''), key="edit_item_name_input")
                    e_unit = st.text_input("Unit of Measure (UoM)*", value=current_values_for_edit.get('unit', ''), key="edit_item_unit_input")
                    e_category = st.text_input("Category", value=current_values_for_edit.get('category', ''), key="edit_item_category_input")
                    e_sub_category = st.text_input("Sub-Category", value=current_values_for_edit.get('sub_category', ''), key="edit_item_subcategory_input")
                with edit_col2:
                    e_permitted = st.text_input("Permitted Departments", value=current_values_for_edit.get('permitted_departments', '') or '', key="edit_item_permitted_depts_input")
                    e_rp = st.number_input("Reorder At", min_value=0.0, value=float(current_values_for_edit.get('reorder_point', 0.0)), step=0.1, format="%.2f", key="edit_item_reorder_point_input")
                
                e_notes = st.text_area("Notes / Description", value=current_values_for_edit.get('notes', '') or '', key="edit_item_notes_input")

                if st.form_submit_button("💾 Update Item Details"):
                    is_valid_edit = True
                    if not e_name: st.warning("Item Name required."); is_valid_edit = False
                    if not e_unit: st.warning("Unit of Measure (UoM) required."); is_valid_edit = False
                    if is_valid_edit:
                        update_data = {"name": e_name.strip(), "unit": e_unit.strip(), "category": e_category.strip() or "Uncategorized",
                                       "sub_category": e_sub_category.strip() or "General", "permitted_departments": e_permitted.strip() or None,
                                       "reorder_point": float(e_rp), "notes": e_notes.strip() or None}
                        ok, msg = item_service.update_item_details(engine, st.session_state.item_to_edit_id, update_data)
                        if ok:
                            st.success(msg)
                            st.session_state.item_to_edit_id = None # Reset selection
                            st.session_state.edit_form_values = None # Clear form values
                            fetch_items_for_display.clear() # Clear page cache
                            st.rerun()
                        else: st.error(msg)
            
            st.divider()
            st.subheader(f"Deactivate '{current_values_for_edit.get('name', 'Item')}'")
            st.caption(f"Deactivating this item will mark it as inactive. It will not be available for new indents or stock movements but will remain in historical records.")
            if st.button(f"🗑️ Deactivate '{current_values_for_edit.get('name', 'Item')}'", key="deactivate_item_btn"):
                if item_service.deactivate_item(engine, st.session_state.item_to_edit_id):
                    st.success(f"'{current_values_for_edit.get('name', 'Item')}' deactivated.")
                    st.session_state.item_to_edit_id = None
                    st.session_state.edit_form_values = None
                    fetch_items_for_display.clear()
                    st.rerun()
                else: st.error(f"Failed to deactivate '{current_values_for_edit.get('name', 'item')}'.")
        else: # Item is currently inactive
            st.info(f"'{current_values_for_edit.get('name', 'This item')}' is currently deactivated.")
            if st.button(f"✅ Reactivate '{current_values_for_edit.get('name', 'Item')}'", key="reactivate_item_btn"):
                if item_service.reactivate_item(engine, st.session_state.item_to_edit_id):
                    st.success(f"'{current_values_for_edit.get('name', 'Item')}' reactivated.")
                    st.session_state.item_to_edit_id = None
                    st.session_state.edit_form_values = None
                    fetch_items_for_display.clear()
                    st.rerun()
                else: st.error(f"Failed to reactivate '{current_values_for_edit.get('name', 'item')}'.")
    elif st.session_state.item_select_key_details and st.session_state.item_select_key_details != list(item_dict_for_select.keys())[0] : # If an item is selected but no details (e.g. it became inactive)
        st.warning("Selected item details could not be loaded, it might have been deactivated or changed. Please re-select from the list.")
    else: # No item selected for detailed view/edit
        st.info("Select an item from the dropdown above to view or edit its details.")