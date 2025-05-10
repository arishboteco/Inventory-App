# app/item_manager_app.py

import sys
import os

# Add the project root (INVENTORY-APP) to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from sqlalchemy import text, func # Minimal sqlalchemy imports needed by functions still in this file
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import pandas as pd
from typing import Any, Optional, Dict, List, Tuple, Set
from datetime import datetime, date, timedelta
import re

# --- Import from our new/refactored modules ---
from app.core.constants import (
    TX_RECEIVING, TX_ADJUSTMENT, TX_WASTAGE, TX_INDENT_FULFILL, TX_SALE,
    STATUS_SUBMITTED, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_CANCELLED,
    ALL_INDENT_STATUSES
)
from app.db.database_utils import connect_db, fetch_data
from app.services import item_service
from app.services import supplier_service
from app.services import stock_service
from app.services import indent_service

# NOTE: Item Master functions and Department Helper functions have been MOVED to app/services/item_service.py

# ─────────────────────────────────────────────────────────
# DASHBOARD UI (Main App Page)
# ─────────────────────────────────────────────────────────
def run_dashboard():
    st.set_page_config(page_title="Inv Manager", page_icon="🍲", layout="wide")
    st.title("🍲 Restaurant Inventory Dashboard")
    st.caption(f"As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    engine = connect_db()
    if not engine:
        st.warning("Database connection failed. Dashboard data cannot be loaded."); st.stop()

    # Call item_service for item data
    items_df = item_service.get_all_items_with_stock(engine, include_inactive=False)
    # Supplier data still comes from local function (will move to supplier_service)
    suppliers_df = supplier_service.get_all_suppliers(engine, include_inactive=False)

    total_active_items = len(items_df)
    total_active_suppliers = len(suppliers_df)
    low_stock_df = pd.DataFrame(); low_stock_count = 0
    if not items_df.empty and 'current_stock' in items_df.columns and 'reorder_point' in items_df.columns:
        try:
            items_df['current_stock_num'] = pd.to_numeric(items_df['current_stock'], errors='coerce').fillna(0)
            items_df['reorder_point_num'] = pd.to_numeric(items_df['reorder_point'], errors='coerce').fillna(0)
            mask = (items_df['current_stock_num'].notna() & items_df['reorder_point_num'].notna() &
                    (items_df['reorder_point_num'] > 0) &
                    (items_df['current_stock_num'] <= items_df['reorder_point_num']))
            low_stock_df = items_df.loc[mask, ['name', 'unit', 'current_stock', 'reorder_point']].copy()
            low_stock_count = len(low_stock_df)
        except KeyError as e: st.error(f"Missing column for low-stock calc: {e}")
        except Exception as e: st.error(f"Error calculating low stock: {e}")

    st.header("Key Metrics")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Active Items", total_active_items)
    kpi2.metric("Low Stock Items", low_stock_count, help="Items at or below reorder point (reorder > 0)")
    kpi3.metric("Active Suppliers", total_active_suppliers)
    st.divider()
    st.header("⚠️ Low Stock Items")
    if low_stock_count > 0:
        st.dataframe(low_stock_df, use_container_width=True, hide_index=True,
            column_config={"name": "Item Name", "unit": st.column_config.TextColumn(width="small"),
                           "current_stock": st.column_config.NumberColumn(format="%.2f", width="small"),
                           "reorder_point": st.column_config.NumberColumn(format="%.2f", width="small")})
    elif total_active_items > 0: st.info("No items currently below reorder point.")
    else: st.info("No active items in the system.")

if __name__ == "__main__":
    run_dashboard()