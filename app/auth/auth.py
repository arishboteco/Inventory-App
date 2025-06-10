import streamlit as st

from app.db.database_utils import connect_db
from app.auth.user_auth import verify_login


def get_current_user_id(default: str = "System") -> str:
    """Return the current logged in user ID from session state."""
    return st.session_state.get("user_id", default)


def login_sidebar() -> bool:
    """Render login form in the sidebar and manage session state.

    Returns True if the user is logged in, False otherwise.
    """
    if st.session_state.get("logged_in"):
        with st.sidebar:
            st.markdown(f"**Logged in as:** {st.session_state['user_id']}")
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user_id = ""
                st.rerun()
        return True

    with st.sidebar:
        # Wrap the login inputs in an expander to minimize sidebar height when
        # the user is not logged in.
        with st.expander("Login"):
            st.text_input("Username", key="login_user")
            st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", key="login_button"):
                username = st.session_state.get("login_user", "").strip()
                password = st.session_state.get("login_pass", "")
                if not username or not password:
                    st.warning("Enter username and password")
                else:
                    engine = connect_db()
                    if engine:
                        ok, role = verify_login(engine, username, password)
                        if ok:
                            st.session_state.user_id = username
                            st.session_state.user_role = role
                            st.session_state.logged_in = True
                            st.rerun()
                        else:
                            st.error("Invalid credentials")
                    else:
                        st.error("Database connection failed")
    return False
