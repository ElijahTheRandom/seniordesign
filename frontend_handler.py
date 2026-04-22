"""
logic/frontend_handler.py
-------------------------
Unpacks a completed result Message from BackendHandler and converts
each result into stat card tuples ready for results.py to render.

PUBLIC INTERFACE:
    handle_result(run) -> run
"""
_ID_TO_DISPLAY: dict[str, str] = {
    "mean":                     "Mean",
    "median":                   "Median",
    "mode":                     "Mode",
    "variance":                 "Variance",
    "standard_deviation":       "Standard Deviation",
    "percentile":               "Percentile",
    "pearson":                  "Pearson's Correlation",
    "spearman":                 "Spearman's Rank",
    "least_squares_regression": "Least Squares Regression",
    "chisquared":               "Chi-Square Test",
    #"binomial":                 "Binomial Distribution",
    "coefficient_variation":    "Coefficient of Variation",
}

# Methods that reduce their input to a single 1-D dataset. When the user
# selects more than one column and picks one of these, the backend flattens
# all selected columns together (see methods/*.py — np.asarray(data) with
# no axis, or an explicit .flatten()). We surface a notice on the results
# page so the user isn't surprised by a combined result. Custom methods are
# intentionally excluded — we can't know their shape contract.
_UNIVARIATE_METHOD_IDS: set[str] = {
    "mean",
    "median",
    "mode",
    "variance",
    "standard_deviation",
    "percentile",
    "coefficient_variation",
}


def _load_custom_display_names():
    """Merge custom method display names into _ID_TO_DISPLAY at runtime."""
    try:
        from custom_methods_loader import get_custom_display_names
        _ID_TO_DISPLAY.update(get_custom_display_names())
    except Exception:
        pass


_load_custom_display_names()

def _ordinal(n: int) -> str:
    """Return the ordinal string for an integer (1 → '1st', 2 → '2nd', …)."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _format_scalar(value) -> str:
    """Format a numeric stat value for display, preserving small-magnitude signal.

    Uses 6 significant figures so p-values like 0.00012 stay visible instead of
    collapsing to "0.00". Integers and round floats still render cleanly
    ("3" or "3.14"). Exported reports carry full precision; see
    _render_precision_notice in results.py.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if v != v or v in (float("inf"), float("-inf")):
        return str(v)
    if v == 0:
        return "0"
    return f"{v:.6g}"


def _format_value(value, params_used=None) -> str:
    """Convert a result value to a human-readable string.

    Wrapped defensively: custom (LLM-generated) methods can return
    malformed shapes (non-numeric params, mixed types, nested structures).
    Any formatting failure falls back to ``str(value)`` rather than
    propagating an exception up into the render loop.
    """
    try:
        if isinstance(value, (int, float)):
            return _format_scalar(value)
        if isinstance(value, list):
            # If params_used is a list of percentile values, label each result.
            try:
                if (
                    params_used is not None
                    and isinstance(params_used, (list, tuple))
                    and len(params_used) == len(value)
                    and all(isinstance(v, (int, float)) for v in value)
                    and all(isinstance(p, (int, float)) for p in params_used)
                ):
                    parts = []
                    for p, v in zip(params_used, value):
                        p_int = int(p) if float(p).is_integer() else p
                        label = _ordinal(p_int) if isinstance(p_int, int) else f"{p_int}"
                        parts.append(f"{label}: {_format_scalar(v)}")
                    return ", ".join(parts)
            except Exception:
                pass
            formatted = [
                _format_scalar(v) if isinstance(v, (int, float)) else str(v)
                for v in value
            ]
            return ", ".join(formatted)
        if isinstance(value, dict):
            # Structured result (e.g. Least Squares Regression)
            if "equation" in value:
                parts = [str(value["equation"])]
                if "r_squared" in value:
                    try:
                        parts.append(f"R² = {float(value['r_squared']):.4f}")
                    except Exception:
                        parts.append(f"R² = {value['r_squared']}")
                return "  ".join(parts)
            return str(value)
        # pandas DataFrame (e.g. binomial distribution table)
        try:
            import pandas as pd
            if isinstance(value, pd.DataFrame):
                return value.to_string(index=False, float_format="{:.4f}".format)
        except Exception:
            pass
        return str(value)
    except Exception:
        try:
            return str(value)
        except Exception:
            return "<unprintable result>"


def handle_result(run: dict) -> dict:
    """
    Unpack result_message.results and attach card tuples to the run dict.

    Args:
        run: The run dict from session state. Must contain "result_message"
             (a Message object returned by BackendHandler).

    Returns:
        The same run dict with run["cards"], run["precision_warnings"], and
        run["multi_column_univariate_names"] populated.
        run["precision_warnings"] is a list of {"name": str, "note": str} dicts,
        one entry per result where loss_of_precision is a non-False truthy value.
        run["multi_column_univariate_names"] lists the display names of the
        univariate methods that ran against >1 selected column; empty if none.
    """
    cards = []
    precision_warnings = []
    multi_column_univariate_names: list[str] = []
    multi_column = len(run.get("columns") or []) > 1
    for result in run["result_message"].results:
        display_name = _ID_TO_DISPLAY.get(result['id'], result['id'])
        if result.get("ok"):
            value = result.get("value")
            value_str = _format_value(value, params_used=result.get("params_used"))
            cards.append(("stat", f"<b>{display_name}</b>", value_str))
        else:
            error_msg = result.get("error") or "Computation failed"
            cards.append(("error", f"<b>{display_name}</b>", str(error_msg)))

        lop = result.get("loss_of_precision")
        if lop:
            precision_warnings.append({"name": display_name, "note": str(lop)})

        if multi_column and result.get("id") in _UNIVARIATE_METHOD_IDS:
            multi_column_univariate_names.append(display_name)

    run["cards"] = cards
    run["precision_warnings"] = precision_warnings
    run["multi_column_univariate_names"] = multi_column_univariate_names
    return run