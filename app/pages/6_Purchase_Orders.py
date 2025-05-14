# app/pages/6_Purchase_Orders.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
from typing import Dict, Any, Optional

# --- Assuming your project structure for imports ---
try:
    from app.db.database_utils import connect_db
    from app.services import purchase_order_service
    from app.services import supplier_service
    from app.services import item_service
    from app.core.constants import (
        ALL_PO_STATUSES, PO_STATUS_DRAFT, PO_STATUS_ORDERED,
        PO_STATUS_FULLY_RECEIVED, PO_STATUS_PARTIALLY_RECEIVED, PO_STATUS_CANCELLED
    )
except ImportError as e:
    st.error(f"Import error in 6_Purchase_Orders.py: {e}. Please ensure all modules are correctly placed.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during an import in 6_Purchase_Orders.py: {e}")
    st.stop()

# --- Page Config and Title ---
st.title("🛒 Purchase Order Management")
st.write("Create, view, and manage Purchase Orders (POs) for your suppliers. Track procurement from order to receipt.")
st.divider()

# --- Database Connection ---
db_engine = connect_db()
if not db_engine:
    st.error("Database connection failed. Cannot manage Purchase Orders.")
    st.stop()

# --- Session State Initialization ---
if 'po_view_mode' not in st.session_state:
    st.session_state.po_view_mode = "list"
if 'po_to_edit_id' not in st.session_state:
    st.session_state.po_to_edit_id = None
if 'po_to_view_id' not in st.session_state:
    st.session_state.po_to_view_id = None

# For create form state
if 'create_po_form_reset_signal' not in st.session_state:
    st.session_state.create_po_form_reset_signal = True # Start with true to ensure fresh state on first load of create
if 'po_line_items' not in st.session_state:
    st.session_state.po_line_items = []
if 'po_next_line_id' not in st.session_state:
    st.session_state.po_next_line_id = 0

# For persisting form header values in create mode
default_supplier_key = "-- Select Supplier --"
if "create_po_supplier_name_form_val" not in st.session_state: st.session_state.create_po_supplier_name_form_val = default_supplier_key
if "create_po_order_date_form_val" not in st.session_state: st.session_state.create_po_order_date_form_val = date.today()
if "create_po_exp_delivery_date_form_val" not in st.session_state: st.session_state.create_po_exp_delivery_date_form_val = None
if "create_po_notes_form_val" not in st.session_state: st.session_state.create_po_notes_form_val = ""
if "create_po_user_id_form_val" not in st.session_state: st.session_state.create_po_user_id_form_val = ""


# --- Helper Functions ---
def change_view_mode(mode, po_id=None):
    st.session_state.po_view_mode = mode
    if mode == "edit" and po_id:
        st.session_state.po_to_edit_id = po_id
        st.session_state.po_to_view_id = None # Clear other mode IDs
    elif mode == "view_details" and po_id:
        st.session_state.po_to_view_id = po_id
        st.session_state.po_to_edit_id = None # Clear other mode IDs
    else:
        st.session_state.po_to_edit_id = None
        st.session_state.po_to_view_id = None
    
    if mode == "create":
        st.session_state.create_po_form_reset_signal = True # Signal to reset create form state
    elif st.session_state.po_view_mode != "create" : # Reset if navigating away from create
        st.session_state.create_po_form_reset_signal = True


# --- Main Page Logic ---

if st.session_state.po_view_mode == "list":
    st.subheader("📋 Existing Purchase Orders")

    filter_col1, filter_col2, filter_col3 = st.columns([2,2,1])
    with filter_col1:
        search_po_number = st.text_input("Search by PO Number:", key="po_search_po_number_v4", placeholder="e.g., PO-0001", help="Enter partial or full PO number to search.")
    with filter_col2:
        suppliers_df_for_filter_list = supplier_service.get_all_suppliers(db_engine, include_inactive=True)
        supplier_options_filter_list = {default_supplier_key: None} 
        if not suppliers_df_for_filter_list.empty:
            for _, row in suppliers_df_for_filter_list.iterrows():
                supplier_options_filter_list[f"{row['name']} {'(Inactive)' if not row['is_active'] else ''}"] = row['supplier_id']
        
        selected_supplier_name_filter_list = st.selectbox(
            "Filter by Supplier:",
            options=list(supplier_options_filter_list.keys()),
            key="po_filter_supplier_v4",
            help="Select a supplier to filter the PO list."
        )
        selected_supplier_id_filter_list = supplier_options_filter_list[selected_supplier_name_filter_list]

    with filter_col3:
        selected_status_filter_list = st.selectbox(
            "Filter by Status:",
            options=["All Statuses"] + ALL_PO_STATUSES,
            key="po_filter_status_v4",
            help="Select a PO status to filter the list."
        )

    if st.button("➕ Create New Purchase Order", key="nav_create_po_btn_v2", type="primary", use_container_width=True):
        change_view_mode("create")
        st.rerun()
    st.divider()

    query_filters = {}
    if search_po_number:
        query_filters["po_number_ilike"] = search_po_number
    if selected_supplier_id_filter_list:
        query_filters["supplier_id"] = selected_supplier_id_filter_list
    if selected_status_filter_list != "All Statuses":
        query_filters["status"] = selected_status_filter_list

    pos_df = purchase_order_service.list_pos(db_engine, filters=query_filters)

    if pos_df.empty:
        st.info("ℹ️ No Purchase Orders found matching your criteria.")
    else:
        st.write(f"Found {len(pos_df)} Purchase Order(s).")
        
        column_config_list = {
            "po_id": None, 
            "supplier_id": None,
            "created_by_user_id": None,
            "updated_at": None,
            "notes": None,
            "po_number": st.column_config.TextColumn("PO Number", width="medium", help="Unique Purchase Order identification number."),
            "supplier_name": st.column_config.TextColumn("Supplier", help="Name of the supplier."),
            "order_date": st.column_config.DateColumn("Order Date", format="YYYY-MM-DD", help="Date the PO was placed."),
            "expected_delivery_date": st.column_config.DateColumn("Expected Delivery", format="YYYY-MM-DD", help="Anticipated delivery date."),
            "status": st.column_config.TextColumn("Status", width="medium", help="Current status of the PO."),
            "total_amount": st.column_config.NumberColumn("Total Amount", format="%.2f", help="Total monetary value of the PO."),
            "created_at": st.column_config.DatetimeColumn("Created At", format="YYYY-MM-DD HH:mm", help="Timestamp of PO creation."),
        }
        
        st.dataframe(
            pos_df,
            use_container_width=True,
            hide_index=True,
            column_order=[
                "po_number", "supplier_name", "order_date", "expected_delivery_date",
                "status", "total_amount", "created_at"
            ],
            column_config=column_config_list
        )

elif st.session_state.po_view_mode == "create":
    st.subheader("🆕 Create New Purchase Order")
    
    if st.button("⬅️ Back to PO List", key="back_to_po_list_create_v5"):
        change_view_mode("list")
        st.rerun() 

    # --- Data Fetching for Dropdowns ---
    suppliers_df_create_form = supplier_service.get_all_suppliers(db_engine, include_inactive=False)
    supplier_dict_create_form = {default_supplier_key: None} 
    if not suppliers_df_create_form.empty:
        supplier_dict_create_form.update({row['name']: row['supplier_id'] for _, row in suppliers_df_create_form.iterrows()})
    
    items_df_create_form = item_service.get_all_items_with_stock(db_engine, include_inactive=False)
    item_dict_create_form = {"-- Select Item --": (None, None)} 
    if not items_df_create_form.empty:
        for _, row in items_df_create_form.iterrows():
            item_dict_create_form[f"{row['name']} ({row['unit']})"] = (row['item_id'], row['unit'])

    # --- Initialize or Reset Line Items if signal is set ---
    if st.session_state.create_po_form_reset_signal:
        st.session_state.po_line_items = [{'id': 0, 'item_key': "-- Select Item --", 'quantity': 1.0, 'unit_price': 0.0, 'unit': ''}]
        st.session_state.po_next_line_id = 1
        # Reset persisted header form values as well
        st.session_state.create_po_supplier_name_form_val = default_supplier_key
        st.session_state.create_po_order_date_form_val = date.today()
        st.session_state.create_po_exp_delivery_date_form_val = None
        st.session_state.create_po_notes_form_val = ""
        st.session_state.create_po_user_id_form_val = ""
        st.session_state.create_po_form_reset_signal = False
    elif 'po_line_items' not in st.session_state or not st.session_state.po_line_items : # Ensure initialization if empty
            st.session_state.po_line_items = [{'id': 0, 'item_key': "-- Select Item --", 'quantity': 1.0, 'unit_price': 0.0, 'unit': ''}]
            st.session_state.po_next_line_id = 1
            
    # --- Functions to Modify Line Items ---
    def add_po_line_item_ss_create_page(): # Unique name
        new_id = st.session_state.po_next_line_id
        st.session_state.po_line_items.append({'id': new_id, 'item_key': "-- Select Item --", 'quantity': 1.0, 'unit_price': 0.0, 'unit': ''})
        st.session_state.po_next_line_id += 1

    def remove_po_line_item_ss_create_page(line_id_to_remove): # Unique name
        st.session_state.po_line_items = [line for line in st.session_state.po_line_items if line['id'] != line_id_to_remove]
        if not st.session_state.po_line_items:
            add_po_line_item_ss_create_page()

    # --- PO HEADER SECTION (Rendered first) ---
    st.markdown("##### 📋 PO Header Details")
    with st.form("create_po_form_v5_header_submit"): # Unique form key
        current_supplier_name_val = st.session_state.create_po_supplier_name_form_val
        if current_supplier_name_val not in supplier_dict_create_form: # Ensure current value is valid
            current_supplier_name_val = default_supplier_key
            st.session_state.create_po_supplier_name_form_val = default_supplier_key
        
        supplier_form_idx = list(supplier_dict_create_form.keys()).index(current_supplier_name_val)

        selected_supplier_widget_val = st.selectbox(
            "Select Supplier*",
            options=list(supplier_dict_create_form.keys()),
            index=supplier_form_idx,
            key="create_po_supplier_name_widget_v2", # Unique key
            help="Choose the supplier for this Purchase Order."
        )
        st.session_state.create_po_supplier_name_form_val = selected_supplier_widget_val
        selected_supplier_id_for_submit = supplier_dict_create_form[selected_supplier_widget_val]

        col_header1, col_header2 = st.columns(2)
        with col_header1:
            order_date_widget_val = st.date_input("Order Date*", value=st.session_state.create_po_order_date_form_val, key="create_po_order_date_widget_v2", help="Date the order is placed.")
            st.session_state.create_po_order_date_form_val = order_date_widget_val
        with col_header2:
            exp_delivery_date_widget_val = st.date_input("Expected Delivery Date", value=st.session_state.create_po_exp_delivery_date_form_val, key="create_po_exp_delivery_date_widget_v2", help="Optional: When do you expect delivery?")
            st.session_state.create_po_exp_delivery_date_form_val = exp_delivery_date_widget_val
        
        notes_widget_val = st.text_area("Overall PO Notes", value=st.session_state.create_po_notes_form_val, key="create_po_notes_widget_v2", placeholder="e.g., Payment terms, delivery instructions...", help="Optional notes for the entire PO.")
        st.session_state.create_po_notes_form_val = notes_widget_val
        user_id_widget_val = st.text_input("Your Name/ID*", value=st.session_state.create_po_user_id_form_val, key="create_po_user_id_widget_v2", placeholder="Enter your identifier", help="Identifier of the person creating this PO.")
        st.session_state.create_po_user_id_form_val = user_id_widget_val
        
        st.divider()
        # Final Submit Button for the entire PO
        submitted_final_po_btn_form = st.form_submit_button("💾 Create Purchase Order", type="primary", use_container_width=True)

    # --- PO LINE ITEMS SECTION (Rendered AFTER the Header form, but managed interactively) ---
    st.markdown("##### 🛍️ PO Line Items")
    line_header_cols_items = st.columns([4, 1, 1.5, 1, 0.5])
    line_header_cols_items[0].markdown("**Item**")
    line_header_cols_items[1].markdown("**Quantity**")
    line_header_cols_items[2].markdown("**Unit Price**")
    line_header_cols_items[3].markdown("**Unit**")
    line_header_cols_items[4].markdown("**Action**")

    current_render_lines_data_items = [] 
    for i, line_state_items in enumerate(st.session_state.po_line_items):
        cols_items = st.columns([4, 1, 1.5, 1, 0.5])
        line_id_items = line_state_items['id']
        
        current_item_key_items = line_state_items.get('item_key', "-- Select Item --")
        if current_item_key_items not in item_dict_create_form:
             current_item_key_items = "-- Select Item --"
        try:
            select_box_idx_items = list(item_dict_create_form.keys()).index(current_item_key_items)
        except ValueError:
            select_box_idx_items = 0

        selected_item_name_widget = cols_items[0].selectbox(
            "Item", options=list(item_dict_create_form.keys()),
            key=f"line_item_name_widget_{line_id_items}", 
            index=select_box_idx_items, label_visibility="collapsed"
        )
        _item_id_from_widget, unit_from_widget = item_dict_create_form[selected_item_name_widget]
        
        qty_widget = cols_items[1].number_input(
            "Qty", value=float(line_state_items.get('quantity',1.0)), min_value=0.01, step=0.1, format="%.2f",
            key=f"line_item_qty_widget_{line_id_items}", label_visibility="collapsed"
        )
        price_widget = cols_items[2].number_input(
            "Price", value=float(line_state_items.get('unit_price',0.0)), min_value=0.00, step=0.01, format="%.2f",
            key=f"line_item_price_widget_{line_id_items}", label_visibility="collapsed"
        )
        cols_items[3].text_input("Unit_display", value=(unit_from_widget or ''), key=f"line_display_unit_widget_{line_id_items}", disabled=True, label_visibility="collapsed")

        if len(st.session_state.po_line_items) > 1:
            if cols_items[4].button("➖", key=f"del_line_widget_btn_{line_id_items}", help="Remove this line"):
                remove_po_line_item_ss_create_page(line_id_items)
                st.rerun()
        else:
            cols_items[4].write("")
            
        current_render_lines_data_items.append({
            'id': line_id_items, 'item_key': selected_item_name_widget,
            'quantity': qty_widget, 'unit_price': price_widget,
            'unit': (unit_from_widget or '')
        })
    st.session_state.po_line_items = current_render_lines_data_items

    if st.button("➕ Add Item Line", on_click=add_po_line_item_ss_create_page, key="add_po_line_main_btn_v5", help="Add a new blank item line to the PO."):
        # Rerun happens automatically if on_click modifies state and a widget using it is re-rendered
        pass
    st.divider()

    # --- Submission Logic (triggered by the form's submit button) ---
    if submitted_final_po_btn_form: # Check if the form's submit button was pressed
        if not selected_supplier_id_for_submit: # Using value captured when form was defined
            st.warning("⚠️ Please select a supplier in the PO Header section.")
        elif not st.session_state.create_po_user_id_form_val.strip(): # Using session state value persisted from widget
            st.warning("⚠️ Please enter 'Your Name/ID' in the PO Header section.")
        else:
            po_header_data = {
                "supplier_id": selected_supplier_id_for_submit,
                "order_date": st.session_state.create_po_order_date_form_val,
                "expected_delivery_date": st.session_state.create_po_exp_delivery_date_form_val,
                "notes": st.session_state.create_po_notes_form_val,
                "created_by_user_id": st.session_state.create_po_user_id_form_val.strip(),
                "status": PO_STATUS_DRAFT 
            }
            
            valid_items_to_submit = []
            is_items_valid = True
            if not st.session_state.po_line_items or all(item_dict_create_form[line.get('item_key', "-- Select Item --")][0] is None for line in st.session_state.po_line_items):
                st.error("🛑 Please add at least one valid item to the Purchase Order using the 'Add Item Line' section.")
                is_items_valid = False

            if is_items_valid:
                for line_item_data_final_submit in st.session_state.po_line_items:
                    item_id_final_submit, _ = item_dict_create_form.get(line_item_data_final_submit['item_key'], (None,None))
                    if item_id_final_submit is None:
                        st.error(f"🛑 Item '{line_item_data_final_submit['item_key']}' is not valid or not selected. Please correct or remove the line.")
                        is_items_valid = False; break
                    try:
                        current_qty_final_submit = float(line_item_data_final_submit['quantity'])
                        current_price_final_submit = float(line_item_data_final_submit['unit_price'])
                    except (ValueError, TypeError):
                        st.error(f"🛑 Invalid quantity or price for item '{line_item_data_final_submit['item_key']}'.")
                        is_items_valid = False; break

                    if current_qty_final_submit <= 0:
                        st.error(f"🛑 Quantity for item '{line_item_data_final_submit['item_key']}' must be greater than 0.")
                        is_items_valid = False; break
                    valid_items_to_submit.append({
                        "item_id": item_id_final_submit,
                        "quantity_ordered": current_qty_final_submit,
                        "unit_price": current_price_final_submit
                    })
            
            if not valid_items_to_submit and is_items_valid: 
                 st.error("🛑 No valid items to submit. Ensure items are added and quantities are positive.")
                 is_items_valid = False

            if is_items_valid:
                success, message, new_po_id = purchase_order_service.create_po(
                    db_engine, po_header_data, valid_items_to_submit
                )
                if success:
                    st.success(f"✅ {message} (PO ID: {new_po_id})")
                    change_view_mode("list") # This will also trigger reset signal
                    st.rerun()
                else:
                    st.error(f"❌ Failed to create Purchase Order: {message}")

elif st.session_state.po_view_mode == "edit":
    st.subheader(f"✏️ Edit Purchase Order (ID: {st.session_state.po_to_edit_id})")
    if st.button("⬅️ Back to PO List", key="back_to_po_list_edit_v3"):
        change_view_mode("list")
        st.rerun()
    st.info("📝 Edit functionality for Purchase Orders is under development.")
    # TODO: Implement PO Edit Form 
    # Fetch PO details: purchase_order_service.get_po_by_id(db_engine, st.session_state.po_to_edit_id)
    # Pre-fill form (similar to create, but with existing data and likely disabled if not in DRAFT status)
    # On submit, call a new purchase_order_service.update_po_details() function

elif st.session_state.po_view_mode == "view_details":
    st.subheader(f"📄 View Purchase Order Details (ID: {st.session_state.po_to_view_id})")
    if st.button("⬅️ Back to PO List", key="back_to_po_list_view_v3"):
        change_view_mode("list")
        st.rerun()
    st.info("📄 View details functionality for Purchase Orders is under development.")
    # TODO: Implement PO View Details
    # Fetch PO details: purchase_order_service.get_po_by_id(db_engine, st.session_state.po_to_view_id)
    # Display header and items in a read-only format.
    # Add buttons for "Receive Goods" or "Cancel PO" depending on status and user role.