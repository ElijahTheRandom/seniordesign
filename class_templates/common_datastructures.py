message = {
    # ----------- request context -----------
    "dataset_id": "ds_001",        # Req 1.1 (CSV imported into an internal table -> dataset identity), Req 3.10 (multiple analyses per session), Req 5.4 (compare across runs/datasets)
    "dataset_version": 3,          # Req 1.9 (re-run after edits without restart), Req 4.5 (pipeline records dataset version), Req 4.6 (replay prior run)

    # ----------- selection -----------
    "selection": {                 # Req 2.10 (subset of rows/cols), Req 3.9 (report exact selection used)
        "rows": [0, 1, 2, 3],
        "cols": [0]
    },

    # ----------- requested operations -----------
    "methods": [                   # Req 1.8 (select one or more statistics to run)
        {"id": "mean", "params": {}},                 # Req 1.3 (mean)
        {"id": "median", "params": {}},               # Req 1.4 (median)
        {"id": "percentiles", "params": {"p": [25, 50, 75]}}  # Req 2.4 (percentiles with user-chosen percentile values)
    ],

    # ----------- raw data -----------
    "data": [                      # Req 1.1 (data imported from CSV / internal table); also supports Req 1.2 (edited data can be sent if you don't patch)
        22,
        30,
        "N/A",
        41
    ],

    # ----------- backend results -----------
    # empty on request; filled on response
    "results": [                   # Req 1.6 (display computed results in GUI), Req 4.9 (consistent structured output schema), Req 3.10 (combined report for multiple runs)
        {
            "id": "mean",          # Req 1.3 (mean)
            "ok": False,           # Req 4.10 (runtime validation outcome / failure)
            "value": None,         # Req 1.6 (standard place for computed value)
            "error": "Non-numeric cell detected",  # Req 4.10 (precise failure reason tied to applicability/preconditions)
            "loss_of_precision": None, # Req 5.6 (indicate if precision was lost during computation)
            "non_numeric_cells": [ # Req 1.7 (detect non-numeric cells and report affected row/col positions)
                {"row": 2, "col": 0, "value": "N/A"}
            ]
        },
        {
            "id": "median",        # Req 1.4 (median)
            "ok": True,            # Req 1.6 (result display), Req 4.10 (validation passed)
            "value": 30,
            "error": None,
            "loss_of_precision": None, # Req 5.6 (indicate if precision was lost during computation)
            "non_numeric_cells": []
        }
    ],

    # ----------- text + graphics -----------
    "summary_text": "",            # Req 1.10 (export plain-text summary report of most recent run)
    "graphics": [                  # Req 3.1–3.6 (choose/render graphs), Req 3.7 (export graph as JPEG)
        {"type": "bar", "path": "exports/age_bar.jpg"}
    ]
}
