import math
from pathlib import Path
from typing import List, Tuple, Dict, Any
import streamlit as st
from inventory.services.ui_service import autofill_component_meta as _autofill_component_meta

from ..core.logging import LOG_FILE


def read_recent_logs(limit: int = 100, log_file: str | Path = LOG_FILE) -> str:
    """Return the last ``limit`` lines from the log file.

    Parameters
    ----------
    limit:
        Maximum number of lines to return from the end of the file.
    log_file:
        Path to the log file. Defaults to the application's configured
        ``LOG_FILE``.

    Returns
    -------
    str
        Concatenated string of the last ``limit`` lines. If the file is
        missing or unreadable an empty string is returned.
    """

    path = Path(log_file)
    try:
        with path.open("r", encoding="utf-8") as fh:
            return "".join(fh.readlines()[-limit:])
    except (FileNotFoundError, OSError):
        return ""


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


def autofill_component_meta(rows, choice_map: Dict[str, Dict[str, Any]]):
    """Return rows with unit and category filled from ``choice_map``.

    Accepts either a sequence of row dicts or a pandas ``DataFrame``. A
    ``DataFrame`` is converted to records and reconstructed to avoid a
    hard dependency on pandas in this module.
    """

    if rows is None:
        return rows
    if hasattr(rows, "to_dict") and hasattr(rows.__class__, "__call"):
        records = rows.to_dict("records")
        updated = _autofill_component_meta(records, choice_map)
        return rows.__class__(updated)
    return _autofill_component_meta(rows, choice_map)
