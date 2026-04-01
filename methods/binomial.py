import os
import numpy as np
from io import BytesIO
import matplotlib.pyplot as plt
from scipy.stats import binom

"""
    "graphics": [ #3.6
        {
            "type": "scatter", 
            "x_col": 2, 
            "y_col": 3, 
            "path": "exports/scatter_plot.jpg"
            "output":{
                    "type": self.type,
                    "ok": False,
                    "path": self.params.get("path"),
                    "error": error_message,
                    "params_used": self.params,
            }
        }
    ],
"""

class Binomial:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.type = "binomial"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if "path" not in self.params or not self.params["path"]:
            return "No output path provided"
        
        return True

    def _generate_return_structure(self):
        # Check whether this statistic is valid for the given data selection
        return {
            "type": self.type,
            "ok": True,
            "path": self.params.get("path"),
            "error": None,
            "params_used": self.params,
        }

    def _generate_return_structure_error(self, error_message):
        return {
            "type": self.type,
            "ok": False,
            "path": self.params.get("path"),
            "error": error_message,
            "params_used": self.params,
        }

    def _create_chart(self):
        # Create and return a chart object (e.g., matplotlib Figure).
        # Prefer parameters from self.params (passed by the frontend UI);
        # fall back to reading from self.data for backwards compatibility.
        if "n" in self.params:
            n = int(self.params["n"])
            p = float(self.params["p"])
            kMin = int(self.params.get("k_min", 0))
            kMax = int(self.params.get("k_max", n))
        else:
            array = np.asarray(self.data).flatten()
            n = int(array[0])
            p = float(array[1])
            kMin = int(array[2])
            kMax = int(array[3]) if len(array) > 3 else n
        

        k = np.arange(kMin, kMax + 1)

        rows = []

        for i in k:
            rows.append([
                    str(i), 
                    f"{binom.pmf(i, n, p):.4f}", 
                    f"{binom.cdf(i, n, p):.4f}",
                f"{binom.sf(i - 1, n, p):.4f}"
            ])

        col_labels = ["k", "P(X = k)", "P(X ≤ k)", "P(X ≥ k)"]

        fig_height = max(2, 0.5 * len(rows) + 1.2)
        fig, ax = plt.subplots(figsize = (4.5, 2.8))
        ax.axis("off")

        table = ax.table(
            cellText = rows,
            colLabels = col_labels,
            cellLoc = "center",
            loc = "center"
        )

        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.4)

        plt.tight_layout()
        
        buffer = BytesIO()

        plt.savefig(buffer, format = "png", bbox_inches = "tight", dpi = 200)
        plt.close(fig)
        buffer.seek(0)

        return buffer

    def create_graphic(self):
        # Perform the statistical computation and return a standardized result dictionary
        _applicable = self._applicable()
        if _applicable is not True:
            return self._generate_return_structure_error(_applicable)
        
        try:
            chart = self._create_chart()
            output_path = self.params["path"]
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            with open(output_path, "wb") as f:
                f.write(chart.getvalue())
        except Exception as exc:
            return self._generate_return_structure_error(str(exc))

        return self._generate_return_structure()
