# app/pages/6_Purchase_Orders.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
from typing import Dict, Any, Optional, List

# --- Assuming your project structure for imports ---
try:
    from app.db.database_utils import connect_db
    from app.services import purchase_order_service
    from app.services import supplier_service
    from app.services import item_service
    from app.services import goods_receiving_service 
    from app.core.constants import (
        ALL_PO_STATUSES, PO_STATUS_DRAFT, PO_STATUS_ORDERED,
        PO_STATUS_PARTIALLY_RECEIVED, PO_STATUS_FULLY_RECEIVED, PO_STATUS_CANCELLED
    )
except ImportError as e:
    st.error(f"Import error in 6_Purchase_Orders.py: {e}. Please ensure all modules are correctly placed.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred during an import in 6_Purchase_Orders.py: {e}")
    st.stop()

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
if 'po_grn_view_mode' not in st.session_state: 
    st.session_state.po_grn_view_mode = "list_po"
if 'po_to_edit_id' not in st.session_state:
    st.session_state.po_to_edit_id = None
if 'po_to_view_id' not in st.session_state:
    st.session_state.po_to_view_id = None
if 'po_for_grn_id' not in st.session_state: 
    st.session_state.po_for_grn_id = None
if 'po_for_grn_details' not in st.session_state: 
    st.session_state.po_for_grn_details = None
if 'grn_line_items' not in st.session_state: 
    st.session_state.grn_line_items = []

if 'form_reset_signal' not in st.session_state: 
    st.session_state.form_reset_signal = True 
if 'form_po_line_items' not in st.session_state: 
    st.session_state.form_po_line_items = []
if 'form_po_next_line_id' not in st.session_state:
    st.session_state.form_po_next_line_id = 0

DEFAULT_SUPPLIER_KEY_PG6 = "-- Select Supplier --" 

if "form_supplier_name_val" not in st.session_state: st.session_state.form_supplier_name_val = DEFAULT_SUPPLIER_KEY_PG6
if "form_order_date_val" not in st.session_state: st.session_state.form_order_date_val = date.today()
if "form_exp_delivery_date_val" not in st.session_state: st.session_state.form_exp_delivery_date_val = None
if "form_notes_val" not in st.session_state: st.session_state.form_notes_val = ""
if "form_user_id_val" not in st.session_state: st.session_state.form_user_id_val = ""
if "current_po_status_for_edit" not in st.session_state: st.session_state.current_po_status_for_edit = None
if "loaded_po_for_edit_id" not in st.session_state: st.session_state.loaded_po_for_edit_id = None


if "po_submitter_user_id" not in st.session_state: st.session_state.po_submitter_user_id = "System"

if "grn_received_date_val" not in st.session_state: st.session_state.grn_received_date_val = date.today()
if "grn_received_by_val" not in st.session_state: st.session_state.grn_received_by_val = "" 
if "grn_header_notes_val" not in st.session_state: st.session_state.grn_header_notes_val = ""


def change_view_mode(mode, po_id=None, clear_grn_state=True, clear_po_form_state=True): 
    previous_mode = st.session_state.get('po_grn_view_mode', 'list_po')
    st.session_state.po_grn_view_mode = mode
    st.session_state.po_to_edit_id = po_id if mode == "edit_po" else None
    st.session_state.po_to_view_id = po_id if mode == "view_po_details" else None
    st.session_state.po_for_grn_id = po_id if mode == "create_grn_for_po" else None
    
    if mode == "create_grn_for_po" and po_id:
        po_details_for_grn_init_func = purchase_order_service.get_po_by_id(db_engine, po_id) 
        st.session_state.po_for_grn_details = po_details_for_grn_init_func 
        st.session_state.grn_line_items = [] 
        if po_details_for_grn_init_func and po_details_for_grn_init_func.get("items"):
            previously_received_df = goods_receiving_service.get_received_quantities_for_po(db_engine, po_id)
            for item in po_details_for_grn_init_func["items"]:
                po_item_id = item["po_item_id"]; ordered_qty = float(item["quantity_ordered"])
                already_received_series = previously_received_df[previously_received_df['po_item_id'] == po_item_id]['total_previously_received']
                already_received_qty = float(already_received_series.iloc[0]) if not already_received_series.empty else 0.0
                remaining_to_receive = max(0.0, ordered_qty - already_received_qty)
                st.session_state.grn_line_items.append({
                    "po_item_id": po_item_id, "item_id": item["item_id"], "item_name": item["item_name"], "item_unit": item["item_unit"],
                    "quantity_ordered_on_po": ordered_qty, "total_previously_received": already_received_qty, 
                    "quantity_remaining_on_po": remaining_to_receive, "quantity_received_now": 0.0, 
                    "unit_price_at_receipt": float(item["unit_price"]) 
                })
    elif clear_grn_state and mode != "create_grn_for_po": 
        st.session_state.po_for_grn_id = None; st.session_state.po_for_grn_details = None
        st.session_state.grn_line_items = []; st.session_state.grn_received_date_val = date.today()
        st.session_state.grn_received_by_val = ""; st.session_state.grn_header_notes_val = ""

    if mode in ["create_po", "edit_po"]:
        if previous_mode not in ["create_po", "edit_po"] or \
           (mode == "edit_po" and (previous_mode != "edit_po" or st.session_state.po_to_edit_id != st.session_state.get('loaded_po_for_edit_id'))) or \
           (mode == "create_po" and previous_mode != "create_po"): 
             st.session_state.form_reset_signal = True
    elif previous_mode in ["create_po", "edit_po"] and mode not in ["create_po", "edit_po"] and clear_po_form_state: 
        st.session_state.form_reset_signal = True

# --- Main Page Logic ---
if st.session_state.po_grn_view_mode == "list_po":
    st.subheader("📋 Existing Purchase Orders")
    filter_col1_list_view, filter_col2_list_view, filter_col3_list_view = st.columns([2,2,1]) 
    with filter_col1_list_view:
        search_po_list_val_widget = st.text_input("Search PO #:", key="po_search_ui_v15_final", placeholder="e.g., PO-0001", help="Partial/full PO number.") 
    with filter_col2_list_view:
        suppliers_df_list_widget = supplier_service.get_all_suppliers(db_engine, True)
        supplier_options_list_widget = {DEFAULT_SUPPLIER_KEY_PG6: None, **{f"{r['name']} {'(Inactive)' if not r['is_active'] else ''}": r['supplier_id'] for _, r in suppliers_df_list_widget.iterrows()}}
        sel_supp_name_list_widget = st.selectbox(
            "Filter by Supplier:", options=list(supplier_options_list_widget.keys()), 
            key="po_filter_supp_ui_v15_final", help="Filter by supplier." 
        )
        sel_supp_id_list_widget = supplier_options_list_widget[sel_supp_name_list_widget]
    with filter_col3_list_view:
        sel_status_list_widget = st.selectbox(
            "Filter by Status:", options=["All Statuses"] + ALL_PO_STATUSES, 
            key="po_filter_stat_ui_v15_final", help="Filter by PO status."
        )

    if st.button("➕ Create New Purchase Order", key="nav_create_po_btn_v15_final", type="primary", use_container_width=True): 
        change_view_mode("create_po", clear_po_form_state=True); st.rerun() 
    st.divider()

    q_filters_list_ui = {} 
    if search_po_list_val_widget: q_filters_list_ui["po_number_ilike"] = search_po_list_val_widget
    if sel_supp_id_list_widget: q_filters_list_ui["supplier_id"] = sel_supp_id_list_widget
    if sel_status_list_widget != "All Statuses": q_filters_list_ui["status"] = sel_status_list_widget
    pos_df_list_widget = purchase_order_service.list_pos(db_engine, filters=q_filters_list_ui) 

    if pos_df_list_widget.empty: st.info("ℹ️ No Purchase Orders found matching criteria.")
    else:
        st.write(f"Found {len(pos_df_list_widget)} PO(s).")
        for _, row_list_widget in pos_df_list_widget.iterrows(): 
            status_list_widget_item = row_list_widget['status'] 
            st.markdown(f"**PO #: {row_list_widget['po_number']}** | {row_list_widget['supplier_name']} | Status: _{status_list_widget_item}_")
            disp_cols_list_widget_item = st.columns([1.5, 1.5, 1, 1, 2.5]) 
            disp_cols_list_widget_item[0].markdown(f"<small>Order: {pd.to_datetime(row_list_widget['order_date']).strftime('%d-%b-%y')}</small>", unsafe_allow_html=True)
            disp_cols_list_widget_item[1].markdown(f"<small>Expected: {pd.to_datetime(row_list_widget['expected_delivery_date']).strftime('%d-%b-%y') if pd.notna(row_list_widget['expected_delivery_date']) else 'N/A'}</small>", unsafe_allow_html=True)
            disp_cols_list_widget_item[2].markdown(f"<small>Total: {row_list_widget['total_amount']:.2f}</small>", unsafe_allow_html=True)
            with disp_cols_list_widget_item[3]:
                 if st.button("👁️ View", key=f"view_po_btn_list_corrected_v8_{row_list_widget['po_id']}", help="View PO Details", use_container_width=True):
                    change_view_mode("view_po_details", po_id=row_list_widget['po_id']); st.rerun()
            with disp_cols_list_widget_item[4]:
                action_buttons_cols_list_widget = st.columns([1,1]) 
                submitter_id_list_widget = st.session_state.get("form_user_id_val") or st.session_state.get("po_submitter_user_id", "SystemActionPO")
                if status_list_widget_item == PO_STATUS_DRAFT:
                    if action_buttons_cols_list_widget[0].button("✏️ Edit", key=f"edit_po_btn_list_corrected_v7_{row_list_widget['po_id']}", help="Edit this Draft PO", use_container_width=True):
                        change_view_mode("edit_po", po_id=row_list_widget['po_id'], clear_po_form_state=False); st.rerun()
                else: action_buttons_cols_list_widget[0].write("")
                if status_list_widget_item in [PO_STATUS_ORDERED, PO_STATUS_PARTIALLY_RECEIVED]:
                    if action_buttons_cols_list_widget[1].button("📥 Receive", key=f"receive_po_btn_list_corrected_v8_{row_list_widget['po_id']}", help="Record goods receipt for this PO.", type="primary", use_container_width=True): 
                        change_view_mode("create_grn_for_po", po_id=row_list_widget['po_id'], clear_grn_state=False); st.rerun()
                else: action_buttons_cols_list_widget[1].write("")
            st.divider()

elif st.session_state.po_grn_view_mode in ["create_po", "edit_po"]:
    is_edit_mode = st.session_state.po_grn_view_mode == "edit_po"
    form_title = "✏️ Edit Purchase Order" if is_edit_mode else "🆕 Create New Purchase Order"
    st.subheader(form_title)

    # --- Data Fetching for Dropdowns ---
    supp_df_form_ui = supplier_service.get_all_suppliers(db_engine, include_inactive=is_edit_mode) 
    supp_dict_form_ui = {DEFAULT_SUPPLIER_KEY_PG6: None, 
                         **{f"{r['name'].strip()} {'(Inactive)' if not r['is_active'] else ''}": r['supplier_id'] 
                            for _,r in supp_df_form_ui.iterrows() if r['name']}} # Ensure name is not None
    item_df_form_ui = item_service.get_all_items_with_stock(db_engine, include_inactive=is_edit_mode) 
    item_dict_form_ui = {"-- Select Item --": (None,None), 
                         **{f"{r['name'].strip()} ({r['unit'].strip()}) {'[Inactive]' if not r['is_active'] else ''}": \
                            (r['item_id'],r['unit'].strip()) 
                            for _,r in item_df_form_ui.iterrows() if r['name'] and r['unit']}} # Ensure name and unit are not None

    if is_edit_mode:
        if not st.session_state.po_to_edit_id:
            st.error("❌ PO ID for editing is missing.")
            if st.button("⬅️ Back to PO List", key="back_edit_po_no_id_v8_corrected"): change_view_mode("list_po"); st.rerun()
            st.stop()
        
        if st.session_state.form_reset_signal or st.session_state.get('loaded_po_for_edit_id') != st.session_state.po_to_edit_id:
            print(f"DEBUG: Loading/Re-loading PO {st.session_state.po_to_edit_id} for edit.") 
            po_data_to_edit = purchase_order_service.get_po_by_id(db_engine, st.session_state.po_to_edit_id)
            if not po_data_to_edit: st.error(f"❌ Could not load PO (ID: {st.session_state.po_to_edit_id})."); change_view_mode("list_po"); st.rerun(); st.stop()
            if po_data_to_edit.get('status') != PO_STATUS_DRAFT: 
                st.warning(f"⚠️ PO {po_data_to_edit.get('po_number')} ({po_data_to_edit.get('status')}) cannot be edited."); change_view_mode("list_po"); st.rerun(); st.stop()

            st.session_state.current_po_status_for_edit = po_data_to_edit.get('status')
            
            supp_name_for_edit_form = DEFAULT_SUPPLIER_KEY_PG6
            for name_key, supp_id_val_dict in supp_dict_form_ui.items(): # Iterate through the generated dict
                if supp_id_val_dict == po_data_to_edit.get('supplier_id'): 
                    supp_name_for_edit_form = name_key
                    break
            st.session_state.form_supplier_name_val = supp_name_for_edit_form
            
            st.session_state.form_order_date_val = pd.to_datetime(po_data_to_edit.get('order_date')).date() if pd.notna(po_data_to_edit.get('order_date')) else date.today()
            st.session_state.form_exp_delivery_date_val = pd.to_datetime(po_data_to_edit.get('expected_delivery_date')).date() if pd.notna(po_data_to_edit.get('expected_delivery_date')) else None
            st.session_state.form_notes_val = po_data_to_edit.get('notes', "")
            st.session_state.form_user_id_val = po_data_to_edit.get('created_by_user_id', st.session_state.get("po_submitter_user_id", ""))
            
            st.session_state.form_po_line_items = []
            st.session_state.form_po_next_line_id = 0
            
            for item_idx, item_data_db in enumerate(po_data_to_edit.get("items", [])):
                item_name_db = item_data_db['item_name'].strip() if item_data_db.get('item_name') else "Unknown Item"
                item_unit_db = item_data_db['item_unit'].strip() if item_data_db.get('item_unit') else "N/A"
                item_key_to_find = f"{item_name_db} ({item_unit_db})"
                
                db_item_details_for_status = item_df_form_ui[item_df_form_ui['item_id'] == item_data_db['item_id']]
                if not db_item_details_for_status.empty and not db_item_details_for_status.iloc[0]['is_active']:
                    item_key_to_find += " [Inactive]"
                
                print(f"DEBUG (Edit PO Pre-fill): Attempting to match item_key: '{item_key_to_find}'")
                if item_key_to_find not in item_dict_form_ui:
                    print(f"WARNING (Edit PO Pre-fill): Item key '{item_key_to_find}' for item_id {item_data_db['item_id']} not found in item_dict_form_ui. Using fallback or adding temp.")
                    # Fallback: if not found, use a placeholder or add a temporary entry to item_dict_form_ui if essential
                    # This indicates data inconsistency or item name/unit change post PO creation
                    # For now, we'll try to use it as is, selectbox might default if no exact match.
                    # A more robust solution might involve storing item_id and reconstructing the key based on current master data.
                    pass # Let selectbox default if key is not perfect

                st.session_state.form_po_line_items.append({
                    'id': item_idx, 
                    'item_key': item_key_to_find, 
                    'quantity': float(item_data_db['quantity_ordered']),
                    'unit_price': float(item_data_db['unit_price']),
                    'unit': item_unit_db # Store the stripped unit
                })
                st.session_state.form_po_next_line_id = item_idx + 1
            
            if not st.session_state.form_po_line_items : 
                 st.session_state.form_po_line_items = [{'id':0,'item_key':"-- Select Item --",'quantity':1.0,'unit_price':0.0,'unit':''}]
                 st.session_state.form_po_next_line_id = 1
            st.session_state.loaded_po_for_edit_id = st.session_state.po_to_edit_id
            st.session_state.form_reset_signal = False
    
    elif st.session_state.form_reset_signal: 
        st.session_state.form_po_line_items = [{'id':0,'item_key':"-- Select Item --",'quantity':1.0,'unit_price':0.0,'unit':''}]
        st.session_state.form_po_next_line_id = 1
        st.session_state.form_supplier_name_val = DEFAULT_SUPPLIER_KEY_PG6
        st.session_state.form_order_date_val = date.today()
        st.session_state.form_exp_delivery_date_val = None
        st.session_state.form_notes_val = ""; st.session_state.form_user_id_val = st.session_state.get("po_submitter_user_id", "")
        st.session_state.form_reset_signal = False
    elif not st.session_state.form_po_line_items: 
        st.session_state.form_po_line_items = [{'id':0,'item_key':"-- Select Item --",'quantity':1.0,'unit_price':0.0,'unit':''}]
        st.session_state.form_po_next_line_id = 1

    if st.button("⬅️ Back to PO List", key=f"back_form_po_corrected_v9_{is_edit_mode}"): change_view_mode("list_po", clear_po_form_state=True); st.rerun() 
            
    def add_po_line_ss_form_active_corrected(): 
        new_id = st.session_state.form_po_next_line_id
        st.session_state.form_po_line_items.append({'id':new_id,'item_key':"-- Select Item --",'quantity':1.0,'unit_price':0.0,'unit':''})
        st.session_state.form_po_next_line_id+=1

    def remove_po_line_ss_form_active_corrected(id_rem): 
        st.session_state.form_po_line_items=[l for l in st.session_state.form_po_line_items if l['id']!=id_rem]
        if not st.session_state.form_po_line_items: add_po_line_ss_form_active_corrected()

    st.markdown("##### 📋 PO Header Details")
    form_key_actual_corrected_v6 = "edit_po_form_v10_corrected" if is_edit_mode else "create_po_form_v10_corrected" 
    with st.form(form_key_actual_corrected_v6): 
        current_supplier_form_val_widget_corrected_v6 = st.session_state.form_supplier_name_val
        if current_supplier_form_val_widget_corrected_v6 not in supp_dict_form_ui: current_supplier_form_val_widget_corrected_v6 = DEFAULT_SUPPLIER_KEY_PG6
        supplier_idx_form_ui_val_widget_corrected_v6 = list(supp_dict_form_ui.keys()).index(current_supplier_form_val_widget_corrected_v6)
        sel_supp_widget_form_ui_val_corrected_v6 = st.selectbox("Supplier*", options=list(supp_dict_form_ui.keys()), index=supplier_idx_form_ui_val_widget_corrected_v6, key="form_supp_widget_v10_corrected", help="Choose supplier.") 
        st.session_state.form_supplier_name_val = sel_supp_widget_form_ui_val_corrected_v6
        sel_supp_id_submit_form_ui_val_corrected_v6 = supp_dict_form_ui[sel_supp_widget_form_ui_val_corrected_v6] 
        
        hcols1_form_ui_val_corrected_v6, hcols2_form_ui_val_corrected_v6 = st.columns(2)
        with hcols1_form_ui_val_corrected_v6: st.session_state.form_order_date_val = hcols1_form_ui_val_corrected_v6.date_input("Order Date*", value=st.session_state.form_order_date_val, key="form_order_date_widget_v10_corrected", help="Order placement date.") 
        with hcols2_form_ui_val_corrected_v6: st.session_state.form_exp_delivery_date_val = hcols2_form_ui_val_corrected_v6.date_input("Expected Delivery", value=st.session_state.form_exp_delivery_date_val, key="form_exp_del_widget_v10_corrected", help="Optional: Expected arrival.") 
        st.session_state.form_notes_val = st.text_area("PO Notes", value=st.session_state.form_notes_val, key="form_notes_widget_v10_corrected", placeholder="e.g., Payment terms...", help="Optional notes for PO.") 
        st.session_state.form_user_id_val = st.text_input("Your Name/ID*", value=st.session_state.form_user_id_val, key="form_user_id_widget_v10_corrected", placeholder="Creator's/Editor's identifier", help="Your identifier.") 
        if is_edit_mode and st.session_state.current_po_status_for_edit == PO_STATUS_DRAFT:
            if st.form_submit_button("➡️ Submit PO to Supplier", use_container_width=True, help="Finalize and submit this draft PO."):
                user_id_for_status_update_form_val_v5 = st.session_state.form_user_id_val.strip() or st.session_state.po_submitter_user_id 
                s_stat_form_val_v5, m_stat_form_val_v5 = purchase_order_service.update_po_status(db_engine, st.session_state.po_to_edit_id, PO_STATUS_ORDERED, user_id_for_status_update_form_val_v5) 
                if s_stat_form_val_v5: st.success(f"PO status updated to '{PO_STATUS_ORDERED}'. {m_stat_form_val_v5}"); change_view_mode("list_po", clear_po_form_state=True); st.rerun()
                else: st.error(f"❌ Failed to submit PO: {m_stat_form_val_v5}")
        st.divider()
        form_submit_label_final_ui_corrected_v6 = "💾 Update Purchase Order" if is_edit_mode else "💾 Create Purchase Order"
        submit_btn_po_form_final_ui_corrected_v6 = st.form_submit_button(form_submit_label_final_ui_corrected_v6, type="primary", use_container_width=True)

    st.markdown("##### 🛍️ PO Line Items")
    l_hcols_form_final_ui_v6 = st.columns([4,1,1.5,1,0.5]); l_hcols_form_final_ui_v6[0].markdown("**Item**"); l_hcols_form_final_ui_v6[1].markdown("**Qty**"); l_hcols_form_final_ui_v6[2].markdown("**Price**"); l_hcols_form_final_ui_v6[3].markdown("**Unit**"); l_hcols_form_final_ui_v6[4].markdown("**Act**")
    current_lines_render_form_final_ui_v6 = [] 
    for i,l_state_form_final_ui_v6 in enumerate(st.session_state.form_po_line_items):
        l_cols_form_final_ui_v6 = st.columns([4,1,1.5,1,0.5]); l_id_form_final_ui_v6 = l_state_form_final_ui_v6['id']
        curr_item_key_form_final_ui_v6 = l_state_form_final_ui_v6.get('item_key',"-- Select Item --")
        if curr_item_key_form_final_ui_v6 not in item_dict_form_ui: curr_item_key_form_final_ui_v6="-- Select Item --"; st.session_state.form_po_line_items[i]['item_key'] = curr_item_key_form_final_ui_v6
        try: item_idx_form_final_ui_v6 = list(item_dict_form_ui.keys()).index(curr_item_key_form_final_ui_v6)
        except ValueError: item_idx_form_final_ui_v6 = 0; print(f"ERROR: Index not found for item key '{curr_item_key_form_final_ui_v6}'")
        sel_item_name_widget_form_final_ui_v6 = l_cols_form_final_ui_v6[0].selectbox(f"Item_line_{l_id_form_final_ui_v6}",options=list(item_dict_form_ui.keys()),key=f"form_line_item_name_corrected_v8_{l_id_form_final_ui_v6}",index=item_idx_form_final_ui_v6,label_visibility="collapsed") 
        _,unit_w_form_final_ui_v6 = item_dict_form_ui[sel_item_name_widget_form_final_ui_v6]
        qty_w_form_final_ui_v6 = l_cols_form_final_ui_v6[1].number_input(f"Qty_line_{l_id_form_final_ui_v6}",value=float(l_state_form_final_ui_v6.get('quantity',1.0)),min_value=0.01,step=0.1,format="%.2f",key=f"form_line_qty_corrected_v8_{l_id_form_final_ui_v6}",label_visibility="collapsed") 
        price_w_form_final_ui_v6 = l_cols_form_final_ui_v6[2].number_input(f"Price_line_{l_id_form_final_ui_v6}",value=float(l_state_form_final_ui_v6.get('unit_price',0.0)),min_value=0.00,step=0.01,format="%.2f",key=f"form_line_price_corrected_v8_{l_id_form_final_ui_v6}",label_visibility="collapsed") 
        l_cols_form_final_ui_v6[3].text_input(f"Unit_line_{l_id_form_final_ui_v6}",value=(unit_w_form_final_ui_v6 or ''),key=f"form_line_unit_corrected_v8_{l_id_form_final_ui_v6}",disabled=True,label_visibility="collapsed") 
        if len(st.session_state.form_po_line_items)>1:
            if l_cols_form_final_ui_v6[4].button("➖",key=f"form_del_line_btn_corrected_v8_{l_id_form_final_ui_v6}",help="Remove line"): remove_po_line_ss_form_active_corrected(l_id_form_final_ui_v6); st.rerun() 
        else: l_cols_form_final_ui_v6[4].write("")
        current_lines_render_form_final_ui_v6.append({'id':l_id_form_final_ui_v6,'item_key':sel_item_name_widget_form_final_ui_v6,'quantity':qty_w_form_final_ui_v6,'unit_price':price_w_form_final_ui_v6,'unit':(unit_w_form_final_ui_v6 or '')})
    st.session_state.form_po_line_items = current_lines_render_form_final_ui_v6
    if st.button("➕ Add Item Line", on_click=add_po_line_ss_form_active_corrected, key="form_add_po_line_btn_v9_corrected", help="Add item line."): pass 
    st.divider()

    if submit_btn_po_form_final_ui_corrected_v6: 
        if not sel_supp_id_submit_form_ui_val_corrected_v6: st.warning("⚠️ Supplier required.") 
        elif not st.session_state.form_user_id_val.strip(): st.warning("⚠️ Your Name/ID required.")
        else:
            header_data_submit_final_form_ui_corrected_v6 = {"supplier_id":sel_supp_id_submit_form_ui_val_corrected_v6, "order_date":st.session_state.form_order_date_val, 
                           "expected_delivery_date":st.session_state.form_exp_delivery_date_val, "notes":st.session_state.form_notes_val}
            items_to_submit_final_form_ui_corrected_v6, valid_items_final_form_ui_corrected_v6 = [], True 
            if not st.session_state.form_po_line_items or all(item_dict_form_ui[l.get('item_key',"-- Select Item --")][0] is None for l in st.session_state.form_po_line_items):
                st.error("🛑 Add at least one valid item."); valid_items_final_form_ui_corrected_v6=False
            if valid_items_final_form_ui_corrected_v6:
                for l_data_final_form_ui_corrected_v6 in st.session_state.form_po_line_items:
                    item_id_final_form_ui_corrected_v6, _ = item_dict_form_ui.get(l_data_final_form_ui_corrected_v6['item_key'],(None,None))
                    if item_id_final_form_ui_corrected_v6 is None: st.error(f"🛑 Item '{l_data_final_form_ui_corrected_v6['item_key']}' invalid."); valid_items_final_form_ui_corrected_v6=False; break
                    try: qty_final_form_ui_corrected_v6,price_final_form_ui_corrected_v6 = float(l_data_final_form_ui_corrected_v6['quantity']),float(l_data_final_form_ui_corrected_v6['unit_price'])
                    except(ValueError,TypeError): st.error(f"🛑 Invalid qty/price for '{l_data_final_form_ui_corrected_v6['item_key']}'."); valid_items_final_form_ui_corrected_v6=False; break
                    if qty_final_form_ui_corrected_v6<=0: st.error(f"🛑 Qty for '{l_data_final_form_ui_corrected_v6['item_key']}' > 0."); valid_items_final_form_ui_corrected_v6=False; break
                    items_to_submit_final_form_ui_corrected_v6.append({"item_id":item_id_final_form_ui_corrected_v6,"quantity_ordered":qty_final_form_ui_corrected_v6,"unit_price":price_final_form_ui_corrected_v6})
            if not items_to_submit_final_form_ui_corrected_v6 and valid_items_final_form_ui_corrected_v6: st.error("🛑 No valid items to submit."); valid_items_final_form_ui_corrected_v6=False
            if valid_items_final_form_ui_corrected_v6:
                current_user_id_submit_form_val_v6 = st.session_state.form_user_id_val.strip() 
                if is_edit_mode:
                    s_upd_final_form,m_upd_final_form = purchase_order_service.update_po_details(db_engine, st.session_state.po_to_edit_id, header_data_submit_final_form_ui_corrected_v6, items_to_submit_final_form_ui_corrected_v6, current_user_id_submit_form_val_v6)
                    if s_upd_final_form: st.success(f"✅ {m_upd_final_form}"); change_view_mode("list_po", clear_po_form_state=True); st.rerun()
                    else: st.error(f"❌ Failed to update PO: {m_upd_final_form}")
                else: 
                    header_data_submit_final_form_ui_corrected_v6["created_by_user_id"] = current_user_id_submit_form_val_v6
                    header_data_submit_final_form_ui_corrected_v6["status"] = PO_STATUS_DRAFT
                    s_create_final_form_ui,m_create_final_form_ui,new_id_create_final_form_ui = purchase_order_service.create_po(db_engine,header_data_submit_final_form_ui_corrected_v6,items_to_submit_final_form_ui_corrected_v6)
                    if s_create_final_form_ui: st.success(f"✅ {m_create_final_form_ui} (PO ID: {new_id_create_final_form_ui})"); change_view_mode("list_po", clear_po_form_state=True); st.rerun()
                    else: st.error(f"❌ Failed to create PO: {m_create_final_form_ui}")

elif st.session_state.po_grn_view_mode == "create_grn_for_po":
    # CORRECTED: Use a consistent variable for PO details in this block
    active_grn_po_details_data = st.session_state.po_for_grn_details 
    st.subheader(f"📥 Record GRN for PO: {active_grn_po_details_data.get('po_number', 'N/A') if active_grn_po_details_data else 'N/A'}")
    if st.button("⬅️ Back to PO List", key="back_grn_v15_corrected_final"): 
        change_view_mode("list_po", clear_grn_state=True); st.rerun()
    if not active_grn_po_details_data or not st.session_state.grn_line_items:
        st.warning("⚠️ PO details not loaded/no items. Reloading or go back.");
        if st.session_state.po_for_grn_id: change_view_mode("create_grn_for_po", po_id=st.session_state.po_for_grn_id, clear_grn_state=False); st.rerun()
        else: change_view_mode("list_po"); st.rerun()
        st.stop()
    st.markdown(f"**Supplier:** {active_grn_po_details_data['supplier_name']} | **Order Date:** {pd.to_datetime(active_grn_po_details_data['order_date']).strftime('%Y-%m-%d')}")
    st.markdown(f"**Expected Delivery:** {pd.to_datetime(active_grn_po_details_data['expected_delivery_date']).strftime('%Y-%m-%d') if pd.notna(active_grn_po_details_data['expected_delivery_date']) else 'N/A'}")
    st.divider()
    with st.form("create_grn_form_v15_final_corrected_submit"): 
        st.markdown("##### 📋 GRN Header")
        grn_hdr_cols_submit_final_v9_ui = st.columns(2) 
        with grn_hdr_cols_submit_final_v9_ui[0]: st.session_state.grn_received_date_val = st.date_input("Received Date*", value=st.session_state.grn_received_date_val, key="grn_recv_date_v15_corrected_final", help="Date goods received.") 
        with grn_hdr_cols_submit_final_v9_ui[1]: st.session_state.grn_received_by_val = st.text_input("Received By*", value=st.session_state.grn_received_by_val, key="grn_recv_by_v15_corrected_final", help="Person recording receipt.") 
        st.session_state.grn_header_notes_val = st.text_area("GRN Notes", value=st.session_state.grn_header_notes_val, key="grn_notes_hdr_v15_corrected_final", placeholder="e.g., Invoice #...", help="Optional GRN notes.") 
        st.divider(); st.markdown("##### 📦 Items Received")
        grn_item_hdrs_submit_final_v9_ui = st.columns([2.5,1,1,1.2,1.2,2]); grn_item_hdrs_submit_final_v9_ui[0].markdown("**Item(Unit)**"); grn_item_hdrs_submit_final_v9_ui[1].markdown("**Ord**"); grn_item_hdrs_submit_final_v9_ui[2].markdown("**PrevRcvd**"); grn_item_hdrs_submit_final_v9_ui[3].markdown("**Pend**"); grn_item_hdrs_submit_final_v9_ui[4].markdown("**RcvNow***"); grn_item_hdrs_submit_final_v9_ui[5].markdown("**Price***")
        for i,line_grn_submit_final_v9_ui in enumerate(st.session_state.grn_line_items): 
            item_cols_grn_submit_final_v9_ui=st.columns([2.5,1,1,1.2,1.2,2]);key_prefix_grn_submit_final_v9_ui=f"grn_line_submit_final_ui_v9_corrected_{line_grn_submit_final_v9_ui.get('po_item_id',line_grn_submit_final_v9_ui.get('item_id',i))}" 
            item_cols_grn_submit_final_v9_ui[0].write(f"{line_grn_submit_final_v9_ui['item_name']}({line_grn_submit_final_v9_ui['item_unit']})");item_cols_grn_submit_final_v9_ui[1].write(f"{line_grn_submit_final_v9_ui['quantity_ordered_on_po']:.2f}");item_cols_grn_submit_final_v9_ui[2].write(f"{line_grn_submit_final_v9_ui.get('total_previously_received',0.0):.2f}")
            qty_pending_po_line_final_v9_ui=float(line_grn_submit_final_v9_ui.get('quantity_remaining_on_po',0.0));item_cols_grn_submit_final_v9_ui[3].write(f"{qty_pending_po_line_final_v9_ui:.2f}")
            st.session_state.grn_line_items[i]['quantity_received_now']=item_cols_grn_submit_final_v9_ui[4].number_input(f"QtyRcvNow_{key_prefix_grn_submit_final_v9_ui}",value=float(line_grn_submit_final_v9_ui.get('quantity_received_now',0.0)),min_value=0.0,max_value=qty_pending_po_line_final_v9_ui,step=0.01,format="%.2f",key=f"{key_prefix_grn_submit_final_v9_ui}_qty_v16",label_visibility="collapsed",help=f"Max:{qty_pending_po_line_final_v9_ui:.2f}")
            st.session_state.grn_line_items[i]['unit_price_at_receipt']=item_cols_grn_submit_final_v9_ui[5].number_input(f"PriceRcv_{key_prefix_grn_submit_final_v9_ui}",value=float(line_grn_submit_final_v9_ui.get('unit_price_at_receipt',0.0)),min_value=0.00,step=0.01,format="%.2f",key=f"{key_prefix_grn_submit_final_v9_ui}_price_v16",label_visibility="collapsed",help="Actual price.")
            st.caption("") 
        st.divider()
        submit_grn_btn_final_submit_v9_ui = st.form_submit_button("💾 Record Goods Received", type="primary", use_container_width=True) 
        if submit_grn_btn_final_submit_v9_ui: 
            if not st.session_state.grn_received_by_val.strip(): st.warning("⚠️ 'Received By' required.")
            else:
                hdr_submit_grn_final_submit_v9_ui = {"po_id":active_grn_po_details_data['po_id'],"supplier_id":active_grn_po_details_data['supplier_id'], "received_date":st.session_state.grn_received_date_val,"notes":st.session_state.grn_header_notes_val, "received_by_user_id":st.session_state.grn_received_by_val.strip()}
                items_submit_grn_final_list_submit_v9_ui, one_item_rcvd_final_flag_submit_v9_ui = [], False 
                for l_data_grn_final_submit_loop_v9_ui in st.session_state.grn_line_items: 
                    qty_rcv_now_final_submit_loop_v9_ui = float(l_data_grn_final_submit_loop_v9_ui.get('quantity_received_now',0.0))
                    max_allowed_for_item_submit_loop_v9_ui = float(l_data_grn_final_submit_loop_v9_ui.get('quantity_remaining_on_po', 0.0))
                    if qty_rcv_now_final_submit_loop_v9_ui > max_allowed_for_item_submit_loop_v9_ui:
                        st.error(f"🛑 For {l_data_grn_final_submit_loop_v9_ui['item_name']}, received ({qty_rcv_now_final_submit_loop_v9_ui}) > pending ({max_allowed_for_item_submit_loop_v9_ui}). Correct."); items_submit_grn_final_list_submit_v9_ui = []; break 
                    if qty_rcv_now_final_submit_loop_v9_ui > 0:
                        one_item_rcvd_final_flag_submit_v9_ui = True
                        items_submit_grn_final_list_submit_v9_ui.append({ "item_id":l_data_grn_final_submit_loop_v9_ui['item_id'],"po_item_id":l_data_grn_final_submit_loop_v9_ui['po_item_id'], "quantity_ordered_on_po":l_data_grn_final_submit_loop_v9_ui['quantity_ordered_on_po'], "quantity_received":qty_rcv_now_final_submit_loop_v9_ui, "unit_price_at_receipt":float(l_data_grn_final_submit_loop_v9_ui['unit_price_at_receipt']), "item_notes":l_data_grn_final_submit_loop_v9_ui.get('item_notes_grn') })
                if not items_submit_grn_final_list_submit_v9_ui and one_item_rcvd_final_flag_submit_v9_ui : pass 
                elif not one_item_rcvd_final_flag_submit_v9_ui: st.warning("⚠️ Enter quantity for at least one item.")
                else: 
                    s_grn_final_submit_v9_ui,m_grn_final_submit_v9_ui,new_id_grn_final_submit_v9_ui = goods_receiving_service.create_grn(db_engine,hdr_submit_grn_final_submit_v9_ui,items_submit_grn_final_list_submit_v9_ui) 
                    if s_grn_final_submit_v9_ui: st.success(f"✅ {m_grn_final_submit_v9_ui} (GRN ID: {new_id_grn_final_submit_v9_ui})"); change_view_mode("list_po",clear_grn_state=True); purchase_order_service.list_pos.clear(); st.rerun()
                    else: st.error(f"❌ Failed to create GRN: {m_grn_final_submit_v9_ui}")

elif st.session_state.po_grn_view_mode == "view_po_details":
    st.subheader(f"📄 View Purchase Order Details")
    if st.button("⬅️ Back to PO List", key="back_to_po_list_from_view_details_v7_corrected_final"): 
        change_view_mode("list_po"); st.rerun()
    po_id_to_view_final_ui_v7 = st.session_state.get('po_to_view_id') 
    if not po_id_to_view_final_ui_v7: st.warning("⚠️ No PO selected. Please go back."); st.stop()
    po_details_data_final_ui_v7 = purchase_order_service.get_po_by_id(db_engine, po_id_to_view_final_ui_v7) 
    if not po_details_data_final_ui_v7: st.error(f"❌ Could not load PO ID: {po_id_to_view_final_ui_v7}."); st.stop()
    st.markdown(f"**PO Number:** `{po_details_data_final_ui_v7.get('po_number', 'N/A')}`")
    st.markdown(f"**Supplier:** {po_details_data_final_ui_v7.get('supplier_name', 'N/A')}")
    header_cols_view_final_ui_v7 = st.columns(2) 
    header_cols_view_final_ui_v7[0].markdown(f"**Order Date:** {pd.to_datetime(po_details_data_final_ui_v7.get('order_date')).strftime('%Y-%m-%d') if pd.notna(po_details_data_final_ui_v7.get('order_date')) else 'N/A'}")
    header_cols_view_final_ui_v7[0].markdown(f"**Expected Delivery:** {pd.to_datetime(po_details_data_final_ui_v7.get('expected_delivery_date')).strftime('%Y-%m-%d') if pd.notna(po_details_data_final_ui_v7.get('expected_delivery_date')) else 'N/A'}")
    header_cols_view_final_ui_v7[1].markdown(f"**Status:** {po_details_data_final_ui_v7.get('status', 'N/A')}")
    header_cols_view_final_ui_v7[1].markdown(f"**Total Amount:** {po_details_data_final_ui_v7.get('total_amount', 0.0):.2f}")
    st.markdown(f"**Created By:** {po_details_data_final_ui_v7.get('created_by_user_id', 'N/A')}")
    st.markdown(f"**Created At:** {pd.to_datetime(po_details_data_final_ui_v7.get('created_at')).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(po_details_data_final_ui_v7.get('created_at')) else 'N/A'}")
    if pd.notna(po_details_data_final_ui_v7.get('updated_at')) and po_details_data_final_ui_v7.get('updated_at') != po_details_data_final_ui_v7.get('created_at'):
         st.markdown(f"**Last Updated At:** {pd.to_datetime(po_details_data_final_ui_v7.get('updated_at')).strftime('%Y-%m-%d %H:%M:%S')}")
    if po_details_data_final_ui_v7.get('notes'):
        with st.expander("View PO Notes"): st.markdown(po_details_data_final_ui_v7['notes'])
    st.divider(); st.markdown("##### Ordered Items")
    po_items_view_final_ui_v7 = po_details_data_final_ui_v7.get("items", []) 
    if po_items_view_final_ui_v7:
        items_df_view_final_ui_v7 = pd.DataFrame(po_items_view_final_ui_v7) 
        st.dataframe(items_df_view_final_ui_v7, column_config={"po_item_id":None,"item_id":None,"item_name":st.column_config.TextColumn("Item Name"),
                                                  "item_unit":st.column_config.TextColumn("Unit",width="small"),"quantity_ordered":st.column_config.NumberColumn("Ordered Qty",format="%.2f"),
                                                  "unit_price":st.column_config.NumberColumn("Unit Price",format="%.2f"),"line_total":st.column_config.NumberColumn("Line Total",format="%.2f")},
                       hide_index=True,use_container_width=True)
    else: st.info("ℹ️ No items found for this PO.")
    st.divider()
    if po_details_data_final_ui_v7.get('status') == PO_STATUS_DRAFT:
        current_user_for_submit_view_v7 = st.session_state.get("form_user_id_val") or st.session_state.po_submitter_user_id
        if st.button("➡️ Submit PO to Supplier", key="submit_po_from_view_details_v8_corrected", type="primary"): 
            s_stat_view_v7, m_stat_view_v7 = purchase_order_service.update_po_status(db_engine, po_id_to_view_final_ui_v7, PO_STATUS_ORDERED, current_user_for_submit_view_v7)
            if s_stat_view_v7: st.success(f"PO {po_details_data_final_ui_v7.get('po_number')} status updated. {m_stat_view_v7}"); change_view_mode("list_po"); st.rerun()
            else: st.error(f"❌ Failed to submit PO: {m_stat_view_v7}")

elif st.session_state.po_grn_view_mode == "edit_po": # This is the stub for edit mode
    st.subheader(f"✏️ Edit Purchase Order (ID: {st.session_state.po_to_edit_id})")
    if st.button("⬅️ Back to PO List", key="back_to_po_list_edit_v16_corrected_final"): 
        change_view_mode("list_po", clear_po_form_state=True); st.rerun() 
    st.info("📝 Edit PO form is active above if a Draft PO was selected. (Functionality combined with Create PO section).")


if st.session_state.po_grn_view_mode == "list_po": 
    st.divider(); st.subheader("🧾 Recent Goods Received Notes")
    grn_list_df_display_final_v10_ui = goods_receiving_service.list_grns(db_engine) 
    if grn_list_df_display_final_v10_ui.empty: st.info("ℹ️ No GRNs recorded yet.")
    else:
        st.dataframe(grn_list_df_display_final_v10_ui,use_container_width=True,hide_index=True,
                       column_config={"grn_id":None,"po_id":None,"supplier_id":None,
                                      "grn_number":st.column_config.TextColumn("GRN #"),"po_number":st.column_config.TextColumn("Related PO #"),
                                      "supplier_name":st.column_config.TextColumn("Supplier"),"received_date":st.column_config.DateColumn("Received On",format="YYYY-MM-DD"),
                                      "received_by_user_id":st.column_config.TextColumn("Received By"),"notes":"GRN Notes",
                                      "created_at":st.column_config.DatetimeColumn("Recorded At",format="YYYY-MM-DD HH:mm")})
