"""
views/homepage.py
-----------------
Renders the PS Analytics homepage: data input panel (left) and
analysis configuration panel (right).

WHY THIS FILE EXISTS:
    The homepage was previously rendered inline in mainpage.py across
    ~537 lines (lines 1983-2519), with UI layout, state coordination,
    and run creation logic all fused together.

    Extracting it here means:
        - The homepage layout is readable top-to-bottom in one file
        - State coordination (checkbox resets, column tracking) is
          explained and isolated
        - The seam between UI and business logic is explicitly marked
          (see _handle_run_analysis — that's where run_manager will plug
          in during Stage 6)

PUBLIC INTERFACE:
    render_homepage(base_dir, error_modal, success_modal)

PRIVATE HELPERS:
    _render_data_panel(base_dir)          ← left column
    _render_grid(uploaded_file)           ← AG Grid display + selection
    _render_analysis_config(edited_table) ← right column
    _render_computation_options(...)      ← checkboxes
    _render_visualization_options(...)    ← viz checkboxes
    _handle_run_analysis(...)             ← validation + run creation

SESSION STATE READ:
    uploaded_file, saved_table, edited_data_cache,
    selected_columns, selected_rows, last_grid_selection,
    checkbox_key_onecol, checkbox_key_twocol,
    last_cols_selected, last_num_cols

SESSION STATE WRITTEN:
    uploaded_file, has_file, saved_table, edited_data_cache,
    selected_columns, selected_rows, last_grid_selection,
    checkbox_key_onecol, checkbox_key_twocol,
    last_cols_selected, last_num_cols,
    modal_message, analysis_runs, active_run_id
"""

import os
import pprint
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from pathlib import Path
import sys
import pandas as pd
import streamlit as st
from streamlit_aggrid_range import aggrid_range

from utils.helpers import apply_grid_selection_to_filters
from pathlib import Path
from logic.run_manager import (
    validate_numeric,
    build_error_message,
    build_success_message,
)
from class_templates.message_structure import Message
from backend_handler import BackendHandler

if "show_success_dialog" not in st.session_state:
    st.session_state.show_success_dialog = False

if "show_error_dialog" not in st.session_state:
    st.session_state.show_error_dialog = False

@st.dialog("Error")
def error_dialog():
    img_path = Path(__file__).parent.parent / "pages" / "assets" / "warningSquirrel.PNG"

    col_img, col_text = st.columns([1, 1.5], gap="medium")
    with col_img:
        st.image(img_path, width=500)
    with col_text:
        st.markdown(st.session_state.modal_message)

@st.dialog("Success")
def success_dialog():
    img_path = Path(__file__).parent.parent / "pages" / "assets" / "huzzahAhSquirrel.png"

    col_img, col_text = st.columns([1, 1.5], gap="medium")
    with col_img:
        st.image(img_path, width=500)
    with col_text:
        st.markdown(st.session_state.modal_message)

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def render_homepage(base_dir: str, error_modal, success_modal) -> None:
    """
    Render the full homepage: data input (left) + analysis config (right).

    Args:
        base_dir:     Absolute path to the frontend directory. Used to
                      resolve asset paths passed down to child functions.
        error_modal:  streamlit_modal.Modal instance for invalid-data errors.
        success_modal: streamlit_modal.Modal instance for run-created success.
    """

    if st.session_state.get("show_success_dialog"):
        success_dialog()
        st.session_state.show_success_dialog = False

    if st.session_state.get("show_error_dialog"):
        error_dialog()
        st.session_state.show_error_dialog = False

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<hr style='margin: 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )

    left_col, right_col = st.columns([3, 2], gap="medium")

    with left_col:
        edited_table = _render_data_panel(base_dir)

    with right_col:
        _render_analysis_config(edited_table)

_REPO_ROOT = Path(__file__).resolve().parents[2]        # /app/
_BACKEND_ROOT = _REPO_ROOT / "Backend"                  # /app/Backend/
for _p in (str(_REPO_ROOT), str(_BACKEND_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
# ---------------------------------------------------------------------------
# Left column — Data Input Panel
# ---------------------------------------------------------------------------

def _render_data_panel(base_dir: str) -> pd.DataFrame | None:
    """
    Render the data input panel: file uploader, grid, and selection output.

    Handles the full file lifecycle:
        1. No file uploaded yet → show uploader widget
        2. File uploaded → show Remove + Download buttons, then the grid
        3. File removed → clear all related state and rerun

    Returns:
        The currently active DataFrame (either from the uploaded file or
        restored from saved_table), or None if no data is loaded.
    """
    st.header("Data Input & Table", anchor=False)

    # --- File upload / remove flow ---
    if "uploaded_file" not in st.session_state:
        uploaded_file = st.file_uploader(
            "Upload CSV File",
            type="csv",
            key="uploaded_csv"
        )
        if uploaded_file is not None:
            st.session_state.uploaded_file = uploaded_file
            st.session_state.has_file = True
            st.rerun()

        st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    else:
        uploaded_file = st.session_state.uploaded_file
        _render_file_action_buttons(uploaded_file)

    # Sync the local variable with session state (handles post-rerun state)
    uploaded_file = st.session_state.get("uploaded_file")

    # Detect if the user clicked the native Streamlit ✕ on the uploader
    if uploaded_file is None and "uploaded_file" in st.session_state:
        _clear_file_state()
        st.rerun()

    # --- Grid / table display ---
    edited_table = _render_grid(uploaded_file)

    # Persist edits so they survive reruns
    if edited_table is not None:
        st.session_state.saved_table = edited_table.copy()

    return edited_table


def _render_file_action_buttons(uploaded_file) -> None:
    """
    Render the Remove and Download buttons shown after a file is loaded.

    Remove: clears all file-related state and reruns.
    Download: exports the current (possibly edited) table as CSV.

    Args:
        uploaded_file: The UploadedFile object from st.file_uploader.
    """
    file_key = f"{uploaded_file.name}_{uploaded_file.size}"

    # Ensure cache entry exists before trying to read it for download
    if "edited_data_cache" not in st.session_state:
        st.session_state.edited_data_cache = {}

    if file_key not in st.session_state.edited_data_cache:
        uploaded_file.seek(0)
        temp_df = pd.read_csv(uploaded_file)
        st.session_state.edited_data_cache[file_key] = temp_df.copy()

    col_download, col_remove, _ = st.columns([1, 1, 2])

    with col_remove:
        if st.button("Remove", key="remove_file_btn", use_container_width=True):
            _clear_file_state()
            st.rerun()

    with col_download:
        csv_bytes = (
            st.session_state.edited_data_cache[file_key]
            .to_csv(index=False)
            .encode("utf-8")
        )
        st.download_button(
            label="Download",
            data=csv_bytes,
            file_name=f"edited_{uploaded_file.name}",
            mime="text/csv",
            use_container_width=True,
            key="download_edited"
        )

    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)


def _clear_file_state() -> None:
    """
    Reset all file and selection state back to defaults.

    Called when the user clicks Remove or the native uploader ✕ button.
    Increments checkbox key counters so Streamlit re-renders all
    checkboxes in their default unchecked state.

    WHY KEY COUNTERS WORK:
        Streamlit identifies widgets by their `key` argument. When a key
        changes, Streamlit treats it as a brand-new widget and renders it
        with its default value (unchecked). Incrementing the counter
        effectively forces a checkbox reset without needing to track each
        checkbox's individual state.
    """
    for key in ("uploaded_file", "saved_table", "edited_data_cache"):
        st.session_state.pop(key, None)

    st.session_state.has_file = False

    # Keep previously selected values valid if the underlying DataFrame changed
    # (prevents Streamlit from crashing when a column disappears between reruns)
    st.session_state.selected_columns = []
    st.session_state.selected_rows = []
    st.session_state.last_grid_selection = None
    st.session_state.checkbox_key_onecol += 1
    st.session_state.checkbox_key_twocol += 1


def _render_grid(uploaded_file) -> pd.DataFrame | None:
    """
    Render the AG Grid and return the current DataFrame.

    Handles two scenarios:
        A) Fresh file: reads from uploaded_file, caches the result.
        B) Restored state: reads from saved_table (file was removed but
           data persists within the session).

    After rendering, calls apply_grid_selection_to_filters() to sync
    any cell range selection into session state for the right column.

    Args:
        uploaded_file: UploadedFile object, or None.

    Returns:
        The active DataFrame, or None / empty DataFrame if no data.
    """
    if uploaded_file is not None:
        return _render_grid_from_file(uploaded_file)

    elif st.session_state.get("saved_table") is not None:
        return _render_grid_from_cache()

    else:
        st.info("Upload a CSV file to view it in the interactive grid.")
        return pd.DataFrame(columns=["Enter your data..."])


def _render_grid_from_file(uploaded_file) -> pd.DataFrame:
    """
    Load a CSV from the uploaded file, display it in AG Grid, and return
    the DataFrame.

    Uses a file-keyed cache (`edited_data_cache`) so repeated reruns
    don't re-parse the CSV from disk on every interaction.

    Args:
        uploaded_file: Streamlit UploadedFile object.

    Returns:
        The loaded/cached DataFrame.
    """
    try:
        file_key = f"{uploaded_file.name}_{uploaded_file.size}"

        if "edited_data_cache" not in st.session_state:
            st.session_state.edited_data_cache = {}

        if file_key in st.session_state.edited_data_cache:
            df = st.session_state.edited_data_cache[file_key].copy()
        else:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file)
            st.session_state.edited_data_cache[file_key] = df.copy()

        _display_aggrid(df, grid_key=f"grid_{file_key}")

        # Update cache with any edits made in the grid
        st.session_state.edited_data_cache[file_key] = df.copy()
        return df

    except Exception as e:
        st.error(f"Error processing file: {e}")
        return pd.DataFrame(columns=["Enter your data..."])


def _render_grid_from_cache() -> pd.DataFrame:
    """
    Restore the grid from saved_table when no file is actively uploaded.

    This handles the case where the user uploaded a file earlier in the
    session, the page reran, and the UploadedFile object expired —
    but we still have the DataFrame cached.

    Returns:
        The restored DataFrame from session state.
    """
    try:
        df = st.session_state.saved_table.copy()
        _display_aggrid(df, grid_key="grid_cached")
        return df

    except Exception as e:
        st.error(f"Error displaying cached table: {e}")
        return st.session_state.saved_table.copy()


def _display_aggrid(df: pd.DataFrame, grid_key: str) -> None:
    """
    Render the AG Grid Range component and display any selected ranges.

    After rendering the grid, syncs the cell selection into session state
    via apply_grid_selection_to_filters() so the right-column multiselects
    reflect what the user highlighted in the grid.

    Args:
        df:       The DataFrame to display.
        grid_key: A unique key for this grid instance. Must be stable
                  across reruns for the same data to avoid grid flicker.
    """
    records = df.where(pd.notna(df), other=None).to_dict("records")
    columns = [{"field": c} for c in df.columns]

    selection = aggrid_range(records, columns, key=grid_key)
    apply_grid_selection_to_filters(selection, df)

    st.markdown("")
    st.caption("**Tip:** Click and drag to select a range of cells.")

    if selection:
        _display_selection_output(selection, df)
        #st.info("Select computations and visualizations on the right, then click 'Run Analysis' to see results for the selected range.")
    else:
        st.info("Select a range of cells in the grid to see details here.")


def _display_selection_output(selection: list, df: pd.DataFrame) -> None:
    """
    Show the selected cell ranges below the grid.

    For each selected range, renders a labeled dataframe subset. Also
    prints the raw selection metadata to the console for debugging.

    Args:
        selection: Raw list of range dicts from aggrid_range().
        df:        The DataFrame displayed in the grid.
    """
    print("\n--- Selected Ranges ---")
    pprint.pprint(selection)
    print("-----------------------")

    st.markdown("---")
    st.markdown("**Selection Output**")

    with st.expander("Selected Ranges Metadata", expanded=False):
        st.json(selection)

    for idx, rng in enumerate(selection):
        st.write(f"**Range {idx + 1} Selection:**")

        start_row = rng.get("startRow")
        end_row = rng.get("endRow")
        selected_cols = rng.get("columns", [])

        if start_row is None or end_row is None or not selected_cols:
            st.warning("Invalid selection data received.")
            continue

        start, end = int(start_row), int(end_row)
        valid_cols = [c for c in selected_cols if c in df.columns]

        if not valid_cols:
            st.warning("Selected columns not found in current data.")
            continue

        subset = df.iloc[start: end + 1][valid_cols]

        print(f"\n--- Range {idx + 1} Data ---")
        print(subset.to_markdown(index=False, tablefmt="grid"))
        print("----------------------")

        st.dataframe(subset, use_container_width=True)


# ---------------------------------------------------------------------------
# Right column — Analysis Configuration Panel
# ---------------------------------------------------------------------------

def _render_analysis_config(
    edited_table: pd.DataFrame | None
) -> None:
    """
    Render the analysis configuration panel: column/row selection,
    computation checkboxes, visualization checkboxes, and Run Analysis.

    Args:
        edited_table:  The current DataFrame from the left panel, or None.
        error_modal:   Modal to open when non-numeric data is detected.
        success_modal: Modal to open when a run is created successfully.
    """
    st.header("Analysis Configuration", anchor=False)

    data_ready = (
        edited_table is not None
        and len(edited_table.columns) > 0
        and len(edited_table) > 0
    )

    col1, col2 = _render_column_row_selectors(edited_table, data_ready)

    st.markdown("---")

    mean, median, mode, variance, std, percentiles, \
        pearson, spearman, least_squares_regression, chi_squared, binomial, variation = \
        _render_computation_options(data_ready, col1, col2)

    st.markdown("---")

    hist, box, scatter, line, heatmap = _render_visualization_options(
        data_ready, mean, median, mode, variance, std, percentiles,
        pearson, spearman, least_squares_regression, chi_squared, binomial, variation
    )

    st.markdown("---")
    st.markdown('<div class="run-analysis-anchor"></div>', unsafe_allow_html=True)

    computation_selected = any([
        mean, median, mode, variance, std, percentiles,
        pearson, spearman, least_squares_regression, chi_squared, binomial, variation
    ])

    _handle_run_analysis(
        edited_table=edited_table,
        data_ready=data_ready,
        computation_selected=computation_selected,
        col1=col1,
        col2=col2,
        mean=mean, median=median, mode=mode,
        variance=variance, std=std, percentiles=percentiles,
        pearson=pearson, spearman=spearman, least_squares_regression=least_squares_regression,
        chi_squared=chi_squared, binomial=binomial, variation=variation,
        hist=hist, box=box, scatter=scatter, line=line, heatmap=heatmap,
        error_modal=error_modal,
        success_modal=success_modal,
    )


def _render_column_row_selectors(
    edited_table: pd.DataFrame | None,
    data_ready: bool
) -> tuple[list, list]:
    """
    Render the Columns and Rows multiselects and manage checkbox resets.

    Returns:
        (col1, col2): Selected column names and selected 1-based row ints.

    WHY THE RESET LOGIC EXISTS:
        Streamlit checkboxes persist their state across reruns via their
        widget key. When a user selects columns, checks "Pearson", then
        removes all columns, "Pearson" would still appear checked on the
        next interaction even though it's now disabled.

        The fix: increment the key counter when the user clears columns.
        Streamlit sees the new key as a fresh widget and renders it
        unchecked. See _clear_file_state() for the same pattern applied
        to the Remove button.
    """
    col1, col2 = [], []

    if data_ready:
        available_cols = list(edited_table.columns)
        available_rows = list(range(1, len(edited_table) + 1))

        # Keep multiselect values in sync with the current DataFrame
        # (handles case where columns were removed between reruns)
        st.session_state.selected_columns = [
            c for c in st.session_state.selected_columns
            if c in available_cols
        ]
        st.session_state.selected_rows = [
            r for r in st.session_state.selected_rows
            if r in available_rows
        ]

        col1 = st.multiselect("Columns", available_cols, key="selected_columns")
        st.session_state["current_cols"] = col1

        # --- Reset one-column checkboxes when all columns are cleared ---
        if (
            len(st.session_state.get("last_cols_selected", [])) > 0
            and len(col1) == 0
        ):
            st.session_state.checkbox_key_onecol += 1
        st.session_state.last_cols_selected = col1

        
        col2 = st.multiselect("Rows", available_rows, key="selected_rows")

        # --- Reset two-column checkboxes when dropping below 2 columns ---
        # If user drops from >=2 columns to 1 column,
        # reset two-column statistical method checkboxes
        if st.session_state.get("last_num_cols", 0) >= 2 and len(col1) == 1:
            st.session_state.checkbox_key_twocol += 1
        st.session_state.last_num_cols = len(col1)

    else:
        st.multiselect("Columns", [], disabled=True)
        st.multiselect("Rows", [], disabled=True)

    return col1, col2


# ============================================================================
# ⭐ STATISTICAL METHODS SELECTED BY USER
# Return values: mean, median, mode, variance, std_dev, percentiles (one-column)
#                pearson, spearman, regression, chi_square, binomial, variation
# ============================================================================
# The following function renders checkboxes for: Mean, Median, Mode, Variance,
# Standard Deviation, Percentiles, Pearson, Spearman, Regression, Chi-Square,
# Binomial, and Coefficient of Variation. The return values are the method
# selection flags that get passed to _handle_run_analysis.
# ============================================================================

def _render_computation_options(
    data_ready: bool,
    col1: list,
    col2: list
) -> tuple:
    """
    Render the 12 computation checkboxes in two columns.

    Disable rules:
        - All checkboxes: disabled if no data is loaded (data_ready=False)
        - One-column methods: disabled if no column is selected
        - Two-column methods: disabled if fewer than 2 columns are selected

    Returns:
        Tuple of 12 booleans in order:
        (mean, median, mode, variance, std_dev, percentiles,
         pearson, spearman, regression, chi_square, binomial, variation)
    """
    header_col, btn_col = st.columns([4, 2], gap="small")
    with header_col:
        st.header("Computation Options", anchor=False)
    with btn_col:
        st.markdown("<div style='margin-top: 0.55rem;'></div>", unsafe_allow_html=True)
        _user_defined_computation_options()

    disable_one_col = not data_ready or len(col1) < 1
    disable_two_cols = not data_ready or len(col1) < 2

    # If user drops from >=2 columns to 1 column,
    # reset two-column statistical method checkboxes
    k1 = st.session_state.checkbox_key_onecol
    k2 = st.session_state.checkbox_key_twocol

    c1, c2 = st.columns(2)

    with c1:
        mean        = st.checkbox("Mean",                disabled=disable_one_col,  key=f"mean_c1_{k1}")
        median      = st.checkbox("Median",              disabled=disable_one_col,  key=f"median_c1_{k1}")
        mode        = st.checkbox("Mode",                disabled=disable_one_col,  key=f"mode_c1_{k1}")
        variance    = st.checkbox("Variance",            disabled=disable_one_col,  key=f"variance_c1_{k1}")
        std         = st.checkbox("Standard Deviation",  disabled=disable_one_col,  key=f"std_c1_{k1}")
        percentiles = st.checkbox("Percentiles",         disabled=disable_one_col,  key=f"percentiles_c1_{k1}")

    with c2:
        pearson                = st.checkbox("Pearson's Correlation",     disabled=disable_two_cols, key=f"pearson_c2_{k2}")
        spearman               = st.checkbox("Spearman's Rank",           disabled=disable_two_cols, key=f"spearman_c2_{k2}")
        least_squares_regression = st.checkbox("Least Squares Regression",  disabled=disable_two_cols, key=f"least_squares_regression_c2_{k2}")
        chi_squared            = st.checkbox("Chi-Square Test",           disabled=disable_one_col,  key=f"chi_squared_c2_{k1}")
        binomial               = st.checkbox("Binomial Distribution",     disabled=disable_one_col,  key=f"binomial_c2_{k1}")
        variation              = st.checkbox("Coefficient of Variation",  disabled=disable_one_col,  key=f"variation_c2_{k1}")

    return (
        mean, median, mode, variance, std, percentiles,
        pearson, spearman, least_squares_regression, chi_squared, binomial, variation
    )

def _user_defined_computation_options():
    """
    A placeholder function for future user-defined computational methods. The user
    can click an "Add Method" button to open a form where they can input the name of the method,
    a description, and the code to execute. The form data can then be validated and, if valid,
    added to the list of able computations that the user can select for their analysis runs.
    """

    #Place holder button for adding user-defined methods
    new_method_clicked = st.button(
        "New Method",
        key="add_method",
        use_container_width=True
    )

# ============================================================================
# ⭐ VISUALIZATION OPTIONS SELECTED BY USER
# Return values: hist, box, scatter, line, heatmap
# ============================================================================
# The following function renders checkboxes for: Pie Chart, Vertical Bar Chart,
# Horizontal Bar Chart, Scatter Plot, and Line of Best Fit Scatter Plot.
# The return values are the visualization selection flags.
# ============================================================================

def _render_visualization_options(
    data_ready: bool,
    *computation_flags: bool
) -> tuple:
    """
    Render the 5 visualization checkboxes.

    Visualization options are only enabled when at least one computation
    method is selected. If disabled, all viz session state flags are
    forced to False to prevent stale checked state from a prior selection.

    Args:
        data_ready:         Whether a valid DataFrame is loaded.
        *computation_flags: Unpacked boolean values from computation
                            checkboxes (mean, median, ..., variation).

    Returns:
        Tuple of 5 booleans: (hist, box, scatter, line, heatmap)
    """
    st.header("Visualization Options", anchor=False)

    disable_viz = not any(computation_flags)

    # Force-clear viz state when no computation is selected,
    # preventing "ghost" checked boxes from a previous run config
    if disable_viz:
        for key in ("viz_hist", "viz_box", "viz_scatter", "viz_line", "viz_heatmap"):
            st.session_state[key] = False

    v1, v2 = st.columns(2)

    with v1:
        hist    = st.checkbox("Pie Chart",                     key="viz_hist",    disabled=disable_viz)
        box     = st.checkbox("Vertical Bar Chart",            key="viz_box",     disabled=disable_viz)
        scatter = st.checkbox("Horizontal Bar Chart",          key="viz_scatter", disabled=disable_viz)

    with v2:
        line    = st.checkbox("Scatter Plot",                  key="viz_line",    disabled=disable_viz)
        heatmap = st.checkbox("Line of Best Fit Scatter Plot", key="viz_heatmap", disabled=disable_viz)

    return hist, box, scatter, line, heatmap


# ---------------------------------------------------------------------------
# Run creation
# ---------------------------------------------------------------------------

def _handle_run_analysis(
    edited_table: pd.DataFrame,
    data_ready: bool,
    computation_selected: bool,
    col1: list,
    col2: list,
    **method_flags,
) -> None:
    """
    Render the Run Analysis button and handle its click event.

    On click:
        1. Slices the DataFrame to the selected columns/rows (parsedData)
        2. Validates that all values are numeric if numeric methods are
           selected — opens error_modal if not
        3. Creates a run dict and appends it to analysis_runs — opens
           success_modal on success

    NOTE — STAGE 6 SEAM:
        The validation logic (steps 2-3) will move to logic/run_manager.py
        in Stage 6. At that point, this function becomes:

            result = run_manager.create_run(parsed_data, method_flags)
            if result.has_errors:
                st.session_state.modal_message = result.error_message
                error_modal.open()
            else:
                st.session_state.analysis_runs.append(result.run)
                st.session_state.modal_message = result.success_message
                success_modal.open()

        The UI structure of this function (button + disabled logic) stays
        exactly as-is. Only the logic block inside the `if run_clicked:`
        branch moves out.

    Args:
        edited_table:        Full DataFrame currently in the grid.
        data_ready:          Whether the DataFrame has rows and columns.
        computation_selected: Whether at least one computation is checked.
        col1:                Selected column names.
        col2:                Selected 1-based row indices.
        error_modal:         Modal to open on validation failure.
        success_modal:       Modal to open on successful run creation.
        **method_flags:      Boolean values for all computation + viz
                             checkboxes, keyed by name (mean, median, etc.)
    """
    # Unpack method flags
    mean                   = method_flags.get("mean", False)
    median                 = method_flags.get("median", False)
    mode                   = method_flags.get("mode", False)
    variance               = method_flags.get("variance", False)
    std                    = method_flags.get("std", False)
    percentiles            = method_flags.get("percentiles", False)
    pearson                = method_flags.get("pearson", False)
    spearman               = method_flags.get("spearman", False)
    least_squares_regression = method_flags.get("least_squares_regression", False)
    chi_squared            = method_flags.get("chi_squared", False)
    binomial               = method_flags.get("binomial", False)
    variation              = method_flags.get("variation", False)
    hist                   = method_flags.get("hist", False)
    box                    = method_flags.get("box", False)
    scatter                = method_flags.get("scatter", False)
    line                   = method_flags.get("line", False)
    heatmap                = method_flags.get("heatmap", False)

    run_clicked = st.button(
        "Run Analysis",
        key="run_analysis",
        use_container_width=True,
        disabled=not (data_ready and computation_selected)
    )

    if not run_clicked:
        return

    # --- Slice to selected columns and rows ---
    # Convert to 1-based index so row selections align with multiselect values
    edited_table_for_loc = edited_table.copy()
    edited_table_for_loc.index = range(1, len(edited_table_for_loc) + 1)

    # Apply column/row filters depending on what the user selected
    if col1 and col2:
        parsed_data = edited_table_for_loc.loc[col2, col1].copy()
    elif col1:
        parsed_data = edited_table_for_loc[col1].copy()
    elif col2:
        parsed_data = edited_table_for_loc.loc[col2].copy()
    else:
        parsed_data = edited_table_for_loc.copy()

    # ========================================================================
    # ⭐ PACKAGE ANALYSIS DATA: SELECTED COLUMNS, ROWS, METHODS & VISUALIZATIONS
    # Variables:
    #   - col1 (list of selected column names) 
    #   - col2 (list of selected row indices)
    #   - method_flags dict containing all boolean selections
    #   - parsed_data (DataFrame sliced to selected cols/rows)
    # ========================================================================
    # Build method flags dict for run_manager ---
    # Consolidate all computation + visualization flags into one dict
    # for validation and run creation logic
    method_flags = {
        "mean": mean, "median": median, "mode": mode,
        "variance": variance, "std": std, "percentiles": percentiles,
        "pearson": pearson, "spearman": spearman,
        "least_squares_regression": least_squares_regression,
        "chi_squared": chi_squared, "binomial": binomial, "variation": variation,
        "hist": hist, "box": box, "scatter": scatter,
        "line": line, "heatmap": heatmap,
        "viz_hist":    st.session_state.get("viz_hist", False),
        "viz_box":     st.session_state.get("viz_box", False),
        "viz_scatter": st.session_state.get("viz_scatter", False),
        "viz_line":    st.session_state.get("viz_line", False),
        "viz_heatmap": st.session_state.get("viz_heatmap", False),
    }

    # --- Validate numeric data (logic/run_manager.py) ---
    non_numeric_cells = validate_numeric(parsed_data, method_flags)

    if non_numeric_cells:
        st.session_state.modal_message = build_error_message(non_numeric_cells)
        st.session_state.show_error_dialog = True
        st.rerun()
        return

    # --- Build methods list: only flags whose key is a known backend method ID ---
    methods = [
    {"id": flag_name, "params": {}}
        for flag_name, flag_value in method_flags.items()
        if flag_value
    ]

    # --- Construct the Message and dispatch to BackendHandler ---
    selected_cols = list(parsed_data.columns)
    selected_rows = list(parsed_data.index.tolist())
    dataset_id = (
        st.session_state.uploaded_file.name
        if st.session_state.get("uploaded_file")
        else "unknown"
    )

    request = Message(
        dataset_id=dataset_id,
        dataset_version=1,
        metadata={
            "columns": selected_cols,
            "dataset_id": dataset_id,
        },
        selection={
            "cols": selected_cols,
            "rows": [selected_rows],
        },
        methods=methods,
        data=parsed_data.values.tolist(),
    )

    result_message = BackendHandler().handle_request(request)

    run_count = len(st.session_state.analysis_runs) + 1
    run = {
        "id":             f"run_{run_count}",
        "name":           f"Run {run_count}",
        "methods":        methods,         # list of method dicts with id and params
        "result_message": result_message,  # Message object — contains data, methods, results, selection
        "table":          edited_table,    # full unsliced DataFrame for display in results.py
    }

    st.session_state.analysis_runs.append(run)
    st.session_state.modal_message = build_success_message(run)
    st.session_state.show_success_dialog = True
    st.rerun()
    return
