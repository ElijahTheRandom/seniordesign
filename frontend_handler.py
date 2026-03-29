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


def _load_custom_display_names():
    """Merge custom method display names into _ID_TO_DISPLAY at runtime."""
    try:
        from custom_methods_loader import get_custom_display_names
        _ID_TO_DISPLAY.update(get_custom_display_names())
    except Exception:
        pass


_load_custom_display_names()

def _format_value(value) -> str:
    """Convert a result value to a human-readable string."""
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    if isinstance(value, list):
        formatted = [f"{float(v):.2f}" if isinstance(v, (int, float)) else str(v) for v in value]
        return ", ".join(formatted)
    # pandas DataFrame (e.g. binomial distribution table)
    try:
        import pandas as pd
        if isinstance(value, pd.DataFrame):
            return value.to_string(index=False, float_format="{:.4f}".format)
    except Exception:
        pass
    return str(value)


def handle_result(run: dict) -> dict:
    """
    Unpack result_message.results and attach card tuples to the run dict.

    Args:
        run: The run dict from session state. Must contain "result_message"
             (a Message object returned by BackendHandler).

    Returns:
        The same run dict with run["cards"] populated.
    """
    cards = []
    for result in run["result_message"].results:
        display_name = _ID_TO_DISPLAY.get(result['id'], result['id'])
        if result.get("ok"):
            value = result.get("value")
            value_str = _format_value(value)
            cards.append(("stat", f"<b>{display_name}</b>", value_str))
        else:
            error_msg = result.get("error") or "Computation failed"
            cards.append(("error", f"<b>{display_name}</b>", str(error_msg)))
    run["cards"] = cards
    return run