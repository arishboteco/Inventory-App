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
    """Render the logo image in the Streamlit sidebar."""
    logo_bytes = get_logo_bytes()
    # Explicit width keeps the logo from filling the entire sidebar
    st.sidebar.image(logo_bytes, width=120)
