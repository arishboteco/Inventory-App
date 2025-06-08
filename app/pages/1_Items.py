# app/pages/1_Items.py
import streamlit as st
import pandas as pd

import math

try:
    from app.db.database_utils import connect_db
    from app.services import item_service
    from app.core.constants import FILTER_ALL_CATEGORIES, FILTER_ALL_SUBCATEGORIES
except ImportError as e:
    st.error(f"Import error in 1_Items.py: {e}.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 1_Items.py: {e}")
    st.stop()

# --- Session State (prefixed with ss_items_ for this page) ---
if "ss_items_edit_item_id_val" not in st.session_state:
    st.session_state.ss_items_edit_item_id_val = None
if "ss_items_edit_form_data_dict" not in st.session_state:
    st.session_state.ss_items_edit_form_data_dict = None  # Stores dict for edit form
if "ss_items_show_edit_form_flag" not in st.session_state:
    st.session_state.ss_items_show_edit_form_flag = (
        None  # Stores item_id to show form for, or None
    )
if "ss_items_filter_show_inactive_flag" not in st.session_state:
    st.session_state.ss_items_filter_show_inactive_flag = False
if "ss_items_pagination_current_page_num" not in st.session_state:
    st.session_state.ss_items_pagination_current_page_num = 1
if "ss_items_pagination_items_per_page_val" not in st.session_state:
    st.session_state.ss_items_pagination_items_per_page_val = 10
if "ss_items_filter_search_name_val" not in st.session_state:
    st.session_state.ss_items_filter_search_name_val = ""
if "ss_items_filter_category_key" not in st.session_state:
    st.session_state.ss_items_filter_category_key = (
        FILTER_ALL_CATEGORIES  # Stores the key/name of category
    )
if "ss_items_filter_subcategory_key" not in st.session_state:
    st.session_state.ss_items_filter_subcategory_key = (
        FILTER_ALL_SUBCATEGORIES  # Stores the key/name of subcategory
    )


@st.cache_data(ttl=60)
def fetch_all_items_df_for_items_page(
    _engine, show_inactive: bool
) -> pd.DataFrame:  # Renamed for clarity
    return item_service.get_all_items_with_stock(
        _engine, include_inactive=show_inactive
    )


st.title("📦 Item Master Management")
st.write(
    "Manage your inventory items: add new items, edit existing ones, and view stock levels."
)
st.divider()

engine = connect_db()
if not engine:
    st.error(
        "Database connection failed. Item Management functionality is unavailable."
    )
    st.stop()

# --- ADD NEW ITEM Section ---
with st.expander("➕ Add New Inventory Item", expanded=False):
    with st.form("widget_items_add_form", clear_on_submit=True):
        st.subheader("Enter New Item Details")
        col1_add_items, col2_add_items = st.columns(2)
        with col1_add_items:
            name_add_widget = st.text_input(
                "Item Name*",
                help="Unique name for the item.",
                key="widget_items_add_form_name_input",
            )
            unit_add_widget = st.text_input(
                "Unit of Measure (UoM)*",
                help="e.g., KG, LTR, PCS",
                key="widget_items_add_form_unit_input",
            )
            category_add_widget = st.text_input(
                "Category",
                value="Uncategorized",
                help="e.g., Vegetables, Grains.",
                key="widget_items_add_form_category_input",
            )
            sub_category_add_widget = st.text_input(
                "Sub-Category",
                value="General",
                help="e.g., Leafy Greens, Rice.",
                key="widget_items_add_form_subcategory_input",
            )
        with col2_add_items:
            permitted_departments_add_widget = st.text_input(
                "Permitted Departments",
                help="Enter department names separated by commas (e.g., Kitchen, Bar).",
                key="widget_items_add_form_depts_input",
            )
            reorder_point_add_widget = st.number_input(
                "Reorder At",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                help="Stock level to reorder.",
                key="widget_items_add_form_reorder_input",
            )
            initial_stock_add_widget = st.number_input(
                "Initial Stock Quantity",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                help="Current stock on hand.",
                key="widget_items_add_form_initial_stock_input",
            )
        notes_add_widget = st.text_area(
            "Notes / Description",
            placeholder="Optional details about the item.",
            key="widget_items_add_form_notes_area",
        )

        if st.form_submit_button(
            "💾 Add Item to Master", key="widget_items_add_form_submit_btn"
        ):
            is_valid_add = True
            if not name_add_widget.strip():
                st.warning("Item Name is required.")
                is_valid_add = False
            if not unit_add_widget.strip():
                st.warning("Unit of Measure (UoM) is required.")
                is_valid_add = False

            if is_valid_add:
                item_data_to_add = {
                    "name": name_add_widget.strip(),
                    "unit": unit_add_widget.strip(),
                    "category": category_add_widget.strip() or "Uncategorized",
                    "sub_category": sub_category_add_widget.strip() or "General",
                    "permitted_departments": permitted_departments_add_widget.strip()
                    or None,
                    "reorder_point": float(reorder_point_add_widget),
                    "current_stock": float(initial_stock_add_widget),
                    "notes": notes_add_widget.strip() or None,
                    "is_active": True,
                }
                success_add, message_add = item_service.add_new_item(
                    engine, item_data_to_add
                )
                if success_add:
                    st.success(message_add)
                    fetch_all_items_df_for_items_page.clear()
                    st.rerun()
                else:
                    st.error(message_add)
st.divider()

# --- VIEW & MANAGE EXISTING ITEMS ---
st.subheader("🔍 View & Manage Existing Items")


# --- Filter Callbacks ---
def on_items_category_filter_change():
    st.session_state.ss_items_filter_subcategory_key = FILTER_ALL_SUBCATEGORIES


# Define filter widgets
filter_col1_view, filter_col2_view, filter_col3_view, filter_col4_view = st.columns(
    [2, 2, 2, 1]
)
with filter_col1_view:
    st.text_input(  # Directly updates session state via key
        "Search by Item Name",
        key="ss_items_filter_search_name_val",
        placeholder="e.g., Tomato, Rice",
    )
with filter_col4_view:
    st.toggle(  # Directly updates session state via key
        "Show Inactive",
        key="ss_items_filter_show_inactive_flag",
        help="Toggle to include inactive items in the list",
    )

all_items_df = fetch_all_items_df_for_items_page(
    engine, st.session_state.ss_items_filter_show_inactive_flag
)
filtered_items_df = (
    all_items_df.copy()
)  # Start with all items that match active/inactive toggle

unique_categories_options = [FILTER_ALL_CATEGORIES]
if not all_items_df.empty:
    unique_categories_options.extend(
        sorted(
            all_items_df["category"]
            .astype(str)
            .replace("nan", "Uncategorized")
            .replace("", "Uncategorized")
            .unique()
            .tolist()
        )
    )

with filter_col2_view:
    current_category_key = st.session_state.ss_items_filter_category_key
    category_idx = 0
    if current_category_key in unique_categories_options:
        category_idx = unique_categories_options.index(current_category_key)
    else:  # Should not happen if default is in options
        st.session_state.ss_items_filter_category_key = FILTER_ALL_CATEGORIES

    st.selectbox(
        "Filter by Category",
        options=unique_categories_options,
        key="ss_items_filter_category_key",
        index=category_idx,
        on_change=on_items_category_filter_change,
    )

unique_subcategories_options = [FILTER_ALL_SUBCATEGORIES]
if st.session_state.ss_items_filter_category_key != FILTER_ALL_CATEGORIES:
    if not all_items_df.empty:
        category_filtered_df = all_items_df[
            all_items_df["category"].astype(str)
            == st.session_state.ss_items_filter_category_key
        ]
        if not category_filtered_df.empty:
            unique_subcategories_options.extend(
                sorted(
                    category_filtered_df["sub_category"]
                    .astype(str)
                    .replace("nan", "General")
                    .replace("", "General")
                    .unique()
                    .tolist()
                )
            )
else:
    if not all_items_df.empty:
        unique_subcategories_options.extend(
            sorted(
                all_items_df["sub_category"]
                .astype(str)
                .replace("nan", "General")
                .replace("", "General")
                .unique()
                .tolist()
            )
        )
unique_subcategories_options = sorted(list(set(unique_subcategories_options)))

with filter_col3_view:
    current_subcategory_key = st.session_state.ss_items_filter_subcategory_key
    subcategory_idx = 0
    if current_subcategory_key in unique_subcategories_options:
        subcategory_idx = unique_subcategories_options.index(current_subcategory_key)
    else:
        st.session_state.ss_items_filter_subcategory_key = FILTER_ALL_SUBCATEGORIES
        subcategory_idx = 0  # Index of FILTER_ALL_SUBCATEGORIES

    st.selectbox(
        "Filter by Sub-Category",
        options=unique_subcategories_options,
        key="ss_items_filter_subcategory_key",
        index=subcategory_idx,
    )

# Apply filters
if st.session_state.ss_items_filter_search_name_val:
    search_term_filter = st.session_state.ss_items_filter_search_name_val.lower()
    filtered_items_df = filtered_items_df[
        filtered_items_df["name"]
        .astype(str)
        .str.lower()
        .str.contains(search_term_filter, na=False)
    ]
if st.session_state.ss_items_filter_category_key != FILTER_ALL_CATEGORIES:
    filtered_items_df = filtered_items_df[
        filtered_items_df["category"].astype(str)
        == st.session_state.ss_items_filter_category_key
    ]
if st.session_state.ss_items_filter_subcategory_key != FILTER_ALL_SUBCATEGORIES:
    filtered_items_df = filtered_items_df[
        filtered_items_df["sub_category"].astype(str)
        == st.session_state.ss_items_filter_subcategory_key
    ]

if filtered_items_df.empty:
    st.info(
        "No items found matching your criteria."
        if (
            st.session_state.ss_items_filter_search_name_val
            or st.session_state.ss_items_filter_category_key != FILTER_ALL_CATEGORIES
            or st.session_state.ss_items_filter_subcategory_key
            != FILTER_ALL_SUBCATEGORIES
            or st.session_state.ss_items_filter_show_inactive_flag
        )
        else "No active items found. Add items or adjust filters."
    )
else:
    total_items_display = len(filtered_items_df)
    st.write(f"Found {total_items_display} item(s) matching your criteria.")

    items_per_page_options_list = [5, 10, 20, 50]
    # Directly use session state key for items per page selectbox
    current_ipp_val_for_widget = st.session_state.ss_items_pagination_items_per_page_val
    if current_ipp_val_for_widget not in items_per_page_options_list:
        current_ipp_val_for_widget = items_per_page_options_list[0]
        st.session_state.ss_items_pagination_items_per_page_val = (
            current_ipp_val_for_widget  # Ensure state is valid
        )

    st.selectbox(  # Directly updates session state via key
        "Items per page:",
        options=items_per_page_options_list,
        index=items_per_page_options_list.index(current_ipp_val_for_widget),
        key="ss_items_pagination_items_per_page_val",
    )

    total_pages_calc = math.ceil(
        total_items_display / st.session_state.ss_items_pagination_items_per_page_val
    )
    if total_pages_calc == 0:
        total_pages_calc = 1
    if st.session_state.ss_items_pagination_current_page_num > total_pages_calc:
        st.session_state.ss_items_pagination_current_page_num = total_pages_calc
    if st.session_state.ss_items_pagination_current_page_num < 1:
        st.session_state.ss_items_pagination_current_page_num = 1

    page_nav_cols_display = st.columns(5)
    if page_nav_cols_display[0].button(
        "⏮️ First",
        key="widget_items_pagination_first_btn",
        disabled=(st.session_state.ss_items_pagination_current_page_num == 1),
    ):
        st.session_state.ss_items_pagination_current_page_num = 1
        st.session_state.ss_items_show_edit_form_flag = None
        st.rerun()
    if page_nav_cols_display[1].button(
        "⬅️ Previous",
        key="widget_items_pagination_prev_btn",
        disabled=(st.session_state.ss_items_pagination_current_page_num == 1),
    ):
        st.session_state.ss_items_pagination_current_page_num -= 1
        st.session_state.ss_items_show_edit_form_flag = None
        st.rerun()
    page_nav_cols_display[2].write(
        f"Page {st.session_state.ss_items_pagination_current_page_num} of {total_pages_calc}"
    )
    if page_nav_cols_display[3].button(
        "Next ➡️",
        key="widget_items_pagination_next_btn",
        disabled=(
            st.session_state.ss_items_pagination_current_page_num == total_pages_calc
        ),
    ):
        st.session_state.ss_items_pagination_current_page_num += 1
        st.session_state.ss_items_show_edit_form_flag = None
        st.rerun()
    if page_nav_cols_display[4].button(
        "Last ⏭️",
        key="widget_items_pagination_last_btn",
        disabled=(
            st.session_state.ss_items_pagination_current_page_num == total_pages_calc
        ),
    ):
        st.session_state.ss_items_pagination_current_page_num = total_pages_calc
        st.session_state.ss_items_show_edit_form_flag = None
        st.rerun()

    start_idx_display = (
        st.session_state.ss_items_pagination_current_page_num - 1
    ) * st.session_state.ss_items_pagination_items_per_page_val
    end_idx_display = (
        start_idx_display + st.session_state.ss_items_pagination_items_per_page_val
    )
    paginated_items_df_display = filtered_items_df.iloc[
        start_idx_display:end_idx_display
    ]

    cols_item_list_header = st.columns((3, 1, 2, 1, 1, 1, 2.5, 2.5))
    headers_item_list = [
        "Name",
        "UoM",
        "Category",
        "Stock",
        "Reorder At",
        "Active",
        "Permitted Departments",
        "Actions",
    ]
    for col_item_h, header_item_h in zip(cols_item_list_header, headers_item_list):
        col_item_h.markdown(f"**{header_item_h}**")
    st.divider()

    for _, item_row_display in paginated_items_df_display.iterrows():
        item_id_disp = item_row_display["item_id"]
        item_name_disp = item_row_display["name"]
        is_active_disp = item_row_display["is_active"]

        cols_item_row = st.columns((3, 1, 2, 1, 1, 1, 2.5, 2.5))
        cols_item_row[0].write(item_name_disp)
        cols_item_row[1].write(item_row_display.get("unit", "N/A"))
        cols_item_row[2].write(item_row_display.get("category", "N/A"))
        cols_item_row[3].write(f"{item_row_display.get('current_stock', 0.0):.2f}")
        cols_item_row[4].write(f"{item_row_display.get('reorder_point', 0.0):.2f}")
        cols_item_row[5].checkbox(
            "",
            value=is_active_disp,
            disabled=True,
            key=f"widget_items_list_active_checkbox_{item_id_disp}",
        )
        cols_item_row[6].caption(item_row_display.get("permitted_departments") or "N/A")

        with cols_item_row[7]:
            if st.session_state.get("ss_items_show_edit_form_flag") == item_id_disp:
                if st.button(
                    "✖️ Cancel Edit",
                    key=f"widget_items_list_cancel_edit_btn_{item_id_disp}",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state.ss_items_show_edit_form_flag = None
                    st.rerun()
            else:
                action_buttons_cols = st.columns(2)
                if is_active_disp:
                    if action_buttons_cols[0].button(
                        "✏️",
                        key=f"widget_items_list_edit_btn_{item_id_disp}",
                        help="Edit Item",
                        type="primary",
                        use_container_width=True,
                    ):
                        st.session_state.ss_items_show_edit_form_flag = item_id_disp
                        st.session_state.ss_items_edit_form_data_dict = (
                            item_service.get_item_details(engine, item_id_disp)
                        )
                        st.rerun()
                    if action_buttons_cols[1].button(
                        "🗑️",
                        key=f"widget_items_list_deactivate_btn_{item_id_disp}",
                        help="Deactivate Item",
                        use_container_width=True,
                    ):
                        success_deact_item, msg_deact_item = (
                            item_service.deactivate_item(engine, item_id_disp)
                        )
                        if success_deact_item:
                            st.success(msg_deact_item)
                            fetch_all_items_df_for_items_page.clear()
                            st.rerun()
                        else:
                            st.error(msg_deact_item)
                else:
                    if action_buttons_cols[0].button(
                        "✅",
                        key=f"widget_items_list_reactivate_btn_{item_id_disp}",
                        help="Reactivate Item",
                        use_container_width=True,
                    ):
                        success_react_item, msg_react_item = (
                            item_service.reactivate_item(engine, item_id_disp)
                        )
                        if success_react_item:
                            st.success(msg_react_item)
                            fetch_all_items_df_for_items_page.clear()
                            st.rerun()
                        else:
                            st.error(msg_react_item)
        st.divider()

        if st.session_state.get("ss_items_show_edit_form_flag") == item_id_disp:
            current_values_for_edit_form = st.session_state.get(
                "ss_items_edit_form_data_dict"
            )
            if (
                not current_values_for_edit_form
                or current_values_for_edit_form.get("item_id") != item_id_disp
            ):
                current_values_for_edit_form = item_service.get_item_details(
                    engine, item_id_disp
                )
                st.session_state.ss_items_edit_form_data_dict = (
                    current_values_for_edit_form
                )

            if current_values_for_edit_form:
                with st.form(key=f"widget_items_edit_form_inline_{item_id_disp}"):
                    st.subheader(
                        f"✏️ Editing: {current_values_for_edit_form.get('name', 'Item')}"
                    )
                    stock_val = current_values_for_edit_form.get("current_stock", 0.0)
                    st.caption(
                        f"Item ID: {item_id_disp} | Current Stock: {stock_val:.2f}"
                    )

                    edit_form_col1_detail, edit_form_col2_detail = st.columns(2)
                    with edit_form_col1_detail:
                        e_name = st.text_input(
                            "Item Name*",
                            value=current_values_for_edit_form.get("name", ""),
                            key=f"widget_items_edit_form_name_input_{item_id_disp}",
                        )
                        e_unit = st.text_input(
                            "UoM*",
                            value=current_values_for_edit_form.get("unit", ""),
                            key=f"widget_items_edit_form_unit_input_{item_id_disp}",
                        )
                        e_category = st.text_input(
                            "Category",
                            value=current_values_for_edit_form.get(
                                "category", "Uncategorized"
                            ),
                            key=f"widget_items_edit_form_category_input_{item_id_disp}",
                        )
                        e_sub_category = st.text_input(
                            "Sub-Category",
                            value=current_values_for_edit_form.get(
                                "sub_category", "General"
                            ),
                            key=f"widget_items_edit_form_subcategory_input_{item_id_disp}",
                        )
                    with edit_form_col2_detail:
                        e_permitted = st.text_input(
                            "Permitted Departments",
                            value=current_values_for_edit_form.get(
                                "permitted_departments", ""
                            )
                            or "",
                            key=f"widget_items_edit_form_depts_input_{item_id_disp}",
                            help="Comma-separated list of departments.",
                        )
                        e_rp = st.number_input(
                            "Reorder At",
                            min_value=0.0,
                            value=float(
                                current_values_for_edit_form.get("reorder_point", 0.0)
                            ),
                            step=0.01,
                            format="%.2f",
                            key=f"widget_items_edit_form_reorder_input_{item_id_disp}",
                        )
                    e_notes = st.text_area(
                        "Notes",
                        value=current_values_for_edit_form.get("notes", "") or "",
                        key=f"widget_items_edit_form_notes_area_{item_id_disp}",
                    )

                    if st.form_submit_button(
                        "💾 Update Item Details",
                        key=f"widget_items_edit_form_submit_btn_{item_id_disp}",
                    ):
                        is_valid_edit_form = True
                        if not e_name.strip():
                            st.warning("Item Name is required.")
                            is_valid_edit_form = False
                        if not e_unit.strip():
                            st.warning("Unit of Measure (UoM) is required.")
                            is_valid_edit_form = False

                        if is_valid_edit_form:
                            update_data_for_service = {
                                "name": e_name.strip(),
                                "unit": e_unit.strip(),
                                "category": e_category.strip() or "Uncategorized",
                                "sub_category": e_sub_category.strip() or "General",
                                "permitted_departments": e_permitted.strip() or None,
                                "reorder_point": float(e_rp),
                                "notes": e_notes.strip() or None,
                            }
                            ok_update_item, msg_update_item = (
                                item_service.update_item_details(
                                    engine, item_id_disp, update_data_for_service
                                )
                            )
                            if ok_update_item:
                                st.success(msg_update_item)
                                st.session_state.ss_items_show_edit_form_flag = None
                                st.session_state.ss_items_edit_form_data_dict = None
                                fetch_all_items_df_for_items_page.clear()
                                st.rerun()
                            else:
                                st.error(msg_update_item)
                st.divider()
