# app/pages/7_Recipes.py
import os
import sys
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Recipes", layout="wide")

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_CUR_DIR, os.pardir, os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app.ui.theme import load_css, render_sidebar_logo
from app.ui.navigation import render_sidebar_nav
from app.ui import show_success, show_error

try:
    from app.db.database_utils import connect_db
    from app.services import recipe_service, item_service
    from app.auth.auth import get_current_user_id
except Exception as e:
    st.error(f"Import error in Recipes page: {e}")
    st.stop()

load_css()
render_sidebar_logo()
render_sidebar_nav()

engine = connect_db()
if engine is None:
    show_error("Database connection failed.")
    st.stop()

st.title("Recipe Management")

# --- Add Recipe ---
with st.expander("➕ Add New Recipe", expanded=False):
    with st.form("add_recipe_form"):
        name = st.text_input("Recipe Name*", key="recipe_name")
        desc = st.text_area("Description", key="recipe_desc")
        items_df = item_service.get_all_items_with_stock(engine)
        item_opts = {
            f"{row['name']} ({row['unit']})": int(row["item_id"]) for _, row in items_df.iterrows()
        }
        selected = st.multiselect("Ingredients", list(item_opts.keys()))
        qty_inputs = {}
        for label in selected:
            iid = item_opts[label]
            qty_inputs[iid] = st.number_input(
                f"Qty of {label}", min_value=0.0, step=0.01, format="%.2f", key=f"qty_{iid}"
            )
        est_cost = recipe_service.calculate_recipe_cost(engine, qty_inputs)
        st.markdown(f"**Estimated Cost:** {est_cost:.2f}")
        submit = st.form_submit_button("Save Recipe")
    if submit:
        ingredients = [
            {"item_id": iid, "quantity": q}
            for iid, q in qty_inputs.items()
            if q > 0
        ]
        if not name.strip() or not ingredients:
            st.warning("Name and at least one ingredient required.")
        else:
            ok, msg, _ = recipe_service.create_recipe(
                engine,
                {"name": name.strip(), "description": desc.strip()},
                ingredients,
            )
            if ok:
                show_success(msg)
            else:
                st.warning(msg)

# --- List and Edit Recipes ---
recipes_df = recipe_service.list_recipes(engine, include_inactive=True)
if recipes_df.empty:
    st.info("No recipes found.")
else:
    st.subheader("Existing Recipes")
    for _, row in recipes_df.iterrows():
        rid = int(row["recipe_id"])
        with st.expander(row["name"], expanded=False):
            st.write(row["description"] or "")
            items = recipe_service.get_recipe_items(engine, rid)
            st.dataframe(items[["item_name", "quantity"]], use_container_width=True)
            if st.button("Edit", key=f"edit_{rid}"):
                st.session_state["edit_recipe_id"] = rid
            if st.session_state.get("edit_recipe_id") == rid:
                with st.form(f"edit_form_{rid}"):
                    new_name = st.text_input("Recipe Name*", value=row["name"], key=f"ename_{rid}")
                    new_desc = st.text_area("Description", value=row["description"] or "", key=f"edesc_{rid}")
                    item_opts_local = item_opts  # from earlier
                    selected_local = st.multiselect(
                        "Ingredients", list(item_opts_local.keys()),
                        default=[k for k, v in item_opts_local.items() if v in items["item_id"].tolist()],
                        key=f"sel_{rid}"
                    )
                    qty_inputs_local = {}
                    for label in selected_local:
                        iid = item_opts_local[label]
                        current_qty = items.loc[items["item_id"] == iid, "quantity"].iloc[0] if iid in items["item_id"].tolist() else 0
                        qty_inputs_local[iid] = st.number_input(
                            f"Qty of {label}", min_value=0.0, step=0.01, format="%.2f", value=float(current_qty), key=f"eqty_{iid}_{rid}"
                        )
                    est_cost_local = recipe_service.calculate_recipe_cost(engine, qty_inputs_local)
                    st.markdown(f"**Estimated Cost:** {est_cost_local:.2f}")
                    save = st.form_submit_button("Update")
                if save:
                    ing = [
                        {"item_id": iid, "quantity": qty}
                        for iid, qty in qty_inputs_local.items() if qty > 0
                    ]
                    ok, msg = recipe_service.update_recipe(
                        engine,
                        rid,
                        {"name": new_name.strip(), "description": new_desc.strip()},
                        ing,
                    )
                    if ok:
                        show_success(msg)
                        st.session_state["edit_recipe_id"] = None
                    else:
                        st.warning(msg)
