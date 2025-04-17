import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple

# Import shared functions from backend
try:
    from item_manager_app import (
        connect_db,
        get_all_items_with_stock,
        get_item_details,
        add_new_item,
        update_item_details,
        deactivate_item,
        reactivate_item,
    )
except ImportError:
    st.error("Could not import functions from item_manager_app.py. Check paths.")
    st.stop()

# ------------------------------------------------------------------
# Session‑state defaults
# ------------------------------------------------------------------
if "item_to_edit_id" not in st.session_state:
    st.session_state.item_to_edit_id = None
if "edit_form_values" not in st.session_state:
    st.session_state.edit_form_values = None
if "show_inactive" not in st.session_state:
    st.session_state.show_inactive = False

# ------------------------------------------------------------------
# Page setup
# ------------------------------------------------------------------
st.header("Item Management")
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed on this page.")
    st.stop()

# ------------------------------------------------------------------
# Tabs
# ------------------------------------------------------------------
tab_view, tab_add, tab_manage = st.tabs(
    ["📊 View Items", "➕ Add New Item", "✏️ Edit / Manage Selected"]
)

# ------------------------------------------------------------------
# 📊 TAB 1 – VIEW ITEMS
# ------------------------------------------------------------------
with tab_view:
    st.subheader("View Options")
    st.checkbox(
        "Show Deactivated Items?",
        key="show_inactive",
        value=st.session_state.show_inactive,
    )
    st.divider()

    # fetch once
    items_df_with_stock = get_all_items_with_stock(
        db_engine, include_inactive=st.session_state.show_inactive
    )

    # drop duplicate‑named cols (e.g., two “current_stock”)
    items_df_with_stock = items_df_with_stock.loc[
        :, ~items_df_with_stock.columns.duplicated()
    ]

    st.subheader(
        "Full Item List"
        + (
            " (Including Deactivated)"
            if st.session_state.show_inactive
            else " (Active Only)"
        )
    )

    if items_df_with_stock.empty:
        st.info("No items found.")
    else:
        #  make PyArrow happy
        for col in items_df_with_stock.select_dtypes(include=["object"]).columns:
            items_df_with_stock[col] = items_df_with_stock[col].astype(str)

        st.dataframe(
            items_df_with_stock,
            use_container_width=True,
            hide_index=True,
            column_config={
                "item_id": st.column_config.NumberColumn("ID", width="small"),
                "name": st.column_config.TextColumn("Item Name", width="medium"),
                "unit": st.column_config.TextColumn("Unit", width="small"),
                "category": st.column_config.TextColumn("Category"),
                "sub_category": st.column_config.TextColumn("Sub-Category"),
                "permitted_departments": st.column_config.TextColumn(
                    "Permitted Depts", width="medium"
                ),
                "reorder_point": st.column_config.NumberColumn(
                    "Reorder Lvl", width="small", format="%d"
                ),
                "current_stock": st.column_config.NumberColumn(
                    "Current Stock",
                    width="small",
                    help="Calculated from transactions.",
                ),
                "notes": st.column_config.TextColumn("Notes", width="large"),
                "is_active": st.column_config.CheckboxColumn(
                    "Active?", width="small", disabled=True
                ),
            },
            column_order=[
                c
                for c in [
                    "item_id",
                    "name",
                    "category",
                    "sub_category",
                    "unit",
                    "current_stock",
                    "reorder_point",
                    "permitted_departments",
                    "is_active",
                    "notes",
                ]
                if c in items_df_with_stock.columns
            ],
        )

# ---------- dropdown list for Manage tab ----------
if (
    not items_df_with_stock.empty
    and {"item_id", "name", "is_active"}.issubset(items_df_with_stock.columns)
):
    item_options_list: List[Tuple[str, int]] = [
        (
            f"{row['name']}{'' if row['is_active'] else ' (Inactive)'}",
            int(row["item_id"]),
        )
        for _, row in items_df_with_stock.iterrows()
    ]
    item_options_list.sort()
else:
    item_options_list = []

# ------------------------------------------------------------------
# ➕ TAB 2 – ADD NEW ITEM
# ------------------------------------------------------------------
with tab_add:
    with st.form("new_item_form", clear_on_submit=True):
        st.subheader("Enter New Item Details:")
        new_name = st.text_input("Item Name*")
        new_unit = st.text_input("Unit (e.g., Kg, Pcs, Ltr)")
        new_category = st.text_input("Category")
        new_sub_category = st.text_input("Sub-Category")
        new_permitted_departments = st.text_input(
            "Permitted Departments (Comma‑separated or All)"
        )
        new_reorder_point = st.number_input(
            "Reorder Point", min_value=0, value=0, step=1
        )
        new_notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save New Item")

        if submitted:
            if not new_name:
                st.warning("Item Name is required.")
            else:
                success = add_new_item(
                    db_engine,
                    new_name.strip(),
                    new_unit.strip() or None,
                    new_category.strip() or "Uncategorized",
                    new_sub_category.strip() or "General",
                    new_permitted_departments.strip() or None,
                    new_reorder_point,
                    new_notes.strip() or None,
                )
                if success:
                    st.success(f"Item “{new_name}” added!")
                    get_all_items_with_stock.clear()
                    st.rerun()

# ------------------------------------------------------------------
# ✏️ TAB 3 – EDIT / MANAGE
# ------------------------------------------------------------------
with tab_manage:
    st.subheader("Select Item to Manage")

    edit_options = [("--- Select ---", None)] + item_options_list

    def load_item_for_edit():
        tup = st.session_state.item_to_edit_select
        item_id = tup[1] if tup else None
        if item_id:
            details = get_item_details(db_engine, item_id)
            st.session_state.item_to_edit_id = item_id if details else None
            st.session_state.edit_form_values = details if details else None
        else:
            st.session_state.item_to_edit_id = None
            st.session_state.edit_form_values = None

    current_id = st.session_state.get("item_to_edit_id")
    try:
        current_idx = next(
            i for i, opt in enumerate(edit_options) if opt[1] == current_id
        )
    except StopIteration:
        current_idx = 0

    st.selectbox(
        "Select Item:",
        options=edit_options,
        format_func=lambda x: x[0],
        index=current_idx,
        key="item_to_edit_select",
        on_change=load_item_for_edit,
        label_visibility="collapsed",
    )

    if (
        st.session_state.item_to_edit_id is not None
        and st.session_state.edit_form_values is not None
    ):
        details = st.session_state.edit_form_values
        is_active = details.get("is_active", True)

        st.divider()

        if is_active:
            with st.form("edit_item_form"):
                st.subheader(
                    f"Editing: {details.get('name', '')} (ID {st.session_state.item_to_edit_id})"
                )
                edit_name = st.text_input(
                    "Item Name*", value=details.get("name", "")
                )
                edit_unit = st.text_input("Unit", value=details.get("unit", ""))
                edit_category = st.text_input(
                    "Category", value=details.get("category", "")
                )
                edit_sub_category = st.text_input(
                    "Sub-Category", value=details.get("sub_category", "")
                )
                edit_permitted_departments = st.text_input(
                    "Permitted Departments",
                    value=details.get("permitted_departments", ""),
                )
                rp_val = details.get("reorder_point", 0)
                edit_rp = st.number_input(
                    "Reorder Point",
                    min_value=0,
                    value=int(rp_val) if pd.notna(rp_val) else 0,
                    step=1,
                )
                edit_notes = st.text_area("Notes", value=details.get("notes", ""))

                if st.form_submit_button("Update Item Details"):
                    if not edit_name:
                        st.warning("Item Name cannot be empty.")
                    else:
                        updated = {
                            "name": edit_name.strip(),
                            "unit": edit_unit.strip() or None,
                            "category": edit_category.strip() or "Uncategorized",
                            "sub_category": edit_sub_category.strip() or "General",
                            "permitted_departments": edit_permitted_departments.strip()
                            or None,
                            "reorder_point": edit_rp,
                            "notes": edit_notes.strip() or None,
                        }
                        ok = update_item_details(
                            db_engine, st.session_state.item_to_edit_id, updated
                        )
                        if ok:
                            st.success("Item updated!")
                            get_all_items_with_stock.clear()
                            st.session_state.item_to_edit_id = None
                            st.session_state.edit_form_values = None
                            st.rerun()

            # Deactivate
            st.divider()
            st.subheader("Deactivate Item")
            st.warning("⚠️ Deactivating removes item from active lists.")
            if st.button("🗑️ Deactivate This Item"):
                if deactivate_item(db_engine, st.session_state.item_to_edit_id):
                    st.success("Item deactivated.")
                    get_all_items_with_stock.clear()
                    st.session_state.item_to_edit_id = None
                    st.session_state.edit_form_values = None
                    st.rerun()
        else:
            # Reactivate
            st.info(
                f"Item **“{details.get('name', '')}”** (ID {st.session_state.item_to_edit_id}) is deactivated."
            )
            if st.button("✅ Reactivate This Item"):
                if reactivate_item(db_engine, st.session_state.item_to_edit_id):
                    st.success("Item reactivated.")
                    get_all_items_with_stock.clear()
                    st.session_state.item_to_edit_id = None
                    st.session_state.edit_form_values = None
                    st.rerun()
    else:
        st.info("Select an item from the dropdown above to manage it.")
