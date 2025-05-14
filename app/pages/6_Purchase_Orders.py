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

default_supplier_key_ui = "-- Select Supplier --" 
if "create_po_supplier_name_form_val" not in st.session_state: st.session_state.create_po_supplier_name_form_val = default_supplier_key_ui
if "create_po_order_date_form_val" not in st.session_state: st.session_state.create_po_order_date_form_val = date.today()
if "create_po_exp_delivery_date_form_val" not in st.session_state: st.session_state.create_po_exp_delivery_date_form_val = None
if "create_po_notes_form_val" not in st.session_state: st.session_state.create_po_notes_form_val = ""
if "create_po_user_id_form_val" not in st.session_state: st.session_state.create_po_user_id_form_val = ""
if "po_submitter_user_id" not in st.session_state: st.session_state.po_submitter_user_id = "System"

if "grn_received_date_val" not in st.session_state: st.session_state.grn_received_date_val = date.today()
if "grn_received_by_val" not in st.session_state: st.session_state.grn_received_by_val = ""
if "grn_header_notes_val" not in st.session_state: st.session_state.grn_header_notes_val = ""


# --- Helper Functions ---
def change_view_mode(mode, po_id=None, clear_grn_state=True): 
    previous_mode = st.session_state.get('po_grn_view_mode', 'list_po')
    st.session_state.po_grn_view_mode = mode

    st.session_state.po_to_edit_id = po_id if mode == "edit_po" else None
    st.session_state.po_to_view_id = po_id if mode == "view_po_details" else None
    
    if mode == "create_grn_for_po" and po_id:
        st.session_state.po_for_grn_id = po_id
        st.session_state.po_for_grn_details = purchase_order_service.get_po_by_id(db_engine, po_id)
        st.session_state.grn_line_items = [] # Reset GRN lines specific to this PO
        if st.session_state.po_for_grn_details and st.session_state.po_for_grn_details.get("items"):
            for item in st.session_state.po_for_grn_details["items"]:
                st.session_state.grn_line_items.append({
                    "po_item_id": item["po_item_id"], "item_id": item["item_id"],
                    "item_name": item["item_name"], "item_unit": item["item_unit"],
                    "quantity_ordered_on_po": float(item["quantity_ordered"]),
                    "quantity_received_now": 0.0, 
                    "unit_price_at_receipt": float(item["unit_price"])
                })
    elif clear_grn_state: 
        st.session_state.po_for_grn_id = None # Clear if not navigating to create_grn_for_po
        st.session_state.po_for_grn_details = None
        st.session_state.grn_line_items = []
        st.session_state.grn_received_date_val = date.today()
        st.session_state.grn_received_by_val = ""
        st.session_state.grn_header_notes_val = ""

    if mode == "create_po":
        if previous_mode != "create_po": 
             st.session_state.create_po_form_reset_signal = True
    elif previous_mode == "create_po" and mode != "create_po": 
        st.session_state.create_po_form_reset_signal = True

# --- Main Page Logic ---

if st.session_state.po_grn_view_mode == "list_po":
    st.subheader("📋 Existing Purchase Orders")
    fcol1, fcol2, fcol3 = st.columns([2,2,1])
    search_po_list_ui = fcol1.text_input("Search PO #:", key="po_search_ui_v8", placeholder="e.g., PO-0001", help="Partial/full PO number.") # Key change
    supp_df_list_ui = supplier_service.get_all_suppliers(db_engine, True)
    supp_opts_list_ui = {default_supplier_key_ui: None, **{f"{r['name']} {'(Inactive)' if not r['is_active'] else ''}": r['supplier_id'] for _, r in supp_df_list_ui.iterrows()}}
    sel_supp_name_list_ui = fcol2.selectbox("Filter by Supplier:", options=list(supp_opts_list_ui.keys()), key="po_filter_supp_ui_v8", help="Filter by supplier.") # Key change
    sel_status_list_ui = fcol3.selectbox("Filter by Status:", options=["All Statuses"] + ALL_PO_STATUSES, key="po_filter_stat_ui_v8", help="Filter by PO status.") # Key change

    if st.button("➕ Create New Purchase Order", key="nav_create_po_btn_v7", type="primary", use_container_width=True): # Key change
        change_view_mode("create_po"); st.rerun()
    st.divider()

    q_filters_list = {} # Unique var name
    if search_po_list_ui: q_filters_list["po_number_ilike"] = search_po_list_ui
    if supp_opts_list_ui[sel_supp_name_list_ui]: q_filters_list["supplier_id"] = supp_opts_list_ui[sel_supp_name_list_ui]
    if sel_status_list_ui != "All Statuses": q_filters_list["status"] = sel_status_list_ui
    pos_df_list_ui = purchase_order_service.list_pos(db_engine, filters=q_filters_list) # Unique var name

    if pos_df_list_ui.empty: st.info("ℹ️ No Purchase Orders found matching criteria.")
    else:
        st.write(f"Found {len(pos_df_list_ui)} PO(s).")
        for _, row_list_ui in pos_df_list_ui.iterrows(): # Unique var name
            status_list_ui = row_list_ui['status'] # Unique var name
            st.markdown(f"**PO #: {row_list_ui['po_number']}** | {row_list_ui['supplier_name']} | Status: _{status_list_ui}_")
            disp_cols_list_ui = st.columns([2,2,1.5,3]) # Unique var name
            disp_cols_list_ui[0].markdown(f"<small>Order: {pd.to_datetime(row_list_ui['order_date']).strftime('%d-%b-%y')}</small>", unsafe_allow_html=True)
            disp_cols_list_ui[1].markdown(f"<small>Expected: {pd.to_datetime(row_list_ui['expected_delivery_date']).strftime('%d-%b-%y') if pd.notna(row_list_ui['expected_delivery_date']) else 'N/A'}</small>", unsafe_allow_html=True)
            disp_cols_list_ui[2].markdown(f"<small>Total: {row_list_ui['total_amount']:.2f}</small>", unsafe_allow_html=True)
            with disp_cols_list_ui[3]:
                btn_cols_list_ui = st.columns([1,1.5,1.5]) # Unique var name
                submitter_id_list_ui = st.session_state.get("create_po_user_id_form_val") or st.session_state.get("po_submitter_user_id", "SystemAction") # Unique var name
                
                if status_list_ui == PO_STATUS_DRAFT:
                    if btn_cols_list_ui[1].button("➡️ Submit PO", key=f"submit_po_btn_ui_{row_list_ui['po_id']}", help="Submit PO to supplier.", use_container_width=True): # Key change
                        s_upd,m_upd = purchase_order_service.update_po_status(db_engine, row_list_ui['po_id'], PO_STATUS_ORDERED, submitter_id_list_ui)
                        if s_upd: st.success(f"PO {row_list_ui['po_number']} submitted."); purchase_order_service.list_pos.clear(); st.rerun()
                        else: st.error(f"Failed to submit PO: {m_upd}")
                
                if status_list_ui in [PO_STATUS_ORDERED, PO_STATUS_PARTIALLY_RECEIVED]:
                    if btn_cols_list_ui[2].button("📥 Receive", key=f"receive_po_btn_ui_{row_list_ui['po_id']}", help="Record goods receipt.", type="primary", use_container_width=True): # Key change
                        change_view_mode("create_grn_for_po", po_id=row_list_ui['po_id'], clear_grn_state=False); st.rerun()
                elif status_list_ui != PO_STATUS_DRAFT: btn_cols_list_ui[1].write(""); btn_cols_list_ui[2].write("") 
            st.divider()

elif st.session_state.po_grn_view_mode == "create_po":
    st.subheader("🆕 Create New Purchase Order")
    if st.button("⬅️ Back to PO List", key="back_create_po_v8"): change_view_mode("list_po"); st.rerun() # Key change

    supp_df_create = supplier_service.get_all_suppliers(db_engine, False)
    supp_dict_create = {default_supplier_key_ui: None, **{r['name']: r['supplier_id'] for _,r in supp_df_create.iterrows()}}
    item_df_create = item_service.get_all_items_with_stock(db_engine, False)
    item_dict_create = {"-- Select Item --": (None,None), **{f"{r['name']} ({r['unit']})":(r['item_id'],r['unit']) for _,r in item_df_create.iterrows()}}

    if st.session_state.create_po_form_reset_signal:
        st.session_state.po_line_items = [{'id':0,'item_key':"-- Select Item --",'quantity':1.0,'unit_price':0.0,'unit':''}]
        st.session_state.po_next_line_id = 1
        st.session_state.create_po_supplier_name_form_val = default_supplier_key_ui
        st.session_state.create_po_order_date_form_val = date.today()
        st.session_state.create_po_exp_delivery_date_form_val = None
        st.session_state.create_po_notes_form_val = ""; st.session_state.create_po_user_id_form_val = st.session_state.get("po_submitter_user_id", "")
        st.session_state.create_po_form_reset_signal = False
    elif not st.session_state.po_line_items:
        st.session_state.po_line_items = [{'id':0,'item_key':"-- Select Item --",'quantity':1.0,'unit_price':0.0,'unit':''}]
        st.session_state.po_next_line_id = 1
            
    def add_po_line_ss_create(): # Name consistent with usage
        new_id = st.session_state.po_next_line_id
        st.session_state.po_line_items.append({'id':new_id,'item_key':"-- Select Item --",'quantity':1.0,'unit_price':0.0,'unit':''})
        st.session_state.po_next_line_id+=1

    def remove_po_line_ss_create(id_rem): # Name consistent
        st.session_state.po_line_items=[l for l in st.session_state.po_line_items if l['id']!=id_rem]
        if not st.session_state.po_line_items: # ** CORRECTED SYNTAX HERE **
            add_po_line_ss_create()

    st.markdown("##### 📋 PO Header Details")
    with st.form("create_po_form_v8_header"): # Key change
        curr_supp_val_form = st.session_state.create_po_supplier_name_form_val
        if curr_supp_val_form not in supp_dict_create: curr_supp_val_form = default_supplier_key_ui
        supp_idx_form = list(supp_dict_create.keys()).index(curr_supp_val_form)

        sel_supp_widget_form = st.selectbox("Supplier*", options=list(supp_dict_create.keys()), index=supp_idx_form, key="create_po_supp_widget_v6", help="Choose supplier.") # Key change
        st.session_state.create_po_supplier_name_form_val = sel_supp_widget_form
        sel_supp_id_submit_form = supp_dict_create[sel_supp_widget_form]

        hcols1_form, hcols2_form = st.columns(2) # Unique var names
        st.session_state.create_po_order_date_form_val = hcols1_form.date_input("Order Date*", value=st.session_state.create_po_order_date_form_val, key="create_po_order_date_widget_v6", help="Order placement date.") # Key change
        st.session_state.create_po_exp_delivery_date_form_val = hcols2_form.date_input("Expected Delivery", value=st.session_state.create_po_exp_delivery_date_form_val, key="create_po_exp_del_widget_v6", help="Optional: Expected arrival.") # Key change
        st.session_state.create_po_notes_form_val = st.text_area("PO Notes", value=st.session_state.create_po_notes_form_val, key="create_po_notes_widget_v6", placeholder="e.g., Payment terms...", help="Optional notes for PO.") # Key change
        st.session_state.create_po_user_id_form_val = st.text_input("Your Name/ID*", value=st.session_state.create_po_user_id_form_val, key="create_po_user_id_widget_v6", placeholder="Creator's identifier", help="Your identifier.") # Key change
        st.divider()
        submit_btn_final_po_form = st.form_submit_button("💾 Create Purchase Order", type="primary", use_container_width=True)

    st.markdown("##### 🛍️ PO Line Items")
    l_hcols_create = st.columns([4,1,1.5,1,0.5]); l_hcols_create[0].markdown("**Item**"); l_hcols_create[1].markdown("**Qty**"); l_hcols_create[2].markdown("**Price**"); l_hcols_create[3].markdown("**Unit**"); l_hcols_create[4].markdown("**Act**")
    
    current_lines_render_create = [] # Unique var name
    for i,l_state_create in enumerate(st.session_state.po_line_items): # Unique var name
        l_cols_create = st.columns([4,1,1.5,1,0.5]); l_id_create = l_state_create['id']
        curr_item_key_create = l_state_create.get('item_key',"-- Select Item --")
        if curr_item_key_create not in item_dict_create: curr_item_key_create="-- Select Item --"
        try: item_idx_create = list(item_dict_create.keys()).index(curr_item_key_create)
        except ValueError: item_idx_create = 0
        
        sel_item_name_widget_create = l_cols_create[0].selectbox("Item",options=list(item_dict_create.keys()),key=f"line_item_name_w_create_{l_id_create}",index=item_idx_create,label_visibility="collapsed") # Unique key
        _,unit_w_create = item_dict_create[sel_item_name_widget_create]
        qty_w_create = l_cols_create[1].number_input("Qty",value=float(l_state_create.get('quantity',1.0)),min_value=0.01,step=0.1,format="%.2f",key=f"line_qty_w_create_{l_id_create}",label_visibility="collapsed") # Unique key
        price_w_create = l_cols_create[2].number_input("Price",value=float(l_state_create.get('unit_price',0.0)),min_value=0.00,step=0.01,format="%.2f",key=f"line_price_w_create_{l_id_create}",label_visibility="collapsed") # Unique key
        l_cols_create[3].text_input("Unit",value=(unit_w_create or ''),key=f"line_unit_w_create_{l_id_create}",disabled=True,label_visibility="collapsed") # Unique key
        if len(st.session_state.po_line_items)>1:
            if l_cols_create[4].button("➖",key=f"del_line_w_btn_create_{l_id_create}",help="Remove this line"): remove_po_line_ss_create(l_id_create); st.rerun() # Unique key
        else: l_cols_create[4].write("")
        current_lines_render_create.append({'id':l_id_create,'item_key':sel_item_name_widget_create,'quantity':qty_w_create,'unit_price':price_w_create,'unit':(unit_w_create or '')})
    st.session_state.po_line_items = current_lines_render_create

    if st.button("➕ Add Item Line", on_click=add_po_line_ss_create, key="add_po_line_main_btn_v9", help="Add new item line."): pass # Key change
    st.divider()

    if submit_btn_final_po_form: # Check the correct submit button variable
        if not sel_supp_id_submit_form: st.warning("⚠️ Please select a supplier.") # Use var from form scope
        elif not st.session_state.create_po_user_id_form_val.strip(): st.warning("⚠️ Please enter 'Your Name/ID'.")
        else:
            header_data_submit = {"supplier_id":sel_supp_id_submit_form, "order_date":st.session_state.create_po_order_date_form_val, # Use correct session state vars
                           "expected_delivery_date":st.session_state.create_po_exp_delivery_date_form_val,
                           "notes":st.session_state.create_po_notes_form_val, 
                           "created_by_user_id":st.session_state.create_po_user_id_form_val.strip(), "status":PO_STATUS_DRAFT}
            items_to_submit_final, valid_items_final = [], True # Unique var names
            if not st.session_state.po_line_items or all(item_dict_create[l.get('item_key',"-- Select Item --")][0] is None for l in st.session_state.po_line_items):
                st.error("🛑 Add at least one valid item."); valid_items_final=False
            if valid_items_final:
                for l_data_final in st.session_state.po_line_items: # Unique var name
                    item_id_final, _ = item_dict_create.get(l_data_final['item_key'],(None,None))
                    if item_id_final is None: st.error(f"🛑 Item '{l_data_final['item_key']}' invalid."); valid_items_final=False; break
                    try: qty_final,price_final = float(l_data_final['quantity']),float(l_data_final['unit_price'])
                    except(ValueError,TypeError): st.error(f"🛑 Invalid qty/price for '{l_data_final['item_key']}'."); valid_items_final=False; break
                    if qty_final<=0: st.error(f"🛑 Qty for '{l_data_final['item_key']}' > 0."); valid_items_final=False; break
                    items_to_submit_final.append({"item_id":item_id_final,"quantity_ordered":qty_final,"unit_price":price_final})
            if not items_to_submit_final and valid_items_final: st.error("🛑 No valid items to submit."); valid_items_final=False
            if valid_items_final:
                s_create,m_create,new_id_create = purchase_order_service.create_po(db_engine,header_data_submit,items_to_submit_final)
                if s_create: st.success(f"✅ {m_create} (PO ID: {new_id_create})"); change_view_mode("list_po"); st.rerun()
                else: st.error(f"❌ Failed to create PO: {m_create}")

elif st.session_state.po_grn_view_mode == "create_grn_for_po":
    # This section is for GRN creation, using unique variable names and keys
    grn_po_details = st.session_state.po_for_grn_details
    st.subheader(f"📥 Record GRN for PO: {grn_po_details.get('po_number', 'N/A') if grn_po_details else 'N/A'}")
    if st.button("⬅️ Back to PO List", key="back_grn_v5"): change_view_mode("list_po", clear_grn_state=True); st.rerun()
    
    if not grn_po_details or not st.session_state.grn_line_items:
        st.warning("⚠️ PO details not loaded or no items. Attempting reload or go back.")
        if st.session_state.po_for_grn_id:
            change_view_mode("create_grn_for_po", po_id=st.session_state.po_for_grn_id, clear_grn_state=False)
            st.rerun()
        else: change_view_mode("list_po"); st.rerun()
        st.stop()

    st.markdown(f"**Supplier:** {grn_po_details['supplier_name']} | **Order Date:** {pd.to_datetime(grn_po_details['order_date']).strftime('%Y-%m-%d')}")
    st.markdown(f"**Expected Delivery:** {pd.to_datetime(grn_po_details['expected_delivery_date']).strftime('%Y-%m-%d') if pd.notna(grn_po_details['expected_delivery_date']) else 'N/A'}")
    st.divider()

    with st.form("create_grn_form_v5"): # Unique key
        st.markdown("##### 📋 GRN Header")
        grn_hdr_cols = st.columns(2)
        st.session_state.grn_received_date_val = grn_hdr_cols[0].date_input("Received Date*", value=st.session_state.grn_received_date_val, key="grn_recv_date_v5", help="Date goods received.")
        st.session_state.grn_received_by_val = grn_hdr_cols[1].text_input("Received By*", value=st.session_state.grn_received_by_val, key="grn_recv_by_v5", help="Person recording receipt.")
        st.session_state.grn_header_notes_val = st.text_area("GRN Notes", value=st.session_state.grn_header_notes_val, key="grn_notes_hdr_v5", placeholder="e.g., Invoice #...", help="Optional GRN notes.")
        st.divider()
        st.markdown("##### 📦 Items Received")
        grn_item_hdrs = st.columns([3,1.5,1,1.5,1.5]); grn_item_hdrs[0].markdown("**Item (Unit)**"); grn_item_hdrs[1].markdown("**Ordered**"); grn_item_hdrs[2].markdown("**Rcv Now***"); grn_item_hdrs[3].markdown("**Price (Receipt)***"); grn_item_hdrs[4].markdown("**Notes**")

        for i, line_grn in enumerate(st.session_state.grn_line_items):
            item_cols_grn = st.columns([3,1.5,1,1.5,1.5])
            key_prefix_grn = f"grn_line_form_{line_grn.get('po_item_id', line_grn.get('item_id',i))}" # Unique key prefix
            item_cols_grn[0].write(f"{line_grn['item_name']} ({line_grn['item_unit']})")
            item_cols_grn[1].write(f"{line_grn['quantity_ordered_on_po']:.2f}")
            max_rcv_grn = float(line_grn['quantity_ordered_on_po']) 
            st.session_state.grn_line_items[i]['quantity_received_now'] = item_cols_grn[2].number_input("QtyRcv", value=float(line_grn.get('quantity_received_now',0.0)),min_value=0.0,max_value=max_rcv_grn,step=0.01,format="%.2f",key=f"{key_prefix_grn}_qty_v4",label_visibility="collapsed",help=f"Max: {max_rcv_grn:.2f}") # Key change
            st.session_state.grn_line_items[i]['unit_price_at_receipt'] = item_cols_grn[3].number_input("PriceRcv", value=float(line_grn.get('unit_price_at_receipt',0.0)),min_value=0.00,step=0.01,format="%.2f",key=f"{key_prefix_grn}_price_v4",label_visibility="collapsed",help="Actual price.") # Key change
            st.session_state.grn_line_items[i]['item_notes_grn'] = item_cols_grn[4].text_input("NotesRcv", value=line_grn.get('item_notes_grn',""),key=f"{key_prefix_grn}_notes_v4",label_visibility="collapsed",placeholder="Item notes...") # Key change
            st.caption("") 
        st.divider()
        submit_grn_btn = st.form_submit_button("💾 Record Goods Received", type="primary", use_container_width=True)

        if submit_grn_btn:
            if not st.session_state.grn_received_by_val.strip(): st.warning("⚠️ 'Received By' required.")
            else:
                hdr_submit_grn = {"po_id":grn_po_details['po_id'],"supplier_id":grn_po_details['supplier_id'],
                              "received_date":st.session_state.grn_received_date_val,"notes":st.session_state.grn_header_notes_val,
                              "received_by_user_id":st.session_state.grn_received_by_val.strip()}
                items_submit_grn_final, one_item_rcvd_final = [], False # Unique var names
                for l_data_grn_final in st.session_state.grn_line_items: # Unique var name
                    qty_rcv_now_final = float(l_data_grn_final.get('quantity_received_now',0.0))
                    if qty_rcv_now_final > 0:
                        one_item_rcvd_final = True
                        items_submit_grn_final.append({"item_id":l_data_grn_final['item_id'],"po_item_id":l_data_grn_final['po_item_id'],
                                                 "quantity_ordered_on_po":l_data_grn_final['quantity_ordered_on_po'],"quantity_received":qty_rcv_now_final,
                                                 "unit_price_at_receipt":float(l_data_grn_final['unit_price_at_receipt']),"item_notes":l_data_grn_final.get('item_notes_grn')})
                if not one_item_rcvd_final: st.warning("⚠️ Enter quantity for at least one item.")
                else:
                    s_grn,m_grn,new_id_grn = goods_receiving_service.create_grn(db_engine,hdr_submit_grn,items_submit_grn_final)
                    if s_grn: st.success(f"✅ {m_grn} (GRN ID: {new_id_grn})"); change_view_mode("list_po",clear_grn_state=True); purchase_order_service.list_pos.clear(); st.rerun()
                    else: st.error(f"❌ Failed to create GRN: {m_grn}")

elif st.session_state.po_grn_view_mode == "edit_po":
    st.subheader(f"✏️ Edit Purchase Order (ID: {st.session_state.po_to_edit_id})")
    if st.button("⬅️ Back to PO List", key="back_to_po_list_edit_v8"): change_view_mode("list_po"); st.rerun() # Key change
    st.info("📝 Edit PO functionality is under development.")

elif st.session_state.po_grn_view_mode == "view_po_details":
    st.subheader(f"📄 View Purchase Order Details (ID: {st.session_state.po_to_view_id})")
    if st.button("⬅️ Back to PO List", key="back_to_po_list_view_v8"): change_view_mode("list_po"); st.rerun() # Key change
    st.info("📄 View PO Details functionality is under development.")

if st.session_state.po_grn_view_mode == "list_po":
    st.divider(); st.subheader("🧾 Recent Goods Received Notes")
    grn_list_df_view = goods_receiving_service.list_grns(db_engine) # Unique var name
    if grn_list_df_view.empty: st.info("ℹ️ No GRNs recorded yet.")
    else:
        st.dataframe(grn_list_df_view,use_container_width=True,hide_index=True,
                       column_config={"grn_id":None,"po_id":None,"supplier_id":None,
                                      "grn_number":st.column_config.TextColumn("GRN #"),"po_number":st.column_config.TextColumn("Related PO #"),
                                      "supplier_name":st.column_config.TextColumn("Supplier"),"received_date":st.column_config.DateColumn("Received On",format="YYYY-MM-DD"),
                                      "received_by_user_id":st.column_config.TextColumn("Received By"),"notes":"GRN Notes",
                                      "created_at":st.column_config.DatetimeColumn("Recorded At",format="YYYY-MM-DD HH:mm")})