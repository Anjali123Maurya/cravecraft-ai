"""Chooses the database: the local file normally, a private in-memory
database per visitor in demo mode (so a public demo never mixes users)."""
import streamlit as st

from core.config import get_settings
from db.session import get_store as _file_store
from db.session import make_store


def get_store():
    if get_settings().demo_mode:
        if "demo_store" not in st.session_state:
            st.session_state["demo_store"] = make_store("sqlite://")
        return st.session_state["demo_store"]
    return _file_store()