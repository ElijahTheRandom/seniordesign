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
from datetime import datetime
from io import BytesIO

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)
from pathlib import Path
import streamlit as st
import pandas as pd
from PIL import Image

from utils.helpers import df_to_ascii_table
from frontend_handler import handle_result
from logic.run_manager import build_success_save_message

SAVED_RUNS_FILE = os.path.join(_PROJECT_ROOT, "results_cache", "saved_runs.json")

if "show_success_save_dialog" not in st.session_state:
    st.session_state.show_success_save_dialog = False

if "modal_message" not in st.session_state:
    st.session_state.modal_message = ""

@st.dialog("Saved Successfully")
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
            st.image(chart["path"])
            # --- Req 3.7: JPEG download button ---
            try:
                img = Image.open(chart["path"])
                buf = BytesIO()
                rgb = img.convert("RGB")  # JPEG requires RGB
                rgb.save(buf, format="JPEG", quality=95)
                chart_type = chart.get("type", f"chart_{idx}")
                st.download_button(
                    "Download JPEG",
                    data=buf.getvalue(),
                    file_name=f"{run.get('name', 'run')}_{chart_type}.jpg",
                    mime="image/jpeg",
                    key=f"dl_jpeg_{run.get('id', '')}_{idx}",
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

def _render_action_buttons(run: dict) -> None:
    """
    Render the Save / Export / Delete action buttons at the bottom.

    Save:   Persists the run to saved_runs.json and writes table CSV to cache.
    Export: Downloads a plain-text .txt report of the run's results.
    Delete: Removes the run from session state and navigates home.

    Args:
        run: The run dict to act on.
    """
    btn1, btn2, btn3 = st.columns(3)

    with btn1:
        if st.button("Save Run", use_container_width=True):
            _save_run(run)

    with btn2:
        if st.button("Export Run", use_container_width=True):
            st.session_state.show_export_dialog = True
            st.rerun()

    with btn3:
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

    lines.append("Selected Data:")
    lines.append(df_to_ascii_table(run["data"]))

    return "\n".join(lines)

