import math
from typing import List, Tuple
import streamlit as st


def render_search_toggle(
    search_container,
    toggle_container,
    search_label: str,
    search_key: str,
    toggle_label: str,
    toggle_key: str,
    *,
    placeholder: str = "",
    toggle_help: str | None = "Include inactive records",
) -> None:
    """Render a text search input and an inactive toggle in the provided containers."""
    with search_container:
        st.text_input(search_label, key=search_key, placeholder=placeholder)
    with toggle_container:
        st.toggle(toggle_label, key=toggle_key, help=toggle_help)


def pagination_controls(
    total_items: int,
    *,
    current_page_key: str,
    items_per_page_key: str,
    items_per_page_options: List[int] | None = None,
) -> Tuple[int, int]:
    """Render pagination controls and return slice indices."""
    if items_per_page_options is None:
        items_per_page_options = [5, 10, 20, 50]

    if items_per_page_key not in st.session_state:
        st.session_state[items_per_page_key] = items_per_page_options[0]

    current_ipp = st.session_state.get(items_per_page_key, items_per_page_options[0])
    if current_ipp not in items_per_page_options:
        current_ipp = items_per_page_options[0]
        st.session_state[items_per_page_key] = current_ipp

    st.selectbox(
        "Items per page:",
        options=items_per_page_options,
        index=items_per_page_options.index(current_ipp),
        key=items_per_page_key,
    )

    total_pages = max(math.ceil(total_items / st.session_state[items_per_page_key]), 1)
    current_page = st.session_state.get(current_page_key, 1)
    if current_page > total_pages:
        current_page = total_pages
    if current_page < 1:
        current_page = 1
    st.session_state[current_page_key] = current_page

    cols = st.columns(5)
    if cols[0].button(
        "⏮️ First",
        key=f"{current_page_key}_first_btn",
        disabled=current_page == 1,
    ):
        st.session_state[current_page_key] = 1
        st.rerun()
    if cols[1].button(
        "⬅️ Previous",
        key=f"{current_page_key}_prev_btn",
        disabled=current_page == 1,
    ):
        st.session_state[current_page_key] -= 1
        st.rerun()
    cols[2].write(f"Page {st.session_state[current_page_key]} of {total_pages}")
    if cols[3].button(
        "Next ➡️",
        key=f"{current_page_key}_next_btn",
        disabled=st.session_state[current_page_key] == total_pages,
    ):
        st.session_state[current_page_key] += 1
        st.rerun()
    if cols[4].button(
        "Last ⏭️",
        key=f"{current_page_key}_last_btn",
        disabled=st.session_state[current_page_key] == total_pages,
    ):
        st.session_state[current_page_key] = total_pages
        st.rerun()

    start_idx = (st.session_state[current_page_key] - 1) * st.session_state[items_per_page_key]
    end_idx = start_idx + st.session_state[items_per_page_key]
    return start_idx, end_idx


def show_success(msg: str) -> None:
    """Display a success message using toast if available."""
    if hasattr(st, "toast"):
        st.toast(msg, icon="✅")
    else:
        st.success(msg)


def show_warning(msg: str) -> None:
    """Display a warning message using toast if available."""
    if hasattr(st, "toast"):
        st.toast(msg, icon="⚠️")
    else:
        st.warning(msg)


def show_error(msg: str) -> None:
    """Display an error message using toast if available."""
    if hasattr(st, "toast"):
        st.toast(msg, icon="❌")
    else:
        st.error(msg)
