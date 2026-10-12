"""MemoryNest — Streamlit entry point.

Run with:  streamlit run app/main.py
"""

from __future__ import annotations

import logging
import os
import sys

# Ensure project root is on sys.path so 'app' imports work when Streamlit runs from app/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging once
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

import streamlit as st

from app.database.database import init_db
from app.services import llm_service
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
    if llm_service.is_mock_mode():
        st.sidebar.warning("Mock LLM mode: answers are not real")
    if st.sidebar.button("Log out"):
        _logout()

    from app.pages import chat, dashboard, documents, history, reminders, summaries, upload

    pages = st.navigation(
    [
        st.Page(dashboard.render, title="Dashboard", url_path="dashboard", default=True),
        st.Page(upload.render, title="Upload", url_path="upload"),
        st.Page(documents.render, title="Documents", url_path="documents"),
        st.Page(chat.render, title="Ask (RAG)", url_path="chat"),
        st.Page(history.render, title="History", url_path="history"),
        st.Page(summaries.render, title="Summaries", url_path="summaries"),
        st.Page(reminders.render, title="Reminders", url_path="reminders"),
    ]
)
    pages.run()


if __name__ == "__main__":
    main()
