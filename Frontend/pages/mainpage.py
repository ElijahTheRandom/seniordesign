"""
mainpage.py  —  PS Analytics main page.

Wires the application together. All behaviour lives in:
    state.py               — session state defaults
    styles/theme.py        — CSS injection
    utils/helpers.py       — shared utilities
    logic/run_manager.py   — run creation and validation
    views/sidebar.py       — sidebar navigation
    views/homepage.py      — data input and analysis config
    views/results.py       — analysis results display
"""

import os
import sys

import streamlit as st
from streamlit_modal import Modal

# ---------------------------------------------------------------------------
# Path setup — makes sibling packages importable from any launch directory
# ---------------------------------------------------------------------------

BASE_DIR     = os.path.dirname(__file__)
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

# ---------------------------------------------------------------------------
# Imports (after path setup)
# ---------------------------------------------------------------------------

from state          import initialize_session_state
from styles.theme   import inject_styles
from utils.helpers  import render_modal_content
from views.sidebar  import render_sidebar
from views.homepage import render_homepage
from views.results  import render_results

# ---------------------------------------------------------------------------
# Page config — must be the very first Streamlit call
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="PS Analytics",
    page_icon=os.path.join(BASE_DIR, "assets", "PStheMainMan.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

initialize_session_state()
inject_styles()

# ---------------------------------------------------------------------------
# Modals — created here because mainpage connects both sides:
#   render_homepage calls .open(); mainpage calls .is_open() to render.
#   Must be rendered LAST — streamlit_modal's backdrop covers earlier content.
# ---------------------------------------------------------------------------

error_modal   = Modal("Invalid Analysis", key="error_modal")
success_modal = Modal("Success!",         key="success_modal")

# ---------------------------------------------------------------------------
# Sidebar — present on every page
# ---------------------------------------------------------------------------

render_sidebar()

# ---------------------------------------------------------------------------
# Main content — route to homepage or selected run
# ---------------------------------------------------------------------------

if st.session_state.active_run_id:
    run = next(
        (r for r in st.session_state.analysis_runs
         if r["id"] == st.session_state.active_run_id),
        None,
    )
    if run:
        render_results(run, BASE_DIR)
else:
    render_homepage(BASE_DIR, error_modal, success_modal)

# ---------------------------------------------------------------------------
# Modals (rendered last)
# ---------------------------------------------------------------------------

if error_modal.is_open():
    with error_modal.container():
        render_modal_content(
            os.path.join(BASE_DIR, "assets", "warningSquirrel.PNG"),
            st.session_state.modal_message,
        )

if success_modal.is_open():
    with success_modal.container():
        render_modal_content(
            os.path.join(BASE_DIR, "assets", "huzzahAhSquirrel.png"),
            st.session_state.modal_message,
        )
