# app/pages/7_Recipes.py
import os
import sys
import streamlit as st
import pandas as pd
import traceback
from typing import Optional

st.set_page_config(page_title="Recipes", layout="wide")

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_CUR_DIR, os.pardir, os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app.ui.theme import load_css, render_sidebar_logo
from app.ui.navigation import render_sidebar_nav
from app.ui import show_success, show_error, show_warning
from app.ui.helpers import autofill_component_meta
from app.ui.choices import build_component_options

try:
    from app.db.database_utils import connect_db
    from app.services import recipe_service, item_service
    from app.core.constants import PLACEHOLDER_SELECT_COMPONENT
except ImportError as e:
    show_error(f"Import error in 7_Recipes.py: {e}.")
    st.stop()
except Exception as e:
    show_error(
        f"An unexpected error occurred during import in 7_Recipes.py: {e}"
    )
    st.stop()

# --- Session State (pg7_ prefix) ---
if "pg7_edit_recipe_id" not in st.session_state:
    st.session_state.pg7_edit_recipe_id = None
if "pg7_clone_recipe_id" not in st.session_state:
    st.session_state.pg7_clone_recipe_id = None


@st.cache_data(ttl=60)
def fetch_items_pg7(_engine):
    return item_service.get_all_items_with_stock(_engine)


@st.cache_data(ttl=60)
def fetch_subrecipes_pg7(_engine):
    return recipe_service.list_recipes(_engine, rtype="SUBRECIPE", include_inactive=False)


@st.cache_data(ttl=60)
def fetch_all_recipes_pg7(_engine):
    return recipe_service.list_recipes(_engine, include_inactive=True)

load_css()
render_sidebar_logo()
render_sidebar_nav()

st.title("🍳 Recipe Management")
st.write(
    "Create, edit, and clone recipes with component breakdowns and standard yields."
)
st.divider()

engine = connect_db()
if not engine:
    show_error("Database connection failed.")
    st.stop()


# helper to display nested components
def render_component_tree(recipe_id: int, indent: int = 0) -> None:
    comps = recipe_service.get_recipe_components(engine, recipe_id)
    for _, comp in comps.iterrows():
        label = f"{' ' * indent}- {comp['component_name']} ({comp['quantity']} {comp['unit'] or ''})"
        st.write(label)
        if comp["component_kind"] == "RECIPE":
            render_component_tree(int(comp["component_id"]), indent + 4)


# --- Add Recipe ---
all_items_df = fetch_items_pg7(engine)
sub_recipes_df = fetch_subrecipes_pg7(engine)

# Build combined options and metadata map
component_options, component_choice_map = build_component_options(
    all_items_df.to_dict("records"),
    sub_recipes_df.to_dict("records"),
    placeholder=PLACEHOLDER_SELECT_COMPONENT,
)
reverse_choice_map = {
    (meta["kind"], meta["id"]): label for label, meta in component_choice_map.items()
}


def sync_component_meta(editor_key: str) -> None:
    """Update session state's dataframe with component defaults."""
    df = st.session_state.get(editor_key)
    if df is None:
        return
    updated = autofill_component_meta(df.copy(), component_choice_map)
    if "category" in updated.columns:
        updated = updated.drop(columns=["category"])
    st.session_state[editor_key] = updated


def build_components(df: pd.DataFrame, current_recipe_id: Optional[int] = None):
    components = []
    errors = []
    seen = set()
    for _, row in df.iterrows():
        label = row.get("component")
        if not label or label == PLACEHOLDER_SELECT_COMPONENT:
            continue
        meta = component_choice_map.get(label)
        if not meta:
            continue
        qty = row.get("quantity")
        if qty is None or float(qty) <= 0:
            errors.append(f"Quantity must be greater than 0 for {label}.")
            continue
        kind = meta["kind"]
        cid = int(meta["id"])
        if current_recipe_id is not None and kind == "RECIPE" and cid == int(current_recipe_id):
            errors.append("Recipe cannot reference itself.")
            continue
        key = (kind, cid)
        if key in seen:
            errors.append(f"Duplicate component {label}.")
            continue
        unit = row.get("unit") or meta.get("unit")
        components.append(
            {
                "component_kind": kind,
                "component_id": cid,
                "quantity": float(qty),
                "unit": unit,
                "loss_pct": 0.0,
                "sort_order": len(components) + 1,
                "notes": row.get("notes") or None,
            }
        )
        seen.add(key)
    if not components:
        errors.append("At least one component is required.")
    return components, errors


with st.expander("➕ Add New Recipe", expanded=False):
    with st.form("pg7_add_recipe_form", clear_on_submit=True):
        st.subheader("Enter New Recipe Details")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Recipe Name*",
                key="pg7_recipe_name",
                help="Unique name for the recipe.",
            )
            rtype = st.text_input(
                "Type",
                key="pg7_recipe_type",
                help="e.g., Starter, Main Course",
            )
            default_yield_qty = st.number_input(
                "Default Yield Quantity",
                min_value=0.0,
                step=0.01,
                key="pg7_recipe_yield_qty",
                help="Standard yield quantity.",
            )
        with col2:
            default_yield_unit = st.text_input(
                "Default Yield Unit",
                key="pg7_recipe_yield_unit",
                help="e.g., kg, servings",
            )
            tags = st.text_input(
                "Tags (comma separated)",
                key="pg7_recipe_tags",
                help="Optional tags for searching.",
            )
        desc = st.text_area(
            "Description",
            key="pg7_recipe_desc",
            help="Optional recipe description.",
        )
        plating_notes = st.text_area(
            "Plating Notes",
            key="pg7_recipe_plating",
            help="Instructions for plating, if any.",
        )
        st.subheader("Components")
        comp_df = pd.DataFrame(
            {
                "component": pd.Series(dtype="str"),
                "quantity": pd.Series(dtype="float"),
                "unit": pd.Series(dtype="str"),
                "notes": pd.Series(dtype="str"),
            }
        )
        sync_component_meta("pg7_add_recipe_editor")
        st.data_editor(
            comp_df,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            column_config={
                "component": st.column_config.SelectboxColumn(
                    "Component",
                    options=component_options,
                    default=PLACEHOLDER_SELECT_COMPONENT,
                ),
                "quantity": st.column_config.NumberColumn(
                    "Qty", min_value=0.0, step=0.01, format="%.2f"
                ),
                "unit": st.column_config.TextColumn("Unit", disabled=True),
                "notes": st.column_config.TextColumn("Notes"),
            },
            key="pg7_add_recipe_editor",
        )
        edited_df = st.session_state["pg7_add_recipe_editor"]

        submit = st.form_submit_button("Save Recipe")

    if submit:
        components, errors = build_components(edited_df)
        if not name.strip():
            errors.append("Recipe name is required.")
        if errors:
            for err in errors:
                show_warning(err)
        else:
            try:
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
            except Exception:
                print(traceback.format_exc())
                show_error("Could not save. See logs.")
            else:
                if ok:
                    show_success(msg)
                    fetch_items_pg7.clear()
                    fetch_subrecipes_pg7.clear()
                    fetch_all_recipes_pg7.clear()
                    for key in [
                        "pg7_recipe_name",
                        "pg7_recipe_type",
                        "pg7_recipe_yield_qty",
                        "pg7_recipe_yield_unit",
                        "pg7_recipe_tags",
                        "pg7_recipe_desc",
                        "pg7_recipe_plating",
                        "pg7_add_recipe_editor",
                    ]:
                        st.session_state.pop(key, None)
                    st.rerun()
                else:
                    show_warning(msg)

st.divider()

# --- List and Edit Recipes ---
recipes_df = fetch_all_recipes_pg7(engine)
if recipes_df.empty:
    st.info("No recipes found.")
else:
    st.subheader("📖 Existing Recipes")
    for _, row in recipes_df.iterrows():
        rid = int(row["recipe_id"])
        with st.expander(row["name"], expanded=False):
            st.write(row["description"] or "")
            render_component_tree(rid)
            if st.button("Edit", key=f"pg7_edit_btn_{rid}"):
                st.session_state.pg7_edit_recipe_id = rid
            if st.session_state.pg7_edit_recipe_id == rid:
                with st.form(f"pg7_edit_form_{rid}"):
                    st.subheader("Edit Recipe Details")
                    col1, col2 = st.columns(2)
                    with col1:
                        new_name = st.text_input(
                            "Recipe Name*", value=row["name"], key=f"pg7_ename_{rid}"
                        )
                        new_type = st.text_input(
                            "Type", value=row.get("type") or "", key=f"pg7_etype_{rid}"
                        )
                        new_yield_qty = st.number_input(
                            "Default Yield Quantity",
                            value=float(row.get("default_yield_qty") or 0),
                            step=0.01,
                            key=f"pg7_eyqty_{rid}",
                        )
                    with col2:
                        new_yield_unit = st.text_input(
                            "Default Yield Unit",
                            value=row.get("default_yield_unit") or "",
                            key=f"pg7_eyunit_{rid}",
                        )
                        new_tags = st.text_input(
                            "Tags", value=row.get("tags") or "", key=f"pg7_etags_{rid}"
                        )
                    new_desc = st.text_area(
                        "Description", value=row["description"] or "", key=f"pg7_edesc_{rid}"
                    )
                    new_plating = st.text_area(
                        "Plating Notes",
                        value=row.get("plating_notes") or "",
                        key=f"pg7_eplating_{rid}",
                    )
                    st.subheader("Components")
                    comps = recipe_service.get_recipe_components(engine, rid)
                    grid_df_local = pd.DataFrame(
                        {
                            "component": [
                                reverse_choice_map.get(
                                    (r.component_kind, int(r.component_id)), None
                                )
                                for _, r in comps.iterrows()
                            ],
                            "quantity": comps["quantity"],
                            "unit": comps["unit"].astype("string"),
                            "notes": comps["notes"].astype("string"),
                        }
                    )
                    options_edit = [
                        label
                        for label in component_options
                        if label not in component_choice_map
                        or not (
                            component_choice_map[label]["kind"] == "RECIPE"
                            and component_choice_map[label]["id"] == rid
                        )
                    ]
                    key_edit = f"pg7_edit_editor_{rid}"
                    sync_component_meta(key_edit)
                    st.data_editor(
                        grid_df_local,
                        num_rows="dynamic",
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "component": st.column_config.SelectboxColumn(
                                "Component",
                                options=options_edit,
                                default=PLACEHOLDER_SELECT_COMPONENT,
                            ),
                            "quantity": st.column_config.NumberColumn(
                                "Qty", min_value=0.0, step=0.01, format="%.2f"
                            ),
                            "unit": st.column_config.TextColumn("Unit", disabled=True),
                            "notes": st.column_config.TextColumn("Notes"),
                        },
                        key=key_edit,
                    )
                    edited_local = st.session_state[key_edit]
                    save = st.form_submit_button("Update")

                if save:
                    components, errors = build_components(edited_local, current_recipe_id=rid)
                    if not new_name.strip():
                        errors.append("Recipe name is required.")
                    if errors:
                        for err in errors:
                            show_warning(err)
                    else:
                        try:
                            ok, msg = recipe_service.update_recipe(
                                engine,
                                rid,
                                {
                                    "name": new_name.strip(),
                                    "description": new_desc.strip(),
                                    "type": new_type.strip() if new_type else None,
                                    "default_yield_qty": new_yield_qty,
                                    "default_yield_unit": new_yield_unit.strip() if new_yield_unit else None,
                                    "plating_notes": new_plating.strip() if new_plating else None,
                                    "tags": new_tags.strip() if new_tags else None,
                                },
                                components,
                            )
                        except Exception:
                            print(traceback.format_exc())
                            show_error("Could not save. See logs.")
                        else:
                            if ok:
                                show_success(msg)
                                st.session_state.pg7_edit_recipe_id = None
                                fetch_items_pg7.clear()
                                fetch_subrecipes_pg7.clear()
                                fetch_all_recipes_pg7.clear()
                                st.rerun()
                            else:
                                show_warning(msg)

            if st.button("Clone", key=f"pg7_clone_btn_{rid}"):
                st.session_state.pg7_clone_recipe_id = rid
            if st.session_state.pg7_clone_recipe_id == rid:
                with st.form(f"pg7_clone_form_{rid}"):
                    st.subheader("Clone Recipe")
                    c_name = st.text_input("New Recipe Name*", key=f"pg7_cname_{rid}")
                    c_desc = st.text_area(
                        "Description", value=row["description"] or "", key=f"pg7_cdesc_{rid}"
                    )
                    render_component_tree(rid)
                    clone_sub = st.form_submit_button("Create Clone")
                if clone_sub:
                    try:
                        ok, msg, _ = recipe_service.clone_recipe(
                            engine, rid, c_name.strip(), c_desc.strip()
                        )
                    except Exception:
                        print(traceback.format_exc())
                        show_error("Could not save. See logs.")
                    else:
                        if ok:
                            show_success(msg)
                            st.toast("Cloned", icon="✅")
                            st.session_state.pg7_clone_recipe_id = None
                            fetch_items_pg7.clear()
                            fetch_subrecipes_pg7.clear()
                            fetch_all_recipes_pg7.clear()
                            st.rerun()
                        else:
                            show_warning(msg)
