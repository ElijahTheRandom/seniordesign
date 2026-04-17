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
import json

import streamlit.components.v1 as components

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
import data_server as _data_server
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
    export_custom_methods_bundle,
    import_custom_methods_bundle,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _img_to_b64(filename: str) -> str:
    path = Path(BASE_DIR) / "pages" / "assets" / filename
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# Pre-encode theme icons once at module load so render_theme_toggle() never
# reads from disk on every render.
_MOON_ICON_B64 = _img_to_b64("moonIcon.png")
_SUN_ICON_B64  = _img_to_b64("sunIcon.png")

@st.cache_resource
def _get_backend_handler():
    return BackendHandler()

@st.cache_resource
def _get_executor():
    """Single-thread pool for background computation."""
    return ThreadPoolExecutor(max_workers=1)


def _param_warning(msg: str) -> None:
    """Render a compact inline callout with an upward caret, styled to branch from the input above."""
    st.markdown(
        f"""
        <div style="margin-top:0.2rem; margin-bottom:0.1rem;">
            <div style="
                width:0; height:0;
                border-left:8px solid transparent;
                border-right:8px solid transparent;
                border-bottom:8px solid rgba(228,120,29,0.55);
                margin-left:14px;
            "></div>
            <div style="
                background:rgba(228,120,29,0.10);
                border:1px solid rgba(228,120,29,0.55);
                border-radius:0 8px 8px 8px;
                padding:0.35rem 0.7rem;
                font-size:0.82rem;
                color:rgba(255,255,255,0.88);
                font-weight:500;
                line-height:1.4;
            ">⚠&nbsp; {msg}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


_GIF_PATH = Path(__file__).parent.parent / "pages" / "assets" / "ThinkingAhSquirrel.GIF"
# Pre-encode once at module load so the overlay JS never needs to re-read the file
with open(_GIF_PATH, "rb") as _f:
    _GIF_B64 = base64.b64encode(_f.read()).decode()

_HUZZAH_PATH = Path(__file__).parent.parent / "pages" / "assets" / "huzzahAhSquirrel.png"
# Pre-encode once at module load to avoid disk I/O on every success popup
with open(_HUZZAH_PATH, "rb") as _f:
    _HUZZAH_B64 = base64.b64encode(_f.read()).decode()

_WARNING_SQUIRREL_PATH = Path(__file__).parent.parent / "pages" / "assets" / "warningSquirrel.PNG"
# Pre-encode once at module load so error_dialog never reads from disk on render
with open(_WARNING_SQUIRREL_PATH, "rb") as _f:
    _WARNING_SQUIRREL_B64 = base64.b64encode(_f.read()).decode()


def _show_loading_gif(caption: str = "Loading\u2026") -> None:
    """Display the loading GIF centered on the page using base64 embedding."""
    st.markdown(
        f"""
        <div style="display:flex; flex-direction:column; align-items:center; margin-top:4rem;">
            <img class="ps-squirrel" src="data:image/gif;base64,{_GIF_B64}" style="max-width:420px; width:100%;" />
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

if "_grid_version" not in st.session_state:
    st.session_state._grid_version = 0

# Row-data version for the AG Grid component.  The React side keeps its own
# internal rowData state and only re-seeds from the rowData prop when this
# counter increases — so reruns triggered by the user's own drag/edit events
# don't force AG Grid to reconcile rows (which was wiping mid-drag selections
# and flickering freshly-edited cells back to their pre-edit values).  Bump
# only when the underlying DataFrame changes from a non-grid source (new file,
# header rename).
if "_row_data_version" not in st.session_state:
    st.session_state._row_data_version = 0

# ---------------------------------------------------------------------------
# Large file threshold
# ---------------------------------------------------------------------------
# Python-side cost (CSV parse + DataFrame serialization) first becomes
# noticeable around 10,000 rows.  Browser-side AG Grid rendering adds on top,
# so we warn users at this point and let them opt out of the table.
_LARGE_FILE_ROW_THRESHOLD = 10_000

# How many rows to show in the sampled table for large files.
# AG Grid virtualises these 10 K rows smoothly.  Column-header clicks map
# to "all rows" in the full dataset via the total_rows short-circuit in
# normalize_grid_selection, so computations always run on the full data.
_SAMPLE_DISPLAY_ROWS = 10_000


@st.dialog("Large File Detected", width="small")
def _large_file_warning_dialog():
    """
    Shown when an uploaded CSV exceeds _LARGE_FILE_ROW_THRESHOLD rows.
    The user chooses between hiding the table for better performance or
    displaying it anyway at the cost of increased load time.
    """
    rows = st.session_state.get("_large_file_rows", 0)
    cols = st.session_state.get("_large_file_cols", 0)
    cells = rows * cols

    _, img_col, _ = st.columns([1, 2, 1])
    with img_col:
        st.markdown(
            f'<img class="ps-squirrel" src="data:image/png;base64,{_WARNING_SQUIRREL_B64}"'
            ' style="width:100%;max-width:100%;" />',
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<p style='text-align:center;font-weight:600;margin:0.5rem 0 0.25rem'>"
        f"This file is large</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='text-align:center;color:#aaa;font-size:0.875rem;margin:0 0 1rem'>"
        f"{rows:,} rows &times; {cols} columns &nbsp;&middot;&nbsp; {cells:,} cells</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Rendering the full table may cause **noticeable lag**. "
        "You can hide the table and still run all computations using the column "
        "selectors — or display the table at reduced performance.",
    )

    st.markdown("<div style='margin-bottom:0.75rem'></div>", unsafe_allow_html=True)

    col_hide, col_show = st.columns(2)
    with col_hide:
        if st.button("Hide Table", use_container_width=True, type="primary",
                     key="_lfw_hide"):
            st.session_state.large_file_hide_table = True
            st.session_state._large_file_warning_pending = False
            st.rerun()
    with col_show:
        if st.button("Show Anyway", use_container_width=True,
                     key="_lfw_show"):
            st.session_state.large_file_hide_table = False
            st.session_state._large_file_warning_pending = False
            st.rerun()

def _show_loading_overlay(caption: str = "Loading\u2026") -> None:
    """Inject a full-screen loading overlay into the parent document.

    Appears instantly because it lives outside the Streamlit iframe.
    Idempotent — a second call while the overlay is visible is a no-op.
    Call _hide_loading_overlay() to remove it.
    """
    import json as _json
    caption_json = _json.dumps(caption)
    components.html(
        f"""
        <script>
        (function() {{
            const doc = window.parent.document;
            if (doc.getElementById('ps-loading-overlay')) return;

            if (!doc.getElementById('ps-loading-styles')) {{
                const s = doc.createElement('style');
                s.id = 'ps-loading-styles';
                s.textContent = [
                    '#ps-loading-overlay{{position:fixed;inset:0;background:rgba(0,0,0,0.72);',
                    'display:flex;align-items:center;justify-content:center;z-index:10000;',
                    'backdrop-filter:blur(3px)}}',
                    '#ps-loading-overlay .ps-box{{background:#1e2530;border:1px solid rgba(228,120,29,0.4);',
                    'border-radius:16px;padding:2rem 2.5rem;display:flex;flex-direction:column;',
                    'align-items:center;gap:1rem;min-width:220px}}',
                    '#ps-loading-overlay img{{width:140px;height:140px;object-fit:contain;border-radius:8px}}',
                    '#ps-loading-overlay p{{color:#fff;font-size:0.95rem;margin:0;',
                    'font-family:sans-serif;text-align:center;opacity:0.9}}',
                ].join('');
                doc.head.appendChild(s);
            }}

            const overlay = doc.createElement('div');
            overlay.id = 'ps-loading-overlay';
            const box = doc.createElement('div');
            box.className = 'ps-box';
            const img = doc.createElement('img');
            img.src = 'data:image/gif;base64,{_GIF_B64}';
            const p = doc.createElement('p');
            p.textContent = {caption_json};
            box.appendChild(img);
            box.appendChild(p);
            overlay.appendChild(box);
            doc.body.appendChild(overlay);
        }})();
        </script>
        """,
        height=0,
    )


def _hide_loading_overlay() -> None:
    """Remove the loading overlay from the parent document (safe to call when absent)."""
    components.html(
        """
        <script>
        (function() {
            const el = window.parent.document.getElementById('ps-loading-overlay');
            if (el) el.remove();
        })();
        </script>
        """,
        height=0,
    )


def _show_computing_toast(caption: str = "Running analysis\u2026") -> None:
    """Inject a persistent corner toast while computation runs.

    Lives in window.parent.document so it survives page navigation.
    Idempotent — safe to call on every render while computing.
    Call _hide_computing_toast() when done.
    """
    import json as _json
    caption_json = _json.dumps(caption)
    components.html(
        f"""
        <script>
        (function() {{
            const doc = window.parent.document;
            if (doc.getElementById('ps-computing-toast')) return;

            const toast = doc.createElement('div');
            toast.id = 'ps-computing-toast';
            toast.style.cssText = [
                'position:fixed', 'top:1.25rem', 'right:1.25rem', 'z-index:9998',
                'background:#1e2530', 'border:1px solid rgba(228,120,29,0.45)',
                'border-radius:12px', 'padding:0.9rem 1.1rem',
                'display:flex', 'align-items:center', 'gap:0.9rem',
                'box-shadow:0 8px 32px rgba(0,0,0,0.55)', 'max-width:340px',
            ].join(';');

            const img = doc.createElement('img');
            img.src = 'data:image/gif;base64,{_GIF_B64}';
            img.style.cssText = [
                'width:54px', 'height:54px',
                'object-fit:contain', 'border-radius:8px',
                'flex-shrink:0',
            ].join(';');

            const txt = doc.createElement('div');
            txt.textContent = {caption_json};
            txt.style.cssText =
                'color:#ffffff;font-size:0.875rem;line-height:1.45;font-family:sans-serif';

            toast.appendChild(img);
            toast.appendChild(txt);
            doc.body.appendChild(toast);
        }})();
        </script>
        """,
        height=0,
    )


def _hide_computing_toast() -> None:
    """Remove the computing corner toast (safe to call when absent)."""
    components.html(
        """
        <script>
        (function() {
            const el = window.parent.document.getElementById('ps-computing-toast');
            if (el) el.remove();
        })();
        </script>
        """,
        height=0,
    )


@st.dialog("Error", width="small")
def error_dialog():
    message = st.session_state.modal_message

    # Squirrel centered on top
    _, img_col, _ = st.columns([1, 2, 1])
    with img_col:
        st.markdown(
            f'<img class="ps-squirrel" src="data:image/png;base64,{_WARNING_SQUIRREL_B64}" style="width:100%;max-width:100%;" />',
            unsafe_allow_html=True,
        )

    lines = message.split("\n")
    non_empty = [l for l in lines if l.strip()]

    if len(non_empty) <= 1:
        st.markdown(f"<div style='text-align:center'>{message}</div>", unsafe_allow_html=True)
    else:
        tip_prefixes = ("Ensure", "Please", "Fix", "Tip", "Note")
        tip_lines = [l for l in non_empty if any(l.strip().startswith(p) for p in tip_prefixes)]
        detail_lines = [l for l in non_empty if not any(l.strip().startswith(p) for p in tip_prefixes)]

        # Header (bold summary line)
        if detail_lines:
            header = detail_lines[0]
            body = detail_lines[1:]
            st.markdown(
                f"<p style='text-align:center;font-weight:600;margin:0.25rem 0 0.5rem'>{header}</p>",
                unsafe_allow_html=True,
            )
            if body:
                st.markdown("\n".join(body))

        if tip_lines:
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption(f"💡 {tip_lines[0]}")


def _show_success_toast() -> None:
    """Inject a self-dismissing toast notification into the parent page.

    Uses window.parent.document so the toast lives outside the Streamlit
    iframe and persists across reruns until its 3-second timer expires.
    """
    import re, json as _json
    message = st.session_state.get("modal_message", "")
    b64 = _HUZZAH_B64

    # Convert basic markdown (** bold **, newlines) to safe HTML
    html_msg = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', message)
    html_msg = html_msg.replace("\n", "<br>")
    msg_json = _json.dumps(html_msg)

    components.html(
        f"""
        <script>
        (function() {{
            const doc = window.parent.document;

            // Inject keyframe styles once
            if (!doc.getElementById('ps-toast-styles')) {{
                const s = doc.createElement('style');
                s.id = 'ps-toast-styles';
                s.textContent =
                    '@keyframes ps-in{{from{{opacity:0;transform:translateY(-14px)}}' +
                    'to{{opacity:1;transform:translateY(0)}}}}' +
                    '@keyframes ps-out{{from{{opacity:1;transform:translateY(0)}}' +
                    'to{{opacity:0;transform:translateY(-14px)}}}}';
                doc.head.appendChild(s);
            }}

            // Remove any existing toast before adding a new one
            const prev = doc.getElementById('ps-success-toast');
            if (prev) prev.remove();

            const toast = doc.createElement('div');
            toast.id = 'ps-success-toast';
            toast.style.cssText = [
                'position:fixed', 'top:1.25rem', 'right:1.25rem', 'z-index:9999',
                'background:#1e2530', 'border:1px solid rgba(228,120,29,0.45)',
                'border-radius:12px', 'padding:0.9rem 1.1rem',
                'display:flex', 'align-items:center', 'gap:0.9rem',
                'box-shadow:0 8px 32px rgba(0,0,0,0.55)', 'max-width:340px',
                'pointer-events:none',
                'animation:ps-in 0.3s ease, ps-out 0.45s ease 4.55s forwards'
            ].join(';');

            const img = doc.createElement('img');
            img.src = 'data:image/png;base64,{b64}';
            img.style.cssText = 'width:52px;height:52px;object-fit:contain;border-radius:6px;flex-shrink:0';

            const txt = doc.createElement('div');
            txt.innerHTML = {msg_json};
            txt.style.cssText = 'color:#ffffff;font-size:0.875rem;line-height:1.45;font-family:sans-serif';

            toast.appendChild(img);
            toast.appendChild(txt);
            doc.body.appendChild(toast);

            setTimeout(() => {{ if (toast.parentNode) toast.remove(); }}, 5000);
        }})();
        </script>
        """,
        height=0,
    )

# ---------------------------------------------------------------------------
# Header detection helpers
# ---------------------------------------------------------------------------

def _col_letter(i: int) -> str:
    """Return a spreadsheet-style column label for index i (0-based): A, B, …, Z, AA, AB, …"""
    label = ""
    i += 1  # convert to 1-based
    while i > 0:
        i, rem = divmod(i - 1, 26)
        label = chr(65 + rem) + label
    return label

def _detect_has_headers(raw_bytes: bytes) -> bool:
    """
    Heuristic: does the CSV's first row look like column headers?

    Returns True if every value in the first row is a non-numeric string
    and at least one column in subsequent rows contains numeric data.
    Falls back to True (the pandas default) when uncertain.
    """
    try:
        df = pd.read_csv(io.BytesIO(raw_bytes), header=None, nrows=20)
    except Exception:
        return True

    if len(df) < 2:
        return False

    first_row = df.iloc[0]

    # If any first-row value is numeric, it's likely data, not a header
    for val in first_row:
        if pd.isna(val):
            continue
        try:
            float(str(val))
            return False
        except (ValueError, TypeError):
            pass

    # Check if rows 2+ have at least some numeric data
    rest = df.iloc[1:]
    for col in rest.columns:
        coerced = pd.to_numeric(rest[col], errors="coerce")
        if coerced.notna().any():
            return True

    # All-string data throughout — assume headers (common convention)
    return True


def _on_header_toggle(file_key: str) -> None:
    """Callback: re-parse CSV when the user toggles the header checkbox."""
    has_headers = st.session_state.get(f"_has_headers_{file_key}", True)
    raw = st.session_state.get("_csv_raw_bytes")

    # Try to recover raw bytes from the uploaded file if not cached
    if raw is None:
        uf = st.session_state.get("uploaded_file")
        if uf is not None:
            try:
                uf.seek(0)
                raw = uf.read()
                st.session_state._csv_raw_bytes = raw
            except Exception:
                return

    if raw is None:
        return

    if has_headers:
        df = pd.read_csv(io.BytesIO(raw))
    else:
        df = pd.read_csv(io.BytesIO(raw), header=None)
        df.columns = [f"Column {_col_letter(i)}" for i in range(len(df.columns))]

    st.session_state.edited_data_cache[file_key] = df

    # Reset column-related state since column names changed
    st.session_state.selected_columns = []
    st.session_state.selected_rows = []
    st.session_state.last_grid_selection = None
    st.session_state.checkbox_key_onecol += 1
    st.session_state.checkbox_key_twocol += 1
    # Bump the grid version so the component remounts with fresh columns
    st.session_state._grid_version = st.session_state.get("_grid_version", 0) + 1
    st.session_state._row_data_version = st.session_state.get("_row_data_version", 0) + 1

    # --- Large-file state sync ---
    # If this file is currently loaded as a large file, the header change
    # affects:
    #   1. _total_rows: toggling header=None adds the former header row as
    #      data row 1, so the count increases by 1 (and vice versa).
    #   2. The sample-records cache: column names / first-row content have
    #      changed, so the cached serialised records must be invalidated so
    #      _display_aggrid_server re-serialises from the new df on next render.
    #   3. The data server: kept consistent (used for accurate /meta responses).
    if st.session_state.get("_data_key") == file_key:
        new_total = len(df)
        st.session_state._total_rows = new_total
        st.session_state._large_file_rows = new_total
        st.session_state._large_file_cols = len(df.columns)
        # Invalidate the sample records cache so _display_aggrid_server
        # rebuilds it with the updated column names and first-row data.
        st.session_state.pop(f"_sample_records_{file_key}", None)
        # Keep the data server consistent in case it is queried.
        try:
            _data_server.store_dataframe(file_key, df)
        except Exception:
            pass


def _render_header_settings(uploaded_file) -> None:
    """
    Render the header-detection toggle.

    Shown between the file action buttons and the grid.
    """
    if uploaded_file is None:
        return

    file_key = f"{uploaded_file.name}_{uploaded_file.size}"
    cache = st.session_state.get("edited_data_cache", {})
    if file_key not in cache:
        return

    # --- Header toggle ---
    detected = st.session_state.get(f"_headers_detected_{file_key}", True)
    toggle_key = f"_has_headers_{file_key}"
    st.session_state.setdefault(toggle_key, detected)

    st.checkbox(
        "First row contains headers",
        key=toggle_key,
        on_change=_on_header_toggle,
        args=(file_key,),
    )




# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def poll_background_computation() -> None:
    """Check whether a background computation is complete and handle the result.

    Call this on every render from mainpage.py so it runs regardless of which
    view the user is on.  Manages the corner computing toast and fires the
    success/error dialogs via session state flags.
    """
    future = st.session_state.get("_compute_future")

    if future is None:
        # Not computing — hide the corner toast if it was shown last render.
        if st.session_state.get("_computing_toast_shown"):
            _hide_computing_toast()
            st.session_state._computing_toast_shown = False
        return

    # Computation is in progress — show corner toast on the first render.
    if not st.session_state.get("_computing_toast_shown"):
        _show_computing_toast("Running analysis\u2026 this won't take long.")
        st.session_state._computing_toast_shown = True

    if not future.done():
        # Still running — return so the rest of the render (view routing,
        # navigation, etc.) can complete normally.  The caller (mainpage.py)
        # schedules the next poll check at the very end of the render cycle.
        return

    # ── Future completed ──────────────────────────────────────────────────
    meta = st.session_state._compute_meta
    try:
        result_message = future.result()
    except _ValidationError as ve:
        st.session_state._compute_future = None
        st.session_state._compute_meta = None
        st.session_state.modal_message = str(ve)
        st.session_state.show_error_dialog = True
        # Leave _computing_toast_shown = True so render B's future-is-None
        # branch hides the toast after the rerun (calling _hide_computing_toast
        # just before st.rerun risks the iframe script being discarded before
        # it executes).
        st.rerun()
        return
    except Exception as exc:
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
        "measurement_levels": meta.get("measurement_levels", {}),
    }
    handle_result(run)

    st.session_state.analysis_runs.append(run)
    st.session_state.modal_message = build_success_message(run)
    st.session_state.show_success_dialog = True
    st.session_state._compute_future = None
    st.session_state._compute_meta = None
    # Bump grid version so the grid remounts with a clean selection state.
    st.session_state._grid_version = st.session_state.get("_grid_version", 0) + 1
    st.session_state._row_data_version = st.session_state.get("_row_data_version", 0) + 1
    st.session_state.selected_columns = []
    st.session_state.selected_rows = []
    st.session_state.last_grid_selection = None
    st.session_state["_raw_grid_selection"] = []
    # Rerun so the sidebar renders with the new run already in analysis_runs,
    # and the success/error dialogs fire from the clean top-of-render state.
    # Leave _computing_toast_shown = True — render B's future-is-None branch
    # will call _hide_computing_toast() there, where no subsequent st.rerun()
    # races against the iframe script that removes the toast from the DOM.
    st.rerun()


def render_homepage(base_dir: str) -> None:
    """
    Render the full homepage: data input (left) + analysis config (right).

    Args:
        base_dir: Absolute path to the frontend directory. Used to
                  resolve asset paths passed down to child functions.
    """
    # ------------------------------------------------------------------
    # CSV loading overlay — blocks interaction until table data is ready.
    # Only injected/removed on state transitions to avoid iframe churn.
    # (Computation uses a non-blocking corner toast instead — see
    #  poll_background_computation() called from mainpage.py.)
    # ------------------------------------------------------------------
    _was_overlay_active = st.session_state.get("_overlay_active", False)
    if st.session_state.get("_csv_loading"):
        if not _was_overlay_active:
            _show_loading_overlay("Loading CSV data\u2026")
        else:
            # Placeholder keeps the element tree stable across reruns so that
            # the st.columns block below never shifts position — which would
            # cause Streamlit to recreate the grid and all widgets inside it.
            components.html("<span></span>", height=0)
        st.session_state._overlay_active = True
    else:
        if _was_overlay_active:
            _hide_loading_overlay()
        else:
            components.html("<span></span>", height=0)
        st.session_state._overlay_active = False
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
            st.session_state._csv_raw_bytes = raw
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

                # Auto-detect whether the first row is headers
                raw = st.session_state.get("_csv_raw_bytes")
                if raw is not None:
                    detected = _detect_has_headers(raw)
                else:
                    detected = True
                st.session_state[f"_headers_detected_{file_key}"] = detected
                st.session_state.setdefault(f"_has_headers_{file_key}", detected)

                if not detected:
                    # Re-parse without headers and generate column names
                    if raw is not None:
                        df = pd.read_csv(io.BytesIO(raw), header=None)
                    df.columns = [
                        f"Column {_col_letter(i)}" for i in range(len(df.columns))
                    ]

                st.session_state.edited_data_cache[file_key] = df

                # Check size — trigger large-file warning if above threshold
                if len(df) >= _LARGE_FILE_ROW_THRESHOLD:
                    st.session_state._large_file_rows = len(df)
                    st.session_state._large_file_cols = len(df.columns)
                    st.session_state._large_file_warning_pending = True
                    # Register with the data server for infinite scroll
                    st.session_state._data_key = file_key
                    st.session_state._total_rows = len(df)
                    _data_server.store_dataframe(file_key, df)
                else:
                    # Reset hide flag when a small file replaces a large one
                    st.session_state.large_file_hide_table = False
                    st.session_state._large_file_warning_pending = False
                    st.session_state.pop("_data_key", None)
                    st.session_state.pop("_total_rows", None)
            except Exception as exc:
                st.session_state.modal_message = f"Failed to parse CSV: {exc}"
                st.session_state.show_error_dialog = True
            st.session_state._csv_loading = False
            st.session_state._csv_future = None
            st.rerun()
            return
        # Still loading (or just kicked off) — poll.
        time.sleep(0.5)
        st.rerun()

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<hr style='margin: 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )

    # Fire large-file warning dialog if a freshly loaded file is above the threshold
    if st.session_state.get("_large_file_warning_pending"):
        _large_file_warning_dialog()

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
    st.markdown("# Data Input & Table")

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

    # --- Header settings (toggle + rename) ---
    _render_header_settings(uploaded_file)

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
    # Clear the data server entry for the file being removed
    old_key = st.session_state.get("_data_key")
    if old_key:
        _data_server.clear_dataframe(old_key)

    for key in ("uploaded_file", "saved_table", "edited_data_cache",
                 "_csv_loading", "_csv_future", "_raw_grid_selection", "_csv_raw_bytes",
                 "large_file_hide_table", "_large_file_warning_pending",
                 "_large_file_rows", "_large_file_cols",
                 "_data_key", "_total_rows"):
        st.session_state.pop(key, None)

    # Clear per-file header detection state and sample records cache
    for key in list(st.session_state.keys()):
        if key.startswith(("_headers_detected_", "_has_headers_", "_sample_records_")):
            del st.session_state[key]

    st.session_state.has_file = False

    # Keep previously selected values valid if the underlying DataFrame changed
    # (prevents Streamlit from crashing when a column disappears between reruns)
    st.session_state.selected_columns = []
    st.session_state.selected_rows = []
    st.session_state.last_grid_selection = None
    st.session_state.checkbox_key_onecol += 1
    st.session_state.checkbox_key_twocol += 1
    # Reset range-input state so the new file starts fresh.
    for _k in ("_range_input_text", "_range_input_error", "_programmatic_ranges",
               "_range_text_sig", "_range_typed"):
        st.session_state.pop(_k, None)
    st.session_state["_programmatic_ranges_version"] = 0
    st.session_state["_programmatic_pending"] = 0


# ---------------------------------------------------------------------------
# Range-input helpers
# ---------------------------------------------------------------------------

def _compute_ref_string(
    col1: list,
    col2: list,
    raw_grid_selection: list | None,
    df: "pd.DataFrame | None",
) -> str:
    """
    Build an Excel-style reference string from the current selection.

    Mirrors the format shown in the reference bar so the text input displays
    the same notation the user would type: ``A[1]:A[100]``, ``ColName``, etc.

    When col2 is empty (meaning "all rows"), just the column names are shown
    without row numbers so the canonical form is clean and round-trips
    correctly through _parse_range_string.
    """
    if not col1:
        return ""

    if not col2:
        # All-rows selection — show bare column names.
        return ", ".join(col1)

    # Specific rows: derive from the raw selection when available so
    # Ctrl-click multi-ranges each get their own correct row span.
    if raw_grid_selection:
        parts = []
        for rng in raw_grid_selection:
            start = rng.get("startRow")
            end   = rng.get("endRow")
            cols  = rng.get("columns", [])
            if start is None or end is None or not cols:
                continue
            r0, r1 = int(start) + 1, int(end) + 1
            valid = [c for c in cols if df is not None and c in df.columns]
            if not valid:
                continue
            if len(valid) == 1:
                c = valid[0]
                parts.append(f"{c}[{r0}]:{c}[{r1}]" if r0 != r1 else f"{c}[{r0}]")
            else:
                # Rectangular multi-column range: A[1]:B[100] form
                parts.append(
                    f"{valid[0]}[{r0}]:{valid[-1]}[{r1}]" if r0 != r1
                    else f"{valid[0]}[{r0}]:{valid[-1]}[{r0}]"
                )
        if parts:
            return ", ".join(parts)

    # Fall back: build from col1/col2
    r0, r1 = col2[0], col2[-1]
    return ", ".join(
        f"{c}[{r0}]:{c}[{r1}]" if r0 != r1 else f"{c}[{r0}]" for c in col1
    )


def _parse_range_string(
    text: str,
    df: "pd.DataFrame",
    n_displayed: int,
) -> tuple[list, list, list, str]:
    """
    Parse an Excel-style range string typed by the user.

    Supported formats
    -----------------
    ``ColName``                → whole column, all rows
    ``ColName[5]``             → single row 5
    ``ColName[5]:ColName[20]`` → rows 5–20 (same column on both sides)
    ``ColA[5]:ColB[20]``       → rectangular range across ColA–ColB, rows 5–20
    Multiple ranges separated by commas: ``A[1]:A[50], B[1]:B[50]``

    Column names are matched greedily (longest known name first) so names
    that share a prefix (e.g. ``Col`` and ``Color``) are handled correctly.
    Row numbers must be enclosed in square brackets to disambiguate column
    names that end with digits (e.g. ``column1[2]`` not ``column12``).

    Parameters
    ----------
    text        : user-supplied input string
    df          : the active DataFrame (column names and length are used for
                  validation)
    n_displayed : number of rows currently shown in the grid (used to clamp
                  the programmatic range so AG Grid doesn't try to scroll past
                  the visible rows)

    Returns
    -------
    (grid_ranges, selected_cols, selected_rows, error_message)
    - grid_ranges     : list of {startRow, endRow, columns} dicts (0-based)
                        clamped to n_displayed
    - selected_cols   : list of column names for session state
    - selected_rows   : list of 1-based row ints (empty = all rows)
    - error_message   : non-empty string on failure; all other values are []
    """
    text = text.strip()
    if not text:
        return [], [], [], ""

    col_names = list(df.columns)
    n_rows    = len(df)
    # Sort longest-first so greedy prefix matching prefers longer names.
    cols_by_len = sorted(col_names, key=len, reverse=True)

    def _split_ref(ref: str):
        """Return (col_name, row_int_or_None) or (None, error_string).

        Accepted forms:
          ColName        → whole column (all rows)
          ColName[n]     → single row n  (1-based)
        """
        ref = ref.strip()
        for col in cols_by_len:
            if ref.startswith(col):
                suffix = ref[len(col):]
                if suffix == "":
                    return col, None          # bare column → all rows
                # Must be [n] bracket notation
                if suffix.startswith("[") and suffix.endswith("]"):
                    inner = suffix[1:-1]
                    try:
                        row = int(inner)
                        if row < 1 or row > n_rows:
                            return None, (
                                f"Row {row} is out of range — "
                                f"file has {n_rows:,} rows"
                            )
                        return col, row
                    except ValueError:
                        pass   # malformed bracket content
                # suffix is not empty and not a valid [n] — column name matched
                # as a prefix but the rest isn't valid syntax; keep trying other
                # column names (a longer name might match the whole string).
        return None, f"'{ref}' does not match any column in this file"

    specs = [s.strip() for s in text.replace(";", ",").split(",") if s.strip()]
    if not specs:
        return [], [], [], ""

    grid_ranges  = []
    sel_cols_ord: list = []          # ordered, dedup
    all_rows_set: set  = set()
    has_all_rows = False             # True when at least one "whole column" ref is present

    for spec in specs:
        if ":" in spec:
            left_str, right_str = spec.split(":", 1)
            lc, lr = _split_ref(left_str)
            if lc is None:
                return [], [], [], f"Invalid range start: {lr}"
            rc, rr = _split_ref(right_str)
            if rc is None:
                return [], [], [], f"Invalid range end: {rr}"

            if (lr is None) != (rr is None):
                return [], [], [], (
                    f"Inconsistent row spec in '{spec}': "
                    "both sides must have a row number, or neither"
                )

            # Determine row bounds
            if lr is None:
                r0, r1 = 1, n_rows
                has_all_rows = True
            else:
                r0, r1 = min(lr, rr), max(lr, rr)

            # Determine column range
            if lc == rc:
                range_cols = [lc]
            else:
                # Rectangular: all columns between lc and rc in df order
                try:
                    ci0 = col_names.index(lc)
                    ci1 = col_names.index(rc)
                except ValueError:
                    return [], [], [], f"Column not found"
                c_lo, c_hi = min(ci0, ci1), max(ci0, ci1)
                range_cols = col_names[c_lo : c_hi + 1]
        else:
            col, row = _split_ref(spec)
            if col is None:
                return [], [], [], f"Invalid ref: {row}"
            range_cols = [col]
            if row is None:
                r0, r1 = 1, n_rows
                has_all_rows = True
            else:
                r0 = r1 = row

        # Clamp to the number of rows the grid is actually showing.
        grid_r0 = r0 - 1                          # 0-based
        grid_r1 = min(r1 - 1, n_displayed - 1)    # 0-based, clamped
        grid_ranges.append({
            "startRow": grid_r0,
            "endRow":   grid_r1,
            "columns":  range_cols,
        })

        for c in range_cols:
            if c not in sel_cols_ord:
                sel_cols_ord.append(c)

        if not has_all_rows:
            for r in range(r0, r1 + 1):
                all_rows_set.add(r)

    selected_rows = [] if has_all_rows else sorted(all_rows_set)
    return grid_ranges, sel_cols_ord, selected_rows, ""


def _get_n_displayed(df: "pd.DataFrame | None") -> int:
    """Return the number of rows currently rendered in the AG Grid."""
    if df is None:
        return 0
    total = st.session_state.get("_total_rows")
    if total:
        return min(_SAMPLE_DISPLAY_ROWS, total)
    return len(df)


def _on_range_input_change(df: "pd.DataFrame", n_displayed: int) -> None:
    """
    Streamlit on_change callback for the range text input.

    Parses the typed range string, updates session state on success, or
    stores an error message that blocks the Run Analysis button.
    """
    text = st.session_state.get("_range_input_text", "").strip()

    if not text:
        # Empty input → clear selection and grid highlight
        st.session_state.selected_columns           = []
        st.session_state.selected_rows              = []
        st.session_state["_raw_grid_selection"]     = []
        st.session_state["_range_input_error"]      = ""
        st.session_state["_programmatic_ranges"]    = []
        st.session_state["_programmatic_ranges_version"] = (
            st.session_state.get("_programmatic_ranges_version", 0) + 1
        )
        st.session_state["_programmatic_pending"]   = 1
        st.session_state["_range_typed"]            = True
        st.session_state["_range_text_sig"]         = ((), ())
        return

    grid_ranges, cols, rows, error = _parse_range_string(text, df, n_displayed)

    if error:
        st.session_state["_range_input_error"] = error
        return

    st.session_state["_range_input_error"]           = ""
    st.session_state.selected_columns               = cols
    st.session_state.selected_rows                  = rows
    st.session_state["_programmatic_ranges"]         = grid_ranges
    st.session_state["_programmatic_ranges_version"] = (
        st.session_state.get("_programmatic_ranges_version", 0) + 1
    )
    st.session_state["_programmatic_pending"]        = 1
    st.session_state["_range_typed"]                 = True
    # Record the new selection signature so _render_column_row_selectors
    # doesn't overwrite the input text on the very next render.
    st.session_state["_range_text_sig"] = (tuple(cols), tuple(rows))


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
        return None


def _render_grid_from_file(uploaded_file) -> pd.DataFrame:
    """
    Load a CSV from the uploaded file, display it in AG Grid, and return
    the DataFrame.

    Uses a file-keyed cache (`edited_data_cache`) so repeated reruns
    don't re-parse the CSV from disk on every interaction.

    When the user has chosen to hide the table (large_file_hide_table=True),
    the AG Grid is skipped entirely and manual column/row selectors are shown
    instead — computations still work normally.

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

        if st.session_state.get("large_file_hide_table", False):
            _render_large_file_selectors(df)
            return df

        grid_version = st.session_state.get("_grid_version", 0)
        data_key = st.session_state.get("_data_key")
        total_rows = st.session_state.get("_total_rows")

        if data_key and total_rows:
            # Large file — use server mode (Infinite Row Model)
            _display_aggrid_server(
                df,
                data_key=data_key,
                total_rows=total_rows,
                grid_key=f"grid_{file_key}_v{grid_version}",
            )
            return df

        df = _display_aggrid(df, grid_key=f"grid_{file_key}_v{grid_version}")
        st.session_state.edited_data_cache[file_key] = df
        return df

    except Exception as e:
        st.error(f"Error processing file: {e}")
        return None


def _render_large_file_selectors(df: pd.DataFrame) -> None:
    """
    Shown in place of the AG Grid when the user opted to hide the table.

    Provides manual column and row-range selectors so computations remain
    fully functional.  A button lets the user re-enable the table.
    """
    rows, cols = len(df), len(df.columns)

    st.markdown(
        f"""
        <div style="
            background:rgba(228,120,29,0.08);
            border:1px solid rgba(228,120,29,0.35);
            border-radius:10px;
            padding:0.85rem 1.1rem;
            margin-bottom:1rem;
        ">
            <div style="font-weight:600;color:rgba(228,120,29,0.9);margin-bottom:0.3rem;">
                Table hidden for performance
            </div>
            <div style="font-size:0.85rem;color:#aaa;line-height:1.5;">
                {rows:,} rows &times; {cols} columns &nbsp;&middot;&nbsp;
                {rows * cols:,} cells &nbsp;&mdash;&nbsp;
                Use the selectors below to choose columns and rows for analysis.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Column multiselect ---
    prev_cols = st.session_state.get("selected_columns", [])
    valid_prev = [c for c in prev_cols if c in df.columns]

    # Inject CSS to give the multiselect dropdown enough width and prevent
    # the tag chips from overflowing the container.
    st.markdown(
        """
        <style>
        div[data-testid="stMultiSelect"] > div:first-child {
            min-width: 100%;
        }
        div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
            flex-wrap: wrap;
            min-height: 2.4rem;
            max-height: 8rem;
            overflow-y: auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    selected_cols = st.multiselect(
        "Columns for analysis",
        options=list(df.columns),
        default=valid_prev,
        key="_lf_col_select",
        help="Select one or more columns. All rows of these columns will be used in the analysis.",
    )
    st.session_state.selected_columns = selected_cols

    st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)

    # --- Row range ---
    row_mode = st.radio(
        "Rows to include",
        ["All rows", "Custom range"],
        horizontal=True,
        key="_lf_row_mode",
    )

    if row_mode == "All rows":
        # Empty list means "all rows" throughout the analysis flow —
        # avoids materializing a list of up to 1 M integers.
        st.session_state.selected_rows = []
    else:
        c_start, c_end = st.columns(2)
        with c_start:
            start_row = st.number_input(
                "From row", min_value=1, max_value=rows, value=1, step=1,
                key="_lf_row_start",
            )
        with c_end:
            end_row = st.number_input(
                "To row", min_value=1, max_value=rows, value=min(rows, 10_000), step=1,
                key="_lf_row_end",
            )
        if start_row > end_row:
            st.warning("Start row must be ≤ end row.")
            st.session_state.selected_rows = []
        else:
            st.session_state.selected_rows = list(range(int(start_row), int(end_row) + 1))

    # Sync last_grid_selection so checkbox reset logic works correctly
    new_sig = (tuple(st.session_state.selected_columns), tuple(st.session_state.selected_rows))
    st.session_state.last_grid_selection = new_sig

    st.markdown("<div style='margin-bottom:0.5rem'></div>", unsafe_allow_html=True)

    # --- Toggle to re-enable table ---
    if st.button("Show table preview", key="_lf_show_table_btn"):
        st.session_state.large_file_hide_table = False
        st.session_state._grid_version = st.session_state.get("_grid_version", 0) + 1
        st.session_state._row_data_version = st.session_state.get("_row_data_version", 0) + 1
        st.rerun()


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


def _display_aggrid_server(
    df: "pd.DataFrame",
    data_key: str,
    total_rows: int,
    grid_key: str,
) -> None:
    """
    Render the AG Grid for large files using a client-side sample.

    Passes the first _SAMPLE_DISPLAY_ROWS rows as rowData so the grid
    displays real data immediately without any networking or separate server.
    AG Grid virtual-scrolls those rows smoothly.

    Column-header clicks create a range that spans all *sample* rows
    (0 → sample_size-1).  normalize_grid_selection detects this via its
    total_rows parameter and maps it to col2=[] (all rows in the full
    dataset), so computations always run on the complete file.

    Args:
        df:         The full DataFrame.
        data_key:   Cache key (used for rename propagation).
        total_rows: Full row count (displayed in the banner).
        grid_key:   Unique AG Grid instance key.
    """
    sample_size = min(_SAMPLE_DISPLAY_ROWS, total_rows)
    sample_df = df.head(sample_size)

    # Build records — cached in session state so repeated reruns (e.g. checkbox
    # clicks on the right panel) don't re-serialize 10 K rows each time.
    cache_key = f"_sample_records_{data_key}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = (
            sample_df.where(pd.notna(sample_df), other=None).to_dict("records")
        )
    records = st.session_state[cache_key]

    columns = [{"field": c} for c in df.columns]

    # Banner above the grid
    if total_rows > sample_size:
        st.markdown(
            f"""
            <div style="
                background:rgba(228,120,29,0.08);
                border:1px solid rgba(228,120,29,0.30);
                border-radius:8px;
                padding:0.55rem 1rem;
                margin-bottom:0.5rem;
                font-size:0.83rem;
                color:#ccc;
                line-height:1.5;
            ">
                <span style="color:rgba(228,120,29,0.9);font-weight:600;">
                    Large file preview
                </span>
                &nbsp;&mdash;&nbsp;
                Showing first <strong>{sample_size:,}</strong> of
                <strong>{total_rows:,}</strong> rows.
                &nbsp;Click a column header to select <em>all {total_rows:,} rows</em>
                for analysis.
            </div>
            """,
            unsafe_allow_html=True,
        )

    result = aggrid_range(
        records, columns, key=grid_key,
        programmatic_ranges=st.session_state.get("_programmatic_ranges", []),
        programmatic_ranges_version=st.session_state.get("_programmatic_ranges_version", 0),
        row_data_version=st.session_state.get("_row_data_version", 0),
    )

    if isinstance(result, dict):
        selection = result.get("selections", [])
        edited_data = result.get("editedData")
        renamed_headers = result.get("renamedHeaders")
    else:
        selection = result
        edited_data = None
        renamed_headers = None

    # Apply cell edits back to the sample DataFrame
    if edited_data is not None:
        edited_df = pd.DataFrame(edited_data)
        if list(edited_df.columns) == list(sample_df.columns):
            # Update the sample portion of the cached DataFrame
            df.iloc[:sample_size] = edited_df.values
            st.session_state.edited_data_cache[data_key] = df
            # Invalidate sample records cache so edits are reflected
            st.session_state.pop(cache_key, None)

    # Apply header renames
    if renamed_headers and isinstance(renamed_headers, dict):
        rename_map = {}
        for old_name, new_name in renamed_headers.items():
            new_name = str(new_name).strip()
            if old_name in df.columns and new_name and new_name != old_name:
                rename_map[old_name] = new_name
        if rename_map:
            new_cols = [rename_map.get(c, c) for c in df.columns]
            if len(set(new_cols)) == len(new_cols):
                df = df.rename(columns=rename_map)
                st.session_state.edited_data_cache[data_key] = df
                st.session_state.pop(cache_key, None)
                st.session_state.selected_columns = []
                st.session_state.selected_rows = []
                st.session_state.last_grid_selection = None
                st.session_state.checkbox_key_onecol += 1
                st.session_state.checkbox_key_twocol += 1
                # Column field names changed — bump so the React component
                # re-seeds its internal rowData with the new keys.
                st.session_state._row_data_version = st.session_state.get("_row_data_version", 0) + 1

    # When a programmatic selection is in-flight, the component still returns
    # the previous (stale) selection.  Skip apply until the React effect has
    # applied the new ranges and sent them back via setComponentValue.
    if st.session_state.get("_programmatic_pending", 0) > 0:
        st.session_state._programmatic_pending -= 1
    else:
        # Pass sample_size as total_rows: a full-column selection (0→sample_size-1)
        # is recognised as "all rows" and returns col2=[] without materialising any list.
        apply_grid_selection_to_filters(selection, df, total_rows=sample_size)
        st.session_state["_raw_grid_selection"] = selection

    st.markdown("")
    st.caption(
        "**Large file mode** — "
        "Click a header to select a column (selects all rows for analysis). "
        "Ctrl+click for multiple columns. "
        "Double-click a header to rename it. "
        "Double-click a cell to edit it."
    )

    # Button to switch to manual selectors
    if st.button("Hide table (use manual selectors)", key="_srv_hide_table_btn"):
        st.session_state.large_file_hide_table = True
        st.rerun()

    if selection:
        _display_selection_output(selection, df)
    else:
        st.info("Select a range of cells in the grid to see details here.")


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

    result = aggrid_range(
        records, columns, key=grid_key,
        programmatic_ranges=st.session_state.get("_programmatic_ranges", []),
        programmatic_ranges_version=st.session_state.get("_programmatic_ranges_version", 0),
        row_data_version=st.session_state.get("_row_data_version", 0),
    )

    # The component returns {"selections": [...], "editedData": [...] | null, "renamedHeaders": {...} | null}
    if isinstance(result, dict):
        selection = result.get("selections", [])
        edited_data = result.get("editedData")
        renamed_headers = result.get("renamedHeaders")
    else:
        # Fallback for old format (list of ranges)
        selection = result
        edited_data = None
        renamed_headers = None

    # Apply cell edits back to the DataFrame.
    # edited_data is a list of row-dicts keyed by the column names the grid
    # knows about.  Only apply it when the keys actually match our current
    # columns so a stale payload from a previous grid mount can't corrupt df.
    if edited_data is not None:
        edited_df = pd.DataFrame(edited_data)
        if list(edited_df.columns) == list(df.columns):
            df = edited_df

    # Apply header renames from the grid component
    if renamed_headers and isinstance(renamed_headers, dict):
        rename_map = {}
        for old_name, new_name in renamed_headers.items():
            new_name = str(new_name).strip()
            if old_name in df.columns and new_name and new_name != old_name:
                rename_map[old_name] = new_name
        if rename_map:
            # Ensure no duplicate names
            new_cols = [rename_map.get(c, c) for c in df.columns]
            if len(set(new_cols)) == len(new_cols):
                df = df.rename(columns=rename_map)
                # Clear selection — column names changed so any prior selection
                # is invalid.  We do NOT bump _grid_version here: AG Grid
                # reconciles its columns in-place when Python passes updated
                # columnDefs props, so no remount is needed.  Bumping the key
                # here would force a jarring reload and then lose the user's
                # next selection attempt.
                st.session_state.selected_columns = []
                st.session_state.selected_rows = []
                st.session_state.last_grid_selection = None
                st.session_state.checkbox_key_onecol += 1
                st.session_state.checkbox_key_twocol += 1
                # Column field names changed — bump so the React component
                # re-seeds its internal rowData with the new keys.
                st.session_state._row_data_version = st.session_state.get("_row_data_version", 0) + 1

    # When a programmatic selection is in-flight, the component still returns
    # the previous (stale) selection.  Skip apply until the React effect has
    # applied the new ranges and sent them back via setComponentValue.
    if st.session_state.get("_programmatic_pending", 0) > 0:
        st.session_state._programmatic_pending -= 1
    else:
        apply_grid_selection_to_filters(selection, df)
        st.session_state["_raw_grid_selection"] = selection

    st.markdown("")
    st.caption("**Tip:** Click a header to select a column. "
               "Ctrl+click headers to select multiple columns. "
               "Double-click a header to rename it. "
               "Double-click a cell to edit its value.")

    if selection:
        _display_selection_output(selection, df)
    else:
        st.info("Select a range of cells in the grid to see details here.")

    return df


def _display_selection_output(selection: list, df: pd.DataFrame) -> None:
    """
    Show selected ranges Excel-style: a reference bar + per-range labeled tables.
    """
    st.markdown("---")

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

        # Build per-column refs: ColName[1]:ColName[7]
        r0, r1 = rows_1[0], rows_1[-1]
        refs = [
            f"{col}[{r0}]:{col}[{r1}]" if r0 != r1 else f"{col}[{r0}]"
            for col in valid_cols
        ]

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
    total_cells = sum(len(ri["rows_1"]) * len(ri["cols"]) for ri in ranges_info)
    range_word  = "range" if len(ranges_info) == 1 else "ranges"
    _TAG = (
        "background:#2d2d2d; border:1px solid #555; border-radius:4px;"
        " padding:0.15rem 0.5rem; font-family:monospace; font-size:0.82rem;"
        " color:#e4781d; white-space:nowrap;"
    )
    tags_html = "".join(
        f'<span style="{_TAG}">{ref}</span>'
        for ri in ranges_info for ref in ri["refs"]
    )

    st.markdown(
        f"""
        <div style="
            display:flex; align-items:center; flex-wrap:wrap; gap:0.4rem;
            background:#1e1e1e; border:1px solid #444;
            border-radius:6px; padding:0.4rem 0.8rem; margin-bottom:0.6rem;
        ">
            {tags_html}
            <span style="color:#888; font-size:0.8rem; margin-left:0.35rem;">
                {total_cells} cell{'s' if total_cells != 1 else ''}
                &nbsp;&middot;&nbsp; {len(ranges_info)} {range_word}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Per-range labeled tables ──────────────────────────────────────────
    for i, ri in enumerate(ranges_info):
        col_str = ", ".join(ri["cols"])
        row_str = (
            f"rows {ri['rows_1'][0]}–{ri['rows_1'][-1]}"
            if len(ri["rows_1"]) > 1
            else f"row {ri['rows_1'][0]}"
        )
        ref_str = "  ".join(ri["refs"])
        label = (
            f"**Range {i + 1}** &nbsp; "
            + "".join(
                f'<span style="background:#2d2d2d;border:1px solid #555;border-radius:4px;'
                f'padding:0.1rem 0.4rem;font-family:monospace;font-size:0.78rem;'
                f'color:#e4781d;margin-right:0.3rem;">{ r }</span>'
                for r in ri["refs"]
            )
            + f"<span style='color:#888;font-size:0.82rem;'>&nbsp; {col_str} · {row_str} · "
            + f"{len(ri['rows_1'])} × {len(ri['cols'])}</span>"
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
    st.markdown("# **Analysis Configuration**")

    data_ready = (
        edited_table is not None
        and len(edited_table.columns) > 0
        and len(edited_table) > 0
    )

    col1, col2, range_error = _render_column_row_selectors(edited_table, data_ready)

    # --- Compute data characteristics for smart checkbox disabling ---
    data_info = _compute_data_info(edited_table, col1, col2, data_ready)

    st.markdown("---")

    mean, median, mode, variance, std, percentiles, \
        pearson, spearman, least_squares_regression, chi_squared, variation, \
        custom_flags, invalid_params = \
        _render_computation_options(data_ready, col1, col2, data_info)

    st.markdown("---")

    hist, box, scatter, line, heatmap, binomial = _render_visualization_options(data_ready, col1, data_info)

    st.markdown('---')
    st.markdown('<div class="run-analysis-anchor"></div>', unsafe_allow_html=True)

    computation_selected = any([
        mean, median, mode, variance, std, percentiles,
        pearson, spearman, least_squares_regression, chi_squared, variation,
        hist, box, scatter, line, heatmap, binomial,
    ] + list(custom_flags.values()))

    _handle_run_analysis(
        edited_table=edited_table,
        data_ready=data_ready,
        computation_selected=computation_selected,
        col1=col1,
        col2=col2,
        # A parse error in the range input blocks computation just like any
        # other invalid parameter (the button is shown disabled with a warning).
        invalid_params=invalid_params or bool(range_error),
        mean=mean, median=median, mode=mode,
        variance=variance, std=std, percentiles=percentiles,
        pearson=pearson, spearman=spearman, least_squares_regression=least_squares_regression,
        chi_squared=chi_squared, binomial=binomial, variation=variation,
        hist=hist, box=box, scatter=scatter, line=line, heatmap=heatmap,
        custom_flags=custom_flags,
    )


# ---------------------------------------------------------------------------
# Reference Bar helper
# ---------------------------------------------------------------------------

def _build_refs(cols: list, rows: list) -> list[str]:
    """
    Build per-column cell reference strings in Col[R0]:Col[R1] format.

    Examples:
        cols=["ID"],         rows=[1..7]  →  ["ID[1]:ID[7]"]
        cols=["ID","Age"],   rows=[1..7]  →  ["ID[1]:ID[7]", "Age[1]:Age[7]"]
        cols=["Name"],       rows=[3]     →  ["Name[3]"]
    """
    if not cols or not rows:
        return [col for col in cols] if cols else []
    r0, r1 = rows[0], rows[-1]
    return [f"{col}[{r0}]:{col}[{r1}]" if r0 != r1 else f"{col}[{r0}]" for col in cols]


def _render_column_row_selectors(
    edited_table: pd.DataFrame | None,
    data_ready: bool,
) -> tuple[list, list, str]:
    """
    Render an editable Excel-style selection input and return the current
    column/row selection plus any parse error.

    The input is pre-populated from the grid drag-selection and can be edited
    directly: typing a range and pressing Enter highlights the matching cells
    in the table and updates the selection for analysis.

    Supported input format
    ----------------------
    ``ColName``                    → whole column, all rows
    ``ColName[5]``                 → single cell (row 5)
    ``ColName[5]:ColName[20]``     → rows 5–20 of ColName
    ``ColA[5]:ColB[20]``           → rectangular range across ColA–ColB, rows 5–20
    Comma-separated for multiple ranges: ``A[1]:A[50], B[1]:B[50]``

    Returns
    -------
    (col1, col2, range_error)
    col1        : list of selected column names
    col2        : list of 1-based row ints (empty = all rows)
    range_error : non-empty string when the input is invalid (disables Run Analysis)
    """
    col1 = st.session_state.get("selected_columns", []) if data_ready else []
    col2 = st.session_state.get("selected_rows",    []) if data_ready else []

    # ------------------------------------------------------------------
    # Sync text input from grid selection when the grid changed
    # (but not when the change came from the user typing a range).
    # ------------------------------------------------------------------
    current_sig  = (tuple(col1), tuple(col2))
    last_sig     = st.session_state.get("_range_text_sig")
    range_typed  = st.session_state.pop("_range_typed", False)

    if not range_typed and last_sig != current_sig:
        # Grid drag (or header click) changed the selection → update input.
        raw = st.session_state.get("_raw_grid_selection") or []
        new_text = _compute_ref_string(col1, col2, raw, edited_table)
        st.session_state["_range_input_text"] = new_text
        st.session_state["_range_text_sig"]   = current_sig
        # A new grid selection supersedes any previous parse error.
        st.session_state["_range_input_error"] = ""

    # ------------------------------------------------------------------
    # Editable range input (hidden-table mode shows a plain hint instead)
    # ------------------------------------------------------------------
    hide_table = st.session_state.get("large_file_hide_table", False)

    if not hide_table and data_ready and edited_table is not None:
        n_displayed = _get_n_displayed(edited_table)

        st.markdown(
            """
            <style>
            /* Give the range input the same dark pill look as the old ref-bar */
            div[data-testid="stTextInput"] input[data-testid="stTextInputField"] {
                background: #1e1e1e;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 0.35rem 0.8rem;
                font-family: monospace;
                font-size: 0.82rem;
                color: #e4781d;
            }
            div[data-testid="stTextInput"] input[data-testid="stTextInputField"]:focus {
                border-color: rgba(228,120,29,0.7);
                box-shadow: 0 0 0 2px rgba(228,120,29,0.2);
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.text_input(
            "Selection",
            key="_range_input_text",
            placeholder='e.g. "ColumnA[1]:ColumnA[100]"  or  "ColumnA"',
            label_visibility="collapsed",
            on_change=_on_range_input_change,
            args=(edited_table, n_displayed),
            help=(
                "Type a cell range and press Enter to highlight it in the table.\n\n"
                "**Examples**\n"
                "- `Age` — whole column\n"
                "- `Age[1]:Age[100]` — rows 1–100\n"
                "- `Age[5]:Score[5]` — rectangular range Age→Score at row 5\n"
                "- `Age[1]:Age[50], Score[1]:Score[50]` — two separate ranges\n\n"
                "Or simply drag-select cells directly in the table."
            ),
        )

        range_error = st.session_state.get("_range_input_error", "")
        if range_error:
            _param_warning(f"Invalid selection — {range_error}")
    else:
        range_error = ""
        if hide_table:
            hint = "No selection &mdash; use the column selectors on the left"
        else:
            hint = "No selection &mdash; drag cells in the grid"
        st.markdown(
            f"""
            <div style="
                display:flex; align-items:center;
                background:#1e1e1e; border:1px solid #333;
                border-radius:6px; padding:0.4rem 0.8rem;
            ">
                <span style="color:#555; font-size:0.82rem; font-family:monospace;">
                    {hint}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --- Measurement-level tagging per selected column (Req 4.1-4.2) ---
    _MEASUREMENT_LEVELS = ["Nominal", "Ordinal", "Interval", "Ratio"]
    if col1 and data_ready and edited_table is not None:
        with st.expander("Column Measurement Types", expanded=False):
            ml_dict = st.session_state.get("column_measurement_levels", {})
            for c in col1:
                # Auto-detect default: numeric → Interval, text → Nominal
                if c not in ml_dict:
                    coerced = pd.to_numeric(edited_table[c], errors="coerce")
                    ml_dict[c] = "Interval" if coerced.notna().all() and len(coerced) > 0 else "Nominal"
                ml_dict[c] = st.selectbox(
                    c,
                    _MEASUREMENT_LEVELS,
                    index=_MEASUREMENT_LEVELS.index(ml_dict.get(c, "Nominal")),
                    key=f"ml_{c}",
                )
            # Remove stale entries for columns no longer selected
            ml_dict = {k: v for k, v in ml_dict.items() if k in col1}
            st.session_state["column_measurement_levels"] = ml_dict
        st.markdown("<div style='margin-bottom: 0.75rem;'></div>", unsafe_allow_html=True)
    else:
        st.session_state["column_measurement_levels"] = {}

    # --- Checkbox reset logic (unchanged behaviour) ---
    prev_cols = st.session_state.get("last_cols_selected", [])
    if len(prev_cols) > 0 and len(col1) == 0:
        st.session_state.checkbox_key_onecol += 1
    st.session_state.last_cols_selected = col1
    st.session_state["current_cols"] = col1

    if st.session_state.get("last_num_cols", 0) >= 2 and len(col1) < 2:
        st.session_state.checkbox_key_twocol += 1
    st.session_state.last_num_cols = len(col1)

    return col1, col2, range_error


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
            "num_interval_ratio": 0,
            "num_ordinal_plus": 0,
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
    numeric_cols: set = set()
    for c in subset.columns:
        coerced = pd.to_numeric(subset[c], errors="coerce")
        if coerced.notna().all() or subset[c].isna().all():
            numeric_count += 1
            numeric_cols.add(c)

    # Measurement-level counts — only count columns that are also numeric.
    # A column tagged "Ratio" but containing strings would still fail at
    # float-cast in the backend, so it must not enable any method.
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
        - Float-casting methods require ALL selected columns to be numeric
          (a single non-numeric column causes the backend cast to fail).
          n_ir / n_ord only count columns that are both numeric AND tagged
          at the appropriate measurement level.
        - Mean, Std Dev:
              disabled unless all columns numeric AND ≥1 Interval/Ratio column
        - Median, Percentile:
              disabled unless all columns numeric AND ≥1 Ordinal/Interval/Ratio column
        - Variance: same as Mean/Std Dev plus ≥2 rows (sample variance, ddof=1)
        - Mode: disabled if no numeric column (any measurement level)
        - Pearson: all numeric, ≥2 Interval/Ratio columns, ≥3 rows
        - Spearman: all numeric, ≥2 Ordinal+ columns, ≥3 rows
        - Least Squares Regression: all numeric, ≥2 I/R columns, ≥2 rows
        - Chi-Square: all selected columns numeric AND ≥2 rows
        - Coefficient of Variation: all numeric AND ≥1 Interval/Ratio column

    Returns:
        Tuple of 11 booleans + custom_flags dict + invalid_params bool.
    """
    st.markdown("## Computation Options")

    # --- Derive disable flags from data_info ---
    n_cols = data_info["num_selected_cols"]
    n_num  = data_info["num_numeric_cols"]
    n_rows = data_info["num_rows"]
    has_num = data_info["has_numeric"]
    all_num = data_info["all_numeric"]
    n_ir   = data_info.get("num_interval_ratio", 0)  # interval/ratio columns
    n_ord  = data_info.get("num_ordinal_plus", 0)     # ordinal+ columns

    # Float-casting methods require ALL selected columns to be numeric —
    # a single non-numeric column causes the backend cast to fail.
    # n_ir / n_ord already only count columns that are both numeric and
    # tagged at the right measurement level (enforced in _compute_data_info).

    dis_one_col = not data_ready or not all_num or n_cols < 1
    dis_two_col = not data_ready or not all_num or n_cols < 2

    # If user drops from >=2 columns to 1 column,
    # reset two-column statistical method checkboxes
    k1 = st.session_state.checkbox_key_onecol
    k2 = st.session_state.checkbox_key_twocol

    c1, c2 = st.columns(2)

    with c1:
        mean        = st.checkbox("Mean",                disabled=dis_one_col, key=f"mean_c1_{k1}")        and not dis_one_col
        median      = st.checkbox("Median",              disabled=dis_one_col, key=f"median_c1_{k1}")      and not dis_one_col
        mode        = st.checkbox("Mode",                disabled=dis_one_col, key=f"mode_c1_{k2}")        and not dis_one_col
        variance    = st.checkbox("Variance",            disabled=dis_one_col, key=f"variance_c1_{k2}")    and not dis_one_col
        std         = st.checkbox("Standard Deviation",  disabled=dis_one_col, key=f"std_c1_{k1}")         and not dis_one_col
        percentiles = st.checkbox("Percentiles",         disabled=dis_one_col, key=f"percentiles_c1_{k1}") and not dis_one_col

    with c2:
        pearson                  = st.checkbox("Pearson's Correlation",    disabled=dis_two_col, key=f"pearson_c2_{k2}")    and not dis_two_col
        spearman                 = st.checkbox("Spearman's Rank",          disabled=dis_two_col, key=f"spearman_c2_{k2}")   and not dis_two_col
        least_squares_regression = st.checkbox("Least Squares Regression", disabled=dis_two_col, key=f"lsr_c2_{k2}")        and not dis_two_col
        chi_squared              = st.checkbox("Chi-Square Test",          disabled=dis_one_col, key=f"chi_squared_c2_{k2}") and not dis_one_col
        variation                = st.checkbox("Coefficient of Variation", disabled=dis_one_col, key=f"variation_c2_{k2}")  and not dis_one_col

    # --- Conditional parameter inputs (appear inline when the method is checked) ---
    invalid_params = False

    if percentiles:
        st.markdown("**Percentile Parameters**")
        pcol, _ = st.columns([2, 1])
        with pcol:
            percentile_input_val = st.text_input(
                "Values (comma-separated)",
                value="25, 50, 75",
                key="percentile_values_input",
                placeholder="e.g. 10, 25, 50, 75, 90",
                help="Enter any values between 0 and 100, separated by commas.",
                disabled=dis_one_col,
            )
        try:
            parsed_pcts = [float(v.strip()) for v in percentile_input_val.split(",") if v.strip()]
            if not parsed_pcts or any(v < 0 or v > 100 for v in parsed_pcts):
                invalid_params = True
                with pcol:
                    _param_warning("Values must be numbers between 0 and 100.")
        except ValueError:
            invalid_params = True
            with pcol:
                _param_warning("Values must be valid numbers between 0 and 100.")

    # --- Custom methods ---
    custom_flags = _render_custom_method_checkboxes(data_ready, col1, data_info)

    st.session_state["_analysis_invalid_params"] = invalid_params

    return (
        mean, median, mode, variance, std, percentiles,
        pearson, spearman, least_squares_regression, chi_squared, variation,
        custom_flags, invalid_params,
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

    st.markdown("### Custom Methods")

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
        "cm_import_file",
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


def _format_tool_option_label(tool: dict) -> str:
    """Build a user-friendly toolbox label that distinguishes standard/custom methods."""
    source_label = "Standard" if tool.get("source") == "standard" else "Custom"
    return f"{tool['display_name']} ({source_label})"


def _render_custom_method_transfer_controls():
    """Render export/import controls for the current custom method bundle."""
    registry = load_custom_methods_registry()
    method_count = len(registry)
    exportable_names = {entry["display_name"]: entry["id"] for entry in registry}

    st.markdown("### Transfer Custom Methods")
    st.caption(
        f"You currently have {method_count} custom method(s). "
        "Export a selected bundle or import a previously exported one."
    )

    selected_export_names = []
    if exportable_names:
        selected_export_names = st.multiselect(
            "Choose custom methods to export",
            options=list(exportable_names.keys()),
            default=list(exportable_names.keys()),
            key="cm_export_selection",
            help=(
                "Pick the custom methods to include in the bundle. "
                "Built-in standard methods stay available automatically and are not exported."
            ),
        )

    selected_export_ids = [exportable_names[name] for name in selected_export_names]
    include_dependencies = st.checkbox(
        "Also include any custom-method dependencies",
        value=True,
        key="cm_export_include_dependencies",
        disabled=not selected_export_ids,
    )
    st.caption(
        "⚠ If a selected custom method depends on other custom methods, "
        "include those helper methods automatically."
    )

    bundle_json = export_custom_methods_bundle(
        selected_method_ids=selected_export_ids or [],
        include_dependencies=include_dependencies,
    )
    exported_method_count = len(json.loads(bundle_json).get("methods", []))
    bundle_name = f"custom_methods_export_{time.strftime('%Y%m%d_%H%M%S')}.json"

    st.caption(
        f"The current export will include {exported_method_count} custom method(s). "
        "Standard built-in methods remain available automatically after import."
    )

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Export Selection",
            data=bundle_json,
            file_name=bundle_name,
            mime="application/json",
            use_container_width=True,
            key="cm_export_btn",
            disabled=not selected_export_ids,
        )

    with c2:
        import_clicked = st.button(
            "Import Bundle",
            key="cm_import_btn",
            use_container_width=True,
        )

    uploaded_bundle = st.file_uploader(
        "Import custom methods JSON",
        type=["json"],
        key="cm_import_file",
        label_visibility="collapsed",
    )

    if import_clicked:
        if uploaded_bundle is None:
            st.warning("Choose a JSON export file before importing.")
        else:
            summary = import_custom_methods_bundle(uploaded_bundle.getvalue())
            if summary["imported"]:
                _after_method_change()

            st.session_state["cm_import_summary"] = summary
            st.rerun()

    summary = st.session_state.get("cm_import_summary")
    if summary:
        imported = summary.get("imported", [])
        duplicates = summary.get("skipped_duplicates", [])
        invalid = summary.get("skipped_invalid", [])

        if imported:
            imported_names = ", ".join(item["display_name"] for item in imported)
            st.success(
                f"Imported {len(imported)} custom method(s): {imported_names}"
            )
        elif not duplicates and not invalid:
            st.info("No custom methods were imported.")

        if duplicates:
            duplicate_lines = "\n".join(
                f"- {item['display_name'] or item['id']}: {item['reason']}"
                for item in duplicates
            )
            st.warning(
                "Skipped duplicate custom methods:\n"
                f"{duplicate_lines}"
            )

        if invalid:
            invalid_lines = "\n".join(
                f"- {(item['display_name'] or item['id'] or 'Unknown entry')}: {item['reason']}"
                for item in invalid
            )
            st.error(
                "Some custom methods could not be imported:\n"
                f"{invalid_lines}"
            )


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
        "and `toolbox` (dict of callable built-in and custom methods). "
        "`numpy` is imported as `np` in the generated file."
    )

    # --- Toolbox: dependency selection ---
    available_tools = get_available_tools_info()
    if available_tools:
        tool_options = {
            _format_tool_option_label(t): t["id"]
            for t in available_tools
        }
        selected_tool_names = st.multiselect(
            "Use toolbox methods",
            options=list(tool_options.keys()),
            help=(
                "Select built-in or custom methods this method depends on. "
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
    if st.button("Check Code", use_container_width=True):
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

@st.dialog("Edit Custom Method", width="large")
def _edit_method_dialog():
    """Dialog to select an existing custom method and edit it."""
    registry = load_custom_methods_registry()
    if not registry:
        st.info("No custom methods to edit.")
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
        "and `toolbox` (dict of callable built-in and custom methods). "
        "`numpy` is imported as `np` in the generated file."
    )

    # --- Toolbox: dependency selection ---
    available_tools = get_available_tools_info(exclude_id=method_id)
    existing_deps = entry.get("dependencies", [])
    if available_tools:
        tool_options = {
            _format_tool_option_label(t): t["id"]
            for t in available_tools
        }
        default_names = [
            label for label, tool_id in tool_options.items()
            if tool_id in existing_deps
        ]
        selected_tool_names = st.multiselect(
            "Use toolbox methods",
            options=list(tool_options.keys()),
            default=default_names,
            help=(
                "Select built-in or custom methods this method depends on. "
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
    """Dialog to select an existing custom method and edit it."""
    registry = load_custom_methods_registry()
    if not registry:
        st.info("No custom methods to delete.")
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


# ========================= MANAGE DIALOG ====================================

@st.dialog("**Manage Custom Methods**", width="large")
def _manage_methods_dialog():
    """Central hub for create/edit/delete/export/import custom method actions."""
    registry = load_custom_methods_registry()

    st.markdown(
        "Manage your saved custom methods from one place. "
        "Open the create, edit, or delete dialogs, or transfer methods with export/import."
    )
    st.caption(f"Currently saved: {len(registry)} custom method(s)")

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Create", key="cm_manage_create_btn", use_container_width=True):
            st.session_state["cm_pending_dialog"] = "create"
            st.rerun()
    with b2:
        if st.button("Edit", key="cm_manage_edit_btn", use_container_width=True):
            st.session_state["cm_pending_dialog"] = "edit"
            st.rerun()
    with b3:
        if st.button("Delete", key="cm_manage_delete_btn", use_container_width=True):
            st.session_state["cm_pending_dialog"] = "delete"
            st.rerun()

    st.markdown("---")
    _render_custom_method_transfer_controls()


# ========================= SINGLE ENTRY BUTTON ==============================

def _user_defined_computation_options():
    """
    Render a single entry point for custom method management.
    """
    if st.button("Manage", key="cm_manage_btn", use_container_width=True):
        _manage_methods_dialog()

    # Handle sub-dialog routing set from within _manage_methods_dialog.
    # Calling @st.dialog functions directly inside another @st.dialog raises
    # StreamlitAPIException, so we set a flag and rerun instead.
    pending = st.session_state.pop("cm_pending_dialog", None)
    if pending == "create":
        _create_method_dialog()
    elif pending == "edit":
        _edit_method_dialog()
    elif pending == "delete":
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
    col1: list,
    data_info: dict,
) -> tuple:
    """
    Render the 5 visualization checkboxes.

    Charts can be selected independently of statistical methods.

    Args:
        data_ready: Whether a valid DataFrame is loaded.

    Returns:
        Tuple of 5 booleans: (hist, box, scatter, line, heatmap)
    """
    st.markdown("## Visualization Options")

    disable_one_col      = not data_ready or len(col1) < 1
    disable_two_cols     = not data_ready or len(col1) < 2
    disable_one_col_num  = not data_ready or not data_info["all_numeric"]
    disable_two_cols_num = not data_ready or len(col1) < 2 or not data_info["all_numeric"]

    v1, v2 = st.columns(2)

    with v1:
        hist    = st.checkbox("Pie Chart",                     key="viz_hist",    disabled=disable_one_col)  and not disable_one_col
        box     = st.checkbox("Vertical Bar Chart",            key="viz_box",     disabled=disable_one_col)  and not disable_one_col
        scatter = st.checkbox("Horizontal Bar Chart",          key="viz_scatter", disabled=disable_one_col)  and not disable_one_col

    with v2:
        line    = st.checkbox("Scatter Plot",                  key="viz_line",    disabled=disable_two_cols_num) and not disable_two_cols_num
        heatmap = st.checkbox("Line of Best Fit Scatter Plot", key="viz_heatmap", disabled=disable_two_cols_num) and not disable_two_cols_num
        binomial = st.checkbox("Binomial Distribution",        key="viz_binomial", disabled=disable_one_col_num) and not disable_one_col_num

    # --- Binomial parameter inputs (below the checkbox) ---
    # --- Binomial parameter inputs (below the checkbox) ---
    if binomial and not disable_one_col_num:
        st.markdown("**Binomial Parameters**")
        bn1, bn2, bn3, bn4 = st.columns(4)
        with bn1:
            st.number_input(
                "n (trials)", min_value=1, max_value=100000,
                value=10, step=1,
                key="binomial_n",
                help="Total number of trials.",
                disabled=disable_one_col_num,
            )
        with bn2:
            st.number_input(
                "p (probability)", min_value=0.0, max_value=1.0,
                value=0.5, step=0.01, format="%.4f",
                key="binomial_p",
                help="Probability of success on each trial (0 – 1).",
                disabled=disable_one_col_num,
            )
        with bn3:
            st.number_input(
                "k min", min_value=0,
                value=0, step=1,
                key="binomial_k_min",
                help="Minimum number of successes (start of k-range).",
                disabled=disable_one_col_num,
            )
        with bn4:
            st.number_input(
                "k max", min_value=0,
                value=10, step=1,
                key="binomial_k_max",
                help="Maximum number of successes (end of k-range).",
                disabled=disable_one_col_num,
            )
    k_min_val = st.session_state.get("binomial_k_min", 0)
    k_max_val = st.session_state.get("binomial_k_max", 10)
    if k_min_val > k_max_val:
        _param_warning("k min must be ≤ k max.")
        st.session_state["_analysis_invalid_params"] = True
        k_min_val = st.session_state.get("binomial_k_min", 0)
        k_max_val = st.session_state.get("binomial_k_max", 10)
        if k_min_val > k_max_val:
            _param_warning("k min must be \u2264 k max.")
            st.session_state["_analysis_invalid_params"] = True

    # --- Label count warnings for pie/bar charts ---
    n_rows = data_info.get("num_rows", 0)
    if hist or box or scatter:
        chart_lines = []
        if hist and n_rows >= 35:
            chart_lines.append("**Pie Chart:** Looks best with up to 35 labels. Beyond that, slices become difficult to distinguish.")
        if (box or scatter) and n_rows >= 30:
            chart_lines.append("**Bar Charts:** Looks best with up to 80 labels. Value labels inside bars are hidden when there are more than 30 labels.")
        if chart_lines:
            st.info("\n\n".join(chart_lines))

    return hist, box, scatter, line, heatmap, binomial


# ---------------------------------------------------------------------------
# Run creation
# ---------------------------------------------------------------------------

def _handle_run_analysis(
    edited_table: pd.DataFrame,
    data_ready: bool,
    computation_selected: bool,
    col1: list,
    col2: list,
    invalid_params: bool = False,
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
    _invalid = st.session_state.get("_analysis_invalid_params", False) or invalid_params

    run_clicked = st.button(
        "Run Analysis",
        key="run_analysis",
        use_container_width=True,
        disabled=not (data_ready and computation_selected) or already_computing or _invalid
    )

    if not run_clicked:
        return

    # --- Slice to selected columns and rows ---
    # Convert to 1-based index so row selections align with multiselect values
    if edited_table is not None:
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
    else:
        # Binomial can run from manual parameters without any uploaded dataset.
        parsed_data = pd.DataFrame()

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
        "table":          edited_table if edited_table is not None else pd.DataFrame(),
        "data":           parsed_data.reset_index(drop=True),
        "columns":        col1,
        "rows":           col2,
        "measurement_levels": dict(st.session_state.get("column_measurement_levels", {})),
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

# ---------------------------------------------------------------------------
# Light/Dark Mode Theme Toggler
# ---------------------------------------------------------------------------
def render_theme_toggle():
    '''
    Theme Toggle that inverts the HTML of an entire page
    '''
    _moon_b64 = _MOON_ICON_B64
    _sun_b64  = _SUN_ICON_B64
    _light_css = _light_css = """
        html {
            filter: invert(1) !important;
        }

        /* Keep squirrel assets visually normal in light mode (double invert). */
        #ps-success-toast img,
        #ps-loading-overlay img,
        #ps-computing-toast img,
        img.ps-squirrel {
            filter: invert(1) !important;
        }
    """
    components.html(
        f"""
        <script>
        (function() {{
            const moonB64 = "{_moon_b64}";
            const sunB64  = "{_sun_b64}";
            nowDark = true;
            const STORAGE_KEY = "ps_analytics_theme";
            const STYLE_ID    = "ps-light-mode-overrides";
            const LIGHT_CSS   = `{_light_css}`;

            function isDark() {{
                return (localStorage.getItem(STORAGE_KEY) || "dark") === "dark";
            }}

            function applyTheme(dark) {{
                const doc = window.parent.document;
                let styleEl = doc.getElementById(STYLE_ID);
                if (!dark) {{
                    if (!styleEl) {{
                        styleEl = doc.createElement("style");
                        styleEl.id = STYLE_ID;
                        doc.head.appendChild(styleEl);
                    }}
                    styleEl.textContent = LIGHT_CSS;
                }} else {{
                    if (styleEl) styleEl.remove();
                }}
            }}

            function renderBtn() {{
                const doc = window.parent.document;
                const old = doc.getElementById("ps-theme-btn");
                if (old) old.remove();

                const dark = isDark();
                const btn  = doc.createElement("button");
                btn.id = "ps-theme-btn";
                btn.dataset.isDark = String(dark);
                btn.title = dark ? "Switch to Light Mode" : "Switch to Dark Mode";
                btn.style.cssText = [
                    "position:absolute",
                    "top:16px",
                    "right:122px",
                    "z-index:99999",
                    "width:27.99px",
                    "height:27.99px",
                    "padding:4px",
                    "border-radius:6px",
                    "border:1px solid rgba(228,120,29,0.45)",
                    "background:rgba(228,120,29,0.12)",
                    "cursor:pointer",
                    "display:flex",
                    "align-items:center",
                    "justify-content:center",
                    "transition:background 0.2s"
                ].join(";");

                const img = doc.createElement("img");
                img.src = dark
                    ? "data:image/png;base64," + sunB64
                    : "data:image/png;base64," + moonB64;
                const iconSize = dark ? "16px" : "22px";
                img.style.cssText = "width:" + iconSize + ";height:" + iconSize + ";object-fit:contain;filter:invert(1)";
                btn.appendChild(img);

                btn.addEventListener("mouseenter", () => {{
                    btn.style.background = "rgba(228,120,29,0.28)";
                }});
                btn.addEventListener("mouseleave", () => {{
                    btn.style.background = "rgba(228,120,29,0.12)";
                }});
                btn.addEventListener("click", () => {{
                    localStorage.setItem(STORAGE_KEY, nowDark ? "light" : "dark");
                    applyTheme(!nowDark);
                    nowDark = isDark();
                    renderBtn();
                }});

                const container = doc.querySelector('[data-testid="stAppViewContainer"]') || doc.body;
                container.appendChild(btn);
            }}

            applyTheme(isDark());
            if (window.parent.document.body) {{
                renderBtn();
            }} else {{
                window.parent.addEventListener("DOMContentLoaded", renderBtn);
            }}
        }})();
        </script>
        """,
        height=0,
        
    )