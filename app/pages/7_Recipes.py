# app/pages/7_Recipes.py
import os
import sys
from typing import List

import pandas as pd
import streamlit as st

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_CUR_DIR, os.pardir, os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app.db.database_utils import connect_db
from app.services import item_service
from app.services import recipe_service
from app.ui.theme import load_css, render_sidebar_logo
from app.ui.navigation import render_sidebar_nav
from app.ui import show_error

st.set_page_config(page_title="Recipes", layout="wide")
load_css()
render_sidebar_logo()
render_sidebar_nav()

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please login from the sidebar")
    st.stop()

db_engine = connect_db()
if not db_engine:
    show_error("Database connection failed. Recipes cannot be loaded.")
    st.stop()

st.title("📖 Recipe Management")

@st.cache_data(ttl=120)
def fetch_items(engine):
    df = item_service.get_all_items_with_stock(engine, include_inactive=False)
    return df if not df.empty else pd.DataFrame()

items_df = fetch_items(db_engine)
item_options = {row["name"]: row["item_id"] for _, row in items_df.iterrows()}

with st.form("new_recipe"):
    st.subheader("Create Recipe")
    name = st.text_input("Recipe Name")
    description = st.text_input("Description")
    ingredient_rows: List[dict] = []
    with st.expander("Ingredients"):
        cols = st.columns(3)
        for i in range(5):
            item = cols[0].selectbox(
                f"Item {i+1}", ["-"] + list(item_options.keys()), key=f"ri_item_{i}"
            )
            qty = cols[1].number_input(
                f"Qty {i+1}", min_value=0.0, step=0.1, key=f"ri_qty_{i}"
            )
            if item != "-":
                ingredient_rows.append({"item_id": item_options[item], "quantity": qty})
    submitted = st.form_submit_button("Add Recipe")
    if submitted:
        ok, msg = recipe_service.create_recipe(
            db_engine,
            {"name": name, "description": description},
            ingredient_rows,
        )
        if ok:
            st.success(msg)
            recipe_service.get_all_recipes.clear()
            st.experimental_rerun()
        else:
            st.error(msg)

st.divider()

recipes_df = recipe_service.get_all_recipes(db_engine, include_inactive=True)
if recipes_df.empty:
    st.info("No recipes found")
else:
    st.subheader("Existing Recipes")
    st.dataframe(recipes_df)
