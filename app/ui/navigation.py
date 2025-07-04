import streamlit as st


def render_sidebar_nav() -> None:
    """Render sidebar navigation links to all app pages."""
    with st.sidebar:
        st.page_link("item_manager_app.py", label="🏠 Dashboard")
        st.page_link("pages/1_Items.py", label="Items")
        st.page_link("pages/2_Suppliers.py", label="Suppliers")
        st.page_link("pages/3_Stock_Movements.py", label="Stock Movements")
        st.page_link("pages/4_History_Reports.py", label="History Reports")
        st.page_link("pages/5_Indents.py", label="Indents")
        st.page_link("pages/6_Purchase_Orders.py", label="Purchase Orders")
        st.page_link("pages/7_Recipes.py", label="Recipes")
