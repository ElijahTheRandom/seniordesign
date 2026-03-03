"""
views/sidebar.py
----------------
Renders the PS Analytics sidebar navigation.

WHY THIS FILE EXISTS:
    The sidebar was previously rendered inline in mainpage.py, interleaved
    with session state setup, modal creation, and CSS blocks. Extracting it
    here means:

        - The navigation logic lives in one place
        - mainpage.py calls render_sidebar() — one line, no details
        - The rename flow is self-contained and easy to follow

PUBLIC INTERFACE:
    render_sidebar()   ← the only function mainpage.py needs to call

PRIVATE HELPERS (don't import these directly):
    _render_home_button()
    _render_run_button(run, index)
    _render_rename_form(run)

SESSION STATE USED:
    Read:   active_run_id, analysis_runs, renaming_run_id
    Write:  active_run_id, renaming_run_id, analysis_runs[i]["name"]
"""

from pdb import run

import streamlit as st

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def render_sidebar() -> None:
    """
    Render the full sidebar: top divider, Home button, and the run list.

    Called once from mainpage.py inside a `with st.sidebar:` block.
    Reads from and writes to st.session_state directly.
    """
    with st.sidebar:
        st.markdown("<div style='margin-top: 2.5rem;'></div>", unsafe_allow_html=True)
        st.markdown("<hr class='sidebar-top-divider'>", unsafe_allow_html=True)
        st.header("Page Navigation")

        _render_home_button()
        _render_help_button()
        _render_load_button()

        st.markdown("---")
        st.header("Analysis Runs")

        # Render different UI based on compare mode
        if st.session_state.get("compare_mode_active", False):
            _render_compare_mode()
        else:
            _render_normal_mode()

        st.markdown("---")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _render_normal_mode() -> None:
    """
    Render the sidebar in normal mode: list of runs with a Compare button.

    This is the default mode where runs are displayed as navigation buttons.
    """
    for i, run in enumerate(st.session_state.analysis_runs):
        _render_run_button(run)

    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)

    if len(st.session_state.analysis_runs) < 2 and len(st.session_state.analysis_runs) > 0:
        st.info("At least two runs must be generated before you can compare them.")
    
    # Show Compare button only if there are 2+ runs
    if len(st.session_state.analysis_runs) >= 2:
        if st.button(
            "Compare Runs",
            key="compare_runs_btn",
            use_container_width=True,
            type="secondary"
        ):
            st.session_state.compare_mode_active = True
            st.session_state.selected_runs_for_comparison = []
            st.session_state.show_comparison_view = False
            st.rerun()


def _render_compare_mode() -> None:
    """
    Render the sidebar in compare mode: checkboxes first, then action buttons.
    """

    # --- Checkboxes ---
    for run in st.session_state.analysis_runs:
        is_selected = run["id"] in st.session_state.selected_runs_for_comparison

        new_selected = st.checkbox(
            run["name"],
            value=is_selected,
            key=f"compare_checkbox_{run['id']}"
        )

        if new_selected != is_selected:
            if new_selected:
                st.session_state.selected_runs_for_comparison.append(run["id"])
            else:
                st.session_state.selected_runs_for_comparison.remove(run["id"])
            st.rerun()

    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)

    # --- Side-by-side buttons UNDER checkboxes ---
    compare_col, exit_col = st.columns([1, 1])

    num_selected = len(st.session_state.selected_runs_for_comparison)
    is_enabled = num_selected >= 2

    with exit_col:
        if st.button(
            "Cancel",
            key="exit_compare_mode",
            use_container_width=True,
            type="secondary"
        ):
            st.session_state.compare_mode_active = False
            st.session_state.selected_runs_for_comparison = []
            st.session_state.show_comparison_view = False
            st.rerun()

    with compare_col:
        if st.button(
            f"Compare",
            key="start_comparison_btn",
            use_container_width=True,
            type="primary" if is_enabled else "secondary",
            disabled=not is_enabled
        ):
            st.session_state.show_comparison_view = True
            st.session_state.active_run_id = None
            st.rerun()

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _render_home_button() -> None:

    is_active = st.session_state.get("current_view") == "home"

    if st.button(
        "Home Screen",
        key="nav_home",
        use_container_width=True,
        type="primary" if is_active else "secondary"
    ):
        st.session_state.current_view = "home"
        st.session_state.active_run_id = None
        st.session_state.compare_mode_active = False
        st.session_state.show_comparison_view = False
        st.session_state.show_help_view = False
        st.rerun()


def _render_run_button(run: dict) -> None:
    """
    Render one analysis run entry in the sidebar.

    Each run entry consists of:
        - A clickable button (the run name) that navigates to that run
        - A rename icon (✏️) that opens the inline rename form
        - The rename form itself, shown only when this run is being renamed

    The "primary" vs "secondary" button type visually indicates which
    run is currently active — this mirrors the Home button behavior and
    gives users a consistent "active tab" mental model.

    Args:
        run: A run dict with keys: id, name, table, data, columns,
             rows, methods, visualizations.
    """
    is_active = run["id"] == st.session_state.active_run_id

    # Row: run name button + rename icon, side by side
    cols = st.columns([6, 2])

    with cols[0]:
        if st.button(
            run["name"],
            key=f"nav_run_{run['id']}",
            use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            st.session_state.active_run_id = run["id"]
            st.rerun()

    with cols[1]:
        if st.button(
            "✏️",
            key=f"rename_btn_{run['id']}",
            help="Rename Run"
        ):
            # Toggle: if already renaming this run, cancel; else open form
            if st.session_state.get("renaming_run_id") == run["id"]:
                st.session_state["renaming_run_id"] = None
            else:
                st.session_state["renaming_run_id"] = run["id"]

    # Show inline rename form only for the run currently being renamed
    if st.session_state.get("renaming_run_id") == run["id"]:
        _render_rename_form(run)

def _render_rename_form(run: dict) -> None:
    """
    Render the inline rename form for a single run.

    Shown below the run's nav button when the ✏️ icon has been clicked.
    Provides a text input pre-filled with the current name, and two
    buttons: Save (commits the new name) and Cancel (discards it).

    Empty or whitespace-only names are rejected — the existing name is
    kept instead. This prevents runs with blank labels in the sidebar.

    Args:
        run: The run dict being renamed. Its "name" key is mutated
             in-place on Save.
    """
    new_name = st.text_input(
        "Rename run",
        value=run["name"],
        key=f"rename_input_{run['id']}",
        label_visibility="collapsed"
    )


    save_col, cancel_col = st.columns([1, 1])  # You can tweak ratios here

    with save_col:
        if st.button(
            "Save",
            key=f"save_rename_{run['id']}",
            use_container_width=True,
            type="secondary"  # Make it blend like Home button when inactive
        ):
            run["name"] = new_name.strip() or run["name"]
            st.session_state["renaming_run_id"] = None
            st.rerun()

    with cancel_col:
        if st.button(
            "Cancel",
            key=f"cancel_rename_{run['id']}",
            use_container_width=True,
            type="secondary"  # Same as above
        ):
            st.session_state["renaming_run_id"] = None
            st.rerun()

# Method that will allow the user to load the full data for a previous run by its ID
def _render_load_button() -> None:

    is_active = st.session_state.get("current_view") == "load"

    if st.button(
        "Load Previous Runs",
        key="nav_load",
        use_container_width=True,
        type="primary" if is_active else "secondary"
    ):
        st.session_state.current_view = "load"
        st.session_state.active_run_id = None
        st.session_state.compare_mode_active = False
        st.session_state.show_comparison_view = False
        st.session_state.show_help_view = False
        st.rerun()

# Method that will allow the user to view the help screen
def _render_help_button() -> None:

    is_active = st.session_state.get("current_view") == "help"

    if st.button(
        "Help Screen",
        key="nav_help",
        use_container_width=True,
        type="primary" if is_active else "secondary"
    ):
        st.session_state.current_view = "help"
        st.session_state.active_run_id = None
        st.session_state.compare_mode_active = False
        st.session_state.show_comparison_view = False
        st.session_state.show_help_view = True
        st.rerun()