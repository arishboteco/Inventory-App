from pathlib import Path
import streamlit as st
from .logo import get_logo_bytes

CSS_PATH = Path(__file__).with_name("styles.css")

STATUS_CLASSES = {
    "Completed": "badge-success",
    "Processing": "badge-warning",
    "Cancelled": "badge-error",
}


def load_css():
    if CSS_PATH.exists():
        css = CSS_PATH.read_text()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def format_status_badge(status: str) -> str:
    css_class = STATUS_CLASSES.get(status, "badge-success")
    return f"<span class='{css_class}'>{status}</span>"


def render_sidebar_logo() -> None:
    """Display the logo image in the Streamlit sidebar."""
    st.sidebar.image(get_logo_bytes(), use_column_width=True)

