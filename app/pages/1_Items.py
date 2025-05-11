# app/pages/1_Items.py
import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Tuple, Optional
import math

try:
    from app.db.database_utils import connect_db
    from app.services import item_service
except ImportError as e:
    st.error(f"Import error in 1_Items.py: {e}.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 1_Items.py: {e}")
    st.stop()

# --- Session State ---
if "item_to_edit_id" not in st.session_state: st.session_state.item_to_edit_id = None
if "edit_form_values" not in st.session_state: st.session_state.edit_form_values = None
if "show_edit_form_for_item_id" not in st.session_state: st.session_state.show_edit_form_for_item_id = None
if "show_inactive_items" not in st.session_state: st.session_state.show_inactive_items = False
if "current_page_items" not in st.session_state: st.session_state.current_page_items = 1
if "items_per_page" not in st.session_state: st.session_state.items_per_page = 10
if "item_search_name" not in st.session_state: st.session_state.item_search_name = "" # For name search
if "item_filter_category" not in st.session_state: st.session_state.item_filter_category = "All" # For category filter
if "item_filter_subcategory" not in st.session_state: st.session_state.item_filter_subcategory = "All" # For sub-category filter


@st.cache_data(ttl=60)
def fetch_all_items_df(_engine, show_inactive: bool) -> pd.DataFrame:
    return item_service.get_all_items_with_stock(_engine, include_inactive=show_inactive)

# Suggestion 1: Change st.header to st.title
st.title("📦 Item Master Management")
st.write("Manage your inventory items: add new items, edit existing ones, and view stock levels.")
st.divider()

engine = connect_db()
if not engine: st.error("Database connection failed."); st.stop()

# --- ADD NEW ITEM Section ---
with st.expander("➕ Add New Inventory Item", expanded=False):
    with st.form("add_item_form_v2", clear_on_submit=True):
        st.subheader("Enter New Item Details")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Item Name*", help="Unique name for the item.", key="add_item_name_v2")
            unit = st.text_input("Unit of Measure (UoM)*", help="e.g., KG, LTR, PCS", key="add_item_unit_v2")
            category = st.text_input("Category", value="Uncategorized", help="e.g., Vegetables, Grains.", key="add_item_category_v2")
            sub_category = st.text_input("Sub-Category", value="General", help="e.g., Leafy Greens, Rice.", key="add_item_subcategory_v2")
        with col2:
            # Suggestion 2: Improved help text for Permitted Departments
            permitted_departments = st.text_input(
                "Permitted Departments",
                help="Enter department names separated by commas (e.g., Kitchen, Bar).",
                key="add_item_depts_v2"
            )
            reorder_point = st.number_input("Reorder At", min_value=0.0, value=0.0, step=0.1, format="%.2f", help="Stock level to reorder.", key="add_item_reorder_v2")
            initial_stock = st.number_input("Initial Stock Quantity", min_value=0.0, value=0.0, step=0.1, format="%.2f", help="Current stock on hand.", key="add_item_initial_stock_v2")
        notes = st.text_area("Notes / Description", placeholder="Optional details.", key="add_item_notes_v2")
        
        if st.form_submit_button("💾 Add Item to Master"):
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
                    st.success(message); fetch_all_items_df.clear(); st.rerun()
                else: st.error(message)
st.divider()

# --- VIEW & MANAGE EXISTING ITEMS ---
st.subheader("🔍 View & Manage Existing Items")

all_items_df = fetch_all_items_df(engine, st.session_state.show_inactive_items)
filtered_items_df = all_items_df.copy()

filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 2, 2, 1])
with filter_col1:
    st.session_state.item_search_name = st.text_input(
        "Search by Item Name",
        value=st.session_state.item_search_name,
        key="item_search_name_input",
        placeholder="e.g., Tomato, Rice"
    )
unique_categories = ["All"] + sorted(all_items_df['category'].astype(str).replace('nan', 'Uncategorized').replace('', 'Uncategorized').unique().tolist())
unique_subcategories = ["All"]
with filter_col2:
    st.session_state.item_filter_category = st.selectbox(
        "Filter by Category",
        options=unique_categories,
        key="item_category_filter_select",
        index=unique_categories.index(st.session_state.item_filter_category) if st.session_state.item_filter_category in unique_categories else 0
    )
if st.session_state.item_filter_category != "All":
    category_filtered_df = filtered_items_df[filtered_items_df['category'].astype(str) == st.session_state.item_filter_category]
    unique_subcategories.extend(sorted(category_filtered_df['sub_category'].astype(str).replace('nan', 'General').replace('', 'General').unique().tolist()))
else:
    unique_subcategories.extend(sorted(all_items_df['sub_category'].astype(str).replace('nan', 'General').replace('', 'General').unique().tolist()))
    unique_subcategories = sorted(list(set(unique_subcategories)))
with filter_col3:
    st.session_state.item_filter_subcategory = st.selectbox(
        "Filter by Sub-Category",
        options=unique_subcategories,
        key="item_subcategory_filter_select",
        index=unique_subcategories.index(st.session_state.item_filter_subcategory) if st.session_state.item_filter_subcategory in unique_subcategories else 0
    )
with filter_col4:
    st.session_state.show_inactive_items = st.toggle(
        "Show Inactive",
        value=st.session_state.show_inactive_items,
        key="show_inactive_toggle_items_v5",
        help="Toggle to include inactive items in the list"
    )

if st.session_state.item_search_name:
    search_term = st.session_state.item_search_name.lower()
    filtered_items_df = filtered_items_df[filtered_items_df['name'].astype(str).str.lower().str.contains(search_term, na=False)]
if st.session_state.item_filter_category != "All":
    filtered_items_df = filtered_items_df[filtered_items_df['category'].astype(str) == st.session_state.item_filter_category]
if st.session_state.item_filter_subcategory != "All":
    filtered_items_df = filtered_items_df[filtered_items_df['sub_category'].astype(str) == st.session_state.item_filter_subcategory]

if filtered_items_df.empty:
    st.info("No items found matching your criteria." if (st.session_state.item_search_name or
                                                      st.session_state.item_filter_category != "All" or
                                                      st.session_state.item_filter_subcategory != "All" or
                                                      st.session_state.show_inactive_items)
            else "No active items found. Add items or adjust filters.")
else:
    total_items = len(filtered_items_df)
    st.write(f"Found {total_items} item(s) matching your criteria.")

    items_per_page_options = [5, 10, 20, 50]
    current_ipp_value = st.session_state.items_per_page
    if current_ipp_value not in items_per_page_options:
        current_ipp_value = items_per_page_options[0]
        st.session_state.items_per_page = current_ipp_value
    st.session_state.items_per_page = st.selectbox(
        "Items per page:", options=items_per_page_options,
        index=items_per_page_options.index(current_ipp_value),
        key="items_per_page_selector_v2"
    )
    
    total_pages = math.ceil(total_items / st.session_state.items_per_page)
    if total_pages == 0: total_pages = 1
    if st.session_state.current_page_items > total_pages: st.session_state.current_page_items = total_pages
    if st.session_state.current_page_items < 1: st.session_state.current_page_items = 1
        
    page_nav_cols = st.columns(5)
    if page_nav_cols[0].button("⏮️ First", key="items_first_page_v2", disabled=(st.session_state.current_page_items == 1)):
        st.session_state.current_page_items = 1; st.session_state.show_edit_form_for_item_id = None; st.rerun()
    if page_nav_cols[1].button("⬅️ Previous", key="items_prev_page_v2", disabled=(st.session_state.current_page_items == 1)):
        st.session_state.current_page_items -= 1; st.session_state.show_edit_form_for_item_id = None; st.rerun()
    page_nav_cols[2].write(f"Page {st.session_state.current_page_items} of {total_pages}")
    if page_nav_cols[3].button("Next ➡️", key="items_next_page_v2", disabled=(st.session_state.current_page_items == total_pages)):
        st.session_state.current_page_items += 1; st.session_state.show_edit_form_for_item_id = None; st.rerun()
    if page_nav_cols[4].button("Last ⏭️", key="items_last_page_v2", disabled=(st.session_state.current_page_items == total_pages)):
        st.session_state.current_page_items = total_pages; st.session_state.show_edit_form_for_item_id = None; st.rerun()

    start_idx = (st.session_state.current_page_items - 1) * st.session_state.items_per_page
    end_idx = start_idx + st.session_state.items_per_page
    paginated_items_df = filtered_items_df.iloc[start_idx:end_idx]

    # Suggestion 3: Change list header "Permitted Depts" to "Permitted Departments"
    cols_header = st.columns((3, 1, 2, 1, 1, 1, 2.5, 2.5)) # Adjusted widths slightly for longer header
    headers = ["Name", "UoM", "Category", "Stock", "Reorder At", "Active", "Permitted Departments", "Actions"]
    for col, header in zip(cols_header, headers): col.markdown(f"**{header}**")
    st.divider()

    for index, item_row in paginated_items_df.iterrows():
        item_id = item_row['item_id']; item_name = item_row['name']; is_active = item_row['is_active']
        cols = st.columns((3, 1, 2, 1, 1, 1, 2.5, 2.5)) # Matched header column widths
        cols[0].write(item_name)
        cols[1].write(item_row['unit'])
        cols[2].write(item_row.get('category', 'N/A'))
        cols[3].write(f"{item_row.get('current_stock', 0):.2f}")
        cols[4].write(f"{item_row.get('reorder_point', 0):.2f}")
        cols[5].checkbox("", value=is_active, disabled=True, key=f"active_disp_paginated_v2_{item_id}")
        cols[6].caption(item_row.get('permitted_departments') or "N/A")

        with cols[7]:
            button_key_prefix = f"action_paginated_v2_{item_id}"
            if st.session_state.get('show_edit_form_for_item_id') == item_id:
                if st.button("✖️ Cancel Edit", key=f"{button_key_prefix}_cancel_edit", type="secondary"):
                    st.session_state.show_edit_form_for_item_id = None; st.rerun()
            else:
                if is_active:
                    if st.button("✏️ Edit", key=f"{button_key_prefix}_edit", type="primary"):
                        st.session_state.show_edit_form_for_item_id = item_id
                        st.session_state.edit_form_values = item_service.get_item_details(engine, item_id)
                        st.rerun()
                    if st.button("🗑️ Deactivate", key=f"{button_key_prefix}_deact"):
                        if item_service.deactivate_item(engine, item_id):
                            st.success(f"'{item_name}' deactivated."); fetch_all_items_df.clear(); st.rerun()
                        else: st.error(f"Failed to deactivate '{item_name}'.")
                else:
                    if st.button("✅ Reactivate", key=f"{button_key_prefix}_react"):
                        if item_service.reactivate_item(engine, item_id):
                            st.success(f"'{item_name}' reactivated."); fetch_all_items_df.clear(); st.rerun()
                        else: st.error(f"Failed to reactivate '{item_name}'.")
        st.divider()

        if st.session_state.get('show_edit_form_for_item_id') == item_id:
            current_values_for_edit = st.session_state.get('edit_form_values')
            if not current_values_for_edit:
                current_values_for_edit = item_service.get_item_details(engine, item_id)
                st.session_state.edit_form_values = current_values_for_edit
            if current_values_for_edit:
                with st.form(key=f"edit_form_inline_v2_{item_id}"):
                    st.subheader(f"✏️ Editing: {current_values_for_edit.get('name', 'Item')}")
                    st.caption(f"ID: {item_id} | Stock: {current_values_for_edit.get('current_stock',0):.2f}")
                    edit_form_col1, edit_form_col2 = st.columns(2)
                    with edit_form_col1:
                        e_name = st.text_input("Item Name*", value=current_values_for_edit.get('name', ''), key=f"e_name_v2_{item_id}")
                        e_unit = st.text_input("UoM*", value=current_values_for_edit.get('unit', ''), key=f"e_unit_v2_{item_id}")
                        e_category = st.text_input("Category", value=current_values_for_edit.get('category', ''), key=f"e_cat_v2_{item_id}")
                        e_sub_category = st.text_input("Sub-Category", value=current_values_for_edit.get('sub_category', ''), key=f"e_subcat_v2_{item_id}")
                    with edit_form_col2:
                        # Suggestion 3: Change edit form label "Permitted Depts" to "Permitted Departments"
                        e_permitted = st.text_input(
                            "Permitted Departments", # Changed label
                            value=current_values_for_edit.get('permitted_departments', '') or '',
                            key=f"e_depts_v2_{item_id}",
                            help="Enter department names separated by commas (e.g., Kitchen, Bar)." # Added help text here too
                        )
                        e_rp = st.number_input("Reorder At", min_value=0.0, value=float(current_values_for_edit.get('reorder_point', 0.0)), step=0.1, format="%.2f", key=f"e_rp_v2_{item_id}")
                    e_notes = st.text_area("Notes", value=current_values_for_edit.get('notes', '') or '', key=f"e_notes_v2_{item_id}")
                    
                    if st.form_submit_button("💾 Update Item Details"):
                        is_valid_edit = True
                        if not e_name: st.warning("Item Name required."); is_valid_edit = False
                        if not e_unit: st.warning("UoM required."); is_valid_edit = False
                        if is_valid_edit:
                            update_data = {"name": e_name.strip(), "unit": e_unit.strip(), "category": e_category.strip() or "Uncategorized",
                                           "sub_category": e_sub_category.strip() or "General", "permitted_departments": e_permitted.strip() or None,
                                           "reorder_point": float(e_rp), "notes": e_notes.strip() or None}
                            ok, msg = item_service.update_item_details(engine, item_id, update_data)
                            if ok:
                                st.success(msg); st.session_state.show_edit_form_for_item_id = None
                                fetch_all_items_df.clear(); st.rerun()
                            else: st.error(msg)
                st.divider()