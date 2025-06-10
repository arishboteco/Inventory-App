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
all_items_df = item_service.get_all_items_with_stock(engine)

with st.expander("➕ Add New Recipe", expanded=False):
    with st.form("add_recipe_form"):
        name = st.text_input("Recipe Name*", key="recipe_name")
        desc = st.text_area("Description", key="recipe_desc")

        grid_df = pd.DataFrame({
            "item_id": all_items_df["item_id"].astype(int),
            "Item": all_items_df["name"] + " (" + all_items_df["unit"] + ")",
            "Quantity": 0.0,
        })

        edited_df = st.data_editor(
            grid_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "item_id": st.column_config.NumberColumn("ID", disabled=True),
                "Item": st.column_config.TextColumn("Item", disabled=True),
                "Quantity": st.column_config.NumberColumn(
                    "Qty", min_value=0.0, step=0.01, format="%.2f"
                ),
            },
            key="add_recipe_editor",
        )

        submit = st.form_submit_button("Save Recipe")

    if submit:
        ingredients = [
            {"item_id": int(row["item_id"]), "quantity": float(row["Quantity"])}
            for _, row in edited_df.iterrows()
            if row["Quantity"] > 0
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
                    new_name = st.text_input(
                        "Recipe Name*", value=row["name"], key=f"ename_{rid}"
                    )
                    new_desc = st.text_area(
                        "Description", value=row["description"] or "", key=f"edesc_{rid}"
                    )

                    grid_df_local = pd.DataFrame({
                        "item_id": all_items_df["item_id"].astype(int),
                        "Item": all_items_df["name"] + " (" + all_items_df["unit"] + ")",
                    })
                    grid_df_local["Quantity"] = [
                        items.loc[items["item_id"] == iid, "quantity"].iloc[0]
                        if iid in items["item_id"].tolist()
                        else 0.0
                        for iid in all_items_df["item_id"]
                    ]

                    edited_local = st.data_editor(
                        grid_df_local,
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "item_id": st.column_config.NumberColumn("ID", disabled=True),
                            "Item": st.column_config.TextColumn("Item", disabled=True),
                            "Quantity": st.column_config.NumberColumn(
                                "Qty", min_value=0.0, step=0.01, format="%.2f"
                            ),
                        },
                        key=f"edit_editor_{rid}",
                    )

                    save = st.form_submit_button("Update")

                if save:
                    ing = [
                        {"item_id": int(row["item_id"]), "quantity": float(row["Quantity"])}
                        for _, row in edited_local.iterrows()
                        if row["Quantity"] > 0
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
