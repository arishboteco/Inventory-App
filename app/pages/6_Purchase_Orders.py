# app/pages/6_Purchase_Orders.py
import streamlit as st
import pandas as pd
from datetime import date
from typing import Dict, Any, Optional, List

# --- Assuming your project structure for imports ---
try:
    from app.db.database_utils import connect_db
    from app.services import purchase_order_service
    from app.services import supplier_service
    from app.services import item_service
    from app.services import goods_receiving_service
    from app.core.constants import (
        ALL_PO_STATUSES,
        PO_STATUS_DRAFT,
        PO_STATUS_ORDERED,
        PO_STATUS_PARTIALLY_RECEIVED,
    )
    from app.ui.theme import load_css, format_status_badge, render_sidebar_logo
except ImportError as e:
    st.error(
        f"Import error in 6_Purchase_Orders.py: {e}. Please ensure all modules are correctly placed."
    )
    st.stop()  # Stop execution if imports fail
except Exception as e:  # Catch any other potential import errors
    st.error(
        f"An unexpected error occurred during an import in 6_Purchase_Orders.py: {e}"
    )
    st.stop()

load_css()
render_sidebar_logo()

# --- Page Config and Title ---
st.title("🛒 Purchase Order & Goods Receiving")
st.write("Manage Purchase Orders (POs) and record Goods Received Notes (GRNs).")
st.divider()

# --- Database Connection ---
db_engine = connect_db()
if not db_engine:
    st.error("❌ Database connection failed. Cannot manage Purchase Orders/GRNs.")
    st.stop()

# --- Session State Initialization ---
# View mode and IDs
if "po_grn_view_mode" not in st.session_state:
    st.session_state.po_grn_view_mode = "list_po"  # Default view
if "po_to_edit_id" not in st.session_state:
    st.session_state.po_to_edit_id = None
if "po_to_view_id" not in st.session_state:
    st.session_state.po_to_view_id = None
if "po_for_grn_id" not in st.session_state:
    st.session_state.po_for_grn_id = None
if (
    "po_for_grn_details" not in st.session_state
):  # Stores fetched PO details for GRN creation
    st.session_state.po_for_grn_details = None
if "grn_line_items" not in st.session_state:  # Stores items being prepared for GRN
    st.session_state.grn_line_items = []

# PO Form specific state
if (
    "form_reset_signal" not in st.session_state
):  # Used to signal when PO form should reload/reset
    st.session_state.form_reset_signal = True
if (
    "form_po_line_items" not in st.session_state
):  # Stores line items for create/edit PO form
    st.session_state.form_po_line_items = []
if (
    "form_po_next_line_id" not in st.session_state
):  # Counter for unique IDs for new PO lines
    st.session_state.form_po_next_line_id = 0

DEFAULT_SUPPLIER_KEY_PG6 = "-- Select Supplier --"  # Placeholder for supplier dropdown

# Initialize PO form field values (persisted across reruns within the form)
if "form_supplier_name_val" not in st.session_state:
    st.session_state.form_supplier_name_val = DEFAULT_SUPPLIER_KEY_PG6
if "form_order_date_val" not in st.session_state:
    st.session_state.form_order_date_val = date.today()
if "form_exp_delivery_date_val" not in st.session_state:
    st.session_state.form_exp_delivery_date_val = None  # Optional
if "form_notes_val" not in st.session_state:
    st.session_state.form_notes_val = ""
if "form_user_id_val" not in st.session_state:
    st.session_state.form_user_id_val = ""  # For created_by/updated_by
if "current_po_status_for_edit" not in st.session_state:
    st.session_state.current_po_status_for_edit = (
        None  # Tracks status of PO being edited
    )
if "loaded_po_for_edit_id" not in st.session_state:
    st.session_state.loaded_po_for_edit_id = (
        None  # Tracks which PO ID's data is loaded in form
    )

# Default user ID if not entered by user (can be improved with actual user login later)
if "po_submitter_user_id" not in st.session_state:
    st.session_state.po_submitter_user_id = "System"

# GRN Form field values
if "grn_received_date_val" not in st.session_state:
    st.session_state.grn_received_date_val = date.today()
if "grn_received_by_val" not in st.session_state:
    st.session_state.grn_received_by_val = ""
if "grn_header_notes_val" not in st.session_state:
    st.session_state.grn_header_notes_val = ""


def change_view_mode(
    mode: str,
    po_id: Optional[int] = None,
    clear_grn_state: bool = True,
    clear_po_form_state: bool = True,
):
    """Manages UI view changes and resets relevant session state."""
    previous_mode = st.session_state.get("po_grn_view_mode", "list_po")
    st.session_state.po_grn_view_mode = mode

    st.session_state.po_to_edit_id = po_id if mode == "edit_po" else None
    st.session_state.po_to_view_id = po_id if mode == "view_po_details" else None
    st.session_state.po_for_grn_id = po_id if mode == "create_grn_for_po" else None

    # Load data for GRN creation if switching to that mode with a PO ID
    if mode == "create_grn_for_po" and po_id:
        po_details_for_grn_init_func = purchase_order_service.get_po_by_id(
            db_engine, po_id
        )
        st.session_state.po_for_grn_details = po_details_for_grn_init_func
        st.session_state.grn_line_items = []  # Reset GRN line items
        if po_details_for_grn_init_func and po_details_for_grn_init_func.get("items"):
            previously_received_df = (
                goods_receiving_service.get_received_quantities_for_po(db_engine, po_id)
            )
            for item_grn_prep in po_details_for_grn_init_func["items"]:  # Renamed var
                po_item_id_grn = item_grn_prep["po_item_id"]
                ordered_qty_grn = float(item_grn_prep["quantity_ordered"])

                already_received_series = previously_received_df[
                    previously_received_df["po_item_id"] == po_item_id_grn
                ]["total_previously_received"]
                already_received_qty_grn = (
                    float(already_received_series.iloc[0])
                    if not already_received_series.empty
                    else 0.0
                )

                remaining_to_receive_grn = max(
                    0.0, ordered_qty_grn - already_received_qty_grn
                )

                st.session_state.grn_line_items.append(
                    {
                        "po_item_id": po_item_id_grn,
                        "item_id": item_grn_prep["item_id"],
                        "item_name": item_grn_prep["item_name"],
                        "item_unit": item_grn_prep["item_unit"],
                        "quantity_ordered_on_po": ordered_qty_grn,
                        "total_previously_received": already_received_qty_grn,
                        "quantity_remaining_on_po": remaining_to_receive_grn,
                        "quantity_received_now": 0.0,  # Default to 0 for "Qty Rcv Now"
                        "unit_price_at_receipt": float(
                            item_grn_prep["unit_price"]
                        ),  # Default to PO price
                    }
                )
    elif (
        clear_grn_state and mode != "create_grn_for_po"
    ):  # Clear GRN state if not creating GRN
        st.session_state.po_for_grn_id = None
        st.session_state.po_for_grn_details = None
        st.session_state.grn_line_items = []
        st.session_state.grn_received_date_val = date.today()
        st.session_state.grn_received_by_val = ""
        st.session_state.grn_header_notes_val = ""

    # Signal to reset PO form if mode changes require it
    if mode in ["create_po", "edit_po"]:
        # Reset if:
        # 1. Coming from a non-form mode
        # 2. Switching to "edit_po" and it's a different PO or wasn't in edit mode before
        # 3. Switching to "create_po" and wasn't in create mode before
        if (
            previous_mode not in ["create_po", "edit_po"]
            or (
                mode == "edit_po"
                and (
                    previous_mode != "edit_po"
                    or st.session_state.po_to_edit_id
                    != st.session_state.get("loaded_po_for_edit_id")
                )
            )
            or (mode == "create_po" and previous_mode != "create_po")
        ):
            st.session_state.form_reset_signal = True
    elif (
        previous_mode in ["create_po", "edit_po"]
        and mode not in ["create_po", "edit_po"]
        and clear_po_form_state
    ):
        # If moving away from a form mode, signal reset for next time form is opened
        st.session_state.form_reset_signal = True


# --- Main Page Logic (Router) ---
if st.session_state.po_grn_view_mode == "list_po":
    st.subheader("📋 Existing Purchase Orders")
    # Filters for PO list
    filter_col1_list, filter_col2_list, filter_col3_list = st.columns([2, 2, 1])
    with filter_col1_list:
        search_po_list_val = st.text_input(
            "Search PO #:",
            key="po_search_list_v1",
            placeholder="e.g., PO-0001",
            help="Search by partial or full PO number.",
        )
    with filter_col2_list:
        suppliers_df_list = supplier_service.get_all_suppliers(
            db_engine, True
        )  # Include inactive for filtering
        supplier_options_list = {DEFAULT_SUPPLIER_KEY_PG6: None}
        if not suppliers_df_list.empty:
            supplier_options_list.update(
                {
                    f"{r['name']} {'(Inactive)' if not r['is_active'] else ''}": r[
                        "supplier_id"
                    ]
                    for _, r in suppliers_df_list.iterrows()
                }
            )
        sel_supp_name_list = st.selectbox(
            "Filter by Supplier:",
            options=list(supplier_options_list.keys()),
            key="po_filter_supplier_list_v1",
            help="Filter POs by supplier.",
        )
        sel_supp_id_list = supplier_options_list.get(sel_supp_name_list)
    with filter_col3_list:
        sel_status_list = st.selectbox(
            "Filter by Status:",
            options=["All Statuses"] + ALL_PO_STATUSES,
            key="po_filter_status_list_v1",
            help="Filter POs by status.",
        )

    if st.button(
        "➕ Create New Purchase Order",
        key="nav_to_create_po_btn_v1",
        type="primary",
        use_container_width=True,
    ):
        change_view_mode(
            "create_po", clear_po_form_state=True
        )  # Ensure form reset for new PO
        st.rerun()
    st.divider()

    # Fetch and display POs
    query_filters_list_ui: Dict[str, Any] = {}
    if search_po_list_val:
        query_filters_list_ui["po_number_ilike"] = search_po_list_val
    if sel_supp_id_list:
        query_filters_list_ui["supplier_id"] = sel_supp_id_list
    if sel_status_list != "All Statuses":
        query_filters_list_ui["status"] = sel_status_list

    pos_df_display = purchase_order_service.list_pos(
        db_engine, filters=query_filters_list_ui
    )

    if pos_df_display.empty:
        st.info("ℹ️ No Purchase Orders found matching your criteria.")
    else:
        st.write(f"Found {len(pos_df_display)} Purchase Order(s).")
        for _, row_po_list_item in pos_df_display.iterrows():  # Renamed var
            po_id_list = row_po_list_item["po_id"]
            status_po_list_item = row_po_list_item["status"]

            st.markdown(
                f"**PO #: {row_po_list_item['po_number']}** | Supplier: {row_po_list_item['supplier_name']} | Status: {format_status_badge(status_po_list_item)}",
                unsafe_allow_html=True,
            )

            disp_cols_po_list = st.columns([1.5, 1.5, 1, 1, 2.5])  # Renamed var
            order_date_disp = (
                pd.to_datetime(row_po_list_item["order_date"]).strftime("%d-%b-%y")
                if pd.notna(row_po_list_item["order_date"])
                else "N/A"
            )
            exp_delivery_date_disp = (
                pd.to_datetime(row_po_list_item["expected_delivery_date"]).strftime(
                    "%d-%b-%y"
                )
                if pd.notna(row_po_list_item["expected_delivery_date"])
                else "N/A"
            )
            total_amount_disp = (
                f"{row_po_list_item['total_amount']:.2f}"
                if pd.notna(row_po_list_item["total_amount"])
                else "N/A"
            )

            disp_cols_po_list[0].markdown(
                f"<small>Order Date: {order_date_disp}</small>", unsafe_allow_html=True
            )
            disp_cols_po_list[1].markdown(
                f"<small>Expected Delivery: {exp_delivery_date_disp}</small>",
                unsafe_allow_html=True,
            )
            disp_cols_po_list[2].markdown(
                f"<small>Total: {total_amount_disp}</small>", unsafe_allow_html=True
            )

            with disp_cols_po_list[3]:  # View button
                if st.button(
                    "👁️ View",
                    key=f"view_po_btn_list_v2_{po_id_list}",
                    help="View PO Details",
                    use_container_width=True,
                ):
                    change_view_mode("view_po_details", po_id=po_id_list)
                    st.rerun()

            with disp_cols_po_list[4]:  # Action buttons column
                action_buttons_cols_in_list = st.columns(
                    [1, 1]
                )  # Sub-columns for Edit/Receive

                if status_po_list_item == PO_STATUS_DRAFT:
                    if action_buttons_cols_in_list[0].button(
                        "✏️ Edit",
                        key=f"edit_po_btn_list_v2_{po_id_list}",
                        help="Edit this Draft PO",
                        use_container_width=True,
                    ):
                        change_view_mode(
                            "edit_po", po_id=po_id_list, clear_po_form_state=False
                        )  # Keep form state if any, will be overwritten by load
                        st.rerun()
                # else: action_buttons_cols_in_list[0].write("") # Placeholder if no edit button

                if status_po_list_item in [
                    PO_STATUS_ORDERED,
                    PO_STATUS_PARTIALLY_RECEIVED,
                ]:
                    if action_buttons_cols_in_list[1].button(
                        "📥 Receive",
                        key=f"receive_po_btn_list_v2_{po_id_list}",
                        help="Record goods receipt for this PO.",
                        type="primary",
                        use_container_width=True,
                    ):
                        change_view_mode(
                            "create_grn_for_po", po_id=po_id_list, clear_grn_state=False
                        )  # Don't clear GRN state yet, will load PO details
                        st.rerun()
                # else: action_buttons_cols_in_list[1].write("") # Placeholder if no receive button
            st.divider()

# --- CREATE OR EDIT PO FORM ---
elif st.session_state.po_grn_view_mode in ["create_po", "edit_po"]:
    is_edit_mode = st.session_state.po_grn_view_mode == "edit_po"
    form_title = (
        "✏️ Edit Purchase Order" if is_edit_mode else "🆕 Create New Purchase Order"
    )
    st.subheader(form_title)

    # Data for dropdowns
    supp_df_form = supplier_service.get_all_suppliers(
        db_engine, include_inactive=is_edit_mode
    )
    supp_dict_form = {DEFAULT_SUPPLIER_KEY_PG6: None}
    if not supp_df_form.empty:
        supp_dict_form.update(
            {
                f"{r['name'].strip()} {'(Inactive)' if not r['is_active'] else ''}": r[
                    "supplier_id"
                ]
                for _, r in supp_df_form.iterrows()
                if r["name"]  # Ensure name is not None
            }
        )

    item_df_form = item_service.get_all_items_with_stock(
        db_engine, include_inactive=is_edit_mode
    )
    item_dict_form = {"-- Select Item --": (None, None)}  # (item_id, unit)
    if not item_df_form.empty:
        item_dict_form.update(
            {
                f"{r['name'].strip()} ({r['unit'].strip()}) {'[Inactive]' if not r['is_active'] else ''}": (
                    r["item_id"],
                    r["unit"].strip(),
                )
                for _, r in item_df_form.iterrows()
                if r["name"] and r["unit"]  # Ensure name and unit exist
            }
        )

    # Load data if in Edit Mode and reset signal is active or PO ID changed
    if is_edit_mode:
        if not st.session_state.po_to_edit_id:
            st.error(
                "❌ PO ID for editing is missing. Please return to the list and select a PO."
            )
            if st.button("⬅️ Back to PO List", key="back_edit_po_no_id_v2_page6"):
                change_view_mode("list_po")
                st.rerun()
            st.stop()

        # Condition to load/reload PO data into form state
        if (
            st.session_state.form_reset_signal
            or st.session_state.get("loaded_po_for_edit_id")
            != st.session_state.po_to_edit_id
        ):
            po_data_to_edit = purchase_order_service.get_po_by_id(
                db_engine, st.session_state.po_to_edit_id
            )
            if not po_data_to_edit:
                st.error(
                    f"❌ Could not load details for PO ID: {st.session_state.po_to_edit_id}. It might have been deleted."
                )
                change_view_mode("list_po")
                st.rerun()
                st.stop()

            if po_data_to_edit.get("status") != PO_STATUS_DRAFT:
                st.warning(
                    f"⚠️ PO {po_data_to_edit.get('po_number')} is in '{po_data_to_edit.get('status')}' status and cannot be edited."
                )
                change_view_mode("list_po")
                st.rerun()
                st.stop()

            st.session_state.current_po_status_for_edit = po_data_to_edit.get(
                "status"
            )  # Store current status

            # Pre-fill header fields
            # Find supplier display name from dictionary
            supplier_name_for_form = DEFAULT_SUPPLIER_KEY_PG6
            for name_key, supp_id_val_dict in supp_dict_form.items():
                if supp_id_val_dict == po_data_to_edit.get("supplier_id"):
                    supplier_name_for_form = name_key
                    break
            st.session_state.form_supplier_name_val = supplier_name_for_form

            st.session_state.form_order_date_val = (
                pd.to_datetime(po_data_to_edit.get("order_date")).date()
                if pd.notna(po_data_to_edit.get("order_date"))
                else date.today()
            )
            st.session_state.form_exp_delivery_date_val = (
                pd.to_datetime(po_data_to_edit.get("expected_delivery_date")).date()
                if pd.notna(po_data_to_edit.get("expected_delivery_date"))
                else None
            )
            st.session_state.form_notes_val = po_data_to_edit.get("notes", "")
            st.session_state.form_user_id_val = po_data_to_edit.get(
                "created_by_user_id", st.session_state.get("po_submitter_user_id", "")
            )  # Use stored or default

            # Pre-fill line items
            st.session_state.form_po_line_items = []  # Reset before loading
            next_line_id_counter_edit = 0

            for item_data_db_edit in po_data_to_edit.get("items", []):
                po_item_id_from_db = item_data_db_edit.get("item_id")
                actual_item_key_for_dropdown_edit = (
                    "-- Select Item --"  # Default if not found
                )

                # Find the key in item_dict_form that corresponds to this item_id
                if po_item_id_from_db is not None:
                    for display_key_edit, (
                        master_item_id_edit,
                        _,
                    ) in item_dict_form.items():
                        if master_item_id_edit == po_item_id_from_db:
                            actual_item_key_for_dropdown_edit = display_key_edit
                            break

                if (
                    actual_item_key_for_dropdown_edit == "-- Select Item --"
                    and po_item_id_from_db is not None
                ):
                    # Item might have been deleted or is unselectable for some reason.
                    # Log this for debugging, the UI will show "-- Select Item --".
                    original_po_item_name = item_data_db_edit.get(
                        "item_name", "Unknown/Deleted Item"
                    ).strip()
                    original_po_item_unit = item_data_db_edit.get(
                        "item_unit", "N/A"
                    ).strip()
                    print(
                        f"WARNING (Edit PO Pre-fill): Item ID {po_item_id_from_db} (Name: {original_po_item_name}) from PO not found or matched in current item dropdown options."
                    )
                    # We still add the line, but it will default to placeholder. User will need to re-select.
                    # Alternatively, could try to show the original name/unit as static text if no match.

                st.session_state.form_po_line_items.append(
                    {
                        "id": next_line_id_counter_edit,
                        "item_key": actual_item_key_for_dropdown_edit,  # This key must match item_dict_form
                        "quantity": float(
                            item_data_db_edit.get("quantity_ordered", 0.0)
                        ),
                        "unit_price": float(item_data_db_edit.get("unit_price", 0.0)),
                        "unit": item_data_db_edit.get(
                            "item_unit", ""
                        ).strip(),  # Store the unit from PO for reference
                    }
                )
                next_line_id_counter_edit += 1

            st.session_state.form_po_next_line_id = (
                next_line_id_counter_edit  # For adding new lines later
            )

            if (
                not st.session_state.form_po_line_items
            ):  # If PO had no items, add one blank line
                st.session_state.form_po_line_items = [
                    {
                        "id": 0,
                        "item_key": "-- Select Item --",
                        "quantity": 1.0,
                        "unit_price": 0.0,
                        "unit": "",
                    }
                ]
                st.session_state.form_po_next_line_id = 1

            st.session_state.loaded_po_for_edit_id = (
                st.session_state.po_to_edit_id
            )  # Mark as loaded
            st.session_state.form_reset_signal = False  # Consume reset signal

    # Initialize form for "Create PO" or if reset signal was for create mode
    elif st.session_state.form_reset_signal:
        st.session_state.form_po_line_items = [
            {
                "id": 0,
                "item_key": "-- Select Item --",
                "quantity": 1.0,
                "unit_price": 0.0,
                "unit": "",
            }
        ]
        st.session_state.form_po_next_line_id = 1
        st.session_state.form_supplier_name_val = DEFAULT_SUPPLIER_KEY_PG6
        st.session_state.form_order_date_val = date.today()
        st.session_state.form_exp_delivery_date_val = None
        st.session_state.form_notes_val = ""
        st.session_state.form_user_id_val = st.session_state.get(
            "po_submitter_user_id", ""
        )  # Default user
        st.session_state.loaded_po_for_edit_id = (
            None  # Clear loaded PO ID for create mode
        )
        st.session_state.form_reset_signal = False  # Consume signal
    elif (
        not st.session_state.form_po_line_items
    ):  # Ensure at least one line if state somehow empty
        st.session_state.form_po_line_items = [
            {
                "id": 0,
                "item_key": "-- Select Item --",
                "quantity": 1.0,
                "unit_price": 0.0,
                "unit": "",
            }
        ]
        st.session_state.form_po_next_line_id = 1

    # Back button
    if st.button("⬅️ Back to PO List", key=f"back_form_po_v2_{is_edit_mode}"):
        change_view_mode("list_po", clear_po_form_state=True)
        st.rerun()

    # Callbacks for dynamic line items
    def add_po_line_item_form_ss():  # Renamed for clarity
        new_id_form = st.session_state.form_po_next_line_id
        st.session_state.form_po_line_items.append(
            {
                "id": new_id_form,
                "item_key": "-- Select Item --",
                "quantity": 1.0,
                "unit_price": 0.0,
                "unit": "",
            }
        )
        st.session_state.form_po_next_line_id += 1

    def remove_po_line_item_form_ss(id_to_remove_form):  # Renamed for clarity
        st.session_state.form_po_line_items = [
            l
            for l in st.session_state.form_po_line_items
            if l["id"] != id_to_remove_form
        ]
        if (
            not st.session_state.form_po_line_items
        ):  # Ensure at least one line always exists
            add_po_line_item_form_ss()

    # --- PO Header Form ---
    st.markdown("##### 📋 PO Header Details")
    form_key_po_create_edit = (
        f"po_form_v2_{'edit' if is_edit_mode else 'create'}"  # Dynamic form key
    )
    with st.form(form_key_po_create_edit):
        # Supplier selection
        current_supplier_form_val_widget = st.session_state.form_supplier_name_val
        if (
            current_supplier_form_val_widget not in supp_dict_form
        ):  # Fallback if selected supplier no longer valid
            current_supplier_form_val_widget = DEFAULT_SUPPLIER_KEY_PG6

        supplier_idx_form_ui_val = list(supp_dict_form.keys()).index(
            current_supplier_form_val_widget
        )

        selected_supplier_widget_val = st.selectbox(  # Renamed var
            "Supplier*",
            options=list(supp_dict_form.keys()),
            index=supplier_idx_form_ui_val,
            key="form_po_supplier_select_v2",  # Unique widget key
            help="Choose the supplier for this Purchase Order.",
        )
        st.session_state.form_supplier_name_val = (
            selected_supplier_widget_val  # Update session state
        )
        selected_supplier_id_for_submit = supp_dict_form.get(
            selected_supplier_widget_val
        )  # Get ID for submission

        # Dates and User ID
        hcols_form1, hcols_form2 = st.columns(2)  # Renamed vars
        with hcols_form1:
            st.session_state.form_order_date_val = hcols_form1.date_input(
                "Order Date*",
                value=st.session_state.form_order_date_val,
                key="form_po_order_date_v2",
                help="Date the order is placed.",
            )
        with hcols_form2:
            st.session_state.form_exp_delivery_date_val = hcols_form2.date_input(
                "Expected Delivery Date",
                value=st.session_state.form_exp_delivery_date_val,
                key="form_po_exp_delivery_date_v2",
                help="Optional: Expected date for goods to arrive.",
            )

        st.session_state.form_notes_val = st.text_area(
            "PO Notes",
            value=st.session_state.form_notes_val,
            key="form_po_notes_v2",
            placeholder="e.g., Special instructions, payment terms...",
            help="Optional notes or remarks for this Purchase Order.",
        )
        st.session_state.form_user_id_val = st.text_input(
            "Your Name/ID*",
            value=st.session_state.form_user_id_val,
            key="form_po_user_id_v2",
            placeholder="Enter your identifier (e.g., name or employee ID)",
            help="Identifier of the person creating or editing this PO.",
        )

        # Submit PO to Supplier button (only in edit mode for draft POs within header form)
        if (
            is_edit_mode
            and st.session_state.current_po_status_for_edit == PO_STATUS_DRAFT
        ):
            if st.form_submit_button(
                "➡️ Submit PO to Supplier",
                use_container_width=True,
                help="Finalize and change status to 'Ordered'.",
            ):
                user_id_for_status_update = (
                    st.session_state.form_user_id_val.strip()
                    or st.session_state.po_submitter_user_id
                )
                success_status_update, msg_status_update = (
                    purchase_order_service.update_po_status(
                        db_engine,
                        st.session_state.po_to_edit_id,
                        PO_STATUS_ORDERED,
                        user_id_for_status_update,
                    )
                )
                if success_status_update:
                    st.success(
                        f"PO status successfully updated to '{PO_STATUS_ORDERED}'. {msg_status_update}"
                    )
                    change_view_mode("list_po", clear_po_form_state=True)
                    st.rerun()
                else:
                    st.error(f"❌ Failed to submit PO: {msg_status_update}")

        st.divider()
        form_submit_button_label = (
            "💾 Update Purchase Order" if is_edit_mode else "💾 Create Purchase Order"
        )
        submit_button_po_form = st.form_submit_button(
            form_submit_button_label, type="primary", use_container_width=True
        )

    # --- PO Line Items Section (managed outside the st.form for header for dynamic add/remove) ---
    st.markdown("##### 🛍️ PO Line Items")
    line_header_cols = st.columns([4, 1, 1.5, 1, 0.5])  # Renamed var
    line_header_cols[0].markdown("**Item**")
    line_header_cols[1].markdown("**Qty**")
    line_header_cols[2].markdown("**Unit Price**")
    line_header_cols[3].markdown("**Unit**")
    line_header_cols[4].markdown("**Act**")  # Action (Remove)

    current_lines_for_render_form: List[Dict[str, Any]] = (
        []
    )  # To store widget values for processing
    for i_po_line, line_item_state_form in enumerate(
        st.session_state.form_po_line_items
    ):  # Renamed vars
        line_item_cols_form = st.columns([4, 1, 1.5, 1, 0.5])  # Renamed var
        line_item_id_form = line_item_state_form[
            "id"
        ]  # Unique ID for this line item instance

        # Item Selectbox
        current_item_key_form_line = line_item_state_form.get(
            "item_key", "-- Select Item --"
        )
        if (
            current_item_key_form_line not in item_dict_form
        ):  # Fallback if key is somehow invalid
            current_item_key_form_line = "-- Select Item --"
            st.session_state.form_po_line_items[i_po_line][
                "item_key"
            ] = current_item_key_form_line  # Correct session state

        try:
            item_idx_form_line = list(item_dict_form.keys()).index(
                current_item_key_form_line
            )
        except ValueError:
            item_idx_form_line = 0  # Default to placeholder
            print(
                f"ERROR [PO Form Render]: Index not found for item key '{current_item_key_form_line}' in line {line_item_id_form}"
            )

        selected_item_name_widget_val = line_item_cols_form[0].selectbox(  # Renamed var
            f"Item_line_select_{line_item_id_form}",
            options=list(item_dict_form.keys()),
            key=f"form_po_line_item_name_v2_{line_item_id_form}",  # Unique widget key
            index=item_idx_form_line,
            label_visibility="collapsed",
        )

        # Update unit based on selection
        _, unit_from_selection = item_dict_form.get(
            selected_item_name_widget_val, (None, "")
        )

        # Quantity Input
        qty_widget_val = line_item_cols_form[1].number_input(  # Renamed var
            f"Qty_line_num_input_{line_item_id_form}",
            value=float(line_item_state_form.get("quantity", 1.0)),
            min_value=0.01,
            step=0.01,
            format="%.2f",  # Min 0.01 for PO
            key=f"form_po_line_qty_v2_{line_item_id_form}",
            label_visibility="collapsed",
        )

        # Price Input
        price_widget_val = line_item_cols_form[2].number_input(  # Renamed var
            f"Price_line_num_input_{line_item_id_form}",
            value=float(line_item_state_form.get("unit_price", 0.0)),
            min_value=0.00,
            step=0.01,
            format="%.2f",
            key=f"form_po_line_price_v2_{line_item_id_form}",
            label_visibility="collapsed",
        )

        # Unit Display (disabled input)
        line_item_cols_form[3].text_input(
            f"Unit_line_text_disp_{line_item_id_form}",
            value=(unit_from_selection or ""),  # Display unit from selection
            key=f"form_po_line_unit_disp_v2_{line_item_id_form}",
            disabled=True,
            label_visibility="collapsed",
        )

        # Remove Line Button
        if len(st.session_state.form_po_line_items) > 1:
            if line_item_cols_form[4].button(
                "➖",
                key=f"form_po_del_line_btn_v2_{line_item_id_form}",
                help="Remove this item line",
            ):
                remove_po_line_item_form_ss(line_item_id_form)
                st.rerun()  # Rerun to reflect removal
        else:
            line_item_cols_form[4].write("")  # Placeholder for single line

        # Store current values from widgets to be used on form submission
        current_lines_for_render_form.append(
            {
                "id": line_item_id_form,
                "item_key": selected_item_name_widget_val,
                "quantity": qty_widget_val,
                "unit_price": price_widget_val,
                "unit": (unit_from_selection or ""),
            }
        )

    # Update session state with values from rendered widgets (important for multi-page forms or complex interactions)
    st.session_state.form_po_line_items = current_lines_for_render_form

    # Add Item Line Button
    if st.button(
        "➕ Add Item Line",
        on_click=add_po_line_item_form_ss,
        key="form_po_add_line_btn_v2",
        help="Add a new item line to the Purchase Order.",
    ):
        pass  # Rerun handled by on_click if it modifies state that needs redraw, or manually st.rerun()
    st.divider()

    # --- Processing Logic for Create/Update PO Form ---
    if submit_button_po_form:
        # Validation for header
        if not selected_supplier_id_for_submit:
            st.warning(
                "⚠️ Supplier is required. Please select a supplier from the list."
            )
        elif not st.session_state.form_user_id_val.strip():
            st.warning("⚠️ Your Name/ID is required in the PO Header.")
        else:
            # Prepare header data
            po_header_data_for_submit = {  # Renamed var
                "supplier_id": selected_supplier_id_for_submit,
                "order_date": st.session_state.form_order_date_val,
                "expected_delivery_date": st.session_state.form_exp_delivery_date_val,
                "notes": st.session_state.form_notes_val.strip()
                or None,  # Ensure None if empty
            }

            # Prepare and validate line items
            po_items_to_submit: List[Dict[str, Any]] = []  # Renamed var, type hint
            are_all_items_valid = True  # Flag for item validation

            if not st.session_state.form_po_line_items or all(
                item_dict_form.get(l.get("item_key", "-- Select Item --"), (None,))[0]
                is None
                for l in st.session_state.form_po_line_items
            ):
                st.error("🛑 Please add at least one valid item to the Purchase Order.")
                are_all_items_valid = False

            if are_all_items_valid:  # Proceed if initial check passes
                for (
                    line_item_data_submit
                ) in st.session_state.form_po_line_items:  # Renamed var
                    item_id_for_submit, _ = item_dict_form.get(
                        line_item_data_submit["item_key"], (None, None)
                    )

                    if item_id_for_submit is None:
                        st.error(
                            f"🛑 Item '{line_item_data_submit['item_key']}' is invalid or not selected. Please select a valid item for all lines."
                        )
                        are_all_items_valid = False
                        break
                    try:
                        qty_for_submit = float(line_item_data_submit["quantity"])
                        price_for_submit = float(line_item_data_submit["unit_price"])
                    except (ValueError, TypeError):
                        st.error(
                            f"🛑 Invalid quantity or price for item '{line_item_data_submit['item_key']}'. Please enter valid numbers."
                        )
                        are_all_items_valid = False
                        break

                    if qty_for_submit <= 0:
                        st.error(
                            f"🛑 Quantity for item '{line_item_data_submit['item_key']}' must be greater than 0."
                        )
                        are_all_items_valid = False
                        break
                    if price_for_submit < 0:
                        st.error(
                            f"🛑 Unit price for item '{line_item_data_submit['item_key']}' cannot be negative."
                        )
                        are_all_items_valid = False
                        break

                    po_items_to_submit.append(
                        {
                            "item_id": item_id_for_submit,
                            "quantity_ordered": qty_for_submit,
                            "unit_price": price_for_submit,
                        }
                    )

            if (
                not po_items_to_submit and are_all_items_valid
            ):  # If loop completed but list is empty (e.g. only placeholder items)
                st.error(
                    "🛑 No valid items to submit. Please add items to the Purchase Order."
                )
                are_all_items_valid = False

            # If all data is valid, proceed with service call
            if are_all_items_valid:
                current_user_id_for_submit = st.session_state.form_user_id_val.strip()

                if (
                    is_edit_mode and st.session_state.po_to_edit_id is not None
                ):  # Ensure po_to_edit_id is valid
                    success_update, msg_update = (
                        purchase_order_service.update_po_details(
                            db_engine,
                            st.session_state.po_to_edit_id,
                            po_header_data_for_submit,
                            po_items_to_submit,
                            current_user_id_for_submit,
                        )
                    )
                    if success_update:
                        st.success(f"✅ {msg_update}")
                        change_view_mode("list_po", clear_po_form_state=True)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to update PO: {msg_update}")
                else:  # Create mode
                    po_header_data_for_submit["created_by_user_id"] = (
                        current_user_id_for_submit
                    )
                    po_header_data_for_submit["status"] = (
                        PO_STATUS_DRAFT  # Default status for new PO
                    )

                    success_create, msg_create, new_po_id_create = (
                        purchase_order_service.create_po(
                            db_engine, po_header_data_for_submit, po_items_to_submit
                        )
                    )
                    if success_create:
                        st.success(f"✅ {msg_create} (ID: {new_po_id_create})")
                        change_view_mode("list_po", clear_po_form_state=True)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to create PO: {msg_create}")

# --- CREATE GRN VIEW ---
elif st.session_state.po_grn_view_mode == "create_grn_for_po":
    active_grn_po_details_data_ui = st.session_state.get(
        "po_for_grn_details"
    )  # Use .get for safety

    st.subheader(
        f"📥 Record GRN for PO: {active_grn_po_details_data_ui.get('po_number', 'N/A') if active_grn_po_details_data_ui else 'N/A'}"
    )

    if st.button("⬅️ Back to PO List", key="back_grn_to_po_list_v2"):
        change_view_mode("list_po", clear_grn_state=True)
        st.rerun()

    if not active_grn_po_details_data_ui or not st.session_state.grn_line_items:
        st.warning(
            "⚠️ PO details not fully loaded or no items to receive. Attempting to reload or please go back to the PO list."
        )
        if (
            st.session_state.po_for_grn_id
        ):  # If po_id is known, try to re-trigger data load
            change_view_mode(
                "create_grn_for_po",
                po_id=st.session_state.po_for_grn_id,
                clear_grn_state=False,
            )
            st.rerun()
        else:  # No po_id, cannot reload, send back to list
            change_view_mode("list_po")
            st.rerun()
        st.stop()  # Stop further rendering if data is missing

    # Display PO Header info for GRN
    order_date_grn_disp = (
        pd.to_datetime(active_grn_po_details_data_ui["order_date"]).strftime("%Y-%m-%d")
        if pd.notna(active_grn_po_details_data_ui.get("order_date"))
        else "N/A"
    )
    exp_delivery_grn_disp = (
        pd.to_datetime(
            active_grn_po_details_data_ui["expected_delivery_date"]
        ).strftime("%Y-%m-%d")
        if pd.notna(active_grn_po_details_data_ui.get("expected_delivery_date"))
        else "N/A"
    )
    st.markdown(
        f"**Supplier:** {active_grn_po_details_data_ui.get('supplier_name', 'N/A')} | **Order Date:** {order_date_grn_disp}"
    )
    st.markdown(f"**Expected Delivery:** {exp_delivery_grn_disp}")
    st.divider()

    # GRN Form
    with st.form("create_grn_form_v2_page6"):  # Unique form key
        st.markdown("##### 📋 GRN Header")
        grn_header_cols_ui = st.columns(2)
        with grn_header_cols_ui[0]:
            st.session_state.grn_received_date_val = st.date_input(
                "Received Date*",
                value=st.session_state.grn_received_date_val,
                key="grn_recv_date_v2",
                help="Date when the goods were actually received.",
            )
        with grn_header_cols_ui[1]:
            st.session_state.grn_received_by_val = st.text_input(
                "Received By (Your Name/ID)*",
                value=st.session_state.grn_received_by_val,
                key="grn_recv_by_v2",
                help="Person who recorded this goods receipt.",
            )
        st.session_state.grn_header_notes_val = st.text_area(
            "GRN Notes",
            value=st.session_state.grn_header_notes_val,
            key="grn_notes_header_v2",
            placeholder="e.g., Invoice #, delivery condition...",
            help="Optional notes for this Goods Received Note.",
        )
        st.divider()

        st.markdown("##### 📦 Items Received")
        # Column headers for GRN items list
        grn_item_headers_ui = st.columns([2.5, 0.8, 1, 1, 1.2, 1.8])  # Adjusted ratios
        grn_item_headers_ui[0].markdown("**Item (Unit)**")
        grn_item_headers_ui[1].markdown("**Ordered**")
        grn_item_headers_ui[2].markdown("**Prev. Rcvd**")
        grn_item_headers_ui[3].markdown("**Pending**")
        grn_item_headers_ui[4].markdown("**Qty Rcv Now***")
        grn_item_headers_ui[5].markdown("**Unit Price Rcvd***")

        # Iterate through items prepared for GRN (from PO)
        for i_grn_line, line_item_grn_ui in enumerate(st.session_state.grn_line_items):
            item_cols_grn_ui = st.columns([2.5, 0.8, 1, 1, 1.2, 1.8])  # Matched ratios
            # Construct a unique key prefix for widgets in this line
            key_prefix_grn_line = f"grn_line_v2_{line_item_grn_ui.get('po_item_id', line_item_grn_ui.get('item_id', i_grn_line))}"

            item_cols_grn_ui[0].write(
                f"{line_item_grn_ui.get('item_name','N/A')} ({line_item_grn_ui.get('item_unit','N/A')})"
            )
            item_cols_grn_ui[1].write(
                f"{line_item_grn_ui.get('quantity_ordered_on_po',0.0):.2f}"
            )
            item_cols_grn_ui[2].write(
                f"{line_item_grn_ui.get('total_previously_received',0.0):.2f}"
            )

            qty_pending_grn_line = float(
                line_item_grn_ui.get("quantity_remaining_on_po", 0.0)
            )
            item_cols_grn_ui[3].write(f"{qty_pending_grn_line:.2f}")

            # Input for "Quantity Received Now"
            st.session_state.grn_line_items[i_grn_line][
                "quantity_received_now"
            ] = item_cols_grn_ui[4].number_input(
                f"QtyRcvNow_{key_prefix_grn_line}",
                value=float(
                    line_item_grn_ui.get("quantity_received_now", 0.0)
                ),  # Default to 0 or previous entry
                min_value=0.0,
                max_value=qty_pending_grn_line,  # Max is pending qty
                step=0.01,
                format="%.2f",
                key=f"{key_prefix_grn_line}_qty_v2",
                label_visibility="collapsed",
                help=f"Max quantity you can receive for this item is {qty_pending_grn_line:.2f}",
            )
            # Input for "Unit Price at Receipt"
            st.session_state.grn_line_items[i_grn_line][
                "unit_price_at_receipt"
            ] = item_cols_grn_ui[5].number_input(
                f"PriceRcv_{key_prefix_grn_line}",
                value=float(
                    line_item_grn_ui.get("unit_price_at_receipt", 0.0)
                ),  # Defaults to PO price
                min_value=0.00,
                step=0.01,
                format="%.2f",
                key=f"{key_prefix_grn_line}_price_v2",
                label_visibility="collapsed",
                help="Actual unit price at the time of receipt.",
            )
            st.caption("")  # Small vertical spacer between item lines

        st.divider()
        submit_grn_button_ui = st.form_submit_button(
            "💾 Record Goods Received", type="primary", use_container_width=True
        )

        if submit_grn_button_ui:
            if not st.session_state.grn_received_by_val.strip():
                st.warning("⚠️ 'Received By (Your Name/ID)' is required.")
            else:
                # Prepare GRN header data for submission
                grn_header_to_submit = {  # Renamed var
                    "po_id": active_grn_po_details_data_ui.get(
                        "po_id"
                    ),  # Get from loaded PO details
                    "supplier_id": active_grn_po_details_data_ui.get("supplier_id"),
                    "received_date": st.session_state.grn_received_date_val,
                    "notes": st.session_state.grn_header_notes_val.strip() or None,
                    "received_by_user_id": st.session_state.grn_received_by_val.strip(),
                }

                grn_items_to_submit: List[Dict[str, Any]] = []  # Renamed var, type hint
                at_least_one_item_received_flag = False

                for (
                    line_data_grn_submit
                ) in st.session_state.grn_line_items:  # Renamed var
                    qty_rcv_now_submit = float(
                        line_data_grn_submit.get("quantity_received_now", 0.0)
                    )
                    max_allowed_for_item_submit = float(
                        line_data_grn_submit.get("quantity_remaining_on_po", 0.0)
                    )

                    # Validate quantity received now against pending quantity
                    if qty_rcv_now_submit > max_allowed_for_item_submit:
                        st.error(
                            f"🛑 For item {line_data_grn_submit['item_name']}, quantity received ({qty_rcv_now_submit:.2f}) "
                            f"cannot exceed pending quantity ({max_allowed_for_item_submit:.2f}). Please correct."
                        )
                        grn_items_to_submit = []  # Invalidate submission
                        at_least_one_item_received_flag = False  # Reset flag
                        break

                    if (
                        qty_rcv_now_submit > 0
                    ):  # Only include items with quantity received
                        at_least_one_item_received_flag = True
                        grn_items_to_submit.append(
                            {
                                "item_id": line_data_grn_submit["item_id"],
                                "po_item_id": line_data_grn_submit.get("po_item_id"),
                                "quantity_ordered_on_po": line_data_grn_submit.get(
                                    "quantity_ordered_on_po"
                                ),
                                "quantity_received": qty_rcv_now_submit,
                                "unit_price_at_receipt": float(
                                    line_data_grn_submit.get(
                                        "unit_price_at_receipt", 0.0
                                    )
                                ),
                                "item_notes": line_data_grn_submit.get(
                                    "item_notes_grn", ""
                                ).strip()
                                or None,  # Assuming item_notes_grn might be a key for specific item notes on GRN
                            }
                        )

                if (
                    not grn_items_to_submit and at_least_one_item_received_flag
                ):  # Should not happen if logic above is correct
                    pass  # Error caught by qty_rcv_now_submit > max_allowed
                elif not at_least_one_item_received_flag:
                    st.warning(
                        "⚠️ Please enter a quantity for at least one item to record the GRN."
                    )
                else:  # Proceed with GRN creation if items are valid
                    success_grn_create, msg_grn_create, new_grn_id_created = (
                        goods_receiving_service.create_grn(
                            db_engine, grn_header_to_submit, grn_items_to_submit
                        )
                    )
                    if success_grn_create:
                        st.success(
                            f"✅ {msg_grn_create} (GRN ID: {new_grn_id_created})"
                        )
                        change_view_mode(
                            "list_po", clear_grn_state=True, clear_po_form_state=True
                        )  # Full reset
                        purchase_order_service.list_pos.clear()  # Ensure PO list refreshes with updated statuses
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to create GRN: {msg_grn_create}")

# --- VIEW PO DETAILS VIEW ---
elif st.session_state.po_grn_view_mode == "view_po_details":
    st.subheader("📄 View Purchase Order Details")
    if st.button("⬅️ Back to PO List", key="back_to_po_list_from_view_v2_page6"):
        change_view_mode("list_po")
        st.rerun()

    po_id_to_view_ui = st.session_state.get("po_to_view_id")
    if not po_id_to_view_ui:
        st.warning("⚠️ No PO selected to view. Please go back to the list.")
        st.stop()

    po_details_data_view_ui = purchase_order_service.get_po_by_id(
        db_engine, po_id_to_view_ui
    )
    if not po_details_data_view_ui:
        st.error(
            f"❌ Could not load details for PO ID: {po_id_to_view_ui}. It might have been deleted."
        )
        st.stop()

    # Display PO Header
    st.markdown(f"**PO Number:** `{po_details_data_view_ui.get('po_number', 'N/A')}`")
    st.markdown(f"**Supplier:** {po_details_data_view_ui.get('supplier_name', 'N/A')}")

    header_cols_view_ui = st.columns(2)
    order_date_view_fmt = (
        pd.to_datetime(po_details_data_view_ui.get("order_date")).strftime("%Y-%m-%d")
        if pd.notna(po_details_data_view_ui.get("order_date"))
        else "N/A"
    )
    exp_del_view_fmt = (
        pd.to_datetime(po_details_data_view_ui.get("expected_delivery_date")).strftime(
            "%Y-%m-%d"
        )
        if pd.notna(po_details_data_view_ui.get("expected_delivery_date"))
        else "N/A"
    )
    created_at_view_fmt = (
        pd.to_datetime(po_details_data_view_ui.get("created_at")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        if pd.notna(po_details_data_view_ui.get("created_at"))
        else "N/A"
    )

    header_cols_view_ui[0].markdown(f"**Order Date:** {order_date_view_fmt}")
    header_cols_view_ui[0].markdown(f"**Expected Delivery:** {exp_del_view_fmt}")
    header_cols_view_ui[1].markdown(
        f"**Status:** {format_status_badge(po_details_data_view_ui.get('status', 'N/A'))}",
        unsafe_allow_html=True,
    )
    header_cols_view_ui[1].markdown(
        f"**Total Amount:** {po_details_data_view_ui.get('total_amount', 0.0):.2f}"
    )

    st.markdown(
        f"**Created By:** {po_details_data_view_ui.get('created_by_user_id', 'N/A')}"
    )
    st.markdown(f"**Created At:** {created_at_view_fmt}")

    if pd.notna(
        po_details_data_view_ui.get("updated_at")
    ) and po_details_data_view_ui.get("updated_at") != po_details_data_view_ui.get(
        "created_at"
    ):
        updated_at_view_fmt = pd.to_datetime(
            po_details_data_view_ui.get("updated_at")
        ).strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(f"**Last Updated At:** {updated_at_view_fmt}")

    if po_details_data_view_ui.get("notes"):
        with st.expander("View PO Notes"):
            st.markdown(po_details_data_view_ui["notes"])

    st.divider()
    st.markdown("##### Ordered Items")
    po_items_view_ui = po_details_data_view_ui.get("items", [])
    if po_items_view_ui:
        items_df_view_ui = pd.DataFrame(po_items_view_ui)
        st.dataframe(
            items_df_view_ui,
            column_config={  # Hide IDs, format numbers
                "po_item_id": None,
                "item_id": None,
                "item_name": st.column_config.TextColumn("Item Name"),
                "item_unit": st.column_config.TextColumn("Unit", width="small"),
                "quantity_ordered": st.column_config.NumberColumn(
                    "Ordered Qty", format="%.2f"
                ),
                "unit_price": st.column_config.NumberColumn(
                    "Unit Price", format="%.2f"
                ),
                "line_total": st.column_config.NumberColumn(
                    "Line Total", format="%.2f"
                ),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("ℹ️ No items found for this Purchase Order.")
    st.divider()

    # Action button: Submit PO (if Draft)
    if po_details_data_view_ui.get("status") == PO_STATUS_DRAFT:
        # Use a default or prompt for user_id if actual logged-in user not available
        user_id_for_submit_from_view = (
            st.session_state.get("form_user_id_val")
            or st.session_state.po_submitter_user_id
        )
        if st.button(
            "➡️ Submit PO to Supplier",
            key="submit_po_from_view_details_v2",
            type="primary",
        ):
            success_submit_view, msg_submit_view = (
                purchase_order_service.update_po_status(
                    db_engine,
                    po_id_to_view_ui,
                    PO_STATUS_ORDERED,
                    user_id_for_submit_from_view,
                )
            )
            if success_submit_view:
                st.success(
                    f"PO {po_details_data_view_ui.get('po_number')} status updated to 'Ordered'. {msg_submit_view}"
                )
                change_view_mode("list_po")  # Go back to list
                st.rerun()
            else:
                st.error(f"❌ Failed to submit PO: {msg_submit_view}")

# --- Display Recent GRNs at the bottom of PO list view ---
# This condition should be outside other elif blocks if it's always shown with list_po
if st.session_state.po_grn_view_mode == "list_po":
    st.divider()
    st.subheader("🧾 Recent Goods Received Notes")
    grn_list_df_display_ui = goods_receiving_service.list_grns(
        db_engine
    )  # No filters for this basic list yet
    if grn_list_df_display_ui.empty:
        st.info("ℹ️ No Goods Received Notes recorded yet.")
    else:
        st.dataframe(
            grn_list_df_display_ui,
            use_container_width=True,
            hide_index=True,
            column_config={  # Configure columns for better display
                "grn_id": None,
                "po_id": None,
                "supplier_id": None,  # Hide IDs
                "grn_number": st.column_config.TextColumn("GRN #"),
                "po_number": st.column_config.TextColumn("Related PO #"),
                "supplier_name": st.column_config.TextColumn("Supplier"),
                "received_date": st.column_config.DateColumn(
                    "Received On", format="YYYY-MM-DD"
                ),
                "received_by_user_id": st.column_config.TextColumn("Received By"),
                "notes": "GRN Notes",
                "created_at": st.column_config.DatetimeColumn(
                    "Recorded At", format="YYYY-MM-DD HH:mm"
                ),
            },
        )
