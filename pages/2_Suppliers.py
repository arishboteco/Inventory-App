import streamlit as st
import pandas as pd
from typing import Any, Optional, Dict, List, Tuple

# Import shared functions and engine from the main app file
try:
    from item_manager_app import (
        connect_db,
        get_all_suppliers,
        get_supplier_details,
        add_supplier,
        update_supplier,
        deactivate_supplier,
        reactivate_supplier
    )
except ImportError:
    st.error("Could not import functions from item_manager_app.py. Ensure it's in the parent directory.")
    st.stop()

# --- Initialize Session State ---
# Ensure state variables needed for this page exist
if 'show_inactive_suppliers' not in st.session_state: st.session_state.show_inactive_suppliers = False
if 'supplier_to_edit_id' not in st.session_state: st.session_state.supplier_to_edit_id = None
if 'edit_supplier_form_values' not in st.session_state: st.session_state.edit_supplier_form_values = None

# --- Page Content ---
st.header("Supplier Management")

# Establish DB connection for this page
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed on this page.")
    st.stop()
else:
    # --- Controls for Viewing Suppliers ---
    st.checkbox("Show Deactivated Suppliers?", key="show_inactive_suppliers", value=st.session_state.show_inactive_suppliers)
    st.divider()

    # --- Display Suppliers Table ---
    st.subheader("Supplier List" + (" (Including Deactivated)" if st.session_state.show_inactive_suppliers else " (Active Only)"))
    suppliers_df = get_all_suppliers(db_engine, include_inactive=st.session_state.show_inactive_suppliers)

    if suppliers_df.empty and 'name' not in suppliers_df.columns:
        st.info("No suppliers found matching the current view setting.")
    else:
        st.dataframe(
            suppliers_df, use_container_width=True, hide_index=True,
            column_config={
                "supplier_id": st.column_config.NumberColumn("ID", width="small"),
                "name": st.column_config.TextColumn("Supplier Name", width="medium"),
                "contact_person": st.column_config.TextColumn("Contact Person", width="medium"),
                "phone": st.column_config.TextColumn("Phone", width="small"),
                "email": st.column_config.TextColumn("Email", width="medium"),
                "address": st.column_config.TextColumn("Address", width="large"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
                "is_active": st.column_config.CheckboxColumn("Active?", width="small", disabled=True)
            },
            column_order=[col for col in ["supplier_id", "name", "contact_person", "phone", "email", "address", "is_active", "notes"] if col in suppliers_df.columns]
        )
    st.divider()

    # Prepare supplier options for dropdowns
    if not suppliers_df.empty and 'supplier_id' in suppliers_df.columns and 'name' in suppliers_df.columns:
        supplier_options_list: List[Tuple[str, int]] = [
            (f"{row['name']}{'' if row['is_active'] else ' (Inactive)'}", row['supplier_id'])
            for index, row in suppliers_df.dropna(subset=['name']).iterrows()
        ]
        supplier_options_list.sort()
    else: supplier_options_list = []

    # Add New Supplier Form
    with st.expander("➕ Add New Supplier"):
        with st.form("new_supplier_form", clear_on_submit=True):
            st.subheader("Enter New Supplier Details:")
            new_s_name = st.text_input("Supplier Name*")
            new_s_contact = st.text_input("Contact Person")
            new_s_phone = st.text_input("Phone")
            new_s_email = st.text_input("Email")
            new_s_address = st.text_area("Address")
            new_s_notes = st.text_area("Notes")
            s_submitted = st.form_submit_button("Save New Supplier")
            if s_submitted:
                if not new_s_name: st.warning("Supplier Name is required.")
                else:
                    supplier_data = {
                        "name": new_s_name.strip(),
                        "contact_person": new_s_contact.strip() or None,
                        "phone": new_s_phone.strip() or None,
                        "email": new_s_email.strip() or None,
                        "address": new_s_address.strip() or None,
                        "notes": new_s_notes.strip() or None
                    }
                    # Call imported function
                    s_success = add_supplier(db_engine, supplier_data)
                    if s_success: st.success(f"Supplier '{new_s_name}' added!"); get_all_suppliers.clear(); st.rerun()

    st.divider()

    # Edit/Deactivate/Reactivate Existing Supplier Section
    st.subheader("✏️ Edit / Deactivate / Reactivate Existing Supplier")
    edit_supplier_options = [("--- Select ---", None)] + supplier_options_list

    def load_supplier_for_edit(): # Callback for supplier selectbox
        selected_option = st.session_state.supplier_to_edit_select; supplier_id_to_load = selected_option[1] if selected_option else None
        if supplier_id_to_load:
            # Call imported function
            details = get_supplier_details(db_engine, supplier_id_to_load)
            st.session_state.supplier_to_edit_id = supplier_id_to_load if details else None; st.session_state.edit_supplier_form_values = details if details else None
        else: st.session_state.supplier_to_edit_id = None; st.session_state.edit_supplier_form_values = None

    current_supplier_edit_id = st.session_state.get('supplier_to_edit_id')
    try: current_supplier_index = [i for i, opt in enumerate(edit_supplier_options) if opt[1] == current_supplier_edit_id][0] if current_supplier_edit_id is not None else 0
    except IndexError: current_supplier_index = 0

    selected_supplier_tuple = st.selectbox( # Dropdown
        "Select Supplier to Edit / Deactivate / Reactivate:", options=edit_supplier_options,
        format_func=lambda x: x[0], key="supplier_to_edit_select",
        on_change=load_supplier_for_edit, index=current_supplier_index
    )

    if st.session_state.supplier_to_edit_id is not None and st.session_state.edit_supplier_form_values is not None:
        current_s_details = st.session_state.edit_supplier_form_values
        supplier_is_active = current_s_details.get('is_active', True)

        if supplier_is_active: # Show Edit/Deactivate for Active suppliers
            with st.form("edit_supplier_form"):
                st.subheader(f"Editing Supplier: {current_s_details.get('name', '')} (ID: {st.session_state.supplier_to_edit_id})")
                # Use unique keys for edit supplier form widgets
                edit_s_name = st.text_input("Supplier Name*", value=current_s_details.get('name', ''), key="edit_s_name")
                edit_s_contact = st.text_input("Contact Person", value=current_s_details.get('contact_person', ''), key="edit_s_contact")
                edit_s_phone = st.text_input("Phone", value=current_s_details.get('phone', ''), key="edit_s_phone")
                edit_s_email = st.text_input("Email", value=current_s_details.get('email', ''), key="edit_s_email")
                edit_s_address = st.text_area("Address", value=current_s_details.get('address', ''), key="edit_s_address")
                edit_s_notes = st.text_area("Notes", value=current_s_details.get('notes', ''), key="edit_s_notes")
                s_update_submitted = st.form_submit_button("Update Supplier Details")
                if s_update_submitted:
                    # Use safe stripping logic
                    s_name_val = st.session_state.edit_s_name.strip() if st.session_state.edit_s_name else ""
                    if not s_name_val: st.warning("Supplier Name cannot be empty.")
                    else:
                        s_updated_data = {
                            "name": s_name_val,
                            "contact_person": st.session_state.edit_s_contact.strip() if st.session_state.edit_s_contact else None,
                            "phone": st.session_state.edit_s_phone.strip() if st.session_state.edit_s_phone else None,
                            "email": st.session_state.edit_s_email.strip() if st.session_state.edit_s_email else None,
                            "address": st.session_state.edit_s_address.strip() if st.session_state.edit_s_address else None,
                            "notes": st.session_state.edit_s_notes.strip() if st.session_state.edit_s_notes else None
                        }
                        # Call imported function
                        s_update_success = update_supplier(db_engine, st.session_state.supplier_to_edit_id, s_updated_data)
                        if s_update_success: st.success(f"Supplier '{s_updated_data['name']}' updated!"); get_all_suppliers.clear(); st.session_state.supplier_to_edit_id = None; st.session_state.edit_supplier_form_values = None; st.rerun()
            st.divider(); st.subheader("Deactivate Supplier"); st.warning("⚠️ Deactivating removes supplier from active lists.")
            if st.button("🗑️ Deactivate This Supplier", key="deactivate_supplier_button", type="secondary"):
                s_name_to_deactivate = current_s_details.get('name', 'this supplier')
                # Call imported function
                s_deactivate_success = deactivate_supplier(db_engine, st.session_state.supplier_to_edit_id)
                if s_deactivate_success: st.success(f"Supplier '{s_name_to_deactivate}' deactivated!"); get_all_suppliers.clear(); st.session_state.supplier_to_edit_id = None; st.session_state.edit_supplier_form_values = None; st.rerun()
                else: st.error("Failed to deactivate supplier.")
        else: # Show Reactivate for Inactive suppliers
            st.info(f"Supplier **'{current_s_details.get('name', '')}'** (ID: {st.session_state.supplier_to_edit_id}) is currently deactivated.")
            if st.button("✅ Reactivate This Supplier", key="reactivate_supplier_button"):
                 # Call imported function
                s_reactivate_success = reactivate_supplier(db_engine, st.session_state.supplier_to_edit_id)
                if s_reactivate_success: st.success(f"Supplier '{current_s_details.get('name', '')}' reactivated!"); get_all_suppliers.clear(); st.session_state.supplier_to_edit_id = None; st.session_state.edit_supplier_form_values = None; st.rerun()
                else: st.error("Failed to reactivate supplier.")


