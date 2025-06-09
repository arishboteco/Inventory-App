import streamlit as st


def render_sidebar_nav() -> None:
    """Render sidebar navigation links to all app pages."""
    with st.sidebar:
        st.page_link("item_manager_app.py", label="🏠 Dashboard")
        st.page_link("page_views/1_Items.py", label="Items")
        st.page_link("page_views/2_Suppliers.py", label="Suppliers")
        st.page_link("page_views/3_Stock_Movements.py", label="Stock Movements")
        st.page_link("page_views/4_History_Reports.py", label="History Reports")
        st.page_link("page_views/5_Indents.py", label="Indents")
        st.page_link("page_views/6_Purchase_Orders.py", label="Purchase Orders")
