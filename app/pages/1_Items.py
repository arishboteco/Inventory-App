# app/pages/1_Items.py
import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Tuple, Optional
import math

try:
    from app.db.database_utils import connect_db
    from app.services import item_service
    from app.core.constants import (
        FILTER_ALL_CATEGORIES, 
        FILTER_ALL_SUBCATEGORIES
    )
except ImportError as e:
    st.error(f"Import error in 1_Items.py: {e}.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 1_Items.py: {e}")
    st.stop()

# --- Session State ---
if "pg1_item_to_edit_id" not in st.session_state: st.session_state.pg1_item_to_edit_id = None
if "pg1_edit_form_values" not in st.session_state: st.session_state.pg1_edit_form_values = None
if "pg1_show_edit_form_for_item_id" not in st.session_state: st.session_state.pg1_show_edit_form_for_item_id = None
if "pg1_show_inactive_items" not in st.session_state: st.session_state.pg1_show_inactive_items = False
if "pg1_current_page_items" not in st.session_state: st.session_state.pg1_current_page_items = 1
if "pg1_items_per_page" not in st.session_state: st.session_state.pg1_items_per_page = 10
if "pg1_item_search_name" not in st.session_state: st.session_state.pg1_item_search_name = "" 

# Initialize filter states if they don't exist
if "pg1_item_filter_category" not in st.session_state: 
    st.session_state.pg1_item_filter_category = FILTER_ALL_CATEGORIES
if "pg1_item_filter_subcategory" not in st.session_state: 
    st.session_state.pg1_item_filter_subcategory = FILTER_ALL_SUBCATEGORIES


@st.cache_data(ttl=60)
def fetch_all_items_df_pg1(_engine, show_inactive: bool) -> pd.DataFrame:
    return item_service.get_all_items_with_stock(_engine, include_inactive=show_inactive)

st.title("📦 Item Master Management")
st.write("Manage your inventory items: add new items, edit existing ones, and view stock levels.")
st.divider()

engine = connect_db()
if not engine: 
    st.error("Database connection failed. Item Management functionality is unavailable.")
    st.stop()

# --- ADD NEW ITEM Section ---
# ... (Add item section remains the same as your last working version for it) ...
with st.expander("➕ Add New Inventory Item", expanded=False):
    with st.form("add_item_form_pg1_v3", clear_on_submit=True): 
        st.subheader("Enter New Item Details")
        col1_add_pg1, col2_add_pg1 = st.columns(2)
        with col1_add_pg1:
            name_add_pg1 = st.text_input("Item Name*", help="Unique name for the item.", key="add_item_name_pg1_v3")
            unit_add_pg1 = st.text_input("Unit of Measure (UoM)*", help="e.g., KG, LTR, PCS", key="add_item_unit_pg1_v3")
            category_add_pg1 = st.text_input("Category", value="Uncategorized", help="e.g., Vegetables, Grains.", key="add_item_category_pg1_v3")
            sub_category_add_pg1 = st.text_input("Sub-Category", value="General", help="e.g., Leafy Greens, Rice.", key="add_item_subcategory_pg1_v3")
        with col2_add_pg1:
            permitted_departments_add_pg1 = st.text_input(
                "Permitted Departments",
                help="Enter department names separated by commas (e.g., Kitchen, Bar).",
                key="add_item_depts_pg1_v3"
            )
            reorder_point_add_pg1 = st.number_input("Reorder At", min_value=0.0, value=0.0, step=0.01, format="%.2f", help="Stock level to reorder.", key="add_item_reorder_pg1_v3")
            initial_stock_add_pg1 = st.number_input("Initial Stock Quantity", min_value=0.0, value=0.0, step=0.01, format="%.2f", help="Current stock on hand.", key="add_item_initial_stock_pg1_v3")
        notes_add_pg1 = st.text_area("Notes / Description", placeholder="Optional details about the item.", key="add_item_notes_pg1_v3")
        
        if st.form_submit_button("💾 Add Item to Master"):
            is_valid_add_pg1 = True
            if not name_add_pg1.strip(): st.warning("Item Name is required."); is_valid_add_pg1 = False
            if not unit_add_pg1.strip(): st.warning("Unit of Measure (UoM) is required."); is_valid_add_pg1 = False
            
            if is_valid_add_pg1:
                item_data_add_pg1 = {
                    "name": name_add_pg1.strip(), 
                    "unit": unit_add_pg1.strip(), 
                    "category": category_add_pg1.strip() or "Uncategorized",
                    "sub_category": sub_category_add_pg1.strip() or "General",
                    "permitted_departments": permitted_departments_add_pg1.strip() or None,
                    "reorder_point": float(reorder_point_add_pg1), 
                    "current_stock": float(initial_stock_add_pg1),
                    "notes": notes_add_pg1.strip() or None, 
                    "is_active": True
                }
                # Assuming add_new_item in item_service was corrected for the 'NoneType' strip error
                success_add_pg1, message_add_pg1 = item_service.add_new_item(engine, item_data_add_pg1)
                if success_add_pg1:
                    st.success(message_add_pg1)
                    fetch_all_items_df_pg1.clear() 
                    st.rerun()
                else: 
                    st.error(message_add_pg1)
st.divider()

# --- VIEW & MANAGE EXISTING ITEMS ---
st.subheader("🔍 View & Manage Existing Items")

# --- Filter Callbacks ---
def on_category_filter_change():
    # When category changes, reset subcategory to "All"
    st.session_state.pg1_item_filter_subcategory = FILTER_ALL_SUBCATEGORIES
    # Note: A rerun will happen automatically after this callback due to widget interaction.

# Define filter widgets
filter_col1_view_pg1, filter_col2_view_pg1, filter_col3_view_pg1, filter_col4_view_pg1 = st.columns([2, 2, 2, 1])
with filter_col1_view_pg1:
    st.session_state.pg1_item_search_name = st.text_input(
        "Search by Item Name",
        value=st.session_state.pg1_item_search_name, # Use existing session state value
        key="item_search_name_input_pg1_v4", 
        placeholder="e.g., Tomato, Rice"
    )
with filter_col4_view_pg1: 
    st.session_state.pg1_show_inactive_items = st.toggle(
        "Show Inactive",
        value=st.session_state.pg1_show_inactive_items, # Use existing session state value
        key="show_inactive_toggle_items_pg1_v7", 
        help="Toggle to include inactive items in the list"
        # The rerun caused by toggle will make fetch_all_items_df_pg1 use the new state
    )

# Fetch data based on the current state of the 'show_inactive_items' toggle
all_items_df_for_page = fetch_all_items_df_pg1(engine, st.session_state.pg1_show_inactive_items)
filtered_items_df_for_page = all_items_df_for_page.copy()


unique_categories_options_pg1 = [FILTER_ALL_CATEGORIES]
if not all_items_df_for_page.empty:
    unique_categories_options_pg1.extend(
        sorted(all_items_df_for_page['category'].astype(str).replace('nan', 'Uncategorized').replace('', 'Uncategorized').unique().tolist())
    )

with filter_col2_view_pg1:
    # Get current category value from session state
    current_category_val = st.session_state.pg1_item_filter_category
    category_idx = 0
    if current_category_val in unique_categories_options_pg1:
        category_idx = unique_categories_options_pg1.index(current_category_val)
    
    st.selectbox( # Assign to session state directly is fine if on_change handles side effects
        "Filter by Category",
        options=unique_categories_options_pg1,
        key="pg1_item_filter_category", # Make key same as session state key
        index=category_idx,
        on_change=on_category_filter_change # Add the callback here
    )

# Dynamically update subcategory options based on selected category
unique_subcategories_options_pg1 = [FILTER_ALL_SUBCATEGORIES]
if st.session_state.pg1_item_filter_category != FILTER_ALL_CATEGORIES:
    if not all_items_df_for_page.empty:
        category_filtered_df_for_subcat_pg1 = all_items_df_for_page[
            all_items_df_for_page['category'].astype(str) == st.session_state.pg1_item_filter_category
        ]
        if not category_filtered_df_for_subcat_pg1.empty:
            unique_subcategories_options_pg1.extend(
                sorted(category_filtered_df_for_subcat_pg1['sub_category'].astype(str).replace('nan', 'General').replace('', 'General').unique().tolist())
            )
else: 
    if not all_items_df_for_page.empty:
        unique_subcategories_options_pg1.extend(
            sorted(all_items_df_for_page['sub_category'].astype(str).replace('nan', 'General').replace('', 'General').unique().tolist())
        )
unique_subcategories_options_pg1 = sorted(list(set(unique_subcategories_options_pg1))) 

with filter_col3_view_pg1:
    current_subcategory_val = st.session_state.pg1_item_filter_subcategory
    subcategory_idx = 0
    if current_subcategory_val in unique_subcategories_options_pg1:
        subcategory_idx = unique_subcategories_options_pg1.index(current_subcategory_val)
    else: # If current subcategory not in new options, default to "All"
        st.session_state.pg1_item_filter_subcategory = FILTER_ALL_SUBCATEGORIES 
        # subcategory_idx remains 0 (index of FILTER_ALL_SUBCATEGORIES)

    st.selectbox( # Assign to session state directly
        "Filter by Sub-Category",
        options=unique_subcategories_options_pg1,
        key="pg1_item_filter_subcategory", # Make key same as session state key
        index=subcategory_idx
    )

# Apply filters to the 'filtered_items_df_for_page'
if st.session_state.pg1_item_search_name:
    search_term_filter_pg1 = st.session_state.pg1_item_search_name.lower()
    filtered_items_df_for_page = filtered_items_df_for_page[filtered_items_df_for_page['name'].astype(str).str.lower().str.contains(search_term_filter_pg1, na=False)]
if st.session_state.pg1_item_filter_category != FILTER_ALL_CATEGORIES: 
    filtered_items_df_for_page = filtered_items_df_for_page[filtered_items_df_for_page['category'].astype(str) == st.session_state.pg1_item_filter_category]
if st.session_state.pg1_item_filter_subcategory != FILTER_ALL_SUBCATEGORIES: 
    filtered_items_df_for_page = filtered_items_df_for_page[filtered_items_df_for_page['sub_category'].astype(str) == st.session_state.pg1_item_filter_subcategory]

# Display logic for filtered items
if filtered_items_df_for_page.empty:
    st.info("No items found matching your criteria." if (st.session_state.pg1_item_search_name or
                                                      st.session_state.pg1_item_filter_category != FILTER_ALL_CATEGORIES or
                                                      st.session_state.pg1_item_filter_subcategory != FILTER_ALL_SUBCATEGORIES or
                                                      st.session_state.pg1_show_inactive_items)
            else "No active items found. Add items or adjust filters.")
else:
    # ... (Pagination and Item Display Logic - KEEP THIS AS IT WAS IN YOUR LAST WORKING VERSION for this section)
    # Ensure variable names like filtered_items_df_for_page are used consistently here.
    total_items_display_pg1 = len(filtered_items_df_for_page) 
    st.write(f"Found {total_items_display_pg1} item(s) matching your criteria.")

    items_per_page_options_list_pg1 = [5, 10, 20, 50]
    current_ipp_val_pg1 = st.session_state.pg1_items_per_page
    if current_ipp_val_pg1 not in items_per_page_options_list_pg1: 
        current_ipp_val_pg1 = items_per_page_options_list_pg1[0]
        st.session_state.pg1_items_per_page = current_ipp_val_pg1
        
    st.session_state.pg1_items_per_page = st.selectbox(
        "Items per page:", options=items_per_page_options_list_pg1,
        index=items_per_page_options_list_pg1.index(current_ipp_val_pg1),
        key="items_per_page_selector_pg1_v4" 
    )
    
    total_pages_calc_pg1 = math.ceil(total_items_display_pg1 / st.session_state.pg1_items_per_page)
    if total_pages_calc_pg1 == 0: total_pages_calc_pg1 = 1 
    if st.session_state.pg1_current_page_items > total_pages_calc_pg1: st.session_state.pg1_current_page_items = total_pages_calc_pg1
    if st.session_state.pg1_current_page_items < 1: st.session_state.pg1_current_page_items = 1
        
    page_nav_cols_display_pg1 = st.columns(5)
    if page_nav_cols_display_pg1[0].button("⏮️ First", key="items_first_page_pg1_v4", disabled=(st.session_state.pg1_current_page_items == 1)):
        st.session_state.pg1_current_page_items = 1; st.session_state.pg1_show_edit_form_for_item_id = None; st.rerun()
    if page_nav_cols_display_pg1[1].button("⬅️ Previous", key="items_prev_page_pg1_v4", disabled=(st.session_state.pg1_current_page_items == 1)):
        st.session_state.pg1_current_page_items -= 1; st.session_state.pg1_show_edit_form_for_item_id = None; st.rerun()
    page_nav_cols_display_pg1[2].write(f"Page {st.session_state.pg1_current_page_items} of {total_pages_calc_pg1}")
    if page_nav_cols_display_pg1[3].button("Next ➡️", key="items_next_page_pg1_v4", disabled=(st.session_state.pg1_current_page_items == total_pages_calc_pg1)):
        st.session_state.pg1_current_page_items += 1; st.session_state.pg1_show_edit_form_for_item_id = None; st.rerun()
    if page_nav_cols_display_pg1[4].button("Last ⏭️", key="items_last_page_pg1_v4", disabled=(st.session_state.pg1_current_page_items == total_pages_calc_pg1)):
        st.session_state.pg1_current_page_items = total_pages_calc_pg1; st.session_state.pg1_show_edit_form_for_item_id = None; st.rerun()

    start_idx_display_pg1 = (st.session_state.pg1_current_page_items - 1) * st.session_state.pg1_items_per_page
    end_idx_display_pg1 = start_idx_display_pg1 + st.session_state.pg1_items_per_page
    paginated_items_df_display_pg1 = filtered_items_df_for_page.iloc[start_idx_display_pg1:end_idx_display_pg1] 

    cols_item_list_header_pg1 = st.columns((3, 1, 2, 1, 1, 1, 2.5, 2.5)) 
    headers_item_list_pg1 = ["Name", "UoM", "Category", "Stock", "Reorder At", "Active", "Permitted Departments", "Actions"]
    for col_item_h, header_item_h in zip(cols_item_list_header_pg1, headers_item_list_pg1): 
        col_item_h.markdown(f"**{header_item_h}**")
    st.divider()

    for _, item_row_display_pg1 in paginated_items_df_display_pg1.iterrows(): 
        item_id_disp_pg1 = item_row_display_pg1['item_id']
        item_name_disp_pg1 = item_row_display_pg1['name']
        is_active_disp_pg1 = item_row_display_pg1['is_active']
        
        cols_item_row_pg1 = st.columns((3, 1, 2, 1, 1, 1, 2.5, 2.5)) 
        cols_item_row_pg1[0].write(item_name_disp_pg1)
        cols_item_row_pg1[1].write(item_row_display_pg1.get('unit', 'N/A'))
        cols_item_row_pg1[2].write(item_row_display_pg1.get('category', 'N/A'))
        cols_item_row_pg1[3].write(f"{item_row_display_pg1.get('current_stock', 0.0):.2f}")
        cols_item_row_pg1[4].write(f"{item_row_display_pg1.get('reorder_point', 0.0):.2f}")
        cols_item_row_pg1[5].checkbox("", value=is_active_disp_pg1, disabled=True, key=f"active_disp_item_pg1_v4_{item_id_disp_pg1}") 
        cols_item_row_pg1[6].caption(item_row_display_pg1.get('permitted_departments') or "N/A")

        with cols_item_row_pg1[7]: 
            button_key_prefix_item_pg1 = f"action_item_pg1_v4_{item_id_disp_pg1}" 
            if st.session_state.get('pg1_show_edit_form_for_item_id') == item_id_disp_pg1:
                if st.button("✖️ Cancel Edit", key=f"{button_key_prefix_item_pg1}_cancel_edit", type="secondary", use_container_width=True):
                    st.session_state.pg1_show_edit_form_for_item_id = None
                    st.rerun()
            else:
                action_buttons_cols_pg1 = st.columns(2) 
                if is_active_disp_pg1:
                    if action_buttons_cols_pg1[0].button("✏️", key=f"{button_key_prefix_item_pg1}_edit", help="Edit Item", type="primary", use_container_width=True):
                        st.session_state.pg1_show_edit_form_for_item_id = item_id_disp_pg1
                        st.session_state.pg1_edit_form_values = item_service.get_item_details(engine, item_id_disp_pg1)
                        st.rerun()
                    if action_buttons_cols_pg1[1].button("🗑️", key=f"{button_key_prefix_item_pg1}_deact", help="Deactivate Item", use_container_width=True):
                        success_deact_item, msg_deact_item = item_service.deactivate_item(engine, item_id_disp_pg1)
                        if success_deact_item:
                            st.success(msg_deact_item); fetch_all_items_df_pg1.clear(); st.rerun()
                        else: st.error(msg_deact_item)
                else: 
                    if action_buttons_cols_pg1[0].button("✅", key=f"{button_key_prefix_item_pg1}_react", help="Reactivate Item", use_container_width=True):
                        success_react_item, msg_react_item = item_service.reactivate_item(engine, item_id_disp_pg1)
                        if success_react_item:
                            st.success(msg_react_item); fetch_all_items_df_pg1.clear(); st.rerun()
                        else: st.error(msg_react_item)
        st.divider()

        if st.session_state.get('pg1_show_edit_form_for_item_id') == item_id_disp_pg1:
            current_values_for_edit_form_pg1 = st.session_state.get('pg1_edit_form_values')
            if not current_values_for_edit_form_pg1 or current_values_for_edit_form_pg1.get('item_id') != item_id_disp_pg1: 
                current_values_for_edit_form_pg1 = item_service.get_item_details(engine, item_id_disp_pg1)
                st.session_state.pg1_edit_form_values = current_values_for_edit_form_pg1
            
            if current_values_for_edit_form_pg1: 
                with st.form(key=f"edit_item_form_inline_pg1_v4_{item_id_disp_pg1}"): 
                    st.subheader(f"✏️ Editing: {current_values_for_edit_form_pg1.get('name', 'Item')}")
                    st.caption(f"Item ID: {item_id_disp_pg1} | Current Stock: {current_values_for_edit_form_pg1.get('current_stock',0.0):.2f}")
                    
                    edit_form_col1_detail_pg1, edit_form_col2_detail_pg1 = st.columns(2)
                    with edit_form_col1_detail_pg1:
                        e_name_pg1 = st.text_input("Item Name*", value=current_values_for_edit_form_pg1.get('name', ''), key=f"e_name_pg1_v4_{item_id_disp_pg1}")
                        e_unit_pg1 = st.text_input("UoM*", value=current_values_for_edit_form_pg1.get('unit', ''), key=f"e_unit_pg1_v4_{item_id_disp_pg1}")
                        e_category_pg1 = st.text_input("Category", value=current_values_for_edit_form_pg1.get('category', 'Uncategorized'), key=f"e_cat_pg1_v4_{item_id_disp_pg1}")
                        e_sub_category_pg1 = st.text_input("Sub-Category", value=current_values_for_edit_form_pg1.get('sub_category', 'General'), key=f"e_subcat_pg1_v4_{item_id_disp_pg1}")
                    with edit_form_col2_detail_pg1:
                        e_permitted_pg1 = st.text_input(
                            "Permitted Departments", 
                            value=current_values_for_edit_form_pg1.get('permitted_departments', '') or '',
                            key=f"e_depts_pg1_v4_{item_id_disp_pg1}",
                            help="Comma-separated list of departments."
                        )
                        e_rp_pg1 = st.number_input("Reorder At", min_value=0.0, value=float(current_values_for_edit_form_pg1.get('reorder_point', 0.0)), step=0.01, format="%.2f", key=f"e_rp_pg1_v4_{item_id_disp_pg1}")
                    e_notes_pg1 = st.text_area("Notes", value=current_values_for_edit_form_pg1.get('notes', '') or '', key=f"e_notes_pg1_v4_{item_id_disp_pg1}")
                    
                    if st.form_submit_button("💾 Update Item Details"):
                        is_valid_edit_form_pg1 = True
                        if not e_name_pg1.strip(): st.warning("Item Name is required."); is_valid_edit_form_pg1 = False
                        if not e_unit_pg1.strip(): st.warning("Unit of Measure (UoM) is required."); is_valid_edit_form_pg1 = False
                        
                        if is_valid_edit_form_pg1:
                            update_data_for_service_pg1 = { 
                                "name": e_name_pg1.strip(), 
                                "unit": e_unit_pg1.strip(), 
                                "category": e_category_pg1.strip() or "Uncategorized",
                                "sub_category": e_sub_category_pg1.strip() or "General", 
                                "permitted_departments": e_permitted_pg1.strip() or None,
                                "reorder_point": float(e_rp_pg1), 
                                "notes": e_notes_pg1.strip() or None
                            }
                            ok_update_item, msg_update_item = item_service.update_item_details(engine, item_id_disp_pg1, update_data_for_service_pg1)
                            if ok_update_item:
                                st.success(msg_update_item)
                                st.session_state.pg1_show_edit_form_for_item_id = None 
                                st.session_state.pg1_edit_form_values = None 
                                fetch_all_items_df_pg1.clear() 
                                st.rerun()
                            else: 
                                st.error(msg_update_item)
                st.divider()