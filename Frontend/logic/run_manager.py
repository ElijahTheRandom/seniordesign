"""
logic/run_manager.py
--------------------
Business logic for creating and validating PS Analytics runs.

WHY THIS FILE EXISTS:
    Run creation and validation were previously embedded inside
    views/homepage.py (_handle_run_analysis), marked with TODO (Stage 6)
    seam comments. They lived there temporarily because it was the safe
    incremental move — extract the UI first, then separate the logic.

    This file completes that separation. The result:

        views/homepage.py   — renders the button, calls these functions
        logic/run_manager.py — does the actual work, no Streamlit

THE RULE FOR THIS FILE:
    No `import streamlit`. No `st.*`. No session state.
    Every function here is pure: given inputs, it returns outputs.
    This makes every function independently testable without a browser.

PUBLIC INTERFACE:
    validate_numeric(data, method_flags)  → list[dict]  (problem cells)
    create_run(parsed_data, edited_table, col1, col2,
               method_flags, run_count)   → dict         (the run object)
    build_error_message(non_numeric_cells) → str
    build_success_message(run)             → str
"""

import uuid
import pandas as pd


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def validate_numeric(
    data: pd.DataFrame,
    method_flags: dict[str, bool],
) -> list[dict]:
    """
    Check whether all values in `data` are numeric, for methods that
    require it.

    Only runs the check if at least one numeric method or numeric
    visualization is selected. Categorical-only methods (Chi-Square,
    Binomial) do not trigger the check.

    Args:
        data:         The sliced DataFrame the user wants to analyze.
        method_flags: Dict of method/viz name → bool, e.g.:
                      {"mean": True, "pearson": False, "viz_hist": True}

    Returns:
        A list of problem-cell dicts, each with keys:
            "row"    – 1-based row index
            "column" – column name
            "value"  – the offending non-numeric value
        Returns an empty list if all data is valid or no numeric
        method is selected.
    """
    numeric_methods = {
        "mean", "median", "mode", "std_dev", "variance",
        "pearson", "spearman", "regression", "percentiles", "variation",
        "viz_hist", "viz_box", "viz_scatter", "viz_line", "viz_heatmap",
    }

    numeric_required = any(
        method_flags.get(m, False)
        for m in numeric_methods
    )

    if not numeric_required:
        return []

    non_numeric = []
    for col in data.columns:
        coerced = pd.to_numeric(data[col], errors="coerce")
        bad_rows = data[coerced.isna() & data[col].notna()]
        for row_idx, val in bad_rows[col].items():
            non_numeric.append({
                "row":    row_idx,
                "column": col,
                "value":  val,
            })

    return non_numeric


def create_run(
    parsed_data: pd.DataFrame,
    edited_table: pd.DataFrame,
    col1: list[str],
    col2: list[int],
    method_flags: dict[str, bool],
    run_count: int,
) -> dict:
    """
    Build a new analysis run dict.

    This is a pure factory function — it creates a run from its
    inputs and returns it. It does not append to session state; that
    remains the caller's responsibility in views/homepage.py.

    Args:
        parsed_data:  The sliced DataFrame (selected cols + rows).
        edited_table: The full unsliced DataFrame (stored for reference).
        col1:         List of selected column names.
        col2:         List of selected 1-based row indices.
        method_flags: Dict of method name → bool (same shape as
                      validate_numeric expects).
        run_count:    Current number of existing runs, used to name
                      this run "Run N+1".

    Returns:
        A run dict with keys:
            id, name, table, data, columns, rows, methods, visualizations
    """
    return {
        "id":   str(uuid.uuid4()),
        "name": f"Run {run_count + 1}",
        "table": edited_table,
        "data":  parsed_data.reset_index(drop=True),
        "columns": col1,
        "rows":    col2,
        "methods": _collect_selected(method_flags, METHOD_NAMES),
        "visualizations": _collect_selected(method_flags, VIZ_NAMES),
    }


def build_error_message(non_numeric_cells: list[dict]) -> str:
    """
    Build the user-facing error message for non-numeric data.

    Shows up to 2 problem cells in detail, then summarises any
    additional ones with "...and N more entries."

    Args:
        non_numeric_cells: List of problem-cell dicts from
                           validate_numeric().

    Returns:
        A multi-line string suitable for display in the error modal.
    """
    preview = non_numeric_cells[:2]
    lines = ["The following non-numeric data was found:"]
    for cell in preview:
        lines.append(
            f" - Row: {cell['row']}, Column: {cell['column']}, "
            f"Value: '{cell['value']}'"
        )
    if len(non_numeric_cells) > 2:
        lines.append(f" ...and {len(non_numeric_cells) - 2} more entries.")
    return "\n".join(lines)


def build_success_message(run: dict) -> str:
    """
    Build the user-facing success message after a run is created.

    Args:
        run: The newly created run dict.

    Returns:
        A short confirmation string for the success modal.
    """
    return (
        f"Analysis '{run['name']}' has been successfully created!\n"
        f"Please see the side bar for your analysis."
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _collect_selected(
    flags: dict[str, bool],
    name_map: dict[str, str],
) -> list[str]:
    """
    Return display names for all flags that are True.

    Args:
        flags:    Dict of internal key → bool  (e.g. {"mean": True})
        name_map: Dict of internal key → display name
                  (e.g. {"mean": "Mean"})

    Returns:
        List of display names whose flag is True, in name_map order.
    """
    return [
        display_name
        for key, display_name in name_map.items()
        if flags.get(key, False)
    ]


# ---------------------------------------------------------------------------
# Name maps
# ---------------------------------------------------------------------------
# These dicts define the canonical mapping between the internal flag key
# (as used in method_flags dicts throughout the app) and the human-readable
# display name stored in run["methods"] and run["visualizations"].
#
# Keeping them here — in the logic layer — means the views never need to
# hardcode these strings. They just pass flags through and let run_manager
# produce the names.

METHOD_NAMES: dict[str, str] = {
    "mean":       "Mean",
    "median":     "Median",
    "mode":       "Mode",
    "variance":   "Variance",
    "std_dev":    "Standard Deviation",
    "percentiles": "Percentiles",
    "pearson":    "Pearson",
    "spearman":   "Spearman",
    "regression": "Regression",
    "chi_square": "Chi-Square",
    "binomial":   "Binomial",
    "variation":  "Variation",
}

VIZ_NAMES: dict[str, str] = {
    "hist":    "Pie Chart",
    "box":     "Vertical Bar Chart",
    "scatter": "Horizontal Bar Chart",
    "line":    "Scatter Plot",
    "heatmap": "Line of Best Fit Scatter Plot",
}
