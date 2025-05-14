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

if 'create_po_form_reset_signal' not in st.session_state:
    st.session_state.create_po_form_reset_signal = True 
if 'po_line_items' not in st.session_state: 
    st.session_state.po_line_items = []
if 'po_next_line_id' not in st.session_state:
    st.session_state.po_next_line_id = 0

default_supplier_key_pg6_ui = "-- Select Supplier --" # Unique key for this page
if "create_po_supplier_name_form_val" not in st.session_state: st.session_state.create_po_supplier_name_form_val = default_supplier_key_pg6_ui
if "create_po_order_date_form_val" not in st.session_state: st.session_state.create_po_order_date_form_val = date.today()
if "create_po_exp_delivery_date_form_val" not in st.session_state: st.session_state.create_po_exp_delivery_date_form_val = None
if "create_po_notes_form_val" not in st.session_state: st.session_state.create_po_notes_form_val = ""
if "create_po_user_id_form_val" not in st.session_state: st.session_state.create_po_user_id_form_val = ""
if "po_submitter_user_id" not in st.session_state: st.session_state.po_submitter_user_id = "System"

if "grn_received_date_val" not in st.session_state: st.session_state.grn_received_date_val = date.today()
if "grn_received_by_val" not in st.session_state: st.session_state.grn_received_by_val = "" 
if "grn_header_notes_val" not in st.session_state: st.session_state.grn_header_notes_val = ""

def change_view_mode(mode, po_id=None, clear_grn_state=True): 
    previous_mode = st.session_state.get('po_grn_view_mode', 'list_po')
    st.session_state.po_grn_view_mode = mode
    st.session_state.po_to_edit_id = po_id if mode == "edit_po" else None
    st.session_state.po_to_view_id = po_id if mode == "view_po_details" else None
    st.session_state.po_for_grn_id = po_id if mode == "create_grn_for_po" else None
    
    if mode == "create_grn_for_po" and po_id:
        po_details = purchase_order_service.get_po_by_id(db_engine, po_id)
        st.session_state.po_for_grn_details = po_details
        st.session_state.grn_line_items = [] 
        if po_details and po_details.get("items"):
            previously_received_df = goods_receiving_service.get_received_quantities_for_po(db_engine, po_id)
            for item in po_details["items"]:
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
    elif clear_grn_state: 
        st.session_state.po_for_grn_id = None; st.session_state.po_for_grn_details = None
        st.session_state.grn_line_items = []; st.session_state.grn_received_date_val = date.today()
        st.session_state.grn_received_by_val = ""; st.session_state.grn_header_notes_val = ""

    if mode == "create_po":
        if previous_mode != "create_po": st.session_state.create_po_form_reset_signal = True
    elif previous_mode == "create_po" and mode != "create_po": st.session_state.create_po_form_reset_signal = True

# --- Main Page Logic ---
if st.session_state.po_grn_view_mode == "list_po":
    st.subheader("📋 Existing Purchase Orders")
    # Corrected variable names for columns here
    filter_col1_list_view, filter_col2_list_view, filter_col3_list_view = st.columns([2,2,1]) 
    with filter_col1_list_view: # Corrected
        search_po_list_val_ui = st.text_input("Search PO #:", key="po_search_ui_v10", placeholder="e.g., PO-0001", help="Partial/full PO number.") # Key change
    with filter_col2_list_view: # Corrected
        suppliers_df_list_view = supplier_service.get_all_suppliers(db_engine, True)
        supplier_options_list_view = {default_supplier_key_pg6_ui: None, **{f"{r['name']} {'(Inactive)' if not r['is_active'] else ''}": r['supplier_id'] for _, r in suppliers_df_list_view.iterrows()}}
        sel_supp_name_list_view = st.selectbox( # Changed from fcol2_list.selectbox
            "Filter by Supplier:", options=list(supplier_options_list_view.keys()), 
            key="po_filter_supp_ui_v10", help="Filter by supplier." # Key change
        )
        sel_supp_id_list_view = supplier_options_list_view[sel_supp_name_list_view]
    with filter_col3_list_view: # Corrected
        sel_status_list_view = st.selectbox( # Changed from fcol3_list.selectbox
            "Filter by Status:", options=["All Statuses"] + ALL_PO_STATUSES, 
            key="po_filter_stat_ui_v10", help="Filter by PO status." # Key change
        )

    if st.button("➕ Create New Purchase Order", key="nav_create_po_btn_v9", type="primary", use_container_width=True): # Key change
        change_view_mode("create_po"); st.rerun()
    st.divider()

    q_filters_list_view = {} 
    if search_po_list_val_ui: q_filters_list_view["po_number_ilike"] = search_po_list_val_ui
    if sel_supp_id_list_view: q_filters_list_view["supplier_id"] = sel_supp_id_list_view
    if sel_status_list_view != "All Statuses": q_filters_list_view["status"] = sel_status_list_view
    pos_df_list_view_ui = purchase_order_service.list_pos(db_engine, filters=q_filters_list_view) 

    if pos_df_list_view_ui.empty: st.info("ℹ️ No Purchase Orders found matching criteria.")
    else:
        st.write(f"Found {len(pos_df_list_view_ui)} PO(s).")
        for _, row_list_view_ui in pos_df_list_view_ui.iterrows(): 
            status_list_view_item = row_list_view_ui['status'] 
            st.markdown(f"**PO #: {row_list_view_ui['po_number']}** | {row_list_view_ui['supplier_name']} | Status: _{status_list_view_item}_")
            disp_cols_list_view_item = st.columns([2,2,1.5,3]) 
            disp_cols_list_view_item[0].markdown(f"<small>Order: {pd.to_datetime(row_list_view_ui['order_date']).strftime('%d-%b-%y')}</small>", unsafe_allow_html=True)
            disp_cols_list_view_item[1].markdown(f"<small>Expected: {pd.to_datetime(row_list_view_ui['expected_delivery_date']).strftime('%d-%b-%y') if pd.notna(row_list_view_ui['expected_delivery_date']) else 'N/A'}</small>", unsafe_allow_html=True)
            disp_cols_list_view_item[2].markdown(f"<small>Total: {row_list_view_ui['total_amount']:.2f}</small>", unsafe_allow_html=True)
            with disp_cols_list_view_item[3]:
                btn_cols_list_view_ui = st.columns([1,1.5,1.5]) 
                submitter_id_list_view = st.session_state.get("create_po_user_id_form_val") or st.session_state.get("po_submitter_user_id", "SystemActionPO")
                
                if status_list_view_item == PO_STATUS_DRAFT:
                    if btn_cols_list_view_ui[1].button("➡️ Submit PO", key=f"submit_po_btn_ui_v2_{row_list_view_ui['po_id']}", help="Submit PO to change status to Ordered.", use_container_width=True): # Key change
                        s_upd_list_view,m_upd_list_view = purchase_order_service.update_po_status(db_engine, row_list_view_ui['po_id'], PO_STATUS_ORDERED, submitter_id_list_view)
                        if s_upd_list_view: st.success(f"PO {row_list_view_ui['po_number']} submitted."); purchase_order_service.list_pos.clear(); st.rerun()
                        else: st.error(f"Failed to submit PO: {m_upd_list_view}")
                
                if status_list_view_item in [PO_STATUS_ORDERED, PO_STATUS_PARTIALLY_RECEIVED]:
                    if btn_cols_list_view_ui[2].button("📥 Receive", key=f"receive_po_btn_ui_v2_{row_list_view_ui['po_id']}", help="Record goods receipt for this PO.", type="primary", use_container_width=True): # Key change
                        change_view_mode("create_grn_for_po", po_id=row_list_view_ui['po_id'], clear_grn_state=False); st.rerun()
                elif status_list_view_item != PO_STATUS_DRAFT: btn_cols_list_view_ui[1].write(""); btn_cols_list_view_ui[2].write("") 
            st.divider()

# --- PASTE THE FULLY CORRECTED "create_po" MODE HERE ---
# This elif block should contain the full UI and logic for PO creation
# as per the version that fixed the UI order (Header before Lines)
# and used unique keys and session state management.
elif st.session_state.po_grn_view_mode == "create_po":
    st.subheader("🆕 Create New Purchase Order")
    if st.button("⬅️ Back to PO List", key="back_create_po_v10_final"): change_view_mode("list_po"); st.rerun()

    supp_df_create_po_final = supplier_service.get_all_suppliers(db_engine, False)
    supp_dict_create_po_final = {default_supplier_key_pg6_ui: None, **{r['name']: r['supplier_id'] for _,r in supp_df_create_po_final.iterrows()}}
    item_df_create_po_final = item_service.get_all_items_with_stock(db_engine, False) 
    item_dict_create_po_final = {"-- Select Item --": (None,None), **{f"{r['name']} ({r['unit']})":(r['item_id'],r['unit']) for _,r in item_df_create_po_final.iterrows()}}

    if st.session_state.create_po_form_reset_signal:
        st.session_state.po_line_items = [{'id':0,'item_key':"-- Select Item --",'quantity':1.0,'unit_price':0.0,'unit':''}]
        st.session_state.po_next_line_id = 1
        st.session_state.create_po_supplier_name_form_val = default_supplier_key_pg6_ui
        st.session_state.create_po_order_date_form_val = date.today()
        st.session_state.create_po_exp_delivery_date_form_val = None
        st.session_state.create_po_notes_form_val = ""; st.session_state.create_po_user_id_form_val = st.session_state.get("po_submitter_user_id", "")
        st.session_state.create_po_form_reset_signal = False
    elif not st.session_state.po_line_items:
        st.session_state.po_line_items = [{'id':0,'item_key':"-- Select Item --",'quantity':1.0,'unit_price':0.0,'unit':''}]
        st.session_state.po_next_line_id = 1
            
    def add_po_line_ss_create_po_final(): 
        new_id = st.session_state.po_next_line_id
        st.session_state.po_line_items.append({'id':new_id,'item_key':"-- Select Item --",'quantity':1.0,'unit_price':0.0,'unit':''})
        st.session_state.po_next_line_id+=1

    def remove_po_line_ss_create_po_final(id_rem): 
        st.session_state.po_line_items=[l for l in st.session_state.po_line_items if l['id']!=id_rem]
        if not st.session_state.po_line_items:
            add_po_line_ss_create_po_final()

    st.markdown("##### 📋 PO Header Details")
    with st.form("create_po_form_v10_header_final"): # Key change
        curr_supp_val_create_po_final = st.session_state.create_po_supplier_name_form_val
        if curr_supp_val_create_po_final not in supp_dict_create_po_final: curr_supp_val_create_po_final = default_supplier_key_pg6_ui
        supp_idx_create_po_final = list(supp_dict_create_po_final.keys()).index(curr_supp_val_create_po_final)

        sel_supp_widget_create_po_final = st.selectbox("Supplier*", options=list(supp_dict_create_po_final.keys()), index=supp_idx_create_po_final, key="create_po_supp_widget_v8_final", help="Choose the supplier for this Purchase Order.")
        st.session_state.create_po_supplier_name_form_val = sel_supp_widget_create_po_final
        sel_supp_id_submit_create_po_final = supp_dict_create_po_final[sel_supp_widget_create_po_final]

        hcols1_create_po_final, hcols2_create_po_final = st.columns(2)
        with hcols1_create_po_final:
            st.session_state.create_po_order_date_form_val = hcols1_create_po_final.date_input("Order Date*", value=st.session_state.create_po_order_date_form_val, key="create_po_order_date_widget_v8_final", help="Order placement date.")
        with hcols2_create_po_final:
            st.session_state.create_po_exp_delivery_date_form_val = hcols2_create_po_final.date_input("Expected Delivery", value=st.session_state.create_po_exp_delivery_date_form_val, key="create_po_exp_del_widget_v8_final", help="Optional: Expected arrival.")
        st.session_state.create_po_notes_form_val = st.text_area("PO Notes", value=st.session_state.create_po_notes_form_val, key="create_po_notes_widget_v8_final", placeholder="e.g., Payment terms...", help="Optional notes for PO.")
        st.session_state.create_po_user_id_form_val = st.text_input("Your Name/ID*", value=st.session_state.create_po_user_id_form_val, key="create_po_user_id_widget_v8_final", placeholder="Creator's identifier", help="Your identifier.")
        st.divider()
        submit_btn_final_po_form_create_final = st.form_submit_button("💾 Create Purchase Order", type="primary", use_container_width=True)

    st.markdown("##### 🛍️ PO Line Items")
    l_hcols_create_po_final = st.columns([4,1,1.5,1,0.5]); l_hcols_create_po_final[0].markdown("**Item**"); l_hcols_create_po_final[1].markdown("**Qty**"); l_hcols_create_po_final[2].markdown("**Price**"); l_hcols_create_po_final[3].markdown("**Unit**"); l_hcols_create_po_final[4].markdown("**Act**")
    
    current_lines_render_create_po_final = [] 
    for i,l_state_create_po_final in enumerate(st.session_state.po_line_items):
        l_cols_create_po_final = st.columns([4,1,1.5,1,0.5]); l_id_create_po_final = l_state_create_po_final['id']
        curr_item_key_create_po_final = l_state_create_po_final.get('item_key',"-- Select Item --")
        if curr_item_key_create_po_final not in item_dict_create_po_final: curr_item_key_create_po_final="-- Select Item --"
        try: item_idx_create_po_final = list(item_dict_create_po_final.keys()).index(curr_item_key_create_po_final)
        except ValueError: item_idx_create_po_final = 0
        
        sel_item_name_widget_create_po_final = l_cols_create_po_final[0].selectbox("Item",options=list(item_dict_create_po_final.keys()),key=f"line_item_name_w_create_po_final_{l_id_create_po_final}",index=item_idx_create_po_final,label_visibility="collapsed")
        _,unit_w_create_po_final = item_dict_create_po_final[sel_item_name_widget_create_po_final]
        qty_w_create_po_final = l_cols_create_po_final[1].number_input("Qty",value=float(l_state_create_po_final.get('quantity',1.0)),min_value=0.01,step=0.1,format="%.2f",key=f"line_qty_w_create_po_final_{l_id_create_po_final}",label_visibility="collapsed")
        price_w_create_po_final = l_cols_create_po_final[2].number_input("Price",value=float(l_state_create_po_final.get('unit_price',0.0)),min_value=0.00,step=0.01,format="%.2f",key=f"line_price_w_create_po_final_{l_id_create_po_final}",label_visibility="collapsed")
        l_cols_create_po_final[3].text_input("Unit",value=(unit_w_create_po_final or ''),key=f"line_unit_w_create_po_final_{l_id_create_po_final}",disabled=True,label_visibility="collapsed")
        if len(st.session_state.po_line_items)>1:
            if l_cols_create_po_final[4].button("➖",key=f"del_line_w_btn_create_po_final_{l_id_create_po_final}",help="Remove this line"): remove_po_line_ss_create_po_final(l_id_create_po_final); st.rerun()
        else: l_cols_create_po_final[4].write("")
        current_lines_render_create_po_final.append({'id':l_id_create_po_final,'item_key':sel_item_name_widget_create_po_final,'quantity':qty_w_create_po_final,'unit_price':price_w_create_po_final,'unit':(unit_w_create_po_final or '')})
    st.session_state.po_line_items = current_lines_render_create_po_final

    if st.button("➕ Add Item Line", on_click=add_po_line_ss_create_po_final, key="add_po_line_main_btn_v11_final", help="Add new item line."): pass 
    st.divider()

    if submit_btn_final_po_form_create_final:
        if not sel_supp_id_submit_create_po_final: st.warning("⚠️ Please select a supplier.")
        elif not st.session_state.create_po_user_id_form_val.strip(): st.warning("⚠️ Please enter 'Your Name/ID'.")
        else:
            header_data_submit_final = {"supplier_id":sel_supp_id_submit_create_po_final, "order_date":st.session_state.create_po_order_date_form_val,
                           "expected_delivery_date":st.session_state.create_po_exp_delivery_date_form_val,
                           "notes":st.session_state.create_po_notes_form_val, 
                           "created_by_user_id":st.session_state.create_po_user_id_form_val.strip(), "status":PO_STATUS_DRAFT}
            items_to_submit_final_list, valid_items_final_flag = [], True 
            if not st.session_state.po_line_items or all(item_dict_create_po_final[l.get('item_key',"-- Select Item --")][0] is None for l in st.session_state.po_line_items):
                st.error("🛑 Add at least one valid item."); valid_items_final_flag=False
            if valid_items_final_flag:
                for l_data_final_submit in st.session_state.po_line_items:
                    item_id_final_submit, _ = item_dict_create_po_final.get(l_data_final_submit['item_key'],(None,None))
                    if item_id_final_submit is None: st.error(f"🛑 Item '{l_data_final_submit['item_key']}' invalid."); valid_items_final_flag=False; break
                    try: qty_final_submit,price_final_submit = float(l_data_final_submit['quantity']),float(l_data_final_submit['unit_price'])
                    except(ValueError,TypeError): st.error(f"🛑 Invalid qty/price for '{l_data_final_submit['item_key']}'."); valid_items_final_flag=False; break
                    if qty_final_submit<=0: st.error(f"🛑 Qty for '{l_data_final_submit['item_key']}' > 0."); valid_items_final_flag=False; break
                    items_to_submit_final_list.append({"item_id":item_id_final_submit,"quantity_ordered":qty_final_submit,"unit_price":price_final_submit})
            if not items_to_submit_final_list and valid_items_final_flag: st.error("🛑 No valid items to submit."); valid_items_final_flag=False
            if valid_items_final_flag:
                s_final_submit,m_final_submit,new_id_final_submit = purchase_order_service.create_po(db_engine,header_data_submit_final,items_to_submit_final_list)
                if s_final_submit: st.success(f"✅ {m_final_submit} (PO ID: {new_id_final_submit})"); change_view_mode("list_po"); st.rerun()
                else: st.error(f"❌ Failed to create PO: {m_final_submit}")

# --- CREATE GRN FOR PO MODE ---
elif st.session_state.po_grn_view_mode == "create_grn_for_po":
    grn_po_details_ui_form_submit = st.session_state.po_for_grn_details 
    st.subheader(f"📥 Record GRN for PO: {grn_po_details_ui_form_submit.get('po_number', 'N/A') if grn_po_details_ui_form_submit else 'N/A'}")
    if st.button("⬅️ Back to PO List", key="back_grn_v8_final"): # Key change
        change_view_mode("list_po", clear_grn_state=True); st.rerun()
    
    if not grn_po_details_ui_form_submit or not st.session_state.grn_line_items:
        st.warning("⚠️ PO details not loaded or no items. Attempting reload or go back.")
        if st.session_state.po_for_grn_id:
            change_view_mode("create_grn_for_po", po_id=st.session_state.po_for_grn_id, clear_grn_state=False)
            st.rerun()
        else: change_view_mode("list_po"); st.rerun()
        st.stop()

    st.markdown(f"**Supplier:** {grn_po_details_ui_form_submit['supplier_name']} | **Order Date:** {pd.to_datetime(grn_po_details_ui_form_submit['order_date']).strftime('%Y-%m-%d')}")
    st.markdown(f"**Expected Delivery:** {pd.to_datetime(grn_po_details_ui_form_submit['expected_delivery_date']).strftime('%Y-%m-%d') if pd.notna(grn_po_details_ui_form_submit['expected_delivery_date']) else 'N/A'}")
    st.divider()

    with st.form("create_grn_form_v8_final_submit"): # Key change
        st.markdown("##### 📋 GRN Header")
        grn_hdr_cols_submit_final = st.columns(2) 
        with grn_hdr_cols_submit_final[0]: st.session_state.grn_received_date_val = st.date_input("Received Date*", value=st.session_state.grn_received_date_val, key="grn_recv_date_v8_final", help="Date goods received.") # Key change
        with grn_hdr_cols_submit_final[1]: st.session_state.grn_received_by_val = st.text_input("Received By*", value=st.session_state.grn_received_by_val, key="grn_recv_by_v8_final", help="Person recording receipt.") # Key change
        st.session_state.grn_header_notes_val = st.text_area("GRN Notes", value=st.session_state.grn_header_notes_val, key="grn_notes_hdr_v8_final", placeholder="e.g., Invoice #...", help="Optional GRN notes.") # Key change
        st.divider()
        st.markdown("##### 📦 Items Received")
        grn_item_hdrs_submit_final = st.columns([2.5, 1, 1, 1.2, 1.2, 2]) 
        grn_item_hdrs_submit_final[0].markdown("**Item (Unit)**"); grn_item_hdrs_submit_final[1].markdown("**Ordered**"); grn_item_hdrs_submit_final[2].markdown("**Prev. Rcvd**"); grn_item_hdrs_submit_final[3].markdown("**Qty Pending**"); grn_item_hdrs_submit_final[4].markdown("**Rcv Now***"); grn_item_hdrs_submit_final[5].markdown("**Price (Receipt)***")

        for i, line_grn_submit_final in enumerate(st.session_state.grn_line_items): 
            item_cols_grn_submit_final = st.columns([2.5, 1, 1, 1.2, 1.2, 2]) 
            key_prefix_grn_submit_final = f"grn_line_submit_final_{line_grn_submit_final.get('po_item_id', line_grn_submit_final.get('item_id',i))}" 
            item_cols_grn_submit_final[0].write(f"{line_grn_submit_final['item_name']} ({line_grn_submit_final['item_unit']})")
            item_cols_grn_submit_final[1].write(f"{line_grn_submit_final['quantity_ordered_on_po']:.2f}")
            item_cols_grn_submit_final[2].write(f"{line_grn_submit_final.get('total_previously_received', 0.0):.2f}")
            qty_pending_po_line_final = float(line_grn_submit_final.get('quantity_remaining_on_po', 0.0)) 
            item_cols_grn_submit_final[3].write(f"{qty_pending_po_line_final:.2f}")
            st.session_state.grn_line_items[i]['quantity_received_now'] = item_cols_grn_submit_final[4].number_input(
                "QtyRcvNow", value=float(line_grn_submit_final.get('quantity_received_now',0.0)), min_value=0.0,
                max_value=qty_pending_po_line_final, step=0.01,format="%.2f",key=f"{key_prefix_grn_submit_final}_qty_v7", # Key change
                label_visibility="collapsed", help=f"Max receivable: {qty_pending_po_line_final:.2f}"
            )
            st.session_state.grn_line_items[i]['unit_price_at_receipt'] = item_cols_grn_submit_final[5].number_input(
                "PriceRcv", value=float(line_grn_submit_final.get('unit_price_at_receipt',0.0)), min_value=0.00,
                step=0.01,format="%.2f",key=f"{key_prefix_grn_submit_final}_price_v7", # Key change
                label_visibility="collapsed",help="Actual price at receipt."
            )
            st.caption("") 
        st.divider()
        submit_grn_btn_final_submit = st.form_submit_button("💾 Record Goods Received", type="primary", use_container_width=True) 

        if submit_grn_btn_final_submit:
            if not st.session_state.grn_received_by_val.strip(): st.warning("⚠️ 'Received By' required.")
            else:
                hdr_submit_grn_final_submit = {"po_id":grn_po_details_ui_form_submit['po_id'],"supplier_id":grn_po_details_ui_form_submit['supplier_id'], 
                              "received_date":st.session_state.grn_received_date_val,"notes":st.session_state.grn_header_notes_val,
                              "received_by_user_id":st.session_state.grn_received_by_val.strip()}
                items_submit_grn_final_list_submit, one_item_rcvd_final_flag_submit = [], False 
                for l_data_grn_final_submit_loop in st.session_state.grn_line_items: 
                    qty_rcv_now_final_submit_loop = float(l_data_grn_final_submit_loop.get('quantity_received_now',0.0))
                    max_allowed_for_item_submit_loop = float(l_data_grn_final_submit_loop.get('quantity_remaining_on_po', 0.0))
                    if qty_rcv_now_final_submit_loop > max_allowed_for_item_submit_loop:
                        st.error(f"🛑 For {l_data_grn_final_submit_loop['item_name']}, received ({qty_rcv_now_final_submit_loop}) > pending ({max_allowed_for_item_submit_loop}). Correct."); items_submit_grn_final_list_submit = []; break 
                    if qty_rcv_now_final_submit_loop > 0:
                        one_item_rcvd_final_flag_submit = True
                        items_submit_grn_final_list_submit.append({
                            "item_id":l_data_grn_final_submit_loop['item_id'],"po_item_id":l_data_grn_final_submit_loop['po_item_id'],
                            "quantity_ordered_on_po":l_data_grn_final_submit_loop['quantity_ordered_on_po'], "quantity_received":qty_rcv_now_final_submit_loop, 
                            "unit_price_at_receipt":float(l_data_grn_final_submit_loop['unit_price_at_receipt']), "item_notes":l_data_grn_final_submit_loop.get('item_notes_grn') })
                if not items_submit_grn_final_list_submit and one_item_rcvd_final_flag_submit : pass 
                elif not one_item_rcvd_final_flag_submit: st.warning("⚠️ Enter quantity for at least one item.")
                else: 
                    s_grn_final_submit,m_grn_final_submit,new_id_grn_final_submit = goods_receiving_service.create_grn(db_engine,hdr_submit_grn_final_submit,items_submit_grn_final_list_submit) 
                    if s_grn_final_submit: 
                        st.success(f"✅ {m_grn_final_submit} (GRN ID: {new_id_grn_final_submit})"); change_view_mode("list_po",clear_grn_state=True); purchase_order_service.list_pos.clear(); st.rerun()
                    else: st.error(f"❌ Failed to create GRN: {m_grn_final_submit}")

elif st.session_state.po_grn_view_mode == "edit_po":
    st.subheader(f"✏️ Edit Purchase Order (ID: {st.session_state.po_to_edit_id})")
    if st.button("⬅️ Back to PO List", key="back_to_po_list_edit_v10_final"): change_view_mode("list_po"); st.rerun() # Key change
    st.info("📝 Edit PO functionality is under development.")

elif st.session_state.po_grn_view_mode == "view_po_details":
    st.subheader(f"📄 View Purchase Order Details (ID: {st.session_state.po_to_view_id})")
    if st.button("⬅️ Back to PO List", key="back_to_po_list_view_v10_final"): change_view_mode("list_po"); st.rerun() # Key change
    st.info("📄 View PO Details functionality is under development.")

if st.session_state.po_grn_view_mode == "list_po":
    st.divider(); st.subheader("🧾 Recent Goods Received Notes")
    grn_list_df_display_ui = goods_receiving_service.list_grns(db_engine) 
    if grn_list_df_display_ui.empty: st.info("ℹ️ No GRNs recorded yet.")
    else:
        st.dataframe(grn_list_df_display_ui,use_container_width=True,hide_index=True,
                       column_config={"grn_id":None,"po_id":None,"supplier_id":None,
                                      "grn_number":st.column_config.TextColumn("GRN #"),"po_number":st.column_config.TextColumn("Related PO #"),
                                      "supplier_name":st.column_config.TextColumn("Supplier"),"received_date":st.column_config.DateColumn("Received On",format="YYYY-MM-DD"),
                                      "received_by_user_id":st.column_config.TextColumn("Received By"),"notes":"GRN Notes",
                                      "created_at":st.column_config.DatetimeColumn("Recorded At",format="YYYY-MM-DD HH:mm")})