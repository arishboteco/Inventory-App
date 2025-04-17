# pages/1_Items.py  – full file with import‑path fix

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
        get_all_items_with_stock,
        get_item_details,
        add_new_item,
        update_item_details,
        deactivate_item,
        reactivate_item,
    )
except ImportError as e:
    st.error(f"Import error: {e}")
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
# Page header & DB
# ─────────────────────────────────────────────────────────
st.header("Item Management")
engine = connect_db()
if not engine:
    st.error("DB connection failed."); st.stop()

# ─────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────
tab_view, tab_add, tab_manage = st.tabs(
    ["📊 View Items", "➕ Add New Item", "✏️ Edit / Manage"]
)

# ------------------------------------------------------------------
# 📊 TAB 1 – VIEW
# ------------------------------------------------------------------
with tab_view:
    st.subheader("View Options")
    st.checkbox(
        "Show Deactivated Items?",
        key="show_inactive",
        value=st.session_state.show_inactive,
    )
    st.divider()

    df = get_all_items_with_stock(engine, include_inactive=st.session_state.show_inactive)
    st.subheader(
        "Item List"
        + (" (Including Deactivated)" if st.session_state.show_inactive else " (Active Only)")
    )

    if df.empty:
        st.info("No items found.")
    else:
        # Cast object columns to string so PyArrow can serialize
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].astype(str)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "item_id": st.column_config.NumberColumn("ID", width="small"),
                "name": st.column_config.TextColumn("Item Name", width="medium"),
                "unit": st.column_config.TextColumn("Unit", width="small"),
                "category": st.column_config.TextColumn("Category"),
                "sub_category": st.column_config.TextColumn("Sub‑Category"),
                "permitted_departments": st.column_config.TextColumn("Permitted Depts", width="medium"),
                "reorder_point": st.column_config.NumberColumn("Reorder Lvl", width="small"),
                "current_stock": st.column_config.NumberColumn("Current Stock", width="small"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
                "is_active": st.column_config.CheckboxColumn("Active?", width="small", disabled=True),
            },
            column_order=[
                c
                for c in [
                    "item_id","name","category","sub_category",
                    "unit","current_stock","reorder_point",
                    "permitted_departments","is_active","notes"
                ]
                if c in df.columns
            ],
        )

# Prepare dropdown options for other tabs
if not df.empty and {"item_id","name"}.issubset(df.columns):
    item_opts: List[Tuple[str,int]] = [
        (f"{r['name']}{'' if r['is_active'] else ' (Inactive)'}", int(r["item_id"]))
        for _, r in df.iterrows()
    ]
    item_opts.sort()
else:
    item_opts = []

# ------------------------------------------------------------------
# ➕ TAB 2 – ADD NEW
# ------------------------------------------------------------------
with tab_add:
    with st.form("new_item_form", clear_on_submit=True):
        st.subheader("Enter New Item Details:")
        n_name   = st.text_input("Item Name*")
        n_unit   = st.text_input("Unit (e.g., Kg, Pcs)")
        n_cat    = st.text_input("Category")
        n_subcat = st.text_input("Sub‑Category")
        n_depts  = st.text_input("Permitted Depts (comma or 'All')")
        n_rp     = st.number_input("Reorder Point", min_value=0, step=1)
        n_notes  = st.text_area("Notes")
        if st.form_submit_button("Save New Item"):
            if not n_name:
                st.warning("Item Name is required.")
            else:
                ok = add_new_item(
                    engine,
                    n_name.strip(),
                    n_unit.strip() or None,
                    n_cat.strip() or "Uncategorized",
                    n_subcat.strip() or "General",
                    n_depts.strip() or None,
                    n_rp,
                    n_notes.strip() or None,
                )
                if ok:
                    st.success("Item added.")
                    get_all_items_with_stock.clear()
                    st.rerun()

# ------------------------------------------------------------------
# ✏️ TAB 3 – EDIT / MANAGE
# ------------------------------------------------------------------
with tab_manage:
    st.subheader("Select Item to Manage")

    sel_opts = [("--- Select ---", None)] + item_opts
    def load_item():
        tup = st.session_state.item_select
        iid = tup[1] if tup else None
        if iid:
            det = get_item_details(engine, iid)
            st.session_state.item_to_edit_id = iid if det else None
            st.session_state.edit_form_values = det if det else None
        else:
            st.session_state.item_to_edit_id = None
            st.session_state.edit_form_values = None

    cur = st.session_state.get("item_to_edit_id")
    idx = next((i for i,o in enumerate(sel_opts) if o[1]==cur), 0)

    st.selectbox(
        "Item",
        options=sel_opts,
        format_func=lambda x: x[0],
        index=idx,
        key="item_select",
        on_change=load_item,
        label_visibility="collapsed",
    )

    if st.session_state.item_to_edit_id and st.session_state.edit_form_values:
        d = st.session_state.edit_form_values
        active = d.get("is_active", True)
        st.divider()

        if active:
            with st.form("edit_form"):
                st.subheader(f"Editing: {d.get('name','')} (ID {st.session_state.item_to_edit_id})")
                e_name   = st.text_input("Item Name*", value=d.get("name",""))
                e_unit   = st.text_input("Unit", value=d.get("unit",""))
                e_cat    = st.text_input("Category", value=d.get("category",""))
                e_subcat = st.text_input("Sub‑Category", value=d.get("sub_category",""))
                e_depts  = st.text_input("Permitted Depts", value=d.get("permitted_departments",""))
                e_rp_val = int(d.get("reorder_point",0) or 0)
                e_rp     = st.number_input("Reorder Point", min_value=0, step=1, value=e_rp_val)
                e_notes  = st.text_area("Notes", value=d.get("notes",""))
                if st.form_submit_button("Update"):
                    if not e_name:
                        st.warning("Name cannot be empty.")
                    else:
                        ok = update_item_details(
                            engine,
                            st.session_state.item_to_edit_id,
                            {
                                "name": e_name.strip(),
                                "unit": e_unit.strip() or None,
                                "category": e_cat.strip() or "Uncategorized",
                                "sub_category": e_subcat.strip() or "General",
                                "permitted_departments": e_depts.strip() or None,
                                "reorder_point": e_rp,
                                "notes": e_notes.strip() or None,
                            },
                        )
                        if ok:
                            st.success("Item updated.")
                            get_all_items_with_stock.clear()
                            st.session_state.item_to_edit_id = None
                            st.session_state.edit_form_values = None
                            st.rerun()

            st.divider()
            st.subheader("Deactivate Item")
            if st.button("🗑️ Deactivate"):
                if deactivate_item(engine, st.session_state.item_to_edit_id):
                    st.success("Item deactivated.")
                    get_all_items_with_stock.clear()
                    st.session_state.item_to_edit_id = None
                    st.session_state.edit_form_values = None
                    st.rerun()
        else:
            st.info("This item is deactivated.")
            if st.button("✅ Reactivate"):
                if reactivate_item(engine, st.session_state.item_to_edit_id):
                    st.success("Item reactivated.")
                    get_all_items_with_stock.clear()
                    st.session_state.item_to_edit_id = None
                    st.session_state.edit_form_values = None
                    st.rerun()
    else:
        st.info("Select an item from the dropdown above to manage.")
