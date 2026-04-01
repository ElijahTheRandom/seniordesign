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
    visualization is selected. Bar and pie charts are excluded since
    they can handle mixed data (a string label column + numeric values).

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
    # List of all of the currently possible numeric methods and plots.
    # Bar and pie charts are excluded — they can handle mixed data
    # (a string label column + a numeric value column).
    numeric_methods = {
        "mean", "median", "mode", "standard_deviation", "variance",
        "pearson", "spearman", "least_squares_regression", "percentile", "coefficient_variation",
        "chisquared", "binomial",
        "scat_plot", "best_fit",
    }
    # Custom methods (prefixed with 'custom_') also require numeric data
    numeric_methods.update(
        k for k in method_flags if k.startswith("custom_")
    )

    # Determines if at least one selected method requires some form of validation
    numeric_required = any(
        method_flags.get(m, False)
        for m in numeric_methods
    )

    # Skips validation if no numeric method is selected
    if not numeric_required:
        return []

    # Stores all sells that fails the validation tests and returns a list of all of the
    # cells that cause issues for the data
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

# Creates a run based on the input from the user
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
        "id":   str(uuid.uuid4()), # Generate a unique id for the run
        "name": f"Run {run_count + 1}",
        "table": edited_table, # Stores the whole og table as a reference
        "data":  parsed_data.reset_index(drop=True), # Stores the sliced data
        "columns": col1,
        "rows":    col2,
        "methods": _collect_selected(method_flags, METHOD_NAMES), # Converts selected items into readable method names
        "visualizations": _collect_selected(method_flags, VIZ_NAMES), # Converts selected items into readable visualization names
    }

# Error message sent to the user if they selected incompatible data for some calculation/visual
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
    lines = ["**Invalid data found:**"]
    for cell in preview:
        lines.append(f"- Row {cell['row']}, Col '{cell['column']}': '{cell['value']}'")
    if len(non_numeric_cells) > 2:
        lines.append(f"...and {len(non_numeric_cells) - 2} more entries.")
    return "\n".join(lines)

# Success message sent to the user once their run tab has been generated and where to go
def build_success_message(run: dict) -> str:
    """
    Build the user-facing success message after a run is created.

    Args:
        run: The newly created run dict.

    Returns:
        A short confirmation string for the success modal.
    """
    return (
        f"**'{run['name']}' has been successfully created!**\n"
        f"- Please see the side bar for your analysis."
    )

def build_success_save_message(run: dict) -> str:
    """
    Build the user-facing success message after a run is saved.

    Args:
        run: The newly created run dict.

    Returns:
        A short confirmation string for the success modal.
    """
    return (
        f"**'{run['name']}' has been successfully saved!**\n"
        f"- Please see the Load Previous Runs section."
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
        for key, display_name in name_map.items() # Preserves the display order
        if flags.get(key, False) # Include only true flags 
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

# Maps the internal method keys to how they're displayed for the user
METHOD_NAMES: dict[str, str] = {
    "mean":                     "Mean",
    "median":                   "Median",
    "mode":                     "Mode",
    "variance":                 "Variance",
    "standard_deviation":       "Standard Deviation",
    "percentile":               "Percentile",
    "pearson":                  "Pearson",
    "spearman":                 "Spearman",
    "least_squares_regression": "Least Squares Regression",
    "chisquared":               "Chi-Square",
    #"binomial":                 "Binomial",
    "coefficient_variation":    "Coefficient of Variation",
}


def _load_custom_method_names():
    """Merge custom method display names into METHOD_NAMES at runtime."""
    try:
        from custom_methods_loader import get_custom_display_names
        METHOD_NAMES.update(get_custom_display_names())
    except Exception:
        pass


_load_custom_method_names()

# Maps the internal visualization key to how they're displayed for the user
VIZ_NAMES: dict[str, str] = {
    "pie_chart": "Pie Chart",
    "vert_bar":  "Vertical Bar Chart",
    "hor_bar":   "Horizontal Bar Chart",
    "scat_plot": "Scatter Plot",
    "best_fit":  "Line of Best Fit Scatter Plot",
    "binomial": "Binomial"
}
