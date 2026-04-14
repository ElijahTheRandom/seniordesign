"""
views/results.py
----------------
Renders the analysis results page for a completed PS Analytics run.

WHY THIS FILE EXISTS:
    The results display was previously inline in mainpage.py (lines
    1842–1982), with stat card generation, visualization rendering,
    export logic, and delete handling all in one block.

    Extracting it here gives the results page its own clear structure:
    header → stat cards → visualizations → data table → action buttons.

PUBLIC INTERFACE:
    render_results(run, base_dir)

PRIVATE HELPERS:
    _render_stat_cards(run)
    _render_visualizations(run)
    _render_data_table(run)
    _render_action_buttons(run)
    _build_export_text(run)

STAT DISPATCH TABLE (module-level):
    STAT_COMPUTERS maps method name strings → compute functions.
    To add a new statistic, write one _compute_*() function and add
    one entry to STAT_COMPUTERS. The rendering loop never changes.

    Each compute function receives run["table"] (a DataFrame) and
    returns a list of card tuples:
        ("stat", title_html, value_str)           — 3-tuple
        ("stat", title_html, value_str, subtext)  — 4-tuple

SESSION STATE READ:
    active_run_id, analysis_runs

SESSION STATE WRITTEN:
    active_run_id, analysis_runs (on delete)
"""
import sys
import os
import json
import base64
import streamlit.components.v1 as components
from pathlib import Path
import streamlit as st
import pandas as pd
from PIL import Image

from utils.helpers import df_to_ascii_table
from frontend_handler import handle_result
from logic.run_manager import build_success_save_message

from PIL import ImageOps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from datetime import datetime
from io import BytesIO

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

SAVED_RUNS_FILE = os.path.join(_PROJECT_ROOT, "results_cache", "saved_runs.json")

_HUZZAH_PATH = Path(__file__).parent.parent / "pages" / "assets" / "huzzahAhSquirrel.png"
with open(_HUZZAH_PATH, "rb") as _f:
    _HUZZAH_B64 = base64.b64encode(_f.read()).decode()

# ADDITIONAL BOOL FOR TESTING PURPOSES
# REPLACE THIS WITH SHARED VARIABLE CONTROLLING LIGHT MODE
lightMode = False

if "show_success_save_dialog" not in st.session_state:
    st.session_state.show_success_save_dialog = False

if "modal_message" not in st.session_state:
    st.session_state.modal_message = ""

@st.dialog("Saved Successfully")
def success_dialog():
    col_img, col_text = st.columns([1, 1.5], gap="medium")
    with col_img:
        st.markdown(
            f'<img class="ps-squirrel" src="data:image/png;base64,{_HUZZAH_B64}" style="width:100%;max-width:500px;" />',
            unsafe_allow_html=True,
        )
    with col_text:
        st.markdown(st.session_state.modal_message)

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def render_results(run: dict, base_dir: str) -> None:
    """
    Render the full results page for a single analysis run.

    Args:
        run:      The run dict: { id, name, table, data, columns, rows,
                                  methods, visualizations }
        base_dir: Absolute path to the frontend directory.
    """

    # Only compute cards if not already cached on the run
    if "cards" not in run:
        run = handle_result(run)

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<hr style='margin: 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )

    if st.session_state.get("show_success_save_dialog"):
        st.session_state.show_success_save_dialog = False
        success_dialog()

    if st.session_state.get("show_export_dialog"):
        _export_run_dialog(run)
        st.session_state.show_export_dialog = False

    if "show_export_dialog" not in st.session_state:
        st.session_state.show_export_dialog = False

    st.header(f"Analysis Results — {run['name']}", anchor=False)
    _render_stat_cards(run)
    _render_precision_warnings(run)
    _render_visualizations(run)
    _render_data_table(run)
    _render_action_buttons(run)


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

# ============================================================================
# ⭐ STATISTICAL RESULTS DISPLAY
# Variables:
#   - run["methods"] (list of selected method names)
#   - STAT_COMPUTERS[method_name] (dispatch table mapping to compute functions)
#   - run["table"] (DataFrame passed to compute functions)
# Rendered via stat cards using _render_stat_card(title, value, subtext)
# ============================================================================

def _render_stat_cards(run: dict, show_divider: bool = True) -> None:
    """
    Compute and render all stat cards for the methods in this run.

    Uses the STAT_COMPUTERS dispatch table to look up the compute
    function for each selected method. Unknown methods are silently
    skipped (future-proofing: old run dicts won't crash the page if a
    method name changes).

    Cards are laid out in a Pinterest-style grid of 3 columns with
    breathing room between rows.
    """
    cards = run.get("cards", [])

    if not cards:
        return

    st.subheader("Statistical Analysis", anchor=False)
    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

    # Render in rows of 3
    for i in range(0, len(cards), 3):
        cols = st.columns([1, 1, 1], gap="large")
        for j in range(3):
            if i + j < len(cards):
                card = cards[i + j]
                with cols[j]:
                    if card[0] == "error":
                        _render_error_card(card[1], card[2])
                    else:
                        _render_stat_card(*card[1:])  # unpack title, value, [subtext]

        st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

    if show_divider:
        st.markdown("---")


def _render_stat_card(title: str, value: str, subtext: str = None) -> None:
    """
    Render a single stat card using the .analysis-card CSS class.

    Args:
        title:   Card header HTML (may contain <b> tags).
        value:   The primary numeric value to display.
        subtext: Optional secondary label below the value.
    """
    subtext_html = (
        f'<div class="analysis-subtext">{subtext}</div>'
        if subtext else ""
    )
    st.markdown(f"""
    <div class="analysis-card">
        <div class="analysis-title">{title}</div>
        <div class="analysis-value">{value}</div>
        {subtext_html}
    </div>
    """, unsafe_allow_html=True)


def _render_error_card(title: str, error_msg: str) -> None:
    """
    Render an error card for a method that could not compute.
    Uses smaller text and a red accent to distinguish from success cards.
    """
    st.markdown(f"""
    <div class="analysis-card-error">
        <div class="analysis-title">{title}</div>
        <div class="analysis-error-msg">{error_msg}</div>
    </div>
    """, unsafe_allow_html=True)


def _render_precision_warnings(run: dict) -> None:
    """
    If any method flagged a loss-of-precision risk, render an info box
    listing each affected method and its explanation.
    """
    warnings = run.get("precision_warnings") or []
    if not warnings:
        return

    lines = []
    for w in warnings:
        lines.append(f"**{w['name']}**: {w['note']}")

    st.info(
        "**Precision / Overflow Notices**\n\n"
        + "\n\n".join(lines),
        icon="ℹ️",
    )
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)


def _render_visualization_download_button(
    image: Image.Image,
    file_name: str,
    button_key: str,
) -> None:
    """Render a browser-side download button that mirrors the visible theme.

    Python cannot read the browser's active CSS-inverted result image directly.
    Instead, this sends the original image bytes to a tiny JS button that checks
    the current theme in localStorage and inverts the downloaded pixels when the
    UI is in light mode so the saved file matches what the user sees.
    """
    image_buffer = BytesIO()
    image.convert("RGB").save(image_buffer, format="PNG")
    image_b64 = base64.b64encode(image_buffer.getvalue()).decode()
    button_id = f"viz-download-{button_key}"
    safe_file_name = json.dumps(file_name)

    components.html(
        f"""
        <div style="margin:0.35rem 0 0.75rem 0;">
            <button id="{button_id}" style="
                background:#262730;
                color:white;
                border:1px solid rgba(250,250,250,0.2);
                border-radius:0.5rem;
                padding:0.45rem 0.8rem;
                cursor:pointer;
                font-size:0.9rem;
            ">Download Visualization</button>
        </div>
        <script>
        (function() {{
            const btn = document.getElementById({json.dumps(button_id)});
            if (!btn || btn.dataset.bound === "1") return;
            btn.dataset.bound = "1";

            btn.addEventListener("click", async () => {{
                const isLightMode = (window.parent.localStorage.getItem("ps_analytics_theme") || "dark") === "light";
                const img = new Image();
                img.src = "data:image/png;base64,{image_b64}";

                await new Promise((resolve, reject) => {{
                    img.onload = resolve;
                    img.onerror = reject;
                }});

                const canvas = document.createElement("canvas");
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext("2d");

                if (isLightMode) {{
                    ctx.filter = "invert(1)";
                }}

                ctx.drawImage(img, 0, 0);

                const link = document.createElement("a");
                link.href = canvas.toDataURL("image/jpeg", 0.95);
                link.download = {safe_file_name};
                document.body.appendChild(link);
                link.click();
                link.remove();
            }});
        }})();
        </script>
        """,
        height=52,
    )


def _render_visualizations(run: dict, show_divider: bool = True) -> None:
    """
    Render the visualizations section using chart images saved by the backend.

    Reads result_message.graphics, which is populated by BackendHandler after
    chart PNGs are generated into the results_cache run folder.

    Args:
        run: The run dict containing "result_message" (a Message object).
    """
    graphics = getattr(run.get("result_message"), "graphics", None)
    if not graphics:
        return

    st.subheader("Visualizations", anchor=False)
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    for idx, chart in enumerate(graphics):
        if chart.get("ok") and chart.get("path"):
            image = Image.open(chart["path"])
            # Test for Light Mode
            if lightMode and chart["type"] != "binomial":
                image = ImageOps.invert(image.convert("RGB"))
            st.image(image)

            # --- Req 3.7: JPEG download button ---
            try:
                img = Image.open(chart["path"])
                chart_type = chart.get("type", f"chart_{idx}")
                _render_visualization_download_button(
                    img,
                    f"{run.get('name', 'run')} {chart_type.replace('_', ' ').title()}.jpg",
                    f"{run.get('id', '')}_{idx}",
                )
            except Exception:
                pass  # If conversion fails, skip the button silently
        else:
            st.error(f"{chart.get('type', 'Chart')}: {chart.get('error', 'Failed to generate')}")

    if show_divider:
        st.markdown("---")


def _render_data_table(run: dict, show_divider: bool = True) -> None:
    """
    Render the selected data table with a row/column summary caption.

    Args:
        run: The run dict containing "data" (the sliced DataFrame).
    """
    st.subheader("Selected Data", anchor=False)
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    st.dataframe(run["data"], use_container_width=True)
    st.caption(
        f"Rows: {len(run['data'])}, Columns: {len(run['data'].columns)}"
    )
    
    if show_divider:
        st.markdown("---")

@st.dialog("Export Run")
def _export_run_dialog(run: dict):

    st.write("Choose an export format:")

    # TXT report
    st.download_button(
        "Export TXT Report",
        data=_build_export_text(run),
        file_name=f"{run['name']} Full Report.txt",
        mime="text/plain",
        use_container_width=True,
    )

    # CSV export
    st.download_button(
        "Export CSV Data",
        data=run["data"].to_csv(index=False),
        file_name=f"{run['name']}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # TSV export
    st.download_button(
        "Export TSV Data",
        data=run["data"].to_csv(index=False, sep="\t"),
        file_name=f"{run['name']}.tsv",
        mime="text/tab-separated-values",
        use_container_width=True,
    )

def _build_charts_zip(run: dict) -> bytes:
    """
    Bundle all successfully generated chart PNGs for a run into a ZIP archive.

    Returns the ZIP as raw bytes ready to pass to st.download_button.
    """
    import zipfile

    graphics = getattr(run.get("result_message"), "graphics", None) or []
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, chart in enumerate(graphics):
            if chart.get("ok") and chart.get("path"):
                chart_type = chart.get("type", f"chart_{idx}")
                arcname = f"{chart_type}_{idx}.png"
                zf.write(chart["path"], arcname=arcname)
    buf.seek(0)
    return buf.getvalue()


def _render_action_buttons(run: dict) -> None:
    """
    Render the Save / Export / Export Charts / Delete action buttons at the bottom.

    Save:          Persists the run to saved_runs.json and writes table CSV to cache.
    Export Run:    Downloads a plain-text .txt report of the run's results.
    Export Charts: Downloads all chart images as a ZIP archive.
    Delete:        Removes the run from session state and navigates home.

    Args:
        run: The run dict to act on.
    """
    btn1, btn2, btn3, btn4 = st.columns(4)

    with btn1:
        if st.button("Save Run", use_container_width=True):
            _save_run(run)

    with btn2:
        if st.button("Export Run", use_container_width=True):
            st.session_state.show_export_dialog = True
            st.rerun()

    with btn3:
        graphics = getattr(run.get("result_message"), "graphics", None) or []
        has_charts = any(c.get("ok") and c.get("path") for c in graphics)
        if has_charts:
            charts_zip = _build_charts_zip(run)
            st.download_button(
                "Export Charts",
                data=charts_zip,
                file_name=f"{run.get('name', 'run')}_charts.zip",
                mime="application/zip",
                use_container_width=True,
                key=f"dl_charts_{run.get('id', '')}",
            )
        else:
            st.button("Export Charts", disabled=True, use_container_width=True)

    with btn4:
        if st.button("Delete Run", use_container_width=True):
            st.session_state.analysis_runs = [
                r for r in st.session_state.analysis_runs
                if r["id"] != run["id"]
            ]
            st.session_state.active_run_id = None
            st.rerun()


# ---------------------------------------------------------------------------
# Save run logic
# ---------------------------------------------------------------------------

def _save_run(run: dict) -> None:
    """
    Persist a run so it can be reloaded from the Load Previous Runs page.

    Steps:
        1. Locate the run's cache folder (from result_message.run_folder).
        2. Save the selected DataFrame as table.csv in that folder.
        3. Add / update an entry in saved_runs.json at the project root.
    """
    result_message = run.get("result_message")
    cache_folder = getattr(result_message, "run_folder", None) if result_message else None

    if not cache_folder or not os.path.isdir(cache_folder):
        st.error("Cannot save: no cache folder found for this run.")
        return

    # 1. Save the table as CSV so it can be reconstructed on load
    table_path = os.path.join(cache_folder, "table.csv")
    if isinstance(run.get("data"), pd.DataFrame):
        run["data"].to_csv(table_path, index=False)

    # 2. Read existing saved_runs.json (or start fresh)
    saved_runs = _read_saved_runs()

    # 3. Build the entry for this run
    entry = {
        "id": run["id"],
        "name": run["name"],
        "saved_at": datetime.now().isoformat(),
        "cache_folder": cache_folder,
        "dataset_id": getattr(result_message, "dataset_id", None),
        "methods": run.get("methods", []),
        "visualizations": run.get("visualizations", []),
    }

    # Replace if the same run id already exists, else append
    saved_runs = [s for s in saved_runs if s["id"] != run["id"]]
    saved_runs.append(entry)

    _write_saved_runs(saved_runs)

    st.session_state.modal_message = build_success_save_message(run)
    st.session_state.show_success_save_dialog = True
    st.rerun()

def _read_saved_runs() -> list:
    """Read and return the list from saved_runs.json, or [] if missing."""
    if not os.path.isfile(SAVED_RUNS_FILE):
        return []
    try:
        with open(SAVED_RUNS_FILE, "r") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_saved_runs(saved_runs: list) -> None:
    """Atomically write the saved_runs list to saved_runs.json."""
    with open(SAVED_RUNS_FILE, "w") as f:
        json.dump(saved_runs, f, indent=2)


# ---------------------------------------------------------------------------
# Export builder
# ---------------------------------------------------------------------------

def _build_export_text(run: dict) -> str:
    """
    Build the plain-text export string for a run's .txt download.

    Sections included:
        - Run name header
        - Methods applied (if any)
        - Visualizations applied (if any)
        - Selected data as an ASCII table

    Args:
        run: The run dict to export.

    Returns:
        A multi-line string ready to be written to a .txt file.
    """
    lines = [f"Analysis Results — {run['name']}", ""]
    # --- Req 3.9: Include the exact row/column selection ---
    sel_cols = run.get("columns", [])
    sel_rows = run.get("rows", [])
    if sel_cols:
        lines.append(f"Selected Columns: {', '.join(str(c) for c in sel_cols)}")
    if sel_rows:
        lines.append(f"Selected Rows: {', '.join(str(r) for r in sel_rows)}")
    else:
        lines.append("Selected Rows: All")
    lines.append("")
    if run.get("cards"):
        stat_cards = [c for c in run["cards"] if c[0] == "stat"]
        error_cards = [c for c in run["cards"] if c[0] == "error"]

        if stat_cards:
            lines.append("Methods Applied:")
            for card in stat_cards:
                title  = card[1].replace("<b>", "").replace("</b>", "")
                value  = card[2]
                if len(card) == 4:
                    subtext = card[3]
                    lines.append(f"{title}: {value} ({subtext})")
                else:
                    lines.append(f"{title}: {value}")
            lines.append("")

        if error_cards:
            lines.append("Errors:")
            for card in error_cards:
                title = card[1].replace("<b>", "").replace("</b>", "")
                lines.append(f"{title}: {card[2]}")
            lines.append("")

    if run.get("visualizations"):
        lines.append("Visualizations Applied:")
        for v in run["visualizations"]:
            lines.append(f"- {v}")
        lines.append("")

    precision_warnings = run.get("precision_warnings") or []
    if precision_warnings:
        lines.append("Precision / Overflow Notices:")
        for w in precision_warnings:
            lines.append(f"  [{w['name']}] {w['note']}")
        lines.append("")

    lines.append("Selected Data:")
    lines.append(df_to_ascii_table(run["data"]))

    return "\n".join(lines)

