import streamlit as st


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
            st.text_input("User ID", key="login_user_id")
            if st.button("Login", key="login_button"):
                user = st.session_state.get("login_user_id", "").strip()
                if user:
                    st.session_state.user_id = user
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.warning("Please enter a user ID to login.")
    return False
