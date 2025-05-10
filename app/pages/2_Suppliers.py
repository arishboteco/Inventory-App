# app/pages/2_Suppliers.py
import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Tuple, Optional

try:
    from app.db.database_utils import connect_db
    from app.services import supplier_service # Import the supplier_service module
except ImportError as e:
    st.error(f"Import error in 2_Suppliers.py: {e}. Ensure 'INVENTORY-APP' is the root for 'streamlit run app/item_manager_app.py'.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 2_Suppliers.py: {e}")
    st.stop()

# Session state (remains the same)
if "show_inactive_suppliers" not in st.session_state: st.session_state.show_inactive_suppliers = False
if "supplier_to_edit_id" not in st.session_state: st.session_state.supplier_to_edit_id = None
if "edit_supplier_form_values" not in st.session_state: st.session_state.edit_supplier_form_values = None

@st.cache_data(ttl=60)
def fetch_suppliers_for_display(_engine, show_inactive: bool) -> pd.DataFrame:
    # Use supplier_service to get data
    return supplier_service.get_all_suppliers(_engine, include_inactive=show_inactive)

# Page Setup
st.header("🤝 Supplier Management")
engine = connect_db()
if not engine:
    st.error("Database connection failed. Cannot manage suppliers.")
    st.stop()

# ADD NEW SUPPLIER Section
with st.expander("➕ Add New Supplier", expanded=False):
    with st.form("add_supplier_form", clear_on_submit=True):
        st.subheader("Enter New Supplier Details:")
        name = st.text_input("Supplier Name*", help="Unique name for the supplier.")
        contact_person = st.text_input("Contact Person")
        phone = st.text_input("Phone Number")
        email = st.text_input("Email Address")
        address = st.text_area("Address")
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("💾 Add Supplier")
        if submitted:
            if not name:
                st.warning("Supplier Name is required.")
            else:
                supplier_data = {
                    "name": name.strip(),
                    "contact_person": (contact_person or "").strip() or None,
                    "phone": (phone or "").strip() or None,
                    "email": (email or "").strip() or None,
                    "address": (address or "").strip() or None,
                    "notes": (notes or "").strip() or None,
                    "is_active": True
                }
                # Call function from supplier_service
                success, message = supplier_service.add_supplier(engine, supplier_data)
                if success:
                    st.success(message)
                    fetch_suppliers_for_display.clear() # Clears this page's display cache
                    # supplier_service.add_supplier internally clears supplier_service.get_all_suppliers cache
                    st.rerun()
                else:
                    st.error(message)

# VIEW / EDIT / DEACTIVATE Section
st.divider()
st.subheader("🔍 View & Manage Existing Suppliers")

show_inactive_sup = st.toggle(
    "Show Inactive Suppliers",
    value=st.session_state.show_inactive_suppliers,
    key="show_inactive_suppliers_toggle"
)
st.session_state.show_inactive_suppliers = show_inactive_sup

suppliers_df_display = fetch_suppliers_for_display(engine, st.session_state.show_inactive_suppliers)

if suppliers_df_display.empty:
    st.info("No suppliers found." if not st.session_state.show_inactive_suppliers else "No active suppliers found. Toggle 'Show Inactive' to see all.")
else:
    supplier_options = suppliers_df_display[['supplier_id', 'name', 'is_active']].copy()
    supplier_options['display_name'] = supplier_options.apply(lambda r: f"{r['name']}" + (" [Inactive]" if not r['is_active'] else ""), axis=1)
    supplier_dict = pd.Series(supplier_options.supplier_id.values, index=supplier_options.display_name).to_dict()

    current_selection_id = st.session_state.get('supplier_to_edit_id')
    selected_display_name = next((name for name, id_ in supplier_dict.items() if id_ == current_selection_id), None)

    def load_supplier_for_edit():
        selected_name = st.session_state.supplier_select_key
        if selected_name and selected_name in supplier_dict:
            st.session_state.supplier_to_edit_id = supplier_dict[selected_name]
            # Call function from supplier_service
            details = supplier_service.get_supplier_details(engine, st.session_state.supplier_to_edit_id)
            st.session_state.edit_supplier_form_values = details
        else:
            st.session_state.supplier_to_edit_id = None
            st.session_state.edit_supplier_form_values = None

    st.selectbox(
        "Select Supplier to View/Edit",
        options=list(supplier_dict.keys()),
        index=list(supplier_dict.keys()).index(selected_display_name) if selected_display_name else 0,
        key="supplier_select_key",
        on_change=load_supplier_for_edit,
        placeholder="Choose a supplier..."
    )

    st.dataframe(
        suppliers_df_display,
        use_container_width=True,
        hide_index=True,
        column_order=["name", "contact_person", "phone", "email", "address", "is_active", "notes", "supplier_id"],
        column_config={
            "supplier_id": st.column_config.NumberColumn("ID", width="small"), "name": "Supplier Name",
            "contact_person": "Contact", "phone": "Phone", "email": "Email", "address": "Address",
            "is_active": st.column_config.CheckboxColumn("Active?", width="small"), "notes": "Notes"
        }
    )

    if st.session_state.supplier_to_edit_id and st.session_state.edit_supplier_form_values:
        st.divider()
        current_values = st.session_state.edit_supplier_form_values
        st.subheader(f"Edit Supplier: {current_values.get('name', 'N/A')}")
        is_currently_active = current_values.get('is_active', False)

        if is_currently_active:
            with st.form("edit_supplier_form"):
                st.caption(f"Supplier ID: {st.session_state.supplier_to_edit_id}")
                e_name = st.text_input("Supplier Name*", value=current_values.get('name', ''))
                e_contact = st.text_input("Contact Person", value=current_values.get('contact_person', '') or '')
                e_phone = st.text_input("Phone", value=current_values.get('phone', '') or '')
                e_email = st.text_input("Email", value=current_values.get('email', '') or '')
                e_address = st.text_area("Address", value=current_values.get('address', '') or '')
                e_notes = st.text_area("Notes", value=current_values.get('notes', '') or '')

                submitted_edit = st.form_submit_button("💾 Update Supplier")
                if submitted_edit:
                    if not e_name:
                        st.warning("Supplier Name is required.")
                    else:
                        update_data = {
                            "name": e_name.strip(),
                            "contact_person": (e_contact or "").strip() or None,
                            "phone": (e_phone or "").strip() or None,
                            "email": (e_email or "").strip() or None,
                            "address": (e_address or "").strip() or None,
                            "notes": (e_notes or "").strip() or None,
                        }
                        # Call function from supplier_service
                        ok, msg = supplier_service.update_supplier(engine, st.session_state.supplier_to_edit_id, update_data)
                        if ok:
                            st.success(msg)
                            st.session_state.supplier_to_edit_id = None
                            st.session_state.edit_supplier_form_values = None
                            fetch_suppliers_for_display.clear()
                            # supplier_service.update_supplier clears its own cache
                            st.rerun()
                        else:
                            st.error(msg)

            st.divider()
            st.subheader("Deactivate Supplier")
            if st.button("🗑️ Deactivate"):
                # Call function from supplier_service
                if supplier_service.deactivate_supplier(engine, st.session_state.supplier_to_edit_id):
                    st.success("Supplier deactivated.")
                    st.session_state.supplier_to_edit_id = None
                    st.session_state.edit_supplier_form_values = None
                    fetch_suppliers_for_display.clear()
                    st.rerun()
                else:
                    st.error("Failed to deactivate supplier.")
        else: # Supplier is currently inactive
            st.info("This supplier is currently deactivated. You can reactivate it below.")
            if st.button("✅ Reactivate"):
                # Call function from supplier_service
                if supplier_service.reactivate_supplier(engine, st.session_state.supplier_to_edit_id):
                    st.success("Supplier reactivated.")
                    st.session_state.supplier_to_edit_id = None
                    st.session_state.edit_supplier_form_values = None
                    fetch_suppliers_for_display.clear()
                    st.rerun()
                else:
                    st.error("Failed to reactivate supplier.")
    else:
        st.info("Select a supplier from the dropdown above to view details or manage.")