# app/pages/2_Suppliers.py
import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Tuple, Optional
import math # For pagination

try:
    from app.db.database_utils import connect_db
    from app.services import supplier_service
except ImportError as e:
    st.error(f"Import error in 2_Suppliers.py: {e}.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 2_Suppliers.py: {e}")
    st.stop()

# --- Session State ---
if "supplier_to_edit_id" not in st.session_state: st.session_state.supplier_to_edit_id = None
if "edit_supplier_form_values" not in st.session_state: st.session_state.edit_supplier_form_values = None
if "show_edit_form_for_supplier_id" not in st.session_state: st.session_state.show_edit_form_for_supplier_id = None
if "show_inactive_suppliers" not in st.session_state: st.session_state.show_inactive_suppliers = False
if "current_page_suppliers" not in st.session_state: st.session_state.current_page_suppliers = 1
if "suppliers_per_page" not in st.session_state: st.session_state.suppliers_per_page = 10
if "supplier_search_term" not in st.session_state: st.session_state.supplier_search_term = ""

@st.cache_data(ttl=60)
def fetch_all_suppliers_df(_engine, show_inactive: bool) -> pd.DataFrame:
    return supplier_service.get_all_suppliers(_engine, include_inactive=show_inactive)

st.title("🤝 Supplier Management")
st.write("Maintain your list of suppliers: add new ones, update details, or manage their active status.")
st.divider()

engine = connect_db()
if not engine: st.error("Database connection failed."); st.stop()

# --- ADD NEW SUPPLIER Section ---
with st.expander("➕ Add New Supplier Record", expanded=False):
    with st.form("add_supplier_form_v2", clear_on_submit=True):
        st.subheader("Enter New Supplier Details")
        form_col1, form_col2 = st.columns(2)
        with form_col1:
            s_name = st.text_input("Supplier Name*", help="Unique name for the supplier.", key="add_s_name")
            s_contact_person = st.text_input(
                "Contact Person",
                key="add_s_contact",
                help="Primary contact name at the supplier."
            )
        with form_col2:
            s_phone = st.text_input(
                "Phone Number",
                key="add_s_phone",
                help="Supplier's primary contact number (e.g., +91 9876543210)."
            )
            s_email = st.text_input(
                "Email Address",
                key="add_s_email",
                help="Supplier's primary email for correspondence (e.g., sales@supplier.com)."
            )
        s_address = st.text_area(
            "Address",
            key="add_s_address",
            help="Full business address of the supplier."
        )
        s_notes = st.text_area("Notes", placeholder="Optional: any specific terms, payment details, etc.", key="add_s_notes")

        if st.form_submit_button("💾 Save Supplier Information"):
            if not s_name:
                st.warning("Supplier Name is required.")
            else:
                supplier_data = {
                    "name": s_name.strip(),
                    "contact_person": (s_contact_person or "").strip() or None,
                    "phone": (s_phone or "").strip() or None,
                    "email": (s_email or "").strip() or None,
                    "address": (s_address or "").strip() or None,
                    "notes": (s_notes or "").strip() or None,
                    "is_active": True
                }
                success, message = supplier_service.add_supplier(engine, supplier_data)
                if success:
                    st.success(message)
                    fetch_all_suppliers_df.clear()
                    st.rerun()
                else:
                    st.error(message)
st.divider()

# --- VIEW & MANAGE EXISTING SUPPLIERS ---
st.subheader("🔍 View & Manage Existing Suppliers")

filter_s_col1, filter_s_col2 = st.columns([3,1])
with filter_s_col1:
    st.session_state.supplier_search_term = st.text_input(
        "Search Suppliers (by Name, Contact, Email)",
        value=st.session_state.supplier_search_term,
        key="supplier_search_input",
        placeholder="e.g., Fresh Produce Inc, John Doe, sales@..."
    )
with filter_s_col2:
    st.session_state.show_inactive_suppliers = st.toggle(
        "Show Inactive",
        value=st.session_state.show_inactive_suppliers,
        key="show_inactive_suppliers_toggle_v2",
        help="Toggle to include inactive suppliers"
    )

all_suppliers_df = fetch_all_suppliers_df(engine, st.session_state.show_inactive_suppliers)
filtered_suppliers_df = all_suppliers_df

if st.session_state.supplier_search_term:
    search_term = st.session_state.supplier_search_term.lower()
    filtered_suppliers_df = all_suppliers_df[
        all_suppliers_df['name'].astype(str).str.lower().str.contains(search_term, na=False) |
        all_suppliers_df['contact_person'].astype(str).str.lower().str.contains(search_term, na=False) |
        all_suppliers_df['email'].astype(str).str.lower().str.contains(search_term, na=False)
    ]

# CRITICAL FIX: Ensure all subsequent logic that uses paginated_suppliers_df is within this 'else' block
if filtered_suppliers_df.empty:
    st.info("No suppliers found matching your criteria." if st.session_state.supplier_search_term or st.session_state.show_inactive_suppliers else "No active suppliers found. Add suppliers or adjust filters.")
else:
    total_suppliers = len(filtered_suppliers_df)
    st.write(f"Found {total_suppliers} supplier(s) matching your criteria.")

    s_items_per_page_options = [5, 10, 20, 50]
    current_s_ipp_value = st.session_state.suppliers_per_page
    if current_s_ipp_value not in s_items_per_page_options:
        current_s_ipp_value = s_items_per_page_options[0]
        st.session_state.suppliers_per_page = current_s_ipp_value
        
    st.session_state.suppliers_per_page = st.selectbox(
        "Suppliers per page:", options=s_items_per_page_options,
        index=s_items_per_page_options.index(current_s_ipp_value),
        key="suppliers_per_page_selector_v2"
    )
    
    s_total_pages = math.ceil(total_suppliers / st.session_state.suppliers_per_page)
    if s_total_pages == 0: s_total_pages = 1
    if st.session_state.current_page_suppliers > s_total_pages: st.session_state.current_page_suppliers = s_total_pages
    if st.session_state.current_page_suppliers < 1: st.session_state.current_page_suppliers = 1
        
    s_page_nav_cols = st.columns(5)
    if s_page_nav_cols[0].button("⏮️ First", key="s_first_page_v3", disabled=(st.session_state.current_page_suppliers == 1)): # incremented key version
        st.session_state.current_page_suppliers = 1; st.session_state.show_edit_form_for_supplier_id = None; st.rerun()
    if s_page_nav_cols[1].button("⬅️ Previous", key="s_prev_page_v3", disabled=(st.session_state.current_page_suppliers == 1)): # incremented key version
        st.session_state.current_page_suppliers -= 1; st.session_state.show_edit_form_for_supplier_id = None; st.rerun()
    s_page_nav_cols[2].write(f"Page {st.session_state.current_page_suppliers} of {s_total_pages}")
    if s_page_nav_cols[3].button("Next ➡️", key="s_next_page_v3", disabled=(st.session_state.current_page_suppliers == s_total_pages)): # incremented key version
        st.session_state.current_page_suppliers += 1; st.session_state.show_edit_form_for_supplier_id = None; st.rerun()
    if s_page_nav_cols[4].button("Last ⏭️", key="s_last_page_v3", disabled=(st.session_state.current_page_suppliers == s_total_pages)): # incremented key version
        st.session_state.current_page_suppliers = s_total_pages; st.session_state.show_edit_form_for_supplier_id = None; st.rerun()

    s_start_idx = (st.session_state.current_page_suppliers - 1) * st.session_state.suppliers_per_page
    s_end_idx = s_start_idx + st.session_state.suppliers_per_page
    paginated_suppliers_df = filtered_suppliers_df.iloc[s_start_idx:s_end_idx] # Definition is here

    s_cols_header = st.columns((3, 2, 2, 2, 1, 2))
    s_headers = ["Supplier Name", "Contact Person", "Phone", "Email", "Active", "Actions"]
    for col, header in zip(s_cols_header, s_headers): col.markdown(f"**{header}**")
    st.divider()

    # This loop (and everything inside it that depends on supplier_row or supplier_id)
    # MUST be within the 'else' block.
    for index, supplier_row in paginated_suppliers_df.iterrows(): # This is approx line 159 from your error
        supplier_id = supplier_row['supplier_id']
        supplier_name = supplier_row['name']
        s_is_active = supplier_row['is_active']

        s_cols = st.columns((3, 2, 2, 2, 1, 2))
        s_cols[0].write(supplier_name)
        s_cols[1].write(supplier_row.get('contact_person') or "N/A")
        s_cols[2].write(supplier_row.get('phone') or "N/A")
        s_cols[3].write(supplier_row.get('email') or "N/A")
        s_cols[4].checkbox("", value=s_is_active, disabled=True, key=f"s_active_disp_{supplier_id}")
        
        with s_cols[5]:
            s_button_key_prefix = f"s_action_{supplier_id}"
            if st.session_state.get('show_edit_form_for_supplier_id') == supplier_id:
                if st.button("✖️ Cancel Edit", key=f"{s_button_key_prefix}_cancel_edit_v3", type="secondary"): # incremented key version
                    st.session_state.show_edit_form_for_supplier_id = None; st.rerun()
            else:
                if s_is_active:
                    if st.button("✏️ Edit", key=f"{s_button_key_prefix}_edit_v3", type="primary"): # incremented key version
                        st.session_state.show_edit_form_for_supplier_id = supplier_id
                        st.session_state.edit_supplier_form_values = supplier_service.get_supplier_details(engine, supplier_id)
                        st.rerun()
                    if st.button("🗑️ Deact.", key=f"{s_button_key_prefix}_deact_v3", help="Deactivate"): # incremented key version
                        if supplier_service.deactivate_supplier(engine, supplier_id):
                            st.success(f"'{supplier_name}' deactivated."); fetch_all_suppliers_df.clear(); st.rerun()
                        else: st.error(f"Failed to deactivate '{supplier_name}'.")
                else:
                    if st.button("✅ Reactivate", key=f"{s_button_key_prefix}_react_v3"): # incremented key version
                        if supplier_service.reactivate_supplier(engine, supplier_id):
                            st.success(f"'{supplier_name}' reactivated."); fetch_all_suppliers_df.clear(); st.rerun()
                        else: st.error(f"Failed to reactivate '{supplier_name}'.")
        st.divider() # Divider for each row

        # The inline edit form logic also MUST be within this 'else' block, typically inside the loop
        if st.session_state.get('show_edit_form_for_supplier_id') == supplier_id:
            current_s_values_for_edit = st.session_state.get('edit_supplier_form_values')
            if not current_s_values_for_edit:
                current_s_values_for_edit = supplier_service.get_supplier_details(engine, supplier_id)
                st.session_state.edit_supplier_form_values = current_s_values_for_edit
            
            if current_s_values_for_edit:
                with st.form(key=f"edit_s_form_inline_v3_{supplier_id}"): # incremented key version
                    st.subheader(f"✏️ Editing Supplier: {current_s_values_for_edit.get('name', 'N/A')}")
                    st.caption(f"Supplier ID: {supplier_id}")
                    
                    s_edit_col1, s_edit_col2 = st.columns(2)
                    with s_edit_col1:
                        es_name = st.text_input("Supplier Name*", value=current_s_values_for_edit.get('name', ''), key=f"es_name_v3_{supplier_id}", help="Unique name for the supplier.")
                        es_contact = st.text_input(
                            "Contact Person",
                            value=current_s_values_for_edit.get('contact_person', '') or '',
                            key=f"es_contact_v3_{supplier_id}",
                            help="Primary contact name at the supplier."
                        )
                    with s_edit_col2:
                        es_phone = st.text_input(
                            "Phone", 
                            value=current_s_values_for_edit.get('phone', '') or '',
                            key=f"es_phone_v3_{supplier_id}",
                            help="Supplier's primary contact number (e.g., +91 9876543210)."
                        )
                        es_email = st.text_input(
                            "Email",
                            value=current_s_values_for_edit.get('email', '') or '',
                            key=f"es_email_v3_{supplier_id}",
                            help="Supplier's primary email for correspondence (e.g., sales@supplier.com)."
                        )
                    es_address = st.text_area(
                        "Address",
                        value=current_s_values_for_edit.get('address', '') or '',
                        key=f"es_address_v3_{supplier_id}",
                        help="Full business address of the supplier."
                    )
                    es_notes = st.text_area("Notes", value=current_s_values_for_edit.get('notes', '') or '', key=f"es_notes_v3_{supplier_id}", placeholder="Optional: any specific terms, payment details, etc.")
                    
                    if st.form_submit_button("💾 Update Supplier Details"):
                        if not es_name: st.warning("Supplier Name required.")
                        else:
                            update_s_data = {"name": es_name.strip(), "contact_person": (es_contact or "").strip() or None,
                                           "phone": (es_phone or "").strip() or None, "email": (es_email or "").strip() or None,
                                           "address": (es_address or "").strip() or None, "notes": (es_notes or "").strip() or None}
                            ok, msg = supplier_service.update_supplier(engine, supplier_id, update_s_data)
                            if ok:
                                st.success(msg); st.session_state.show_edit_form_for_supplier_id = None
                                fetch_all_suppliers_df.clear(); st.rerun()
                            else: st.error(msg)
                st.divider() # Divider for the edit form section
# This is the end of the 'else' block.