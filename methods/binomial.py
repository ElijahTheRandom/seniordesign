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
        """Return None if data is valid, or an error string if not."""
        if self.data is None:
            return "Binomial requires [n, p, kMin] at minimum"
        try:
            arr = np.asarray(self.data).flatten()
        except Exception:
            return "Binomial requires numeric [n, p, kMin] data"
        if len(arr) < 3:
            return "Binomial requires at least 3 values: [n, p, kMin]"
        return None

    def _generate_stat_structure(self, value):
        """Standard stat result dict (used by compute())."""
        return {
            "id": self.type,
            "ok": True,
            "value": value,
            "error": None,
            "loss_of_precision": False,
            "params_used": self.params,
        }

    def _generate_stat_error(self, error_message):
        """Standard error result dict (used by compute())."""
        return {
            "id": self.type,
            "ok": False,
            "value": None,
            "error": error_message,
            "loss_of_precision": False,
            "params_used": self.params,
        }

    def compute(self):
        """Compute the binomial distribution table and return a standard result dict.

        Data format: [n, p, kMin] or [n, p, kMin, kMax]
        Returns value as a pandas DataFrame with columns:
            k, P(X = k), P(X <= k), P(X >= k)
        """
        reason = self._applicable()
        if reason is not None:
            return self._generate_stat_error(reason)

        try:
            import pandas as pd
            arr = np.asarray(self.data).flatten()
            n = int(arr[0])
            p = float(arr[1])
            k_min = int(arr[2])
            k_max = int(arr[3]) if len(arr) > 3 else n

            if n < 1:
                return self._generate_stat_error("n must be >= 1")
            if not (0.0 <= p <= 1.0):
                return self._generate_stat_error(
                    "p must be a probability between 0 and 1"
                )
            if k_min < 0 or k_max < 0:
                return self._generate_stat_error("k_min and k_max must be >= 0")
            if k_max < k_min:
                return self._generate_stat_error("k_max must be >= k_min")

            k_values = np.arange(k_min, k_max + 1)
            df = pd.DataFrame({
                "k":        k_values.tolist(),
                "P(X = k)": binom.pmf(k_values, n, p),
                "P(X <= k)": binom.cdf(k_values, n, p),
                "P(X >= k)": binom.sf(k_values - 1, n, p),
            })
        except Exception as exc:
            return self._generate_stat_error(str(exc))

        return self._generate_stat_structure(df)

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
        # Get parameters either from self.params or from self.data
        if isinstance(self.params, dict) and "n" in self.params and "p" in self.params:
            n = int(self.params.get("n", 0))
            p = float(self.params.get("p", 0))
            k_min = int(self.params.get("k_min", 0))
            k_max = int(self.params.get("k_max", n))
        else:
            array = np.asarray(self.data).flatten()
            if len(array) < 2:
                raise ValueError(
                    "Binomial chart requires [n, p, k_min, k_max] in data "
                    "or parameters {'n':..., 'p':..., 'k_min':..., 'k_max':...}"
                )

            n = int(array[0])
            p = float(array[1])
            k_min = int(array[2]) if len(array) > 2 else 0
            k_max = int(array[3]) if len(array) > 3 else n

        # Validation
        if n < 1:
            raise ValueError("Parameter 'n' must be >= 1")
        if not (0 <= p <= 1):
            raise ValueError("Parameter 'p' must be between 0 and 1")
        if k_min < 0 or k_max < 0:
            raise ValueError("k_min and k_max must be >= 0")
        if k_max < k_min:
            raise ValueError("k_max must be >= k_min")

        k_values = np.arange(k_min, k_max + 1)

        rows = []
        for k in k_values:
            rows.append([
                str(k),
                f"{binom.pmf(k, n, p):.4f}",
                f"{binom.cdf(k, n, p):.4f}",
                f"{binom.sf(k - 1, n, p):.4f}"
            ])

        col_labels = ["k", "P(X = k)", "P(X ≤ k)", "P(X ≥ k)"]

        fig_height = max(2.5, 0.42 * len(rows) + 1.4)
        fig, ax = plt.subplots(figsize=(4.0, fig_height * 0.5 - 0.3))
        fig.patch.set_facecolor("black")
        ax.set_facecolor("black")
        ax.axis("off")

        table = ax.table(
            cellText=rows,
            colLabels=col_labels,
            cellLoc="center",
            loc="center"
        )

        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.0, 1.0)

        # Dark default styling for the exported binomial table image.
        for (r, c), cell in table.get_celld().items():
            cell.set_facecolor("black")
            cell.set_edgecolor("white")
            if r == 0:
                cell.set_text_props(color="white", weight="bold")
            else:
                cell.set_text_props(color="white")

        ax.text(
            0.5,
            1.01,
            f"n = {n}, p = {p}",
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=11,
            color="white",
            bbox=dict(facecolor="black", edgecolor="none", alpha=1.0, pad=0.5)
        )

        plt.tight_layout()
        plt.subplots_adjust(top=0.95)

        buffer = BytesIO()
        fig.savefig(
            buffer,
            format="png",
            bbox_inches="tight",
            dpi=200,
            facecolor=fig.get_facecolor(),
            edgecolor="none",
        )
        plt.close(fig)
        buffer.seek(0)

        return buffer

    def create_graphic(self):
        # Perform the statistical computation and return a standardized result dictionary
        reason = self._applicable()
        if reason is not None:
            return self._generate_return_structure_error(reason)
        
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
