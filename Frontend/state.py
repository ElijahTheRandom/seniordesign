"""
state.py
--------
Single source of truth for all Streamlit session state used in PS Analytics.

WHY THIS FILE EXISTS:
    Session state was previously initialized as scattered `if "x" not in
    st.session_state` blocks in the middle of mainpage.py. This made it
    impossible to answer the question "what state does this app track?"
    without reading the entire file.

    Now there is one answer: open this file.

USAGE:
    Import and call once at the top of mainpage.py, BEFORE any other
    rendering code:

        from state import initialize_session_state
        initialize_session_state()

NOTE ON setdefault():
    `st.session_state.setdefault("key", value)` is equivalent to:
        if "key" not in st.session_state:
            st.session_state["key"] = value

    It is the idiomatic one-liner for safe initialization — it never
    overwrites a value that was already set in a previous rerun.
"""

import streamlit as st


def initialize_session_state() -> None:
    """
    Initialize all session state keys with their default values.

    This function is idempotent — safe to call on every rerun.
    Existing state values are never overwritten.
    """

    # ------------------------------------------------------------------
    # Navigation & Run Management
    # ------------------------------------------------------------------

    # List of all analysis runs created by the user.
    # Each run is a dict: { id, name, table, data, columns, rows,
    #                        methods, visualizations }
    st.session_state.setdefault("analysis_runs", [])

    # The UUID of the currently active run, or None if on the homepage.
    st.session_state.setdefault("active_run_id", None)

    # The UUID of the run currently being renamed, or None.
    st.session_state.setdefault("renaming_run_id", None)

    # ------------------------------------------------------------------
    # File & Table State
    # ------------------------------------------------------------------

    # Whether a CSV file is currently loaded.
    st.session_state.setdefault("has_file", False)

    # The raw uploaded file object (UploadedFile or None).
    # Intentionally NOT set here — its presence/absence is used as a
    # signal for "has the user uploaded a file this session?"

    # The last-edited DataFrame, persisted so edits survive reruns.
    st.session_state.setdefault("saved_table", None)

    # Cache keyed by "{filename}_{filesize}" → edited DataFrame.
    # Allows multiple files to be swapped without losing edits.
    st.session_state.setdefault("edited_data_cache", {})

    # ------------------------------------------------------------------
    # Grid Selection State
    # ------------------------------------------------------------------

    # List of column names currently selected in the AG Grid.
    st.session_state.setdefault("selected_columns", [])

    # List of 1-based row indices currently selected in the AG Grid.
    st.session_state.setdefault("selected_rows", [])

    # Tuple signature of the last grid selection, used to detect changes
    # and avoid redundant reruns: (tuple[col_names], tuple[row_indices])
    st.session_state.setdefault("last_grid_selection", None)

    # ------------------------------------------------------------------
    # Checkbox Key Counters
    # ------------------------------------------------------------------
    # These integers are appended to checkbox widget keys to force
    # Streamlit to re-render them with unchecked defaults when the
    # user clears their column/row selection.

    # Key suffix for single-column checkboxes (Mean, Median, Mode, etc.)
    st.session_state.setdefault("checkbox_key_onecol", 0)

    # Key suffix for two-column checkboxes (Pearson, Spearman, Regression)
    st.session_state.setdefault("checkbox_key_twocol", 0)

    # ------------------------------------------------------------------
    # Modal / Notification State
    # ------------------------------------------------------------------

    # Message displayed in the error or success modal.
    st.session_state.setdefault("modal_message", "")

    # Legacy boolean flags kept for compatibility with streamlit_modal.
    # The modals are controlled via their .open() / .is_open() API, but
    # these flags can serve as additional guards if needed.
    st.session_state.setdefault("show_invalid_modal", False)
    st.session_state.setdefault("show_success_modal", False)

    # ------------------------------------------------------------------
    # Analysis Configuration Helpers
    # ------------------------------------------------------------------
    # Tracks the previous column count so we can detect when the user
    # drops from 2+ columns to 1 (and reset two-column checkboxes).
    st.session_state.setdefault("last_num_cols", 0)

    # Tracks the previously selected columns so we can detect when the
    # user clears all columns (and reset one-column checkboxes).
    st.session_state.setdefault("last_cols_selected", [])
