# app/item_manager_app.py

import os
import sys
from pathlib import Path

# Ensure this file works even when executed using a relative path (e.g.
# `streamlit run app/item_manager_app.py`).
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from .core.logging import configure_logging, flush_logs, LOG_FILE

# Configure logging before importing modules that use it
configure_logging()

import streamlit as st
import pandas as pd
from datetime import datetime
from .ui.theme import load_css, render_sidebar_logo
from .ui.navigation import render_sidebar_nav
from .ui.helpers import read_recent_logs

# --- Import from our new/refactored modules ---
from .core.constants import STATUS_SUBMITTED
from .db.database_utils import connect_db
from .services import item_service
from .services import supplier_service
from .services import indent_service
from .auth.auth import login_sidebar

# STATUS_SUBMITTED is already imported from core.constants above, no need to re-import separately

# NOTE: Item Master functions and Department Helper functions have been MOVED to app/services/item_service.py


# ─────────────────────────────────────────────────────────
# DASHBOARD UI (Main App Page)
# ─────────────────────────────────────────────────────────
def run_dashboard():
    st.set_page_config(
        page_title="Restaurant Inventory Manager", page_icon="🍲", layout="wide"
    )
    load_css()
    render_sidebar_logo()
    render_sidebar_nav(include_clear_logs_button=False)
    if not login_sidebar():
        st.stop()
    if st.sidebar.button("Clear Logs"):
        flush_logs()
        st.toast("Logs cleared")
    with st.sidebar.expander("Recent Logs"):
        log_path = Path(LOG_FILE)
        if log_path.exists():
            preview = read_recent_logs()
            if preview:
                st.code(preview)
            else:
                st.write("Log file is empty.")
            st.download_button(
                "Download Logs",
                data=log_path.read_bytes(),
                file_name=log_path.name,
                mime="text/plain",
            )
        else:
            st.write("Log file not found.")
    st.title("🍲 Restaurant Inventory Dashboard")
    st.caption(
        f"Current Overview as of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    st.write(
        "Welcome to your central hub for managing restaurant inventory."
    )  # Added intro line
    st.divider()

    engine = connect_db()
    if not engine:
        st.warning("Database connection failed. Dashboard data cannot be loaded.")
        st.stop()

    # Fetch data for KPIs
    items_df = item_service.get_all_items_with_stock(engine, include_inactive=False)
    suppliers_df = supplier_service.get_all_suppliers(engine, include_inactive=False)

    # --- Optional: Fetch data for Pending Indents KPI ---
    pending_indents_count = 0
    try:
        indents_df = indent_service.get_indents(engine, status_filter=STATUS_SUBMITTED)
        pending_indents_count = len(indents_df)
    except Exception as e:
        st.error(f"Could not fetch pending indents: {e}")  # Fail gracefully
    # --- End Optional ---

    total_active_items = len(items_df)
    total_active_suppliers = len(suppliers_df)

    low_stock_df = pd.DataFrame()
    low_stock_count = 0
    if (
        not items_df.empty
        and "current_stock" in items_df.columns
        and "reorder_point" in items_df.columns
    ):
        try:
            items_df["current_stock_num"] = pd.to_numeric(
                items_df["current_stock"], errors="coerce"
            ).fillna(0)
            items_df["reorder_point_num"] = pd.to_numeric(
                items_df["reorder_point"], errors="coerce"
            ).fillna(0)
            mask = (
                items_df["current_stock_num"].notna()
                & items_df["reorder_point_num"].notna()
                & (items_df["reorder_point_num"] > 0)
                & (items_df["current_stock_num"] <= items_df["reorder_point_num"])
            )
            low_stock_df = items_df.loc[
                mask, ["name", "base_unit", "current_stock", "reorder_point"]
            ].copy()
            low_stock_count = len(low_stock_df)
        except KeyError as e:
            st.error(f"Missing expected column for low-stock calculation: {e}")
        except Exception as e:
            st.error(f"Error calculating low stock items: {e}")

    # Changed st.header to st.subheader
    st.subheader("📊 Key Performance Indicators")

    # Use 4 columns if adding the new KPI, otherwise 3
    kpi_cols = st.columns(
        4 if pending_indents_count is not None else 3
    )  # Adjust number of columns

    kpi_cols[0].metric(
        "📦 Active Items",
        total_active_items,
        help="Total number of unique items currently marked as active.",
    )
    kpi_cols[1].metric(
        "📉 Low Stock Items",
        low_stock_count,
        help="Items at or below their defined reorder point (and reorder point > 0).",
    )
    kpi_cols[2].metric(
        "🚚 Active Suppliers",
        total_active_suppliers,
        help="Total number of suppliers currently marked as active.",
    )
    if pending_indents_count is not None:  # Check if we fetched this data
        kpi_cols[3].metric(
            "📝 Pending Indents",
            pending_indents_count,
            help="Material requests awaiting processing.",
        )

    # Removed the bar chart to avoid Altair warnings and simplify the dashboard

    st.divider()

    # Changed st.header to st.subheader
    st.subheader("⚠️ Low Stock Items Alert")
    if low_stock_count > 0:
        st.dataframe(
            low_stock_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": st.column_config.TextColumn("Item Name"),
                "base_unit": st.column_config.TextColumn(
                    "UoM", width="small", help="Unit of Measure"
                ),
                "current_stock": st.column_config.NumberColumn(
                    "Current Stock", format="%.2f", width="small"
                ),
                "reorder_point": st.column_config.NumberColumn(
                    "Reorder At", format="%.2f", width="small"
                ),
            },
        )
    elif total_active_items > 0:
        st.info("👍 All item stock levels are currently above their reorder points.")
    else:
        st.info("No active items found in the system to assess stock levels.")


if __name__ == "__main__":
    run_dashboard()
