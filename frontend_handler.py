"""
logic/frontend_handler.py
-------------------------
Unpacks a completed result Message from BackendHandler and converts
each result into stat card tuples ready for results.py to render.

PUBLIC INTERFACE:
    handle_result(run) -> run
"""
from unittest import result


_ID_TO_DISPLAY: dict[str, str] = {
    "mean":                      "Mean",
    "median":                    "Median",
    "mode":                      "Mode",
    "variance":                  "Variance",
    "std":                       "Standard Deviation",
    "percentiles":               "Percentiles",
    "pearson":                   "Pearson's Correlation",
    "spearman":                  "Spearman's Rank",
    "least_squares_regression":  "Least Squares Regression",
    "chi_squared":               "Chi-Square Test",
    "binomial":                  "Binomial Distribution",
    "variation":                 "Coefficient of Variation",
}

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
        if result.get("ok"):
            display_name = _ID_TO_DISPLAY.get(result['id'], result['id'])
            cards.append(("stat", f"<b>{display_name}</b>", f"{result['value']:.2f}"))
    run["cards"] = cards
    return run