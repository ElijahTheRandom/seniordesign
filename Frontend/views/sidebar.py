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
        st.markdown("<hr class='sidebar-top-divider'>", unsafe_allow_html=True)
        st.header("Page Navigation")

        _render_home_button()

        st.markdown("---")
        st.header("Analysis Runs")

        for i, run in enumerate(st.session_state.analysis_runs):
            _render_run_button(run)

        st.markdown("---")
        _load_run_data(st.session_state.active_run_id)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _render_home_button() -> None:
    """
    Render the Home navigation button.

    Styled as "primary" (active/highlighted) when no run is selected,
    "secondary" (muted) when viewing a run. Clicking it sets
    active_run_id to None, returning the user to the homepage.
    """
    is_active = st.session_state.active_run_id is None

    if st.button(
        "Home",
        key="nav_home",
        use_container_width=True,
        type="primary" if is_active else "secondary"
    ):
        st.session_state.active_run_id = None
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
def _load_run_data(run_id: str) -> dict:
    """
    Load the full data for a run by its ID.

    This is a placeholder function. In a real implementation, this would
    likely involve reading from disk or a database, since we don't want
    to keep all run data in memory at all times.

    For now, it just returns the run dict from session state based on ID.
    """
    st.button(
        "Load Previous Runs",
        key=f"load_run_{run_id}",
        use_container_width=True,
        type="secondary"
    )