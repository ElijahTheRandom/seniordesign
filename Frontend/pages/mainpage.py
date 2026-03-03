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
    views/comparison.py    — multi-run comparison view
"""

import os
import sys

import streamlit as st
from streamlit_modal import Modal # we might switch from modal to something else soon but modal = popup

# ---------------------------------------------------------------------------
# Path setup — makes sibling packages importable from any launch directory
# ---------------------------------------------------------------------------

BASE_DIR     = os.path.dirname(__file__) # Absolute path to file directory
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..")) # Root frontend directory (parent)

# Lets Python import sibling modules regardless of where it launches from
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
from views.comparison import render_comparison
from views.help_statistical_methods import render_help_statistical_methods

# ---------------------------------------------------------------------------
# Page config — must be the very first Streamlit call
# ---------------------------------------------------------------------------

# Make sure to keep layout = wide and initial_sidebar_state = collapsed
# These settings keep everything from getting stuck centered and screwing up the layout 
# and keeps the sidebar closed when the user first opens the program
st.set_page_config(
    page_title="PS Analytics",
    page_icon=os.path.join(BASE_DIR, "assets", "PStheMainMan.png"),
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

initialize_session_state() # Makes sure it starts on the main screen and not the last screen the user had pulled up
inject_styles() # Keeps the customized look

# ---------------------------------------------------------------------------
# Modals — created here because mainpage connects both sides:
#   render_homepage calls .open(); mainpage calls .is_open() to render.
#   Must be rendered LAST — streamlit_modal's backdrop covers earlier content.
# ---------------------------------------------------------------------------

error_modal   = Modal("Invalid Analysis", key="error_modal") # When the user does stuff wrong
success_modal = Modal("Success!",         key="success_modal") # When the user has done an applicable calculation

# ---------------------------------------------------------------------------
# Sidebar — present on every page
# ---------------------------------------------------------------------------

render_sidebar() # Fires up the sidebar and all of its functions, buttons, etc.

# ---------------------------------------------------------------------------
# Main content — route to homepage, selected run, or comparison
# ---------------------------------------------------------------------------

# Route based on current state:
#   1. If help view is active → show statistical methods help page
#   2. If comparison view is active → show comparison of selected runs
#   3. If a single run is selected → show its results
#   4. Otherwise → show homepage
if st.session_state.get("current_view") == "help":
    render_help_statistical_methods()
elif st.session_state.get("show_comparison_view", False) and st.session_state.get("selected_runs_for_comparison"):
    render_comparison(st.session_state.selected_runs_for_comparison, BASE_DIR)
elif st.session_state.active_run_id:
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

# Displays warning squirrel and all necessary error info
if error_modal.is_open():
    with error_modal.container():
        render_modal_content(
            os.path.join(BASE_DIR, "assets", "warningSquirrel.PNG"),
            st.session_state.modal_message,
        )

# Displays success squirrel and how to get to your rendered info
if success_modal.is_open():
    with success_modal.container():
        render_modal_content(
            os.path.join(BASE_DIR, "assets", "huzzahAhSquirrel.png"),
            st.session_state.modal_message,
        )
