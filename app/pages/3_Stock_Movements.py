# app/pages/3_Stock_Movements.py
import os
import sys
import streamlit as st

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_CUR_DIR, os.pardir, os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from app.db.database_utils import connect_db
    from app.services import item_service
    from app.services import stock_service
    from app.auth.auth import get_current_user_id
    from app.core.constants import (
        TX_RECEIVING,
        TX_ADJUSTMENT,
        TX_WASTAGE,
        PLACEHOLDER_SELECT_ITEM,
    )
    from app.ui.theme import load_css, render_sidebar_logo
    from app.ui.navigation import render_sidebar_nav
    from app.ui import show_success, show_error
except ImportError as e:
    show_error(f"Import error in 3_Stock_Movements.py: {e}.")
    st.stop()
except Exception as e:
    show_error(f"An unexpected error occurred during import in 3_Stock_Movements.py: {e}")
    st.stop()

SECTIONS_PG3 = {
    "receive": "📥 Goods Received",
    "adjust": "📊 Stock Adjustment",
    "waste": "🗑️ Wastage/Spoilage",
}
SECTION_KEYS_PG3 = list(SECTIONS_PG3.keys())
SECTION_DISPLAY_NAMES_PG3 = list(SECTIONS_PG3.values())

placeholder_option_stock_select_pg3 = (PLACEHOLDER_SELECT_ITEM, -1)

if "pg3_active_stock_movement_section" not in st.session_state:
    st.session_state.pg3_active_stock_movement_section = SECTION_KEYS_PG3[0]

for section_key_pg3 in SECTION_KEYS_PG3:
    item_tuple_key_pg3 = f"pg3_{section_key_pg3}_item_tuple_val"
    selected_id_key_pg3 = f"pg3_{section_key_pg3}_selected_item_id"
    reset_signal_key_pg3 = f"pg3_{section_key_pg3}_reset_signal"
    qty_key_pg3 = f"pg3_{section_key_pg3}_qty_form_val"
    user_id_key_pg3 = f"pg3_{section_key_pg3}_user_id_form_val"
    notes_key_pg3 = f"pg3_{section_key_pg3}_notes_form_val"

    if item_tuple_key_pg3 not in st.session_state:
        st.session_state[item_tuple_key_pg3] = placeholder_option_stock_select_pg3
    if selected_id_key_pg3 not in st.session_state:
        st.session_state[selected_id_key_pg3] = None
    if reset_signal_key_pg3 not in st.session_state:
        st.session_state[reset_signal_key_pg3] = False

    # Initialize quantity based on section type if not already set
    if qty_key_pg3 not in st.session_state:
        st.session_state[qty_key_pg3] = 0.0 if section_key_pg3 == "adjust" else 0.01
        # Or 1.0 for receive/waste, but 0.01 matches min_value

    if user_id_key_pg3 not in st.session_state:
        st.session_state[user_id_key_pg3] = get_current_user_id()
    if notes_key_pg3 not in st.session_state:
        st.session_state[notes_key_pg3] = ""
    if (
        section_key_pg3 == "receive"
        and "pg3_receive_po_id_form_val" not in st.session_state
    ):
        st.session_state.pg3_receive_po_id_form_val = ""

load_css()
render_sidebar_logo()
render_sidebar_nav()

st.title("🚚 Stock Movements Log")
st.write(
    "Use this page to accurately record all changes to your inventory: goods received, adjustments, or wastage/spoilage."
)
st.divider()

db_engine = connect_db()
if not db_engine:
    show_error("❌ Database connection failed. Cannot proceed with stock movements.")
    st.stop()


@st.cache_data(ttl=60)
def fetch_active_items_for_stock_mv_page_pg3(_engine):
    items_df = item_service.get_all_items_with_stock(_engine, include_inactive=False)
    if not items_df.empty:
        return [
            (f"{r['name']} ({r['unit']})", r["item_id"])
            for _, r in items_df.sort_values("name").iterrows()
        ]
    return []


active_item_options_list_pg3 = fetch_active_items_for_stock_mv_page_pg3(db_engine)
item_options_with_placeholder_list_pg3 = [
    placeholder_option_stock_select_pg3
] + active_item_options_list_pg3


def update_selected_item_id_callback_pg3(tuple_key_arg_pg3, id_key_arg_pg3):
    selected_tuple_val_pg3 = st.session_state[tuple_key_arg_pg3]
    st.session_state[id_key_arg_pg3] = (
        selected_tuple_val_pg3[1]
        if selected_tuple_val_pg3 and selected_tuple_val_pg3[1] != -1
        else None
    )


def set_active_section_callback_pg3():
    selected_display_name_val_pg3 = st.session_state.stock_mv_radio_key_pg3_v11
    new_active_section_pg3 = SECTION_KEYS_PG3[0]
    for key_pg3, display_name_pg3 in SECTIONS_PG3.items():
        if display_name_pg3 == selected_display_name_val_pg3:
            new_active_section_pg3 = key_pg3
            break
    st.session_state.pg3_active_stock_movement_section = new_active_section_pg3
    st.session_state[f"pg3_{new_active_section_pg3}_reset_signal"] = True


st.radio(
    "Select Movement Type:",
    options=SECTION_DISPLAY_NAMES_PG3,
    index=SECTION_KEYS_PG3.index(st.session_state.pg3_active_stock_movement_section),
    key="stock_mv_radio_key_pg3_v11",
    on_change=set_active_section_callback_pg3,
    horizontal=True,
)
st.divider()

active_section_prefix_val_pg3 = st.session_state.pg3_active_stock_movement_section
current_item_tuple_key_pg3 = f"pg3_{active_section_prefix_val_pg3}_item_tuple_val"
current_selected_item_id_key_pg3 = (
    f"pg3_{active_section_prefix_val_pg3}_selected_item_id"
)
current_reset_signal_key_pg3 = f"pg3_{active_section_prefix_val_pg3}_reset_signal"
current_qty_ss_key_pg3 = f"pg3_{active_section_prefix_val_pg3}_qty_form_val"
current_user_id_ss_key_pg3 = f"pg3_{active_section_prefix_val_pg3}_user_id_form_val"
current_notes_ss_key_pg3 = f"pg3_{active_section_prefix_val_pg3}_notes_form_val"
current_po_id_ss_key_pg3 = "pg3_receive_po_id_form_val"

if st.session_state.get(current_reset_signal_key_pg3, False):
    st.session_state[current_item_tuple_key_pg3] = placeholder_option_stock_select_pg3
    st.session_state[current_selected_item_id_key_pg3] = None
    # MODIFIED RESET LOGIC FOR QUANTITY
    st.session_state[current_qty_ss_key_pg3] = (
        0.0 if active_section_prefix_val_pg3 == "adjust" else 0.01
    )
    st.session_state[current_user_id_ss_key_pg3] = ""
    st.session_state[current_notes_ss_key_pg3] = ""
    if active_section_prefix_val_pg3 == "receive":
        st.session_state[current_po_id_ss_key_pg3] = ""
    st.session_state[current_reset_signal_key_pg3] = False

st.subheader(SECTIONS_PG3[active_section_prefix_val_pg3])
if active_section_prefix_val_pg3 == "adjust":
    st.caption("Correct discrepancies or make other non-wastage adjustments.")
elif active_section_prefix_val_pg3 == "waste":
    st.caption("Record items damaged, expired, or otherwise unusable.")

item_col_main_pg3, _ = st.columns([2, 1])
with item_col_main_pg3:
    default_item_index_val_pg3 = 0
    current_selected_item_id_val_pg3 = st.session_state.get(
        current_selected_item_id_key_pg3
    )
    if current_selected_item_id_val_pg3 is not None:
        try:
            default_item_index_val_pg3 = [
                opt[1] for opt in item_options_with_placeholder_list_pg3
            ].index(current_selected_item_id_val_pg3)
        except ValueError:
            default_item_index_val_pg3 = 0
            st.session_state[current_selected_item_id_key_pg3] = None
            st.session_state[current_item_tuple_key_pg3] = (
                placeholder_option_stock_select_pg3
            )

    st.selectbox(
        "Item*",
        options=item_options_with_placeholder_list_pg3,
        format_func=lambda x_opt: x_opt[0],
        index=default_item_index_val_pg3,
        key=current_item_tuple_key_pg3,
        help=f"Select the item for {active_section_prefix_val_pg3}.",
        on_change=update_selected_item_id_callback_pg3,
        args=(current_item_tuple_key_pg3, current_selected_item_id_key_pg3),
    )

    selected_item_id_for_stock_disp_pg3 = st.session_state.get(
        current_selected_item_id_key_pg3
    )
    if (
        selected_item_id_for_stock_disp_pg3
        and selected_item_id_for_stock_disp_pg3 != -1
    ):
        item_details_stock_disp_pg3 = item_service.get_item_details(
            db_engine, selected_item_id_for_stock_disp_pg3
        )
        if item_details_stock_disp_pg3:
            st.caption(
                f"Current Stock: {item_details_stock_disp_pg3.get('current_stock', 0):.2f} {item_details_stock_disp_pg3.get('unit', '')}"
            )
        else:
            st.caption("Could not fetch current stock details for the selected item.")
st.divider()

form_key_main_pg3 = f"pg3_{active_section_prefix_val_pg3}_form_v13"  # Incremented key
with st.form(form_key_main_pg3, clear_on_submit=False):
    qty_form_col_main_pg3, user_form_col_main_pg3 = st.columns(2)

    with qty_form_col_main_pg3:
        qty_label_form_pg3 = "Quantity*"
        PRACTICAL_MAX_NEGATIVE_NUMBER_PG3 = -1.7976931348623157e308
        min_widget_val_form_pg3 = 0.01
        help_text_qty_form_pg3 = "Enter the quantity for this movement."

        if active_section_prefix_val_pg3 == "receive":
            qty_label_form_pg3 = "Quantity Received*"
            help_text_qty_form_pg3 = "Quantity of goods received."
        elif active_section_prefix_val_pg3 == "adjust":
            qty_label_form_pg3 = "Quantity Adjusted*"
            min_widget_val_form_pg3 = PRACTICAL_MAX_NEGATIVE_NUMBER_PG3
            help_text_qty_form_pg3 = (
                "Positive value for stock increase, negative value for decrease."
            )
        elif active_section_prefix_val_pg3 == "waste":
            qty_label_form_pg3 = "Quantity Wasted*"
            help_text_qty_form_pg3 = (
                "Quantity of items wasted (will be deducted from stock)."
            )

        # MODIFIED: Default initial_qty_value for number_input
        default_qty_for_section = (
            0.0
            if active_section_prefix_val_pg3 == "adjust"
            else min_widget_val_form_pg3
        )  # Default to min_value for receive/waste
        initial_qty_value_form_pg3 = float(
            st.session_state.get(current_qty_ss_key_pg3, default_qty_for_section)
        )
        # Ensure initial value is not below min_value if session state had an invalid value (e.g. 0 for receive/waste)
        if (
            active_section_prefix_val_pg3 != "adjust"
            and initial_qty_value_form_pg3 < min_widget_val_form_pg3
        ):
            initial_qty_value_form_pg3 = min_widget_val_form_pg3

        st.session_state[current_qty_ss_key_pg3] = st.number_input(
            qty_label_form_pg3,
            min_value=min_widget_val_form_pg3,
            step=0.01,
            format="%.2f",
            key=f"widget_pg3_{active_section_prefix_val_pg3}_qty_v4",  # Incremented key
            value=initial_qty_value_form_pg3,
            help=help_text_qty_form_pg3,
        )

    with user_form_col_main_pg3:
        user_label_form_pg3 = (
            "Recorder"
            if active_section_prefix_val_pg3 != "receive"
            else "Receiver"
        )
        st.session_state[current_user_id_ss_key_pg3] = get_current_user_id()
        st.text_input(
            f"{user_label_form_pg3} ID",
            value=st.session_state[current_user_id_ss_key_pg3],
            disabled=True,
            key=f"widget_pg3_{active_section_prefix_val_pg3}_user_id_v4",
        )

    if active_section_prefix_val_pg3 == "receive":
        st.session_state[current_po_id_ss_key_pg3] = st.text_input(
            "Related PO ID (Optional, numeric part only)",
            key="widget_pg3_receive_po_id_v4",
            placeholder="e.g., 10023 (enter only the number part of PO-xxxx)",
            value=st.session_state.get(current_po_id_ss_key_pg3, ""),
            help="Numeric PO ID if this receipt is against a Purchase Order (e.g., for PO-0045, enter 45).",
        )

    notes_label_form_pg3 = (
        "Reason/Notes*"
        if active_section_prefix_val_pg3 in ["adjust", "waste"]
        else "Notes / Remarks (Optional)"
    )
    notes_placeholder_form_pg3 = (
        "Crucial: Explain reason for adjustment/wastage..."
        if active_section_prefix_val_pg3 in ["adjust", "waste"]
        else "e.g., Supplier name, Invoice #, Batch #..."
    )

    st.session_state[current_notes_ss_key_pg3] = st.text_area(
        notes_label_form_pg3,
        key=f"widget_pg3_{active_section_prefix_val_pg3}_notes_v4",
        placeholder=notes_placeholder_form_pg3,
        value=st.session_state.get(current_notes_ss_key_pg3, ""),
        help="Provide details or reasons for this stock movement. Mandatory for Adjustments and Wastage.",
    )

    submit_button_label_form_pg3 = SECTIONS_PG3[active_section_prefix_val_pg3]
    # This button should be correctly indented inside the 'with st.form(...):' block.
    submitted_form_pg3 = st.form_submit_button(submit_button_label_form_pg3)

    if submitted_form_pg3:
        selected_item_id_submit_pg3 = st.session_state.get(
            current_selected_item_id_key_pg3
        )
        qty_to_process_submit_pg3 = st.session_state.get(current_qty_ss_key_pg3, 0.0)
        user_id_to_process_submit_pg3 = get_current_user_id()
        notes_to_process_submit_pg3 = st.session_state.get(current_notes_ss_key_pg3, "")

        is_valid_submission_pg3 = True
        if not selected_item_id_submit_pg3 or selected_item_id_submit_pg3 == -1:
            st.warning("⚠️ Please select an item first.")
            is_valid_submission_pg3 = False

        try:
            qty_float_submit_pg3 = float(qty_to_process_submit_pg3)
            if active_section_prefix_val_pg3 == "adjust" and qty_float_submit_pg3 == 0:
                st.warning(
                    "⚠️ For 'Stock Adjustment', the quantity adjusted cannot be zero."
                )
                is_valid_submission_pg3 = False
            elif (
                active_section_prefix_val_pg3 != "adjust" and qty_float_submit_pg3 <= 0
            ):
                st.warning(
                    f"⚠️ Quantity for '{SECTIONS_PG3[active_section_prefix_val_pg3]}' must be greater than 0."
                )
                is_valid_submission_pg3 = False
        except (ValueError, TypeError):
            st.warning("⚠️ Invalid quantity entered. Please enter a valid number.")
            is_valid_submission_pg3 = False

        if (
            active_section_prefix_val_pg3 in ["adjust", "waste"]
            and not notes_to_process_submit_pg3.strip()
        ):
            st.warning(
                f"⚠️ A reason/note is mandatory for '{SECTIONS_PG3[active_section_prefix_val_pg3]}'."
            )
            is_valid_submission_pg3 = False

        related_po_id_val_submit_pg3 = None
        if (
            active_section_prefix_val_pg3 == "receive"
            and st.session_state.get(current_po_id_ss_key_pg3, "").strip()
        ):
            try:
                related_po_id_val_submit_pg3 = int(
                    st.session_state.get(current_po_id_ss_key_pg3).strip()
                )
            except ValueError:
                st.warning(
                    "⚠️ Related PO ID must be a numeric value if provided (enter only the number part)."
                )
                is_valid_submission_pg3 = False

        if is_valid_submission_pg3:
            transaction_type_to_submit_pg3 = ""
            quantity_change_val_for_db_pg3 = 0.0

            if active_section_prefix_val_pg3 == "receive":
                transaction_type_to_submit_pg3 = TX_RECEIVING
                quantity_change_val_for_db_pg3 = abs(float(qty_to_process_submit_pg3))
            elif active_section_prefix_val_pg3 == "adjust":
                transaction_type_to_submit_pg3 = TX_ADJUSTMENT
                quantity_change_val_for_db_pg3 = float(qty_to_process_submit_pg3)
            elif active_section_prefix_val_pg3 == "waste":
                transaction_type_to_submit_pg3 = TX_WASTAGE
                quantity_change_val_for_db_pg3 = -abs(float(qty_to_process_submit_pg3))

            success_stock_tx_pg3 = stock_service.record_stock_transaction(
                item_id=selected_item_id_submit_pg3,
                quantity_change=quantity_change_val_for_db_pg3,
                transaction_type=transaction_type_to_submit_pg3,
                user_id=user_id_to_process_submit_pg3.strip(),
                related_po_id=related_po_id_val_submit_pg3,
                notes=notes_to_process_submit_pg3.strip() or None,
                db_engine_param=db_engine,
            )
            if success_stock_tx_pg3:
                item_display_name_success_pg3_tuple = st.session_state.get(
                    current_item_tuple_key_pg3
                )
                item_display_name_success_pg3 = (
                    item_display_name_success_pg3_tuple[0]
                    if item_display_name_success_pg3_tuple
                    else "Selected Item"
                )
                show_success(
                    f"✅ Successfully recorded {active_section_prefix_val_pg3} for '{item_display_name_success_pg3}'."
                )
                st.page_link(
                    "pages/4_History_Reports.py",
                    label="View History Reports",
                    icon="➡️",
                )

                fetch_active_items_for_stock_mv_page_pg3.clear()

                # Reset fields for the current section for a new entry
                st.session_state[current_qty_ss_key_pg3] = (
                    0.0 if active_section_prefix_val_pg3 == "adjust" else 0.01
                )
                st.session_state[current_notes_ss_key_pg3] = ""
                # Optionally keep user_id, reset item selection, or PO ID
                # st.session_state[current_user_id_ss_key_pg3] = "" # If user should re-enter
                # st.session_state[current_item_tuple_key_pg3] = placeholder_option_stock_select_pg3
                # st.session_state[current_selected_item_id_key_pg3] = None
                if active_section_prefix_val_pg3 == "receive":
                    st.session_state[current_po_id_ss_key_pg3] = ""
                st.rerun()
            else:
                show_error(
                    f"❌ Failed to record stock {active_section_prefix_val_pg3}. Check console for specific database errors."
                )
