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
    render_homepage(base_dir)

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

import base64
import io
import os
import sys
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import streamlit as st
from streamlit_aggrid_range import aggrid_range

from utils.helpers import apply_grid_selection_to_filters, normalize_grid_selection
from logic.run_manager import (
    validate_numeric,
    build_error_message,
    build_success_message,
    VIZ_NAMES,
    METHOD_NAMES,
)
from class_templates.message_structure import Message
from backend_handler import BackendHandler
from frontend_handler import handle_result
from custom_methods_loader import (
    load_custom_methods_registry,
    get_custom_display_names,
    get_custom_input_types,
    get_user_code,
    validate_user_code,
    save_custom_method,
    update_custom_method,
    delete_custom_method,
    get_available_tools_info,
    detect_dependency_cycles,
)


@st.cache_resource
def _get_backend_handler():
    return BackendHandler()

@st.cache_resource
def _get_executor():
    """Single-thread pool for background computation."""
    return ThreadPoolExecutor(max_workers=1)


_GIF_PATH = Path(__file__).parent.parent / "pages" / "assets" / "ThinkingAhSquirrel.GIF"


def _show_loading_gif(caption: str = "Loading\u2026") -> None:
    """Display the loading GIF centered on the page using base64 embedding."""
    with open(_GIF_PATH, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""
        <div style="display:flex; flex-direction:column; align-items:center; margin-top:4rem;">
            <img src="data:image/gif;base64,{b64}" style="max-width:420px; width:100%;" />
            <p style="color:#888; margin-top:1rem; font-size:1rem;">{caption}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


class _ValidationError(Exception):
    """Raised inside the background analysis job when data fails validation."""


def _background_run(
    parsed_data: pd.DataFrame,
    method_flags: dict,
    methods: list,
    graphics: list,
    dataset_id: str,
    selected_cols: list,
    selected_rows: list,
    handle_request,
):
    """
    Background job: validate → serialize → run backend.
    Raises _ValidationError on bad data so the UI can show the error dialog.
    """
    non_numeric_cells = validate_numeric(parsed_data, method_flags)
    if non_numeric_cells:
        raise _ValidationError(build_error_message(non_numeric_cells))

    request = Message(
        dataset_id=dataset_id,
        dataset_version=1,
        metadata={"columns": selected_cols, "dataset_id": dataset_id},
        selection={"cols": selected_cols, "rows": [selected_rows]},
        methods=methods,
        graphics=graphics,
        data=[parsed_data[col].tolist() for col in parsed_data.columns],
    )
    return handle_request(request)


if "show_success_dialog" not in st.session_state:
    st.session_state.show_success_dialog = False

if "show_error_dialog" not in st.session_state:
    st.session_state.show_error_dialog = False

@st.dialog("Please Wait")
def _loading_dialog() -> None:
    """Loading popup with animated GIF. Re-opens itself via st.rerun() until the
    loading flag is cleared — giving a persistent dialog effect."""
    caption = st.session_state.get("_loading_caption", "Loading\u2026")
    with open(_GIF_PATH, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    col_img, col_text = st.columns([1, 1.5], gap="medium")
    with col_img:
        st.markdown(
            f'<img src="data:image/gif;base64,{b64}" style="width:100%; border-radius:8px;" />',
            unsafe_allow_html=True,
        )
    with col_text:
        st.markdown(f"**{caption}**")
    time.sleep(0.3)
    st.rerun()


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

def render_homepage(base_dir: str) -> None:
    """
    Render the full homepage: data input (left) + analysis config (right).

    Args:
        base_dir: Absolute path to the frontend directory. Used to
                  resolve asset paths passed down to child functions.
    """

    # ------------------------------------------------------------------
    # CSV loading: poll for completion
    # ------------------------------------------------------------------
    if st.session_state.get("_csv_loading"):
        csv_future = st.session_state.get("_csv_future")
        if csv_future is None:
            # Read bytes in main thread (UploadedFile is not thread-safe),
            # then parse in background so the dialog actually renders first.
            uf = st.session_state.get("uploaded_file")
            try:
                uf.seek(0)
                raw = uf.read()
            except Exception as exc:
                st.session_state.modal_message = f"Failed to read file: {exc}"
                st.session_state.show_error_dialog = True
                st.session_state._csv_loading = False
                st.rerun()
                return
            st.session_state._csv_future = _get_executor().submit(
                lambda data: pd.read_csv(io.BytesIO(data)), raw
            )
        elif csv_future.done():
            try:
                df = csv_future.result()
                uf = st.session_state.uploaded_file
                file_key = f"{uf.name}_{uf.size}"
                if "edited_data_cache" not in st.session_state:
                    st.session_state.edited_data_cache = {}
                st.session_state.edited_data_cache[file_key] = df
            except Exception as exc:
                st.session_state.modal_message = f"Failed to parse CSV: {exc}"
                st.session_state.show_error_dialog = True
            st.session_state._csv_loading = False
            st.session_state._csv_future = None
            st.rerun()
            return
        # Still loading (or just kicked off) — open the loading dialog.
        # _loading_dialog() calls st.rerun() internally, keeping the loop going.
        st.session_state._loading_caption = "Loading CSV data\u2026"
        _loading_dialog()

    # ------------------------------------------------------------------
    # Background computation: poll for completion
    # ------------------------------------------------------------------
    future = st.session_state.get("_compute_future")
    if future is not None:
        if future.done():
            # Computation finished — collect the result and build the run
            meta = st.session_state._compute_meta
            try:
                result_message = future.result()
            except _ValidationError as ve:
                # Validation failed — show error and reset
                st.session_state._compute_future = None
                st.session_state._compute_meta = None
                st.session_state.modal_message = str(ve)
                st.session_state.show_error_dialog = True
                st.rerun()
                return
            except Exception as exc:
                # Computation failed — surface the error and reset
                st.session_state._compute_future = None
                st.session_state._compute_meta = None
                st.session_state.modal_message = f"Computation failed: {exc}"
                st.session_state.show_error_dialog = True
                st.rerun()
                return

            run = {
                "id":             meta["run_id"],
                "name":           meta["run_name"],
                "methods":        meta["methods"],
                "visualizations": meta.get("visualizations", []),
                "result_message": result_message,
                "table":          meta["table"],
                "data":           meta["data"],
                "columns":        meta.get("columns", []),
                "rows":           meta.get("rows", []),
            }
            handle_result(run)

            st.session_state.analysis_runs.append(run)
            st.session_state.modal_message = build_success_message(run)
            st.session_state.show_success_dialog = True
            st.session_state._compute_future = None
            st.session_state._compute_meta = None
            st.rerun()
            return
        else:
            # Still computing — open the loading dialog.
            # _loading_dialog() calls st.rerun() internally, keeping the loop going.
            st.session_state._loading_caption = "Running analysis\u2026 this won't take long."
            _loading_dialog()

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
            st.session_state._csv_loading = True
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
        st.session_state.saved_table = edited_table

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
        st.session_state.edited_data_cache[file_key] = temp_df

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
    for key in ("uploaded_file", "saved_table", "edited_data_cache",
                 "_csv_loading", "_csv_future"):
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
            df = st.session_state.edited_data_cache[file_key]
        else:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file)
            st.session_state.edited_data_cache[file_key] = df

        df = _display_aggrid(df, grid_key=f"grid_{file_key}")
        st.session_state.edited_data_cache[file_key] = df
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
        df = st.session_state.saved_table
        df = _display_aggrid(df, grid_key="grid_cached")
        return df

    except Exception as e:
        st.error(f"Error displaying cached table: {e}")
        return st.session_state.saved_table


def _display_aggrid(df: pd.DataFrame, grid_key: str) -> pd.DataFrame:
    """
    Render the AG Grid Range component and return the (possibly edited) DataFrame.

    After rendering the grid, syncs the cell selection into session state
    via apply_grid_selection_to_filters() so the right-column multiselects
    reflect what the user highlighted in the grid.

    If the user edited any cells, the returned DataFrame contains the
    updated values.

    Args:
        df:       The DataFrame to display.
        grid_key: A unique key for this grid instance. Must be stable
                  across reruns for the same data to avoid grid flicker.

    Returns:
        The DataFrame, updated with any cell edits.
    """
    records = df.where(pd.notna(df), other=None).to_dict("records")
    columns = [{"field": c} for c in df.columns]

    result = aggrid_range(records, columns, key=grid_key)

    # The component returns {"selections": [...], "editedData": [...] | null}
    if isinstance(result, dict):
        selection = result.get("selections", [])
        edited_data = result.get("editedData")
    else:
        # Fallback for old format (list of ranges)
        selection = result
        edited_data = None

    # Apply cell edits back to the DataFrame
    if edited_data is not None:
        df = pd.DataFrame(edited_data, columns=df.columns)

    apply_grid_selection_to_filters(selection, df)

    st.markdown("")
    st.caption("**Tip:** Click and drag to select a range of cells. "
               "Double-click a cell to edit its value.")

    if selection:
        _display_selection_output(selection, df)
    else:
        st.info("Select a range of cells in the grid to see details here.")

    return df


def _col_letter(n: int) -> str:
    """Convert a 0-based column index to an Excel-style letter (A, B, …, Z, AA, …)."""
    result = ""
    while True:
        result = chr(ord("A") + n % 26) + result
        n = n // 26 - 1
        if n < 0:
            break
    return result


def _display_selection_output(selection: list, df: pd.DataFrame) -> None:
    """
    Show selected ranges Excel-style: a reference bar + per-range labeled tables.
    """
    st.markdown("---")

    col_positions = {name: i for i, name in enumerate(df.columns)}

    # Build structured info for every valid range
    ranges_info = []
    for rng in selection:
        start = rng.get("startRow")
        end   = rng.get("endRow")
        cols  = rng.get("columns", [])
        if start is None or end is None or not cols:
            continue
        start, end = int(start), int(end)
        if start > end:
            start, end = end, start
        valid_cols = [c for c in cols if c in df.columns]
        if not valid_cols:
            continue
        rows_0 = list(range(start, end + 1))
        rows_1 = [r + 1 for r in rows_0]
        subset = df.iloc[rows_0][valid_cols].copy()
        subset.index = rows_1

        # Build per-column cell references: A1:A7
        refs = []
        for col in valid_cols:
            letter = _col_letter(col_positions.get(col, 0))
            r0, r1 = rows_1[0], rows_1[-1]
            refs.append(f"{letter}{r0}:{letter}{r1}" if r0 != r1 else f"{letter}{r0}")

        ranges_info.append({
            "cols":   valid_cols,
            "rows_1": rows_1,
            "subset": subset,
            "refs":   refs,
        })

    if not ranges_info:
        st.info("No valid cells in the current selection.")
        return

    # ── Reference bar (Excel Name Box style) ─────────────────────────────
    all_refs = ",  ".join(r for ri in ranges_info for r in ri["refs"])
    total_cells = sum(len(ri["rows_1"]) * len(ri["cols"]) for ri in ranges_info)
    range_word  = "range" if len(ranges_info) == 1 else "ranges"

    st.markdown(
        f"""
        <div style="
            display: flex; align-items: center; gap: 0.75rem;
            background: #1e1e1e; border: 1px solid #444;
            border-radius: 6px; padding: 0.4rem 0.8rem; margin-bottom: 0.6rem;
        ">
            <span style="
                background: #2d2d2d; border: 1px solid #555;
                border-radius: 4px; padding: 0.15rem 0.5rem;
                font-family: monospace; font-size: 0.82rem; color: #e4781d;
                white-space: nowrap;
            ">{all_refs}</span>
            <span style="color: #888; font-size: 0.8rem;">
                {total_cells} cell{'s' if total_cells != 1 else ''}
                &nbsp;·&nbsp; {len(ranges_info)} {range_word}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Per-range labeled tables ──────────────────────────────────────────
    for i, ri in enumerate(ranges_info):
        ref_str  = ",  ".join(ri["refs"])
        col_str  = ", ".join(ri["cols"])
        row_str  = (
            f"rows {ri['rows_1'][0]}–{ri['rows_1'][-1]}"
            if len(ri["rows_1"]) > 1
            else f"row {ri['rows_1'][0]}"
        )
        label = (
            f"**Range {i + 1}** &nbsp; `{ref_str}` &nbsp; "
            f"<span style='color:#888;font-size:0.82rem;'>{col_str} · {row_str} · "
            f"{len(ri['rows_1'])} × {len(ri['cols'])}</span>"
        )
        st.markdown(label, unsafe_allow_html=True)
        st.dataframe(ri["subset"], use_container_width=True)

    with st.expander("Raw selection metadata", expanded=False):
        st.json(selection)


# ---------------------------------------------------------------------------
# Right column — Analysis Configuration Panel
# ---------------------------------------------------------------------------

def _render_analysis_config(
    edited_table: pd.DataFrame | None,
    error_modal=None,
    success_modal=None,
) -> None:
    """
    Render the analysis configuration panel: column/row selection,
    computation checkboxes, visualization checkboxes, and Run Analysis.

    Args:
        edited_table:  The current DataFrame from the left panel, or None.
        **method_flags: Boolean values for all computation + viz checkboxes, keyed by name.
    """
    st.header("Analysis Configuration", anchor=False)

    data_ready = (
        edited_table is not None
        and len(edited_table.columns) > 0
        and len(edited_table) > 0
    )

    col1, col2 = _render_column_row_selectors(edited_table, data_ready)

    # --- Compute data characteristics for smart checkbox disabling ---
    data_info = _compute_data_info(edited_table, col1, col2, data_ready)

    st.markdown("---")

    mean, median, mode, variance, std, percentiles, \
        pearson, spearman, least_squares_regression, chi_squared, binomial, variation, \
        custom_flags = \
        _render_computation_options(data_ready, col1, col2, data_info)

    st.markdown("---")

    hist, box, scatter, line, heatmap = _render_visualization_options(data_ready)

    st.markdown('---')
    st.markdown('<div class="run-analysis-anchor"></div>', unsafe_allow_html=True)

    computation_selected = any([
        mean, median, mode, variance, std, percentiles,
        pearson, spearman, least_squares_regression, chi_squared, binomial, variation,
        hist, box, scatter, line, heatmap,
    ] + list(custom_flags.values()))

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
        custom_flags=custom_flags,
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

        # --- Count how many selected columns are numeric ---
        num_numeric = 0
        for c in col1:
            coerced = pd.to_numeric(edited_table[c], errors="coerce")
            if coerced.notna().all() and len(coerced) > 0:
                num_numeric += 1

        # --- Reset one-col checkboxes when losing all numeric columns ---
        prev_num = st.session_state.get("_last_num_numeric", 0)
        if prev_num > 0 and num_numeric == 0 and len(col1) > 0:
            st.session_state.checkbox_key_onecol += 1
        st.session_state["_last_num_numeric"] = num_numeric

        col2 = st.multiselect("Rows", available_rows, key="selected_rows")

        # --- Reset two-column checkboxes when dropping below 2 columns ---
        # If user drops from >=2 columns to 1 column,
        # reset two-column statistical method checkboxes
        if st.session_state.get("last_num_cols", 0) >= 2 and len(col1) == 1:
            st.session_state.checkbox_key_twocol += 1
        # Also reset two-col checkboxes when numeric columns drop below 2
        if prev_num >= 2 and num_numeric < 2:
            st.session_state.checkbox_key_twocol += 1
        st.session_state.last_num_cols = len(col1)

        # --- Reset checkboxes when row count drops below thresholds ---
        # Effective row count: if user selected specific rows use that,
        # otherwise all rows in the table are used.
        eff_rows = len(col2) if col2 else len(edited_table)
        prev_rows = st.session_state.get("_last_eff_rows", eff_rows)
        # Variance / Chi-Square need ≥2 rows
        if prev_rows >= 2 and eff_rows < 2:
            st.session_state.checkbox_key_onecol += 1
        # Pearson / Spearman need ≥3 rows
        if prev_rows >= 3 and eff_rows < 3:
            st.session_state.checkbox_key_twocol += 1
        st.session_state["_last_eff_rows"] = eff_rows

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

def _compute_data_info(
    edited_table: pd.DataFrame | None,
    col1: list,
    col2: list,
    data_ready: bool,
) -> dict:
    """
    Analyze the currently selected data to determine which methods are
    eligible.  Returns a dict with:

        num_selected_cols   – number of columns selected
        num_numeric_cols    – how many of those columns are numeric
        num_rows            – number of data rows in the selection
        all_numeric         – True if every selected column is numeric
        has_numeric         – True if at least one selected column is numeric
    """
    if not data_ready or not col1:
        return {
            "num_selected_cols": 0,
            "num_numeric_cols": 0,
            "num_rows": 0,
            "all_numeric": False,
            "has_numeric": False,
        }

    subset = edited_table[col1]
    if col2:
        # Re-index to 1-based to match the row selector values
        subset = subset.copy()
        subset.index = range(1, len(subset) + 1)
        subset = subset.loc[subset.index.isin(col2)]

    num_rows = len(subset)

    # A column is "numeric" if pd.to_numeric can coerce every non-null value
    numeric_count = 0
    for c in subset.columns:
        coerced = pd.to_numeric(subset[c], errors="coerce")
        if coerced.notna().all() or subset[c].isna().all():
            numeric_count += 1

    return {
        "num_selected_cols": len(col1),
        "num_numeric_cols": numeric_count,
        "num_rows": num_rows,
        "all_numeric": numeric_count == len(col1) and len(col1) > 0,
        "has_numeric": numeric_count > 0,
    }


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
    col2: list,
    data_info: dict,
) -> tuple:
    """
    Render the 12 computation checkboxes in two columns.

    Disable rules (real-time, based on the current selection):
        - All checkboxes: disabled if no data is loaded (data_ready=False)
        - One-column numeric methods (Mean, Median, Mode, Std Dev, Percentiles):
              disabled if no numeric column selected
        - Variance: disabled if < 1 numeric column OR < 2 rows (ddof=1)
        - Pearson / Spearman: disabled if < 2 numeric columns OR < 3 rows
        - Least Squares Regression: disabled if < 2 numeric columns OR < 2 rows
        - Chi-Square: disabled if < 1 numeric column OR < 2 rows
        - Binomial: disabled if < 1 numeric column
        - Coefficient of Variation: disabled if no numeric column

    Returns:
        Tuple of 12 booleans + custom_flags dict.
    """
    st.header("Computation Options", anchor=False)

    # --- Derive disable flags from data_info ---
    n_cols = data_info["num_selected_cols"]
    n_num  = data_info["num_numeric_cols"]
    n_rows = data_info["num_rows"]
    has_num = data_info["has_numeric"]
    all_num = data_info["all_numeric"]

    # One-column numeric methods: need ≥1 numeric column
    dis_1num = not data_ready or n_num < 1
    # Variance needs ≥1 numeric column AND ≥2 rows (sample variance, ddof=1)
    dis_var  = not data_ready or n_num < 1 or n_rows < 2
    # Two-column numeric methods: need ≥2 numeric columns
    dis_2num = not data_ready or n_num < 2
    # Pearson / Spearman: need ≥2 numeric columns AND ≥3 rows
    dis_corr = not data_ready or n_num < 2 or n_rows < 3
    # Least-squares regression: need ≥2 numeric columns AND ≥2 rows
    dis_lsr  = not data_ready or n_num < 2 or n_rows < 2
    # Chi-Square: needs ≥1 numeric column AND ≥2 observed values
    dis_chi  = not data_ready or n_num < 1 or n_rows < 2
    # Binomial: needs ≥1 numeric column (data is cast to int/float)
    dis_binom = not data_ready or n_num < 1
    # Coefficient of Variation: needs ≥1 numeric column
    dis_cv   = not data_ready or n_num < 1

    # If user drops from >=2 columns to 1 column,
    # reset two-column statistical method checkboxes
    k1 = st.session_state.checkbox_key_onecol
    k2 = st.session_state.checkbox_key_twocol

    c1, c2 = st.columns(2)

    with c1:
        mean        = st.checkbox("Mean",                disabled=dis_1num,  key=f"mean_c1_{k1}")        and not dis_1num
        median      = st.checkbox("Median",              disabled=dis_1num,  key=f"median_c1_{k1}")      and not dis_1num
        mode        = st.checkbox("Mode",                disabled=dis_1num,  key=f"mode_c1_{k1}")        and not dis_1num
        variance    = st.checkbox("Variance",            disabled=dis_var,   key=f"variance_c1_{k1}")    and not dis_var
        std         = st.checkbox("Standard Deviation",  disabled=dis_1num,  key=f"std_c1_{k1}")         and not dis_1num
        percentiles = st.checkbox("Percentiles",         disabled=dis_1num,  key=f"percentiles_c1_{k1}") and not dis_1num

    with c2:
        pearson                = st.checkbox("Pearson's Correlation",     disabled=dis_corr, key=f"pearson_c2_{k2}")                and not dis_corr
        spearman               = st.checkbox("Spearman's Rank",           disabled=dis_corr, key=f"spearman_c2_{k2}")               and not dis_corr
        least_squares_regression = st.checkbox("Least Squares Regression",  disabled=dis_lsr,  key=f"least_squares_regression_c2_{k2}") and not dis_lsr
        chi_squared            = st.checkbox("Chi-Square Test",           disabled=dis_chi,  key=f"chi_squared_c2_{k1}")            and not dis_chi
        binomial               = st.checkbox("Binomial Distribution",     disabled=dis_binom, key=f"binomial_c2_{k1}")              and not dis_binom
        variation              = st.checkbox("Coefficient of Variation",  disabled=dis_cv,   key=f"variation_c2_{k1}")              and not dis_cv

    # --- Conditional parameter inputs (appear inline when the method is checked) ---
    if percentiles:
        st.markdown("**Percentile Parameters**")
        pcol, _ = st.columns([2, 1])
        with pcol:
            st.text_input(
                "Values (comma-separated)",
                value="25, 50, 75",
                key="percentile_values_input",
                placeholder="e.g. 10, 25, 50, 75, 90",
                help="Enter any values between 0 and 100, separated by commas.",
                disabled=dis_1num,
            )

    if binomial:
        if percentiles:
            st.markdown("<div style='margin-top:0.25rem'></div>", unsafe_allow_html=True)
        st.markdown("**Binomial Parameters**")
        bn1, bn2, bn3, bn4 = st.columns(4)
        with bn1:
            st.number_input(
                "n (trials)", min_value=1, max_value=100000,
                value=10, step=1,
                key="binomial_n",
                help="Total number of trials.",
                disabled=dis_binom,
            )
        with bn2:
            st.number_input(
                "p (probability)", min_value=0.0, max_value=1.0,
                value=0.5, step=0.01, format="%.4f",
                key="binomial_p",
                help="Probability of success on each trial (0 – 1).",
                disabled=dis_binom,
            )
        with bn3:
            st.number_input(
                "k min", min_value=0,
                value=0, step=1,
                key="binomial_k_min",
                help="Minimum number of successes (start of k-range).",
                disabled=dis_binom,
            )
        with bn4:
            st.number_input(
                "k max", min_value=0,
                value=10, step=1,
                key="binomial_k_max",
                help="Maximum number of successes (end of k-range).",
                disabled=dis_binom,
            )

    # --- Custom methods ---
    custom_flags = _render_custom_method_checkboxes(data_ready, col1, data_info)

    return (
        mean, median, mode, variance, std, percentiles,
        pearson, spearman, least_squares_regression, chi_squared, binomial, variation,
        custom_flags,
    )


def _render_custom_method_checkboxes(
    data_ready: bool,
    col1: list,
    data_info: dict,
) -> dict[str, bool]:
    """
    Render checkboxes for any user-defined custom methods.

    Reads the custom_methods.json registry and renders one checkbox per
    entry, respecting the method's input_type and numeric requirements.

    Returns:
        Dict mapping custom method ID → bool (checked/unchecked).
    """
    registry = load_custom_methods_registry()

    st.markdown("**Custom Methods**")

    if registry:
        kc = st.session_state.get("checkbox_key_custom", 0)
        k1 = st.session_state.checkbox_key_onecol
        k2 = st.session_state.checkbox_key_twocol
        n_num = data_info["num_numeric_cols"]

        flags = {}
        cm1, cm2 = st.columns(2)
        for idx, entry in enumerate(registry):
            mid = entry["id"]
            label = entry["display_name"]
            itype = entry.get("input_type", "one_column")

            if itype == "two_column":
                disabled = not data_ready or n_num < 2
                key_suffix = f"{k2}_{kc}"
            else:
                disabled = not data_ready or n_num < 1
                key_suffix = f"{k1}_{kc}"

            col_target = cm1 if idx % 2 == 0 else cm2
            with col_target:
                checked = st.checkbox(
                    label, disabled=disabled, key=f"{mid}_{key_suffix}"
                )
                flags[mid] = checked and not disabled
    else:
        flags = {}

    # --- Management buttons always visible under Custom Methods ---
    _user_defined_computation_options()

    return flags

_ONE_COL_TEMPLATE = """# 'data' is a list of lists (one per selected column).
# Flatten to a single numeric array:
import numpy as np
arr = np.asarray(data, dtype=float).flatten()

# --- Your computation here ---
result = float(np.sum(arr ** 2))  # Example: sum of squares
"""

_TWO_COL_TEMPLATE = """# 'data' is a list of two lists: data[0] and data[1].
import numpy as np
x = np.asarray(data[0], dtype=float)
y = np.asarray(data[1], dtype=float)

# --- Your computation here ---
result = float(np.dot(x, y))  # Example: dot product
"""

_PRESET_EXAMPLES = {
    "Sum of Squares (one column)": (
        "one_column",
        """import numpy as np
arr = np.asarray(data, dtype=float).flatten()
result = float(np.sum(arr ** 2))""",
    ),
    "Geometric Mean (one column)": (
        "one_column",
        """import numpy as np
from scipy.stats import gmean
arr = np.asarray(data, dtype=float).flatten()
result = float(gmean(arr[arr > 0]))""",
    ),
    "Weighted Average (two columns)": (
        "two_column",
        """import numpy as np
values = np.asarray(data[0], dtype=float)
weights = np.asarray(data[1], dtype=float)
result = float(np.average(values, weights=weights))""",
    ),
    "Dot Product (two columns)": (
        "two_column",
        """import numpy as np
x = np.asarray(data[0], dtype=float)
y = np.asarray(data[1], dtype=float)
result = float(np.dot(x, y))""",
    ),
}


# ---------------------------------------------------------------------------
# Helper: clear dialog-tracking session state so the next open is fresh
# ---------------------------------------------------------------------------
def _clear_cm_dialog_state():
    for k in (
        "_cm_prev_input_key", "_cm_prev_preset",
        "custom_method_code_input",
        "_cm_edit_code_input",
        "_cm_edit_prev_input", "_cm_edit_prev_preset",
        "_cm_edit_prev_method",
    ):
        st.session_state.pop(k, None)


def _refresh_custom_registries():
    """Push latest custom method names into frontend_handler and run_manager dicts."""
    from frontend_handler import _ID_TO_DISPLAY
    names = get_custom_display_names()
    _ID_TO_DISPLAY.update(names)
    METHOD_NAMES.update(names)


def _after_method_change():
    """Common post-save / post-delete housekeeping."""
    _get_backend_handler().reload_methods()
    _refresh_custom_registries()
    st.session_state.checkbox_key_custom = (
        st.session_state.get("checkbox_key_custom", 0) + 1
    )
    _clear_cm_dialog_state()


# ========================= CREATE DIALOG ====================================

@st.dialog("Create Custom Statistical Method", width="large")
def _create_method_dialog():
    """Dialog form for creating a new custom statistical method."""

    st.markdown(
        "Define your own statistical method. It will be saved and available "
        "as a checkbox alongside the built-in methods."
    )

    method_name = st.text_input(
        "Method Name",
        placeholder="e.g. Geometric Mean",
        key="custom_method_name_input",
    )
    description = st.text_area(
        "Description",
        placeholder="Briefly describe what this method computes.",
        height=68,
        key="custom_method_desc_input",
    )

    col_it, col_ot = st.columns(2)
    with col_it:
        input_type = st.selectbox(
            "Input Type",
            ["One Column", "Two Columns"],
            key="custom_method_input_type",
        )
    with col_ot:
        output_type = st.selectbox(
            "Output Type",
            ["Scalar (single number)", "List", "Dictionary"],
            key="custom_method_output_type",
        )

    input_key = "one_column" if input_type == "One Column" else "two_column"
    output_key = {"Scalar (single number)": "scalar", "List": "list", "Dictionary": "dictionary"}[output_type]

    # Preset selector — filter to matching input type
    preset_names = ["— None —"] + [
        name for name, (itype, _) in _PRESET_EXAMPLES.items()
        if itype == input_key
    ]
    selected_preset = st.selectbox(
        "Load a preset example",
        preset_names,
        key="custom_method_preset",
    )

    # Determine the code template to show
    if selected_preset != "— None —" and selected_preset in _PRESET_EXAMPLES:
        default_code = _PRESET_EXAMPLES[selected_preset][1]
    else:
        default_code = _ONE_COL_TEMPLATE if input_key == "one_column" else _TWO_COL_TEMPLATE

    # --- Reactive code editor: update when input type or preset changes ---
    prev_input = st.session_state.get("_cm_prev_input_key", None)
    prev_preset = st.session_state.get("_cm_prev_preset", None)
    if prev_input is not None and (input_key != prev_input or selected_preset != prev_preset):
        st.session_state["custom_method_code_input"] = default_code
    st.session_state["_cm_prev_input_key"] = input_key
    st.session_state["_cm_prev_preset"] = selected_preset

    st.markdown("---")
    st.markdown(
        "**Compute Logic** — Write Python code that produces a `result` variable. "
        "You have access to `data` (the selected columns), `params` (dict), "
        "and `toolbox` (dict of callable custom methods). "
        "`numpy` is imported as `np` in the generated file."
    )

    # --- Toolbox: dependency selection ---
    available_tools = get_available_tools_info()
    if available_tools:
        tool_options = {t["display_name"]: t["id"] for t in available_tools}
        selected_tool_names = st.multiselect(
            "Use other custom methods (toolbox)",
            options=list(tool_options.keys()),
            help=(
                "Select custom methods this method depends on. "
                "They will be available via the `toolbox` dict in your code."
            ),
            key="custom_method_deps",
        )
        selected_deps = [tool_options[n] for n in selected_tool_names]
        if selected_tool_names:
            with st.expander("Toolbox usage reference", expanded=False):
                for t in available_tools:
                    if t["id"] in selected_deps:
                        st.code(
                            f'# Call "{t["display_name"]}":\n'
                            f'value = toolbox["{t["id"]}"](data)\n'
                            f'# Or with custom params:\n'
                            f'value = toolbox["{t["id"]}"](data, {{"key": "val"}})',
                            language="python",
                        )
    else:
        selected_deps = []

    user_code = st.text_area(
        "Code",
        value=default_code,
        height=220,
        key="custom_method_code_input",
    )

    # --- Check Code button (live validation without saving) ---
    if st.button("\U0001f50d Check Code", use_container_width=True):
        issues = validate_user_code(user_code, input_key)
        if not issues:
            st.success("\u2705 No issues found — code looks good!")
        else:
            for issue in issues:
                if issue.startswith("Hint:"):
                    st.info(issue)
                else:
                    st.error(issue)

    st.markdown("---")
    save_col, cancel_col = st.columns(2)
    with save_col:
        if st.button("Save Method", use_container_width=True, type="primary"):
            ok, msg = save_custom_method(
                name=method_name,
                description=description,
                input_type=input_key,
                output_type=output_key,
                user_code=user_code,
                dependencies=selected_deps,
            )
            if ok:
                _after_method_change()
                st.success(msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)
    with cancel_col:
        if st.button("Cancel", use_container_width=True):
            _clear_cm_dialog_state()
            st.rerun()


# ========================= EDIT DIALOG ======================================

@st.dialog("Edit Custom Statistical Method", width="large")
def _edit_method_dialog():
    """Dialog to select an existing custom method and edit it."""
    registry = load_custom_methods_registry()
    if not registry:
        st.info("No custom methods to edit.")
        if st.button("Close", use_container_width=True):
            st.rerun()
        return

    name_map = {e["display_name"]: e for e in registry}
    selected_name = st.selectbox(
        "Select method to edit",
        list(name_map.keys()),
        key="_cm_edit_selector",
    )
    entry = name_map[selected_name]
    method_id = entry["id"]

    # Detect when a different method is selected (or first open) and
    # seed all form fields with that method's saved values so the
    # text_area / inputs show the real data instead of stale state.
    prev_method = st.session_state.get("_cm_edit_prev_method", None)
    if prev_method != method_id:
        existing_code = get_user_code(method_id) or (
            _TWO_COL_TEMPLATE if entry["input_type"] == "two_column" else _ONE_COL_TEMPLATE
        )
        st.session_state["_cm_edit_code_input"] = existing_code
        st.session_state["_cm_edit_name"] = entry["display_name"]
        st.session_state["_cm_edit_desc"] = entry["description"]
        st.session_state.pop("_cm_edit_prev_input", None)
        st.session_state.pop("_cm_edit_prev_preset", None)
        st.session_state["_cm_edit_prev_method"] = method_id

    # Pre-populate fields from existing entry
    new_name = st.text_input(
        "Method Name",
        value=entry["display_name"],
        key="_cm_edit_name",
    )
    new_desc = st.text_area(
        "Description",
        value=entry["description"],
        height=68,
        key="_cm_edit_desc",
    )

    input_options = ["One Column", "Two Columns"]
    current_input_idx = 0 if entry["input_type"] == "one_column" else 1
    col_it, col_ot = st.columns(2)
    with col_it:
        input_type = st.selectbox(
            "Input Type",
            input_options,
            index=current_input_idx,
            key="_cm_edit_input_type",
        )
    output_options = ["Scalar (single number)", "List", "Dictionary"]
    output_idx_map = {"scalar": 0, "list": 1, "dictionary": 2}
    with col_ot:
        output_type = st.selectbox(
            "Output Type",
            output_options,
            index=output_idx_map.get(entry["output_type"], 0),
            key="_cm_edit_output_type",
        )

    input_key = "one_column" if input_type == "One Column" else "two_column"
    output_key = {"Scalar (single number)": "scalar", "List": "list", "Dictionary": "dictionary"}[output_type]

    # Preset selector
    preset_names = ["— None —"] + [
        name for name, (itype, _) in _PRESET_EXAMPLES.items()
        if itype == input_key
    ]
    selected_preset = st.selectbox(
        "Load a preset example",
        preset_names,
        key="_cm_edit_preset",
    )

    # Determine code to show — prefer whatever is already in session state
    # (set above on method switch), but react to preset / input_type changes.
    current_code = st.session_state.get("_cm_edit_code_input", "")

    if selected_preset != "— None —" and selected_preset in _PRESET_EXAMPLES:
        target_code = _PRESET_EXAMPLES[selected_preset][1]
    else:
        target_code = current_code

    # Reactive update when input type or preset changes
    prev_input = st.session_state.get("_cm_edit_prev_input", None)
    prev_preset = st.session_state.get("_cm_edit_prev_preset", None)
    if prev_input is not None and (input_key != prev_input or selected_preset != prev_preset):
        st.session_state["_cm_edit_code_input"] = target_code
    st.session_state["_cm_edit_prev_input"] = input_key
    st.session_state["_cm_edit_prev_preset"] = selected_preset

    st.markdown("---")
    st.markdown(
        "**Compute Logic** — Write Python code that produces a `result` variable. "
        "You have access to `data` (the selected columns), `params` (dict), "
        "and `toolbox` (dict of callable custom methods). "
        "`numpy` is imported as `np` in the generated file."
    )

    # --- Toolbox: dependency selection ---
    available_tools = get_available_tools_info(exclude_id=method_id)
    existing_deps = entry.get("dependencies", [])
    if available_tools:
        tool_options = {t["display_name"]: t["id"] for t in available_tools}
        reverse_map = {t["id"]: t["display_name"] for t in available_tools}
        default_names = [reverse_map[d] for d in existing_deps if d in reverse_map]
        selected_tool_names = st.multiselect(
            "Use other custom methods (toolbox)",
            options=list(tool_options.keys()),
            default=default_names,
            help=(
                "Select custom methods this method depends on. "
                "They will be available via the `toolbox` dict in your code."
            ),
            key="_cm_edit_deps",
        )
        selected_deps = [tool_options[n] for n in selected_tool_names]
        if selected_tool_names:
            with st.expander("Toolbox usage reference", expanded=False):
                for t in available_tools:
                    if t["id"] in selected_deps:
                        st.code(
                            f'# Call "{t["display_name"]}":\n'
                            f'value = toolbox["{t["id"]}"](data)\n'
                            f'# Or with custom params:\n'
                            f'value = toolbox["{t["id"]}"](data, {{"key": "val"}})',
                            language="python",
                        )
    else:
        selected_deps = existing_deps

    user_code = st.text_area(
        "Code",
        height=220,
        key="_cm_edit_code_input",
    )

    # --- Check Code button (live validation without saving) ---
    if st.button("\U0001f50d Check Code", use_container_width=True):
        issues = validate_user_code(user_code, input_key)
        if not issues:
            st.success("\u2705 No issues found — code looks good!")
        else:
            for issue in issues:
                if issue.startswith("Hint:"):
                    st.info(issue)
                else:
                    st.error(issue)

    st.markdown("---")
    save_col, cancel_col = st.columns(2)
    with save_col:
        if st.button("Save Changes", use_container_width=True, type="primary"):
            ok, msg = update_custom_method(
                method_id=method_id,
                name=new_name,
                description=new_desc,
                input_type=input_key,
                output_type=output_key,
                user_code=user_code,
                dependencies=selected_deps,
            )
            if ok:
                _after_method_change()
                st.success(msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)
    with cancel_col:
        if st.button("Cancel", use_container_width=True):
            _clear_cm_dialog_state()
            st.rerun()


# ========================= DELETE DIALOG ====================================

@st.dialog("Delete Custom Method", width="large")
def _delete_method_dialog():
    """Dialog to select and permanently delete a custom method."""
    registry = load_custom_methods_registry()
    if not registry:
        st.info("No custom methods to delete.")
        if st.button("Close", use_container_width=True):
            st.rerun()
        return

    name_map = {e["display_name"]: e for e in registry}
    selected_name = st.selectbox(
        "Select method to delete",
        list(name_map.keys()),
        key="_cm_delete_selector",
    )
    entry = name_map[selected_name]

    st.markdown("---")
    st.markdown(f"**Method:** {entry['display_name']}")
    st.markdown(f"**Description:** {entry['description']}")
    st.markdown(f"**Input type:** {entry['input_type'].replace('_', ' ').title()}")
    st.markdown(f"**Created:** {entry['created_at'][:10]}")

    st.markdown("---")
    st.warning(
        "This will **permanently** delete the method, its generated code file, "
        "and remove it from any saved analysis runs. This cannot be undone.",
        icon="⚠️",
    )

    confirm = st.checkbox(
        f"I confirm I want to delete **{entry['display_name']}**",
        key="_cm_delete_confirm",
    )

    del_col, cancel_col = st.columns(2)
    with del_col:
        if st.button(
            "Delete Permanently",
            use_container_width=True,
            type="primary",
            disabled=not confirm,
        ):
            ok, msg = delete_custom_method(entry["id"])
            if ok:
                _after_method_change()
                st.success(msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)
    with cancel_col:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


# ========================= THREE PERMANENT BUTTONS ==========================

def _user_defined_computation_options():
    """
    Render three permanent buttons for custom method management:
    Create, Edit, and Delete.
    """
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("➕ Create", key="cm_create_btn", use_container_width=True):
            _create_method_dialog()
    with b2:
        if st.button("✏️ Edit", key="cm_edit_btn", use_container_width=True):
            _edit_method_dialog()
    with b3:
        if st.button("🗑️ Delete", key="cm_delete_btn", use_container_width=True):
            _delete_method_dialog()

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
) -> tuple:
    """
    Render the 5 visualization checkboxes.

    Charts can be selected independently of statistical methods.

    Args:
        data_ready: Whether a valid DataFrame is loaded.

    Returns:
        Tuple of 5 booleans: (hist, box, scatter, line, heatmap)
    """
    st.header("Visualization Options", anchor=False)

    disable_viz = not data_ready

    v1, v2 = st.columns(2)

    with v1:
        hist    = st.checkbox("Pie Chart",                     key="viz_hist",    disabled=disable_viz) and not disable_viz
        box     = st.checkbox("Vertical Bar Chart",            key="viz_box",     disabled=disable_viz) and not disable_viz
        scatter = st.checkbox("Horizontal Bar Chart",          key="viz_scatter", disabled=disable_viz) and not disable_viz

    with v2:
        line    = st.checkbox("Scatter Plot",                  key="viz_line",    disabled=disable_viz) and not disable_viz
        heatmap = st.checkbox("Line of Best Fit Scatter Plot", key="viz_heatmap", disabled=disable_viz) and not disable_viz

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
    custom_flags           = method_flags.get("custom_flags", {})

    already_computing = st.session_state.get("_compute_future") is not None

    run_clicked = st.button(
        "Run Analysis",
        key="run_analysis",
        use_container_width=True,
        disabled=not (data_ready and computation_selected) or already_computing
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
        # Statistical methods — keys match backend methods_list exactly
        "mean": mean, "median": median, "mode": mode,
        "variance": variance, "standard_deviation": std, "percentile": percentiles,
        "pearson": pearson, "spearman": spearman,
        "least_squares_regression": least_squares_regression,
        "chisquared": chi_squared, "binomial": binomial, "coefficient_variation": variation,
        # Charts — keys match backend charts_list exactly
        "pie_chart": hist, "vert_bar": box, "hor_bar": scatter,
        "scat_plot": line, "best_fit": heatmap,
    }
    # Merge custom method selections into method_flags
    method_flags.update(custom_flags)

    # --- Build methods and graphics lists using canonical backend IDs ---
    _BACKEND_METHOD_IDS = {
        "chisquared", "coefficient_variation", "least_squares_regression",
        "mean", "median", "mode", "pearson", "percentile", "spearman",
        "standard_deviation", "variance",
    }
    # Add all custom method IDs so they get dispatched to the backend
    _BACKEND_METHOD_IDS.update(custom_flags.keys())
    _BACKEND_CHART_IDS = {"binomial", "best_fit", "hor_bar", "pie_chart", "scat_plot", "vert_bar"}

    # Parse percentile parameter text input to list of floats
    _percentile_input_value = st.session_state.get("percentile_values_input", "25, 50, 75")
    percentile_values = []
    if isinstance(_percentile_input_value, str):
        for item in _percentile_input_value.split(","):
            try:
                pct = float(item.strip())
                if 0 <= pct <= 100:
                    percentile_values.append(pct)
            except ValueError:
                continue

    if not percentile_values:
        percentile_values = [25, 50, 75]

    methods = []
    for k, v in method_flags.items():
        if v and k in _BACKEND_METHOD_IDS:
            method_params = percentile_values if k == "percentile" else {}
            methods.append({"id": k, "params": method_params})
    _LABEL_FRIENDLY_CHARTS = {"pie_chart", "vert_bar", "hor_bar"}

    binomial_n = st.session_state.get("binomial_n", 10)
    binomial_p = st.session_state.get("binomial_p", 0.5)
    binomial_k_min = st.session_state.get("binomial_k_min", 0)
    binomial_k_max = st.session_state.get("binomial_k_max", int(binomial_n))

    graphics = []
    for k, v in method_flags.items():
        if v and k in _BACKEND_CHART_IDS:
            req = {"type": k}

            if k == "binomial":
                req.update({
                    "n": int(binomial_n),
                    "p": float(binomial_p),
                    "k_min": int(binomial_k_min),
                    "k_max": int(binomial_k_max),
                })

            if k in _LABEL_FRIENDLY_CHARTS:
                num_cols = parsed_data.select_dtypes(include="number").columns.tolist()
                str_cols = parsed_data.select_dtypes(exclude="number").columns.tolist()
                if num_cols and str_cols:
                    req["labels"] = parsed_data[str_cols[0]].astype(str).tolist()
                    req["values"] = parsed_data[num_cols[0]].tolist()
                elif num_cols:
                    req["values"] = parsed_data[num_cols[0]].tolist()
            graphics.append(req)

    # --- Submit ALL heavy work to background so loading dialog appears immediately ---
    # Validation, data serialization, and computation all run in the background.
    # Setting _compute_future here and calling st.rerun() means the loading dialog
    # appears on the very next render — zero UI lag regardless of dataset size.
    selected_cols = list(parsed_data.columns)
    selected_rows = list(parsed_data.index.tolist())
    dataset_id = (
        st.session_state.uploaded_file.name
        if st.session_state.get("uploaded_file")
        else "unknown"
    )

    run_count = len(st.session_state.analysis_runs) + 1
    st.session_state._compute_meta = {
        "run_id":         str(uuid.uuid4()),
        "run_name":       f"Run {run_count}",
        "methods":        methods,
        "visualizations": [VIZ_NAMES[k] for k in _BACKEND_CHART_IDS if method_flags.get(k)],
        "table":          edited_table,
        "data":           parsed_data.reset_index(drop=True),
        "columns":        col1,
        "rows":           col2,
    }
    st.session_state._compute_future = _get_executor().submit(
        _background_run,
        parsed_data,
        method_flags,
        methods,
        graphics,
        dataset_id,
        selected_cols,
        selected_rows,
        _get_backend_handler().handle_request,
    )
    st.session_state._loading_caption = "Running analysis… this won't take long."
    st.rerun()
