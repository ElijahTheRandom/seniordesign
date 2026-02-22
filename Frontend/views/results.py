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

    Each compute function receives run["data"] (a DataFrame) and
    returns a list of card tuples:
        ("stat", title_html, value_str)           — 3-tuple
        ("stat", title_html, value_str, subtext)  — 4-tuple

SESSION STATE READ:
    active_run_id, analysis_runs

SESSION STATE WRITTEN:
    active_run_id, analysis_runs (on delete)
"""

import streamlit as st
import pandas as pd

from utils.helpers import df_to_ascii_table


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
    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<hr style='margin: 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )

    st.header(f"Analysis Results — {run['name']}", anchor=False)
    st.markdown("---")

    _render_stat_cards(run)
    _render_visualizations(run)
    _render_data_table(run)
    _render_action_buttons(run)


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_stat_cards(run: dict) -> None:
    """
    Compute and render all stat cards for the methods in this run.

    Uses the STAT_COMPUTERS dispatch table to look up the compute
    function for each selected method. Unknown methods are silently
    skipped (future-proofing: old run dicts won't crash the page if a
    method name changes).

    Cards are laid out in a Pinterest-style grid of 3 columns with
    breathing room between rows.
    """
    cards = []

    for method in run["methods"]:
        compute_fn = STAT_COMPUTERS.get(method)
        if compute_fn:
            cards.extend(compute_fn(run["data"]))

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


def _render_visualizations(run: dict) -> None:
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

    st.markdown("---")


def _render_data_table(run: dict) -> None:
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
    st.markdown("---")


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
        st.button("Save This Run", use_container_width=True)

    with btn2:
        export_text = _build_export_text(run)
        st.download_button(
            label="Export This Run",
            data=export_text,
            file_name=f"{run['name']}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with btn3:
        if st.button("Delete This Run", use_container_width=True):
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

    if run["methods"]:
        lines.append("Methods Applied:")
        for m in run["methods"]:
            lines.append(f"- {m}")
        lines.append("")

    if run.get("visualizations"):
        lines.append("Visualizations Applied:")
        for v in run["visualizations"]:
            lines.append(f"- {v}")
        lines.append("")

    lines.append("Selected Data:")
    lines.append(df_to_ascii_table(run["data"]))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stat compute functions
# ---------------------------------------------------------------------------
# Each function receives the run's DataFrame and returns a list of card
# tuples. The 3-tuple form is ("stat", title, value). The 4-tuple form
# is ("stat", title, value, subtext).
#
# WHY SEPARATE FUNCTIONS INSTEAD OF elif BRANCHES:
#   - Each stat is independently readable and testable
#   - Adding a new stat = one new function + one dict entry
#   - The rendering loop (in _render_stat_cards) never needs to change
#   - The dispatch table below makes the full list of supported stats
#     visible at a glance
# ---------------------------------------------------------------------------

def _compute_mean(data: pd.DataFrame) -> list:
    return [
        ("stat", "<b>Mean</b>", f"{data[col].mean():.2f}")
        for col in data.select_dtypes(include=["number"]).columns
    ]


def _compute_median(data: pd.DataFrame) -> list:
    return [
        ("stat", "<b>Median</b>", f"{data[col].median():.2f}")
        for col in data.select_dtypes(include=["number"]).columns
    ]


def _compute_mode(data: pd.DataFrame) -> list:
    cards = []
    for col in data.select_dtypes(include=["number"]).columns:
        mode_val = data[col].mode()
        display = f"{mode_val.iloc[0]:.2f}" if len(mode_val) > 0 else "N/A"
        cards.append(("stat", "<b>Mode</b>", display))
    return cards


def _compute_variance(data: pd.DataFrame) -> list:
    return [
        ("stat", "<b>Variance</b>", f"{data[col].var():.2f}")
        for col in data.select_dtypes(include=["number"]).columns
    ]


def _compute_std_dev(data: pd.DataFrame) -> list:
    return [
        ("stat", "<b>Std Dev</b>", f"{data[col].std():.2f}")
        for col in data.select_dtypes(include=["number"]).columns
    ]


def _compute_percentiles(data: pd.DataFrame) -> list:
    cards = []
    for col in data.select_dtypes(include=["number"]).columns:
        p25 = data[col].quantile(0.25)
        p50 = data[col].quantile(0.50)
        p75 = data[col].quantile(0.75)
        cards.append((
            "stat",
            "<b>Percentiles</b>",
            f"{p25:.1f} / {p50:.1f} / {p75:.1f}",
            "25th / 50th / 75th",
        ))
    return cards


def _compute_variation(data: pd.DataFrame) -> list:
    cards = []
    for col in data.select_dtypes(include=["number"]).columns:
        mean_val = data[col].mean()
        std_val  = data[col].std()
        cv = (std_val / mean_val * 100) if mean_val != 0 else 0
        cards.append(("stat", "<b>Coeff. of Variation</b>", f"{cv:.2f}%"))
    return cards


# --- Placeholder stats (real computation will come in Stage 6) ---

def _compute_chi_square(data: pd.DataFrame) -> list:
    # TODO (Stage 6): Replace with real scipy.stats.chi2_contingency call
    return [("stat", "<b>Chi-Square</b>", "12.24", "p-value: 0.032")]


def _compute_pearson(data: pd.DataFrame) -> list:
    # TODO (Stage 6): Replace with real pandas .corr(method='pearson') call
    return [("stat", "<b>Pearson's Corr.</b>", "0.87", "Strong positive")]


def _compute_spearman(data: pd.DataFrame) -> list:
    # TODO (Stage 6): Replace with real pandas .corr(method='spearman') call
    return [("stat", "<b>Spearman's Rank</b>", "0.82", "Strong correlation")]


def _compute_regression(data: pd.DataFrame) -> list:
    # TODO (Stage 6): Replace with real numpy.polyfit / scipy.stats.linregress
    return [("stat", "<b>Regression</b>", "0.76", "Good fit")]


def _compute_binomial(data: pd.DataFrame) -> list:
    # TODO (Stage 6): Replace with real scipy.stats.binom call
    return [("stat", "<b>Binomial Prob</b>", "0.68", "n=10, p=0.5")]


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
# Maps method name strings (as stored in run["methods"]) to their
# compute functions. This is the ONLY place you touch when adding a
# new computation method — write the function above, add one line here.

STAT_COMPUTERS: dict[str, callable] = {
    "Mean":               _compute_mean,
    "Median":             _compute_median,
    "Mode":               _compute_mode,
    "Variance":           _compute_variance,
    "Standard Deviation": _compute_std_dev,
    "Percentiles":        _compute_percentiles,
    "Variation":          _compute_variation,
    "Chi-Square":         _compute_chi_square,
    "Pearson":            _compute_pearson,
    "Spearman":           _compute_spearman,
    "Regression":         _compute_regression,
    "Binomial":           _compute_binomial,
}
