"""MemoryNest — Streamlit entry point.

Run with:  streamlit run app/main.py
"""

from __future__ import annotations

import streamlit as st

from app.database.database import init_db
from app.utils import config
from app.utils.auth import login, register


def _auth_gate() -> bool:
    """Show the login/register form. Returns True when a user is logged in."""
    if st.session_state.get("user") is not None:
        return True

    st.title("🧠 MemoryNest")
    st.caption("Your personal knowledge vault — local RAG over your documents.")

    tab_login, tab_register = st.tabs(["Log in", "Register"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in"):
                user, err = login(username, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                st.error(err or "Login failed")

    with tab_register:
        with st.form("register_form"):
            r_username = st.text_input("Username (3-32 chars)")
            r_email = st.text_input("Email (optional, used for reminders)")
            r_password = st.text_input("Password (min 6 chars)", type="password")
            r_confirm = st.text_input("Confirm password", type="password")
            if st.form_submit_button("Create account"):
                if r_password != r_confirm:
                    st.error("Passwords do not match")
                else:
                    user, err = register(r_username, r_password, r_email or None)
                    if user:
                        st.session_state.user = user
                        st.rerun()
                    st.error(err or "Registration failed")

    st.stop()
    return False


def _logout() -> None:
    st.session_state.user = None
    st.rerun()


def main() -> None:
    config.ensure_dirs()
    init_db()
    st.set_page_config(page_title="MemoryNest", page_icon="🧠", layout="wide")

    user = st.session_state.get("user")
    if user is None:
        _auth_gate()
        return

    st.sidebar.title("🧠 MemoryNest")
    st.sidebar.caption(f"Logged in as **{user.username}**")
    if st.sidebar.button("Log out"):
        _logout()

    from app.pages import chat, dashboard, documents, history, reminders, summaries, upload

    pages = st.navigation(
        [
            st.Page(dashboard.render, title="Dashboard", default=True),
            st.Page(upload.render, title="Upload"),
            st.Page(documents.render, title="Documents"),
            st.Page(chat.render, title="Ask (RAG)"),
            st.Page(history.render, title="History"),
            st.Page(summaries.render, title="Summaries"),
            st.Page(reminders.render, title="Reminders"),
        ]
    )
    pages.run()


if __name__ == "__main__":
    main()
