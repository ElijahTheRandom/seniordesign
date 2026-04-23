"""
views/comparison.py
-------------------
Renders the comparison view for multiple analysis runs.

WHY THIS FILE EXISTS:
    The comparison feature allows users to view results from multiple
    runs side-by-side or in other layouts for easy comparison.

PUBLIC INTERFACE:
    render_comparison(selected_run_ids, base_dir)

PRIVATE HELPERS:
    _render_view_mode_selector()
    _render_side_by_side_comparison(runs)
    _render_stacked_comparison(runs)
    _render_comparison_header(run)
    _render_run_comparison_section(run)

SESSION STATE READ:
    analysis_runs, comparison_view_mode

SESSION STATE WRITTEN:
    comparison_view_mode
"""

import streamlit as st
import pandas as pd
import base64
import json
import streamlit.components.v1 as components
from pathlib import Path
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

import math

from utils.helpers import df_to_ascii_table
from views.results import (
    _render_stat_cards,
    _render_visualizations,
    _render_data_table,
    _build_export_text,
    _build_combined_export,
)
from frontend_handler import _ID_TO_DISPLAY


# ---------------------------------------------------------------------------
# Diff-detection (Req AT 5.4)
# ---------------------------------------------------------------------------
# When the user opens the comparison view we compare the underlying numeric
# results across runs (not the formatted display strings) and surface a
# redder-tinted-orange highlight on every card whose statistic differs.
# A method that ran in some runs but not others also counts as a diff —
# coverage gaps are themselves a difference dimension.

def _values_equal(va, vb) -> bool:
    """Tolerant equality for stat-result values across runs.

    Handles the shapes the methods actually return: scalar numbers, lists
    (percentile), and dicts (least-squares regression's slope/intercept/etc.).
    Falls back to string equality for anything else (e.g. binomial DataFrames
    — exact equality is good enough for the user-visible comparison).
    """
    if va is None and vb is None:
        return True
    if va is None or vb is None:
        return False
    if isinstance(va, bool) or isinstance(vb, bool):
        return va == vb
    if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
        try:
            fa, fb = float(va), float(vb)
        except (TypeError, ValueError):
            return va == vb
        if math.isnan(fa) and math.isnan(fb):
            return True
        if math.isnan(fa) or math.isnan(fb):
            return False
        return math.isclose(fa, fb, rel_tol=1e-9, abs_tol=1e-12)
    if isinstance(va, list) and isinstance(vb, list):
        if len(va) != len(vb):
            return False
        return all(_values_equal(x, y) for x, y in zip(va, vb))
    if isinstance(va, dict) and isinstance(vb, dict):
        # Drop noisy keys whose equality doesn't reflect a meaningful
        # numeric difference (LSR's `chart` is a base64 PNG that varies
        # with rendering env even when the regression itself is identical).
        keys = (set(va) | set(vb)) - {"chart"}
        return all(_values_equal(va.get(k), vb.get(k)) for k in keys)
    try:
        return str(va) == str(vb)
    except Exception:
        return va is vb


def _build_diff_titles(runs: list) -> set[str]:
    """Return display names of statistics that differ across the given runs.

    A statistic is flagged when:
      - its value differs across runs (tolerant float comparison), OR
      - its error differs across runs, OR
      - it appears in some runs but not others (coverage gap).

    Returns the set of display names so the renderer can match against the
    plain title text on each card.
    """
    if len(runs) < 2:
        return set()

    by_id: dict[str, list] = {}
    for run in runs:
        msg = run.get("result_message")
        results = getattr(msg, "results", None) or []
        seen: dict[str, dict] = {}
        for r in results:
            mid = r.get("id")
            if mid:
                seen[mid] = r
        # Record one entry per run per method id (None if the method didn't
        # run for that run — that's a coverage gap and counts as a diff).
        all_ids_so_far = set(by_id) | set(seen)
        for mid in all_ids_so_far:
            by_id.setdefault(mid, []).append(seen.get(mid))

    diff_ids: set[str] = set()
    for mid, entries in by_id.items():
        # Pad missing trailing runs (when a method appears in run 1 but not
        # in run 2, by_id only has one entry — but we need to know it was
        # absent in run 2 too).
        while len(entries) < len(runs):
            entries.append(None)

        if any(e is None for e in entries) and not all(e is None for e in entries):
            diff_ids.add(mid)
            continue

        present = [e for e in entries if e is not None]
        if len(present) < 2:
            continue

        first = present[0]
        for other in present[1:]:
            if first.get("ok") != other.get("ok"):
                diff_ids.add(mid)
                break
            if first.get("ok"):
                if not _values_equal(first.get("value"), other.get("value")):
                    diff_ids.add(mid)
                    break
            else:
                if str(first.get("error") or "") != str(other.get("error") or ""):
                    diff_ids.add(mid)
                    break

    return {_ID_TO_DISPLAY.get(mid, mid) for mid in diff_ids}


def _render_diff_legend(has_diffs: bool, run_count: int) -> None:
    """Small legend explaining the diff highlight so users know what the
    redder tint means. Renders even when no diffs are found so the absence
    is also informative."""
    if run_count < 2:
        return
    if has_diffs:
        st.caption(
            "Cards with a redder-orange border indicate statistics whose value, "
            "error, or presence differs across the runs being compared."
        )
    else:
        st.caption(
            "All shared statistics produced matching values across the selected runs."
        )

def _big_section_divider():
    st.markdown(
        "<hr style='margin: 1rem 0 1.5rem 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def render_comparison(selected_run_ids: list, base_dir: str) -> None:
    """
    Render the full comparison view for multiple selected runs.

    Args:
        selected_run_ids: List of run IDs to compare.
        base_dir:         Absolute path to the frontend directory.
    """

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<hr style='margin: 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )

    # Get the actual run objects from session state
    runs = [
        r for r in st.session_state.analysis_runs
        if r["id"] in selected_run_ids
    ]

    if not runs:
        st.error("No runs selected for comparison.")
        return

    # Auto-switch to stacked mode if >3 runs selected
    if len(runs) > 3:
        st.session_state.comparison_view_mode = "stacked"

    st.header("Run Comparison", anchor=False)
    
    # View mode selector
    _render_view_mode_selector()

    st.markdown(
        "<hr style='margin: 1rem 0 1.5rem 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )

    # Render based on selected view mode
    view_mode = st.session_state.get("comparison_view_mode", "side-by-side")
    
    if view_mode == "side-by-side":
        _render_side_by_side_comparison(runs, base_dir)
    elif view_mode == "stacked":
        _render_stacked_comparison(runs, base_dir)

    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)

    @st.dialog("Export Comparison")
    def _export_comparison_dialog(runs: list):

        st.write("Choose an export format:")

        # ---------- TXT REPORT (UI-CONSISTENT VERSION) ----------
        export_sections = []
        run_names = []

        for run in runs:
            # FORCE same formatting as Results page export
            section = _build_export_text(run)
            export_sections.append(section)
            run_names.append(run["name"])

        export_text = ("\n\n" + "-" * 80 + "\n\n").join(export_sections)

        filename = f"{', '.join(run_names)} Combined Report.txt"

        st.download_button(
            "Export TXT Report",
            data=export_text,
            file_name=filename,
            mime="text/plain",
            use_container_width=True,
        )

        combined_filename = ', '.join(run_names)

        def _build_combined_multi(sep: str) -> str:
            divider = "\n" + ("-" * 80) + "\n\n"
            return divider.join(_build_combined_export(r, sep=sep) for r in runs)

        # ---------- Combined CSV (results + selected data per run) ----------
        st.download_button(
            "Export CSV Report",
            data=_build_combined_multi(","),
            file_name=f"{combined_filename} Combined Report.csv",
            mime="text/csv",
            use_container_width=True,
        )

        # ---------- Combined TSV (results + selected data per run) ----------
        st.download_button(
            "Export TSV Report",
            data=_build_combined_multi("\t"),
            file_name=f"{combined_filename} Combined Report.tsv",
            mime="text/tab-separated-values",
            use_container_width=True,
        )

    export_left, export_center, export_right = st.columns([2,3,2])

    with export_center:

        if st.button("Export Multi-Run Report", use_container_width=True):
            _export_comparison_dialog(runs)

# ---------------------------------------------------------------------------
# View mode selector
# ---------------------------------------------------------------------------

def _render_view_mode_selector() -> None:

    runs = [
        r for r in st.session_state.analysis_runs
        if r["id"] in st.session_state.selected_runs_for_comparison
    ]

    if len(runs) > 3:
        st.write("View Mode (Stacked)")
        st.info(f"{len(runs)} runs selected → stacked mode auto-selected")
        return

    st.subheader("Comparison View Modes:", anchor=False)

    selected_mode = st.radio(
        "Comparison View",
        options=["side-by-side", "stacked"],
        horizontal=False,
        key="view_mode_radio",
        label_visibility="collapsed",
        index=["side-by-side", "stacked"].index(
            st.session_state.get("comparison_view_mode", "side-by-side")
        ),
        format_func=lambda x: "Side by Side" if x == "side-by-side" else "Stacked"
    )

    if selected_mode != st.session_state.get("comparison_view_mode", "side-by-side"):
        st.session_state.comparison_view_mode = selected_mode

# ---------------------------------------------------------------------------
# Comparison layout renderers
# ---------------------------------------------------------------------------
def _render_side_by_side_comparison(runs: list, base_dir: str) -> None:

    """
    Render runs in side-by-side columns.

    Each run gets its own column, and all results are displayed
    horizontally for easy visual comparison.

    Args:
        runs:     List of run dicts to compare.
        base_dir: Absolute path to the frontend directory.
    """

    # ---------- Row 1: Headers ----------
    cols = st.columns(len(runs))
    for col, run in zip(cols, runs):
        with col:
            st.header(run["name"], anchor=False)

    # ---------- Row 2: Statistical Analysis ----------
    # Each run already lives in a 1/N-width column, so pack stat cards
    # one-per-row inside that column instead of squeezing 3 into the
    # already-narrow space. The standard results page (full width) keeps
    # the default 3-per-row layout.
    diff_titles = _build_diff_titles(runs)
    _render_diff_legend(bool(diff_titles), len(runs))
    cols = st.columns(len(runs))
    for col, run in zip(cols, runs):
        with col:
            _render_stat_cards(
                run,
                show_divider=False,
                highlight_titles=diff_titles,
                row_slots=1,
            )

    _big_section_divider()

    # ---------- Row 3: Visualizations ----------
    any_visualizations = any(
        getattr(run.get("result_message"), "graphics", None) for run in runs
    )

    if any_visualizations:
        cols = st.columns(len(runs))
        for col, run in zip(cols, runs):
            with col:
                if getattr(run.get("result_message"), "graphics", None):
                    _render_visualizations(run, show_divider=False)
                else:
                    st.markdown(
                        "<div style='height: 400px;'></div>",
                        unsafe_allow_html=True
                    )

        _big_section_divider()

    # ---------- Row 4: Data Table ----------
    cols = st.columns(len(runs))
    for col, run in zip(cols, runs):
        with col:
            _render_data_table(run, show_divider=False)

    _big_section_divider()


def _render_stacked_comparison(runs: list, base_dir: str) -> None:
    """
    Render runs stacked vertically with big headers like side-by-side.

    Each run is displayed in full width below the previous one,
    with consistent headers and section dividers.
    """
    diff_titles = _build_diff_titles(runs)
    _render_diff_legend(bool(diff_titles), len(runs))

    for run in runs:
        # Big header like side-by-side
        st.header(run["name"], anchor=False)

        # Render stat cards (with diff highlight passed across all runs so
        # the same stat lights up in every section it appears in).
        _render_stat_cards(
            run, show_divider=False, highlight_titles=diff_titles
        )

        # Render visualizations
        _render_visualizations(run, show_divider=False)

        # Render data table
        _render_data_table(run, show_divider=False)

        # Divider between runs
        _big_section_divider()


#
#def _render_diff_comparison(runs: list, base_dir: str) -> None:
#    """
#    Render a diff-style comparison (placeholder for future enhancement).
#
#    This view mode highlights differences between metric values across runs.
#
#    Args:
#        runs:     List of run dicts to compare.
#        base_dir: Absolute path to the frontend directory.
#    """
#    st.info(
#        "Diff view is coming soon! This will highlight metric differences "
#       "across runs for easy spotting of changes."
#   )
#   # Fallback to side-by-side for now
#   _render_side_by_side_comparison(runs, base_dir)


# ---------------------------------------------------------------------------
# Comparison section renderer
# ---------------------------------------------------------------------------

def _render_comparison_section(run: dict, base_dir: str) -> None:
    """
    Render a single run's results in the comparison context.

    This is a condensed version of the full results view, optimized for
    side-by-side comparison.

    Args:
        run:      The run dict to render.
        base_dir: Absolute path to the frontend directory.
    """
    st.subheader(f"{run['name']}", anchor=False)
    
    # Render stat cards
    _render_stat_cards(run, show_divider=False)
    
    # Render visualizations
    _render_visualizations(run, show_divider=False)

    _render_data_table(run, show_divider=False)


# ---------------------------------------------------------------------------
# Advanced: Tabbed comparison (future enhancement)
# ---------------------------------------------------------------------------

def render_comparison_tabbed(selected_run_ids: list, base_dir: str) -> None:
    """
    (Future enhancement) Render comparison with tabbed metric sections.

    This organizes comparison results by metric category:
        [Summary] [Performance Metrics] [Risk Metrics] [Trades]

    Each tab shows side-by-side comparison for that metric category.

    Args:
        selected_run_ids: List of run IDs to compare.
        base_dir:         Absolute path to the frontend directory.
    """
    runs = [
        r for r in st.session_state.analysis_runs
        if r["id"] in selected_run_ids
    ]

    if not runs:
        st.error("No runs selected for comparison.")
        return

    st.header("Run Comparison (Tabbed View)", anchor=False)
    
    # Create tabs for different metric categories
    tab1, tab2, tab3, tab4 = st.tabs([
        "Summary",
        "Performance Metrics",
        "Risk Metrics",
        "Trades"
    ])

    with tab1:
        st.subheader("Summary Statistics")
        cols = st.columns(len(runs))
        for col, run in zip(cols, runs):
            with col:
                st.write(f"**{run['name']}**")
                _render_stat_cards(run)

    with tab2:
        st.subheader("Performance Metrics")
        st.info("Performance metrics visualization coming soon")

    with tab3:
        st.subheader("Risk Metrics")
        st.info("Risk metrics visualization coming soon")

    with tab4:
        st.subheader("Trades & Details")
        cols = st.columns(len(runs))
        for col, run in zip(cols, runs):
            with col:
                st.write(f"**{run['name']}**")
                _render_data_table(run, show_divider=False)