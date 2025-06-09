# app/pages/2_Suppliers.py
import streamlit as st
import pandas as pd

import math
from app.ui.theme import load_css, render_sidebar_logo

try:
    from app.db.database_utils import connect_db
    from app.services import supplier_service

    # No specific UI placeholders from constants.py are heavily used here yet,
    # but good to keep imports organized if they are added later.
    # from app.core.constants import SOME_CONSTANT
except ImportError as e:
    st.error(f"Import error in 2_Suppliers.py: {e}.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during import in 2_Suppliers.py: {e}")
    st.stop()

# --- Session State (prefixed with pg2_ for page-specific scope) ---
if "pg2_supplier_to_edit_id" not in st.session_state:
    st.session_state.pg2_supplier_to_edit_id = None
if "pg2_edit_supplier_form_values" not in st.session_state:
    st.session_state.pg2_edit_supplier_form_values = None
if "pg2_show_edit_form_for_supplier_id" not in st.session_state:
    st.session_state.pg2_show_edit_form_for_supplier_id = None
if "pg2_show_inactive_suppliers" not in st.session_state:
    st.session_state.pg2_show_inactive_suppliers = False
if "pg2_current_page_suppliers" not in st.session_state:
    st.session_state.pg2_current_page_suppliers = 1
if "pg2_suppliers_per_page" not in st.session_state:
    st.session_state.pg2_suppliers_per_page = 10  # Default items per page
if "pg2_supplier_search_term" not in st.session_state:
    st.session_state.pg2_supplier_search_term = ""


@st.cache_data(ttl=60)  # Cache supplier list
def fetch_all_suppliers_df_pg2(
    _engine, show_inactive: bool
) -> pd.DataFrame:  # Page-specific cache function name
    return supplier_service.get_all_suppliers(_engine, include_inactive=show_inactive)


load_css()
render_sidebar_logo()


st.title("🤝 Supplier Management")
st.write(
    "Maintain your list of suppliers: add new ones, update details, or manage their active status."
)
st.divider()

engine = connect_db()
if not engine:
    st.error(
        "Database connection failed. Supplier Management functionality is unavailable."
    )
    st.stop()

# --- ADD NEW SUPPLIER Section ---
with st.expander("➕ Add New Supplier Record", expanded=False):
    # Unique form key for this page
    with st.form("add_supplier_form_pg2_v3", clear_on_submit=True):
        st.subheader("Enter New Supplier Details")
        form_col1_add_pg2, form_col2_add_pg2 = st.columns(2)
        with form_col1_add_pg2:
            s_name_add_pg2 = st.text_input(
                "Supplier Name*",
                help="Unique name for the supplier.",
                key="add_s_name_pg2_v3",
            )
            s_contact_person_add_pg2 = st.text_input(
                "Contact Person",
                key="add_s_contact_pg2_v3",
                help="Primary contact name at the supplier.",
            )
        with form_col2_add_pg2:
            s_phone_add_pg2 = st.text_input(
                "Phone Number",
                key="add_s_phone_pg2_v3",
                help="Supplier's primary contact number (e.g., +91 9876543210).",
            )
            s_email_add_pg2 = st.text_input(
                "Email Address",
                key="add_s_email_pg2_v3",
                help="Supplier's primary email for correspondence (e.g., sales@supplier.com).",
            )
        s_address_add_pg2 = st.text_area(
            "Address",
            key="add_s_address_pg2_v3",
            help="Full business address of the supplier.",
        )
        s_notes_add_pg2 = st.text_area(
            "Notes",
            placeholder="Optional: any specific terms, payment details, etc.",
            key="add_s_notes_pg2_v3",
        )

        if st.form_submit_button("💾 Save Supplier Information"):
            if not s_name_add_pg2.strip():  # Check for empty stripped name
                st.warning("Supplier Name is required.")
            else:
                supplier_data_add_pg2 = {
                    "name": s_name_add_pg2.strip(),
                    "contact_person": (
                        s_contact_person_add_pg2.strip() or None
                    ),  # Ensure None if empty after strip
                    "phone": (s_phone_add_pg2.strip() or None),
                    "email": (s_email_add_pg2.strip() or None),
                    "address": (s_address_add_pg2.strip() or None),
                    "notes": (s_notes_add_pg2.strip() or None),
                    "is_active": True,  # New suppliers are active by default
                }
                success_add_pg2, message_add_pg2 = supplier_service.add_supplier(
                    engine, supplier_data_add_pg2
                )
                if success_add_pg2:
                    st.success(message_add_pg2)
                    fetch_all_suppliers_df_pg2.clear()  # Clear page-specific cache
                    st.rerun()
                else:
                    st.error(message_add_pg2)
st.divider()

# --- VIEW & MANAGE EXISTING SUPPLIERS ---
st.subheader("🔍 View & Manage Existing Suppliers")

filter_s_col1_pg2, filter_s_col2_pg2 = st.columns([3, 1])
with filter_s_col1_pg2:
    st.session_state.pg2_supplier_search_term = st.text_input(
        "Search Suppliers (by Name, Contact, Email)",
        value=st.session_state.pg2_supplier_search_term,
        key="supplier_search_input_pg2_v3",  # Unique key
        placeholder="e.g., Fresh Produce Inc, John Doe, sales@...",
    )
with filter_s_col2_pg2:
    st.session_state.pg2_show_inactive_suppliers = st.toggle(
        "Show Inactive",
        value=st.session_state.pg2_show_inactive_suppliers,
        key="show_inactive_suppliers_toggle_pg2_v3",  # Unique key
        help="Toggle to include inactive suppliers",
    )

all_suppliers_df_pg2 = fetch_all_suppliers_df_pg2(
    engine, st.session_state.pg2_show_inactive_suppliers
)
filtered_suppliers_df_pg2 = (
    all_suppliers_df_pg2.copy()
)  # Start with all (respecting inactive toggle)

if st.session_state.pg2_supplier_search_term:
    search_term_pg2 = st.session_state.pg2_supplier_search_term.lower()
    # Ensure columns exist before trying to filter on them, and handle NaN safely
    name_matches = (
        filtered_suppliers_df_pg2["name"]
        .astype(str)
        .str.lower()
        .str.contains(search_term_pg2, na=False)
    )
    contact_matches = (
        filtered_suppliers_df_pg2["contact_person"]
        .astype(str)
        .str.lower()
        .str.contains(search_term_pg2, na=False)
    )
    email_matches = (
        filtered_suppliers_df_pg2["email"]
        .astype(str)
        .str.lower()
        .str.contains(search_term_pg2, na=False)
    )
    filtered_suppliers_df_pg2 = filtered_suppliers_df_pg2[
        name_matches | contact_matches | email_matches
    ]


if filtered_suppliers_df_pg2.empty:
    st.info(
        "No suppliers found matching your criteria."
        if st.session_state.pg2_supplier_search_term
        or st.session_state.pg2_show_inactive_suppliers
        else "No active suppliers found. Add suppliers or adjust filters."
    )
else:
    total_suppliers_pg2 = len(filtered_suppliers_df_pg2)
    st.write(f"Found {total_suppliers_pg2} supplier(s) matching your criteria.")

    s_items_per_page_options_pg2 = [5, 10, 20, 50]
    current_s_ipp_value_pg2 = st.session_state.pg2_suppliers_per_page
    if current_s_ipp_value_pg2 not in s_items_per_page_options_pg2:
        current_s_ipp_value_pg2 = s_items_per_page_options_pg2[0]
        st.session_state.pg2_suppliers_per_page = current_s_ipp_value_pg2

    st.session_state.pg2_suppliers_per_page = st.selectbox(
        "Suppliers per page:",
        options=s_items_per_page_options_pg2,
        index=s_items_per_page_options_pg2.index(current_s_ipp_value_pg2),
        key="suppliers_per_page_selector_pg2_v3",  # Unique key
    )

    s_total_pages_pg2 = math.ceil(
        total_suppliers_pg2 / st.session_state.pg2_suppliers_per_page
    )
    if s_total_pages_pg2 == 0:
        s_total_pages_pg2 = 1
    if st.session_state.pg2_current_page_suppliers > s_total_pages_pg2:
        st.session_state.pg2_current_page_suppliers = s_total_pages_pg2
    if st.session_state.pg2_current_page_suppliers < 1:
        st.session_state.pg2_current_page_suppliers = 1

    s_page_nav_cols_pg2 = st.columns(5)
    if s_page_nav_cols_pg2[0].button(
        "⏮️ First",
        key="s_first_page_pg2_v4",
        disabled=(st.session_state.pg2_current_page_suppliers == 1),
    ):
        st.session_state.pg2_current_page_suppliers = 1
        st.session_state.pg2_show_edit_form_for_supplier_id = None
        st.rerun()
    if s_page_nav_cols_pg2[1].button(
        "⬅️ Previous",
        key="s_prev_page_pg2_v4",
        disabled=(st.session_state.pg2_current_page_suppliers == 1),
    ):
        st.session_state.pg2_current_page_suppliers -= 1
        st.session_state.pg2_show_edit_form_for_supplier_id = None
        st.rerun()
    s_page_nav_cols_pg2[2].write(
        f"Page {st.session_state.pg2_current_page_suppliers} of {s_total_pages_pg2}"
    )
    if s_page_nav_cols_pg2[3].button(
        "Next ➡️",
        key="s_next_page_pg2_v4",
        disabled=(st.session_state.pg2_current_page_suppliers == s_total_pages_pg2),
    ):
        st.session_state.pg2_current_page_suppliers += 1
        st.session_state.pg2_show_edit_form_for_supplier_id = None
        st.rerun()
    if s_page_nav_cols_pg2[4].button(
        "Last ⏭️",
        key="s_last_page_pg2_v4",
        disabled=(st.session_state.pg2_current_page_suppliers == s_total_pages_pg2),
    ):
        st.session_state.pg2_current_page_suppliers = s_total_pages_pg2
        st.session_state.pg2_show_edit_form_for_supplier_id = None
        st.rerun()

    s_start_idx_pg2 = (
        st.session_state.pg2_current_page_suppliers - 1
    ) * st.session_state.pg2_suppliers_per_page
    s_end_idx_pg2 = s_start_idx_pg2 + st.session_state.pg2_suppliers_per_page
    paginated_suppliers_df_pg2 = filtered_suppliers_df_pg2.iloc[
        s_start_idx_pg2:s_end_idx_pg2
    ]

    s_cols_header_pg2 = st.columns((3, 2, 2, 2.5, 1, 2.5))  # Adjusted for email width
    s_headers_pg2 = [
        "Supplier Name",
        "Contact Person",
        "Phone",
        "Email",
        "Active",
        "Actions",
    ]
    for col_s_h_pg2, header_s_h_pg2 in zip(s_cols_header_pg2, s_headers_pg2):
        col_s_h_pg2.markdown(f"**{header_s_h_pg2}**")
    st.divider()

    for _, supplier_row_pg2 in paginated_suppliers_df_pg2.iterrows():
        supplier_id_pg2 = supplier_row_pg2["supplier_id"]
        supplier_name_pg2 = supplier_row_pg2["name"]
        s_is_active_pg2 = supplier_row_pg2["is_active"]

        s_cols_row_pg2 = st.columns((3, 2, 2, 2.5, 1, 2.5))  # Matched header
        s_cols_row_pg2[0].write(supplier_name_pg2)
        s_cols_row_pg2[1].write(supplier_row_pg2.get("contact_person") or "N/A")
        s_cols_row_pg2[2].write(supplier_row_pg2.get("phone") or "N/A")
        s_cols_row_pg2[3].write(supplier_row_pg2.get("email") or "N/A")
        s_cols_row_pg2[4].checkbox(
            "",
            value=s_is_active_pg2,
            disabled=True,
            key=f"s_active_disp_pg2_{supplier_id_pg2}",
        )  # Unique key

        with s_cols_row_pg2[5]:  # Action buttons
            s_button_key_prefix_pg2 = (
                f"s_action_pg2_{supplier_id_pg2}"  # Unique key prefix
            )
            if (
                st.session_state.get("pg2_show_edit_form_for_supplier_id")
                == supplier_id_pg2
            ):
                if st.button(
                    "✖️ Cancel Edit",
                    key=f"{s_button_key_prefix_pg2}_cancel_edit_v4",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state.pg2_show_edit_form_for_supplier_id = None
                    st.rerun()
            else:
                action_buttons_cols_pg2 = st.columns(
                    2
                )  # For Edit and Activate/Deactivate side-by-side
                if s_is_active_pg2:
                    if action_buttons_cols_pg2[0].button(
                        "✏️",
                        key=f"{s_button_key_prefix_pg2}_edit_v4",
                        help="Edit Supplier",
                        type="primary",
                        use_container_width=True,
                    ):
                        st.session_state.pg2_show_edit_form_for_supplier_id = (
                            supplier_id_pg2
                        )
                        st.session_state.pg2_edit_supplier_form_values = (
                            supplier_service.get_supplier_details(
                                engine, supplier_id_pg2
                            )
                        )
                        st.rerun()
                    if action_buttons_cols_pg2[1].button(
                        "🗑️",
                        key=f"{s_button_key_prefix_pg2}_deact_v4",
                        help="Deactivate Supplier",
                        use_container_width=True,
                    ):
                        success_deact_pg2, msg_deact_pg2 = (
                            supplier_service.deactivate_supplier(
                                engine, supplier_id_pg2
                            )
                        )
                        if success_deact_pg2:
                            st.success(msg_deact_pg2)
                            fetch_all_suppliers_df_pg2.clear()
                            st.rerun()
                        else:
                            st.error(msg_deact_pg2)
                else:  # Supplier is inactive
                    if action_buttons_cols_pg2[0].button(
                        "✅",
                        key=f"{s_button_key_prefix_pg2}_react_v4",
                        help="Reactivate Supplier",
                        use_container_width=True,
                    ):
                        success_react_pg2, msg_react_pg2 = (
                            supplier_service.reactivate_supplier(
                                engine, supplier_id_pg2
                            )
                        )
                        if success_react_pg2:
                            st.success(msg_react_pg2)
                            fetch_all_suppliers_df_pg2.clear()
                            st.rerun()
                        else:
                            st.error(msg_react_pg2)
        st.divider()

        # Inline Edit Form for selected supplier
        if (
            st.session_state.get("pg2_show_edit_form_for_supplier_id")
            == supplier_id_pg2
        ):
            current_s_values_for_edit_pg2 = st.session_state.get(
                "pg2_edit_supplier_form_values"
            )
            # Ensure correct supplier's data is loaded for edit form
            if (
                not current_s_values_for_edit_pg2
                or current_s_values_for_edit_pg2.get("supplier_id") != supplier_id_pg2
            ):
                current_s_values_for_edit_pg2 = supplier_service.get_supplier_details(
                    engine, supplier_id_pg2
                )
                st.session_state.pg2_edit_supplier_form_values = (
                    current_s_values_for_edit_pg2
                )

            if current_s_values_for_edit_pg2:  # Check if data was successfully fetched
                # Unique form key for edit
                with st.form(key=f"edit_s_form_inline_pg2_v4_{supplier_id_pg2}"):
                    st.subheader(
                        f"✏️ Editing Supplier: {current_s_values_for_edit_pg2.get('name', 'N/A')}"
                    )
                    st.caption(f"Supplier ID: {supplier_id_pg2}")

                    s_edit_col1_pg2, s_edit_col2_pg2 = st.columns(2)
                    with s_edit_col1_pg2:
                        es_name_pg2 = st.text_input(
                            "Supplier Name*",
                            value=current_s_values_for_edit_pg2.get("name", ""),
                            key=f"es_name_pg2_v4_{supplier_id_pg2}",
                        )
                        es_contact_pg2 = st.text_input(
                            "Contact Person",
                            value=current_s_values_for_edit_pg2.get(
                                "contact_person", ""
                            )
                            or "",  # Ensure string for value
                            key=f"es_contact_pg2_v4_{supplier_id_pg2}",
                        )
                    with s_edit_col2_pg2:
                        es_phone_pg2 = st.text_input(
                            "Phone",
                            value=current_s_values_for_edit_pg2.get("phone", "") or "",
                            key=f"es_phone_pg2_v4_{supplier_id_pg2}",
                        )
                        es_email_pg2 = st.text_input(
                            "Email",
                            value=current_s_values_for_edit_pg2.get("email", "") or "",
                            key=f"es_email_pg2_v4_{supplier_id_pg2}",
                        )
                    es_address_pg2 = st.text_area(
                        "Address",
                        value=current_s_values_for_edit_pg2.get("address", "") or "",
                        key=f"es_address_pg2_v4_{supplier_id_pg2}",
                    )
                    es_notes_pg2 = st.text_area(
                        "Notes",
                        value=current_s_values_for_edit_pg2.get("notes", "") or "",
                        key=f"es_notes_pg2_v4_{supplier_id_pg2}",
                    )

                    if st.form_submit_button("💾 Update Supplier Details"):
                        if not es_name_pg2.strip():
                            st.warning("Supplier Name is required.")
                        else:
                            update_s_data_pg2 = {
                                "name": es_name_pg2.strip(),
                                "contact_person": (es_contact_pg2.strip() or None),
                                "phone": (es_phone_pg2.strip() or None),
                                "email": (es_email_pg2.strip() or None),
                                "address": (es_address_pg2.strip() or None),
                                "notes": (es_notes_pg2.strip() or None),
                            }
                            ok_update_pg2, msg_update_pg2 = (
                                supplier_service.update_supplier(
                                    engine, supplier_id_pg2, update_s_data_pg2
                                )
                            )
                            if ok_update_pg2:
                                st.success(msg_update_pg2)
                                st.session_state.pg2_show_edit_form_for_supplier_id = (
                                    None  # Close form
                                )
                                st.session_state.pg2_edit_supplier_form_values = (
                                    None  # Clear form values
                                )
                                fetch_all_suppliers_df_pg2.clear()  # Clear cache
                                st.rerun()
                            else:
                                st.error(msg_update_pg2)
                st.divider()
