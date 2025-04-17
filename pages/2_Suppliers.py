# pages/2_Suppliers.py  – full file with sys.path patch
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:          # <-- key fix
    sys.path.append(str(ROOT))

import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Tuple, Optional

# ─────────────────────────────────────────────────────────
# Back‑end imports
# ─────────────────────────────────────────────────────────
try:
    from item_manager_app import (
        connect_db,
        get_all_suppliers,
        get_supplier_details,
        add_supplier,
        update_supplier,
        deactivate_supplier,
        reactivate_supplier,
    )
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

# ─────────────────────────────────────────────────────────
# Session‑state defaults
# ─────────────────────────────────────────────────────────
if "show_inactive_suppliers" not in st.session_state:
    st.session_state.show_inactive_suppliers = False
if "supplier_to_edit_id" not in st.session_state:
    st.session_state.supplier_to_edit_id = None
if "edit_supplier_form_values" not in st.session_state:
    st.session_state.edit_supplier_form_values = None

# ─────────────────────────────────────────────────────────
# Page header & DB
# ─────────────────────────────────────────────────────────
st.header("Supplier Management")
engine = connect_db()
if not engine:
    st.error("DB connection failed."); st.stop()

# ─────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────
tab_view, tab_add, tab_manage = st.tabs(
    ["📊 View Suppliers", "➕ Add New Supplier", "✏️ Edit / Manage"]
)

# ------------------------------------------------------------------
# 📊 TAB 1 – VIEW
# ------------------------------------------------------------------
with tab_view:
    st.subheader("View Options")
    st.checkbox(
        "Show Deactivated Suppliers?",
        key="show_inactive_suppliers",
        value=st.session_state.show_inactive_suppliers,
    )
    st.divider()

    df = get_all_suppliers(engine, include_inactive=st.session_state.show_inactive_suppliers)
    st.subheader(
        "Supplier List"
        + (" (Including Deactivated)" if st.session_state.show_inactive_suppliers else " (Active Only)")
    )

    if df.empty:
        st.info("No suppliers found.")
    else:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "supplier_id": st.column_config.NumberColumn("ID", width="small"),
                "name": st.column_config.TextColumn("Supplier Name", width="medium"),
                "contact_person": st.column_config.TextColumn("Contact Person", width="medium"),
                "phone": st.column_config.TextColumn("Phone", width="small"),
                "email": st.column_config.TextColumn("Email", width="medium"),
                "address": st.column_config.TextColumn("Address", width="large"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
                "is_active": st.column_config.CheckboxColumn("Active?", width="small", disabled=True),
            },
            column_order=[
                c
                for c in [
                    "supplier_id",
                    "name",
                    "contact_person",
                    "phone",
                    "email",
                    "address",
                    "is_active",
                    "notes",
                ]
                if c in df.columns
            ],
        )

# ------------------------------------------------------------------
# ➕ TAB 2 – ADD NEW
# ------------------------------------------------------------------
with tab_add:
    with st.form("new_supplier_form", clear_on_submit=True):
        st.subheader("Enter New Supplier Details:")
        s_name   = st.text_input("Supplier Name*")
        s_person = st.text_input("Contact Person")
        s_phone  = st.text_input("Phone")
        s_email  = st.text_input("Email")
        s_addr   = st.text_area("Address")
        s_notes  = st.text_area("Notes")
        if st.form_submit_button("Save New Supplier"):
            if not s_name:
                st.warning("Supplier Name is required.")
            else:
                ok = add_supplier(
                    engine,
                    s_name.strip(),
                    s_person.strip() or None,
                    s_phone.strip() or None,
                    s_email.strip() or None,
                    s_addr.strip() or None,
                    s_notes.strip() or None,
                )
                if ok:
                    st.success("Supplier added!")
                    get_all_suppliers.clear()
                    st.rerun()

# ------------------------------------------------------------------
# ✏️ TAB 3 – EDIT / MANAGE
# ------------------------------------------------------------------
with tab_manage:
    st.subheader("Select Supplier to Manage")

    df_manage = get_all_suppliers(
        engine, include_inactive=st.session_state.show_inactive_suppliers
    )
    opts: List[Tuple[str, int]] = (
        [
            (
                f"{r['name']}{'' if r['is_active'] else ' (Inactive)'}",
                int(r["supplier_id"]),
            )
            for _, r in df_manage.iterrows()
        ]
        if not df_manage.empty
        else []
    )
    opts.sort()
    select_opts = [("--- Select ---", None)] + opts

    def load_supplier():
        tup = st.session_state.supplier_to_edit_select
        sid = tup[1] if tup else None
        if sid:
            det = get_supplier_details(engine, sid)
            st.session_state.supplier_to_edit_id = sid if det else None
            st.session_state.edit_supplier_form_values = det if det else None
        else:
            st.session_state.supplier_to_edit_id = None
            st.session_state.edit_supplier_form_values = None

    cur_id = st.session_state.get("supplier_to_edit_id")
    idx = next((i for i, o in enumerate(select_opts) if o[1] == cur_id), 0)

    st.selectbox(
        "Supplier",
        options=select_opts,
        format_func=lambda x: x[0],
        index=idx,
        key="supplier_to_edit_select",
        on_change=load_supplier,
        label_visibility="collapsed",
    )

    if (
        st.session_state.supplier_to_edit_id
        and st.session_state.edit_supplier_form_values
    ):
        d = st.session_state.edit_supplier_form_values
        active = d.get("is_active", True)

        st.divider()
        if active:
            # ---- EDIT FORM ----
            with st.form("edit_supplier_form"):
                st.subheader(
                    f"Editing: {d.get('name', '')} (ID {st.session_state.supplier_to_edit_id})"
                )
                e_name   = st.text_input("Supplier Name*", value=d.get("name", ""))
                e_person = st.text_input("Contact Person", value=d.get("contact_person", ""))
                e_phone  = st.text_input("Phone", value=d.get("phone", ""))
                e_email  = st.text_input("Email", value=d.get("email", ""))
                e_addr   = st.text_area("Address", value=d.get("address", ""))
                e_notes  = st.text_area("Notes", value=d.get("notes", ""))

                if st.form_submit_button("Update Supplier Details"):
                    if not e_name:
                        st.warning("Supplier Name cannot be empty.")
                    else:
                        ok = update_supplier(
                            engine,
                            st.session_state.supplier_to_edit_id,
                            {
                                "name": e_name.strip(),
                                "contact_person": e_person.strip() or None,
                                "phone": e_phone.strip() or None,
                                "email": e_email.strip() or None,
                                "address": e_addr.strip() or None,
                                "notes": e_notes.strip() or None,
                            },
                        )
                        if ok:
                            st.success("Supplier updated.")
                            get_all_suppliers.clear()
                            st.session_state.supplier_to_edit_id = None
                            st.session_state.edit_supplier_form_values = None
                            st.rerun()

            # ---- Deactivate ----
            st.divider()
            st.subheader("Deactivate Supplier")
            if st.button("🗑️ Deactivate"):
                if deactivate_supplier(engine, st.session_state.supplier_to_edit_id):
                    st.success("Supplier deactivated.")
                    get_all_suppliers.clear()
                    st.session_state.supplier_to_edit_id = None
                    st.session_state.edit_supplier_form_values = None
                    st.rerun()
        else:
            st.info("This supplier is deactivated.")
            if st.button("✅ Reactivate"):
                if reactivate_supplier(engine, st.session_state.supplier_to_edit_id):
                    st.success("Supplier reactivated.")
                    get_all_suppliers.clear()
                    st.session_state.supplier_to_edit_id = None
                    st.session_state.edit_supplier_form_values = None
                    st.rerun()
    else:
        st.info("Select a supplier from the dropdown above to manage.")
