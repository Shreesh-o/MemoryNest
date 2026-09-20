"""Dashboard — high-level view: counts, upcoming deadlines, recent activity."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    user = st.session_state.user
    st.header("Dashboard")
    st.info("Dashboard coming online — building...")
    st.caption(f"User: {user.username}")
