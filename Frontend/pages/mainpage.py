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
from views.sidebar  import render_sidebar
from views.homepage import render_homepage, render_theme_toggle
from views.homepage import poll_background_computation, error_dialog, _show_success_toast
from views.results  import render_results
from views.comparison import render_comparison
from views.help_statistical_methods import render_help_statistical_methods
from views.load_previous_runs import render_load_previous_runs
from PIL import Image
from pathlib import Path

# ---------------------------------------------------------------------------
# Page config — must be the very first Streamlit call
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Make sure to keep layout = wide and initial_sidebar_state = collapsed
# These settings keep everything from getting stuck centered and screwing up the layout 
# and keeps the sidebar closed when the user first opens the program
st.set_page_config(
    page_title="PS Analytics",
    layout="wide",
    page_icon=Image.open(Path(BASE_DIR) / "pages" / "assets" / "PStheMainMan.png"),
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

initialize_session_state() # Makes sure it starts on the main screen and not the last screen the user had pulled up
inject_styles() # Keeps the customized look

# ---------------------------------------------------------------------------
# Sidebar — present on every page
# ---------------------------------------------------------------------------

render_sidebar() # Fires up the sidebar and all of its functions, buttons, etc.

# ---------------------------------------------------------------------------
# Theme Toggle — present on every page
# ---------------------------------------------------------------------------
render_theme_toggle()

# ---------------------------------------------------------------------------
# Background computation polling — runs on every page so the user can
# navigate freely while a calculation is in progress.
# ---------------------------------------------------------------------------
poll_background_computation()

# Success / error dialogs — shown here so they appear regardless of which
# view is active when the computation finishes.
if st.session_state.get("show_success_dialog"):
    _show_success_toast()
    st.session_state.show_success_dialog = False

if st.session_state.get("show_error_dialog"):
    error_dialog()
    st.session_state.show_error_dialog = False

# ---------------------------------------------------------------------------
# Main content — route to homepage, selected run, or comparison
# ---------------------------------------------------------------------------

# Route based on current state:
#   1. If help view is active → show statistical methods help page
#   2. If comparison view is active → show comparison of selected runs
#   3. If a single run is selected → show its results
#   4. If load previous runs view is active → show load previous runs page
#   5. Otherwise → show homepage
if st.session_state.get("current_view") == "help":
    render_help_statistical_methods()
elif st.session_state.get("current_view") == "load":
    render_load_previous_runs()
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
    render_homepage(BASE_DIR)

# ---------------------------------------------------------------------------
# Computation watcher — a fragment that ticks every 500 ms in isolation.
# Only its own tiny subtree rerenders on each tick (nothing visible is
# rendered inside it), so the rest of the page stays completely stable.
# When the future finishes, it fires one clean full-app rerun so that
# poll_background_computation() can process the result and show dialogs.
# ---------------------------------------------------------------------------
@st.fragment(run_every="500ms")
def _computation_watcher():
    if st.session_state.get("_compute_future") is None:
        return
    future = st.session_state.get("_compute_future")
    if future is not None and future.done():
        st.rerun(scope="app")

_computation_watcher()


