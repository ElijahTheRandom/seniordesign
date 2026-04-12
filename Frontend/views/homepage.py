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

_favicon_icons = json.dumps([
    _img_to_b64("ps_main_man.png"),
    _img_to_b64("ElijahSquirrel.png"),
    _img_to_b64("AshtonSquirrel.png"),
    _img_to_b64("ChrisSquirrel.png"),
    _img_to_b64("HyattSquirrel.png"),
    _img_to_b64("SamSquirrel.png"),
])

def _get_theme_icon_b64(filename: str) -> str:
    """Load a theme icon (moon/sun) from the assets folder as base64."""
    path = Path(BASE_DIR) / "pages" / "assets" / filename
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

_MOON_ICON_B64 = _get_theme_icon_b64("moonIcon.png")
_SUN_ICON_B64  = _get_theme_icon_b64("sunIcon.png")

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
    col_img, col_text = st.columns([1, 1.5], gap="medium")
    with col_img:
        st.image(img_path, width=500)
    with col_text:
        st.markdown(st.session_state.modal_message)
# ---------------------------------------------------------------------------
# Header detection helpers
# ---------------------------------------------------------------------------

def _col_letter(index: int) -> str:
    """Convert a zero-based column index to Excel-style letters (A, B, ..., AA)."""
    if index < 0:
        return "A"

    letters = ""
    n = index
    while True:
        n, remainder = divmod(n, 26)
        letters = chr(ord("A") + remainder) + letters
        if n == 0:
            break
        n -= 1
    return letters

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

def render_homepage(base_dir: str) -> None:
    """
    Render the full homepage: data input (left) + analysis config (right).

    Args:
        base_dir: Absolute path to the frontend directory. Used to
                  resolve asset paths passed down to child functions.
    """

    components.html(
        f"""
        <script>
        (function() {{
            const icons = {_favicon_icons};
            let i = 0;
            function rotateFavicon() {{
                let link = window.parent.document.querySelector("link[rel~='icon']");
                if (!link) {{
                    link = window.parent.document.createElement("link");
                    link.rel = "icon";
                    window.parent.document.head.appendChild(link);
                }}
                link.type = "image/png";
                link.href = "data:image/png;base64," + icons[i % icons.length];
                i++;
            }}
            rotateFavicon();
            setInterval(rotateFavicon, 1000);
        }})();
        </script>
        """,
        height=0,
    )
        
    # # ------------------------------------------------------------------
    # # Theme toggle: floating moon/sun button in the top-right toolbar area.
    # # Injects a <style> tag into the parent document to override Streamlit's
    # # CSS variables with a light-mode palette when active.
    # # ------------------------------------------------------------------
    _moon_b64 = _MOON_ICON_B64
    _sun_b64  = _SUN_ICON_B64
    _light_css = _light_css = """
        html {
            filter: invert(1) !important;
        }
        html img,
        html video,
        html [data-testid="stImage"] img {
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
                img.style.cssText = "width:22px;height:22px;object-fit:contain;filter:invert(1)";
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
                "measurement_levels": meta.get("measurement_levels", {}),
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
    for key in ("uploaded_file", "saved_table", "edited_data_cache",
                 "_csv_loading", "_csv_future", "_raw_grid_selection", "_csv_raw_bytes"):
        st.session_state.pop(key, None)

    # Clear per-file header detection state
    for key in list(st.session_state.keys()):
        if key.startswith(("_headers_detected_", "_has_headers_")):
            del st.session_state[key]

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
        return None


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
        return None


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

    # Apply cell edits back to the DataFrame
    if edited_data is not None:
        df = pd.DataFrame(edited_data, columns=df.columns)

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
                # Reset column selections since names changed
                st.session_state.selected_columns = []
                st.session_state.selected_rows = []
                st.session_state.checkbox_key_onecol += 1
                st.session_state.checkbox_key_twocol += 1

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

        # Build per-column refs: ColName1:ColName7
        r0, r1 = rows_1[0], rows_1[-1]
        refs = [
            f"{col}{r0}:{col}{r1}" if r0 != r1 else f"{col}{r0}"
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

    col1, col2 = _render_column_row_selectors(edited_table, data_ready)

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
        invalid_params=invalid_params,
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
    Build per-column cell reference strings in ColR0:ColR1 format.

    Examples:
        cols=["ID"],         rows=[1..7]  →  ["ID1:ID7"]
        cols=["ID","Age"],   rows=[1..7]  →  ["ID1:ID7", "Age1:Age7"]
        cols=["Name"],       rows=[3]     →  ["Name3"]
    """
    if not cols or not rows:
        return [col for col in cols] if cols else []
    r0, r1 = rows[0], rows[-1]
    return [f"{col}{r0}:{col}{r1}" if r0 != r1 else f"{col}{r0}" for col in cols]


def _render_column_row_selectors(
    edited_table: pd.DataFrame | None,
    data_ready: bool
) -> tuple[list, list]:
    """
    Show a read-only Excel-style reference bar reflecting the current AG Grid
    drag-selection, then return the selected columns and rows for downstream use.

    The user makes their selection by dragging over cells in the grid on the
    left.  apply_grid_selection_to_filters() (called inside _display_aggrid)
    writes the normalised result to session state.  This function reads that
    state and renders the same orange-tag reference bar shown below the grid.

    Returns:
        (col1, col2): Selected column names and 1-based row ints.
    """
    col1 = st.session_state.get("selected_columns", []) if data_ready else []
    col2 = st.session_state.get("selected_rows",    []) if data_ready else []

    # --- Reference bar display ---
    _TAG = (
        "background:#2d2d2d; border:1px solid #555; border-radius:4px;"
        " padding:0.15rem 0.5rem; font-family:monospace; font-size:0.82rem;"
        " color:#e4781d; white-space:nowrap;"
    )
    if data_ready and edited_table is not None and col1:
        raw = st.session_state.get("_raw_grid_selection") or []

        # Build one ref-tag per column per raw range so Ctrl-selections
        # each show their own correct row span.
        all_refs = []
        total_cells = 0
        for rng in raw:
            start = rng.get("startRow")
            end   = rng.get("endRow")
            cols  = rng.get("columns", [])
            if start is None or end is None or not cols:
                continue
            start, end = int(start), int(end)
            if start > end:
                start, end = end, start
            valid_cols = [c for c in cols if c in edited_table.columns]
            if not valid_cols:
                continue
            r0, r1 = start + 1, end + 1
            for col in valid_cols:
                all_refs.append(f"{col}{r0}:{col}{r1}" if r0 != r1 else f"{col}{r0}")
            total_cells += len(valid_cols) * (end - start + 1)

        # Fall back to normalised union if raw had nothing usable
        if not all_refs:
            all_refs    = _build_refs(col1, col2)
            total_cells = len(col1) * (len(col2) if col2 else len(edited_table))

        tags_html = "".join(f'<span style="{_TAG}">{r}</span>' for r in all_refs)
        st.markdown(
            f"""
            <div style="
                display:flex; align-items:center; flex-wrap:wrap; gap:0.4rem;
                background:#1e1e1e; border:1px solid #444;
                border-radius:6px; padding:0.4rem 0.8rem;
            ">
                {tags_html}
                <span style="color:#888; font-size:0.8rem; margin-left:0.35rem;">
                    {total_cells} cell{'s' if total_cells != 1 else ''}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="
                display:flex; align-items:center;
                background:#1e1e1e; border:1px solid #333;
                border-radius:6px; padding:0.4rem 0.8rem;
            ">
                <span style="color:#555; font-size:0.82rem; font-family:monospace;">
                    No selection &mdash; drag cells in the grid
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
    for c in subset.columns:
        coerced = pd.to_numeric(subset[c], errors="coerce")
        if coerced.notna().all() or subset[c].isna().all():
            numeric_count += 1

    # Measurement-level counts from user tags
    ml = st.session_state.get("column_measurement_levels", {})
    num_interval_ratio = sum(1 for c in col1 if ml.get(c) in ("Interval", "Ratio"))
    num_ordinal_plus = sum(1 for c in col1 if ml.get(c) in ("Ordinal", "Interval", "Ratio"))

    return {
        "num_selected_cols": len(col1),
        "num_numeric_cols": numeric_count,
        "num_rows": num_rows,
        "all_numeric": numeric_count == len(col1) and len(col1) > 0,
        "has_numeric": numeric_count > 0,
        "num_interval_ratio": num_interval_ratio,
        "num_ordinal_plus": num_ordinal_plus,
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

    # Interval/ratio methods: Mean, Median, Std Dev, Percentiles, CV
    dis_1num = not data_ready or n_num < 1 or n_ir < 1
    # Variance needs interval/ratio AND ≥2 rows (sample variance, ddof=1)
    dis_var  = not data_ready or n_num < 1 or n_ir < 1 or n_rows < 2
    # Mode works on any measurement level — just needs data
    dis_mode = not data_ready or n_num < 1
    # Pearson: needs ≥2 interval/ratio columns AND ≥3 rows
    dis_corr = not data_ready or n_num < 2 or n_ir < 2 or n_rows < 3
    # Spearman: works on ordinal+, needs ≥2 ordinal+ columns AND ≥3 rows
    dis_spear = not data_ready or n_num < 2 or n_ord < 2 or n_rows < 3
    # Least-squares regression: needs ≥2 interval/ratio columns AND ≥2 rows
    dis_lsr  = not data_ready or n_num < 2 or n_ir < 2 or n_rows < 2
    # Chi-Square: needs ≥1 numeric column AND ≥2 observed values
    dis_chi  = not data_ready or n_num < 1 or n_rows < 2
    # Binomial: needs ≥1 numeric column (data is cast to int/float)
    dis_binom = not data_ready or n_num < 1
    # Coefficient of Variation: needs ≥1 interval/ratio column
    dis_cv   = not data_ready or n_num < 1 or n_ir < 1

    # If user drops from >=2 columns to 1 column,
    # reset two-column statistical method checkboxes
    k1 = st.session_state.checkbox_key_onecol
    k2 = st.session_state.checkbox_key_twocol

    c1, c2 = st.columns(2)

    with c1:
        mean        = st.checkbox("Mean",                disabled=dis_1num,  key=f"mean_c1_{k1}")        and not dis_1num
        median      = st.checkbox("Median",              disabled=dis_1num,  key=f"median_c1_{k1}")      and not dis_1num
        mode        = st.checkbox("Mode",                disabled=dis_mode,  key=f"mode_c1_{k1}")        and not dis_mode
        variance    = st.checkbox("Variance",            disabled=dis_var,   key=f"variance_c1_{k1}")    and not dis_var
        std         = st.checkbox("Standard Deviation",  disabled=dis_1num,  key=f"std_c1_{k1}")         and not dis_1num
        percentiles = st.checkbox("Percentiles",         disabled=dis_1num,  key=f"percentiles_c1_{k1}") and not dis_1num

    with c2:
        pearson                = st.checkbox("Pearson's Correlation",     disabled=dis_corr,  key=f"pearson_c2_{k2}")                and not dis_corr
        spearman               = st.checkbox("Spearman's Rank",           disabled=dis_spear, key=f"spearman_c2_{k2}")               and not dis_spear
        least_squares_regression = st.checkbox("Least Squares Regression",  disabled=dis_lsr,  key=f"least_squares_regression_c2_{k2}") and not dis_lsr
        chi_squared            = st.checkbox("Chi-Square Test",           disabled=dis_chi,  key=f"chi_squared_c2_{k1}")            and not dis_chi
        variation              = st.checkbox("Coefficient of Variation",  disabled=dis_cv,   key=f"variation_c2_{k1}")              and not dis_cv

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
                disabled=dis_1num,
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
        help=(
            "If a selected custom method depends on other custom methods, "
            "include those helper methods automatically."
        ),
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

    disable_one_col  = not data_ready or len(col1) < 1
    disable_two_cols = not data_ready or len(col1) < 2
    disable_binomial = False

    v1, v2 = st.columns(2)

    with v1:
        hist    = st.checkbox("Pie Chart",                     key="viz_hist",    disabled=disable_one_col)  and not disable_one_col
        box     = st.checkbox("Vertical Bar Chart",            key="viz_box",     disabled=disable_one_col)  and not disable_one_col
        scatter = st.checkbox("Horizontal Bar Chart",          key="viz_scatter", disabled=disable_one_col)  and not disable_one_col

    with v2:
        line    = st.checkbox("Scatter Plot",                  key="viz_line",    disabled=disable_two_cols) and not disable_two_cols
        heatmap = st.checkbox("Line of Best Fit Scatter Plot", key="viz_heatmap", disabled=disable_two_cols) and not disable_two_cols
        binomial = st.checkbox("Binomial Distribution",        key="viz_binomial", disabled=disable_binomial) and not disable_binomial

    # --- Binomial parameter inputs (below the checkbox) ---
    dis_binom = disable_binomial
    if binomial and not dis_binom:
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
                help="Probability of success on each trial (0 \u2013 1).",
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
        k_min_val = st.session_state.get("binomial_k_min", 0)
        k_max_val = st.session_state.get("binomial_k_max", 10)
        if k_min_val > k_max_val:
            _param_warning("k min must be \u2264 k max.")
            st.session_state["_analysis_invalid_params"] = True

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
    binomial_only_run      = binomial and not data_ready

    already_computing = st.session_state.get("_compute_future") is not None
    _invalid = st.session_state.get("_analysis_invalid_params", False) or invalid_params

    run_clicked = st.button(
        "Run Analysis",
        key="run_analysis",
        use_container_width=True,
        disabled=not ((data_ready and computation_selected) or binomial_only_run) or already_computing or _invalid
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
