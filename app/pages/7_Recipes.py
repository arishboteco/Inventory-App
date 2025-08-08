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

# helper to display nested components
def render_component_tree(recipe_id: int, indent: int = 0) -> None:
    comps = recipe_service.get_recipe_components(engine, recipe_id)
    for _, comp in comps.iterrows():
        label = f"{' ' * indent}- {comp['component_name']} ({comp['quantity']} {comp['unit'] or ''})"
        st.write(label)
        if comp["component_kind"] == "RECIPE":
            render_component_tree(int(comp["component_id"]), indent + 4)

# --- Add Recipe ---
all_items_df = item_service.get_all_items_with_stock(engine)
all_recipes_df = recipe_service.list_recipes(engine, include_inactive=True)

component_options = [
    f"ITEM:{row['item_id']}:{row['name']} ({row['unit']})" for _, row in all_items_df.iterrows()
] + [
    f"RECIPE:{row['recipe_id']}:{row['name']} ({row['default_yield_unit'] or ''})"
    for _, row in all_recipes_df.iterrows()
]

with st.expander("➕ Add New Recipe", expanded=False):
    with st.form("add_recipe_form"):
        name = st.text_input("Recipe Name*", key="recipe_name")
        desc = st.text_area("Description", key="recipe_desc")
        rtype = st.text_input("Type", key="recipe_type")
        default_yield_qty = st.number_input(
            "Default Yield Quantity", min_value=0.0, step=0.01, key="recipe_yield_qty"
        )
        default_yield_unit = st.text_input("Default Yield Unit", key="recipe_yield_unit")
        plating_notes = st.text_area("Plating Notes", key="recipe_plating")
        tags = st.text_input("Tags (comma separated)", key="recipe_tags")

        comp_df = pd.DataFrame(
            {
                "component": pd.Series(dtype="str"),
                "quantity": pd.Series(dtype="float"),
                "unit": pd.Series(dtype="str"),
                "loss_pct": pd.Series(dtype="float"),
                "sort_order": pd.Series(dtype="int"),
                "notes": pd.Series(dtype="str"),
            }
        )
        edited_df = st.data_editor(
            comp_df,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            column_config={
                "component": st.column_config.SelectboxColumn(
                    "Component", options=component_options
                ),
                "quantity": st.column_config.NumberColumn(
                    "Qty", min_value=0.0, step=0.01, format="%.2f"
                ),
                "unit": st.column_config.TextColumn("Unit"),
                "loss_pct": st.column_config.NumberColumn(
                    "Loss %", min_value=0.0, step=0.01, format="%.2f"
                ),
                "sort_order": st.column_config.NumberColumn("Sort"),
                "notes": st.column_config.TextColumn("Notes"),
            },
            key="add_recipe_editor",
        )

        submit = st.form_submit_button("Save Recipe")

    if submit:
        components = []
        for idx, row in edited_df.iterrows():
            comp = row.get("component")
            qty = row.get("quantity")
            if not comp or qty is None or float(qty) <= 0:
                continue
            try:
                kind, cid, _ = comp.split(":", 2)
            except ValueError:
                continue
            components.append(
                {
                    "component_kind": kind,
                    "component_id": int(cid),
                    "quantity": float(qty),
                    "unit": row.get("unit") or None,
                    "loss_pct": float(row.get("loss_pct") or 0),
                    "sort_order": int(row.get("sort_order") or idx + 1),
                    "notes": row.get("notes") or None,
                }
            )
        if not name.strip() or not components:
            st.warning("Name and at least one component required.")
        else:
            ok, msg, _ = recipe_service.create_recipe(
                engine,
                {
                    "name": name.strip(),
                    "description": desc.strip(),
                    "type": rtype.strip() if rtype else None,
                    "default_yield_qty": default_yield_qty,
                    "default_yield_unit": default_yield_unit.strip()
                    if default_yield_unit
                    else None,
                    "plating_notes": plating_notes.strip() if plating_notes else None,
                    "tags": tags.strip() if tags else None,
                },
                components,
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
            render_component_tree(rid)
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
                    new_type = st.text_input(
                        "Type", value=row.get("type") or "", key=f"etype_{rid}"
                    )
                    new_yield_qty = st.number_input(
                        "Default Yield Quantity",
                        value=float(row.get("default_yield_qty") or 0),
                        step=0.01,
                        key=f"eyqty_{rid}",
                    )
                    new_yield_unit = st.text_input(
                        "Default Yield Unit",
                        value=row.get("default_yield_unit") or "",
                        key=f"eyunit_{rid}",
                    )
                    new_plating = st.text_area(
                        "Plating Notes", value=row.get("plating_notes") or "", key=f"eplating_{rid}"
                    )
                    new_tags = st.text_input(
                        "Tags", value=row.get("tags") or "", key=f"etags_{rid}"
                    )

                    comps = recipe_service.get_recipe_components(engine, rid)
                    grid_df_local = pd.DataFrame(
                        {
                            "component": [
                                f"{r.component_kind}:{r.component_id}:{r.component_name}"
                                for _, r in comps.iterrows()
                            ],
                            "quantity": comps["quantity"],
                            "unit": comps["unit"].astype("string"),
                            "loss_pct": comps["loss_pct"],
                            "sort_order": comps["sort_order"],
                            "notes": comps["notes"].astype("string"),
                        }
                    )
                    edited_local = st.data_editor(
                        grid_df_local,
                        num_rows="dynamic",
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "component": st.column_config.SelectboxColumn(
                                "Component", options=component_options
                            ),
                            "quantity": st.column_config.NumberColumn(
                                "Qty", min_value=0.0, step=0.01, format="%.2f"
                            ),
                            "unit": st.column_config.TextColumn("Unit"),
                            "loss_pct": st.column_config.NumberColumn(
                                "Loss %", min_value=0.0, step=0.01, format="%.2f"
                            ),
                            "sort_order": st.column_config.NumberColumn("Sort"),
                            "notes": st.column_config.TextColumn("Notes"),
                        },
                        key=f"edit_editor_{rid}",
                    )

                    save = st.form_submit_button("Update")

                if save:
                    components = []
                    for idx, rowc in edited_local.iterrows():
                        comp = rowc.get("component")
                        qty = rowc.get("quantity")
                        if not comp or qty is None or float(qty) <= 0:
                            continue
                        try:
                            kind, cid, _ = comp.split(":", 2)
                        except ValueError:
                            continue
                        components.append(
                            {
                                "component_kind": kind,
                                "component_id": int(cid),
                                "quantity": float(qty),
                                "unit": rowc.get("unit") or None,
                                "loss_pct": float(rowc.get("loss_pct") or 0),
                                "sort_order": int(rowc.get("sort_order") or idx + 1),
                                "notes": rowc.get("notes") or None,
                            }
                        )
                    ok, msg = recipe_service.update_recipe(
                        engine,
                        rid,
                        {
                            "name": new_name.strip(),
                            "description": new_desc.strip(),
                            "type": new_type.strip() if new_type else None,
                            "default_yield_qty": new_yield_qty,
                            "default_yield_unit": new_yield_unit.strip()
                            if new_yield_unit
                            else None,
                            "plating_notes": new_plating.strip() if new_plating else None,
                            "tags": new_tags.strip() if new_tags else None,
                        },
                        components,
                    )
                    if ok:
                        show_success(msg)
                        st.session_state["edit_recipe_id"] = None
                    else:
                        st.warning(msg)

            if st.button("Clone", key=f"clone_{rid}"):
                st.session_state["clone_recipe_id"] = rid
            if st.session_state.get("clone_recipe_id") == rid:
                with st.form(f"clone_form_{rid}"):
                    c_name = st.text_input("New Recipe Name*", key=f"cname_{rid}")
                    c_desc = st.text_area(
                        "Description", value=row["description"] or "", key=f"cdesc_{rid}"
                    )
                    render_component_tree(rid)
                    clone_sub = st.form_submit_button("Create Clone")
                if clone_sub:
                    ok, msg, _ = recipe_service.clone_recipe(
                        engine, rid, c_name.strip(), c_desc.strip()
                    )
                    if ok:
                        show_success(msg)
                        st.session_state["clone_recipe_id"] = None
                    else:
                        st.warning(msg)
