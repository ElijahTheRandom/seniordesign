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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from pathlib import Path
import sys
import streamlit as st
import pandas as pd

from utils.helpers import df_to_ascii_table
from frontend_handler import handle_result



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
    run = handle_result(run)

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<hr style='margin: 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )

    st.markdown("""
    <style>
    div[data-testid="stAppViewContainer"] .block-container {
        height: auto !important;
        min-height: auto !important;
        max-height: none !important;
        padding-left: 0.5rem !important;
        padding-right: 1rem !important;
        padding-bottom: 0.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

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


def _render_visualizations(run: dict, show_divider: bool = True) -> None:
    """
    Render the visualizations section if any were selected.

    Currently shows placeholder info boxes. Each visualization type
    listed in run["visualizations"] will display as a labeled stub,
    ready to be replaced with real chart rendering in a future stage.

    Args:
        run: The run dict containing the "visualizations" list.
    """
    if not run.get("visualizations"):
        return

    st.subheader("Visualizations", anchor=False)
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    for viz in run["visualizations"]:
        st.info(f"{viz} visualization will be rendered here")

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

    st.dataframe(run["table"], use_container_width=True)
    st.caption(
        f"Rows: {len(run['table'])}, Columns: {len(run['table'].columns)}"
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

    Save:   Placeholder (not yet implemented).
    Export: Downloads a plain-text .txt report of the run's results.
    Delete: Removes the run from session state and navigates home.

    Args:
        run: The run dict to act on.
    """
    btn1, btn2, btn3 = st.columns(3)

    with btn1:
        st.button("Save Run", use_container_width=True)

    with btn2:
        if st.button("Export Run", use_container_width=True):
            _export_run_dialog(run)

    with btn3:
        if st.button("Delete Run", use_container_width=True):
            st.session_state.analysis_runs = [
                r for r in st.session_state.analysis_runs
                if r["id"] != run["id"]
            ]
            st.session_state.active_run_id = None
            st.rerun()


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

    if run.get("cards"):
        lines.append("Methods Applied:")

        for card in run["cards"]:
            title  = card[1].replace("<b>", "").replace("</b>", "")
            value  = card[2]
            if len(card) == 4:
                subtext = card[3]
                lines.append(f"{title}: {value} ({subtext})")
            else:
                lines.append(f"{title}: {value}")

        lines.append("")

    if run.get("visualizations"):
        lines.append("Visualizations Applied:")
        for v in run["visualizations"]:
            lines.append(f"- {v}")
        lines.append("")

    lines.append("Selected Data:")
    lines.append(df_to_ascii_table(run["table"]))

    return "\n".join(lines)

