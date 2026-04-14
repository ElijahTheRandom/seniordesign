import base64
from io import BytesIO

import numpy as np


class LeastSquaresRegression:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "least_squares_regression"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if self.data is None or len(self.data) < 2 or len(self.data[0]) != len(self.data[1]):
            return "Least Squares Regression requires exactly 2 columns of equal length"
        return None

    def _generate_return_structure(self, value):
        # Check whether this statistic is valid for the given data selection
        return {
            "id": self.stat_id,
            "ok": True,
            "value": value,
            "error": None,
            "loss_of_precision": False,
            "params_used": self.params
        }

    def _generate_return_structure_error(self, error_message):
        return {
            "id": self.stat_id,
            "ok": False,
            "value": None,
            "error": error_message,
            "loss_of_precision": False,
            "params_used": self.params
        }

    def compute(self):
        # Perform the statistical computation and return a standardized result dictionary
        reason = self._applicable()
        if reason is not None:
            return self._generate_return_structure_error(reason)
        
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            # Turn the xs and ys into np arrays
            x = np.array(self.data[0], dtype=float)
            y = np.array(self.data[1], dtype=float)

            # Calculate the slope and intercept with np
            slope, intercept = np.polyfit(x, y, 1)

            # R-squared
            y_pred = slope * x + intercept
            ss_res = float(np.sum((y - y_pred) ** 2))
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            r_squared = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0

            equation = f"y = {slope:.3f}x + {intercept:.3f}"

            # Generate scatter + regression line chart
            fig, ax = plt.subplots(figsize=(5, 4))
            fig.patch.set_facecolor("#1e2530")
            ax.set_facecolor("#1e2530")
            ax.scatter(x, y, color="steelblue", alpha=0.7, s=20, label="Data")
            x_line = np.linspace(x.min(), x.max(), 300)
            ax.plot(x_line, slope * x_line + intercept,
                    color="#e4781d", linewidth=2, label="Fit")
            ax.set_xlabel("x", color="white")
            ax.set_ylabel("y", color="white")
            ax.tick_params(colors="white")
            for spine in ax.spines.values():
                spine.set_edgecolor((1, 1, 1, 0.3))
            ax.legend(facecolor="#1e2530", labelcolor="white", framealpha=0.6)
            plt.tight_layout()

            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", dpi=100,
                        facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            buf.seek(0)
            chart_b64 = base64.b64encode(buf.read()).decode("utf-8")

            value = {
                "slope":     float(slope),
                "intercept": float(intercept),
                "r_squared": float(r_squared),
                "equation":  equation,
                "chart":     chart_b64,
            }

        except Exception as e:
            return self._generate_return_structure_error(str(e))

        results = self._generate_return_structure(value)
        return results

    def create_graphic(self, results):
        # No standalone graphic for least squares regression
        # (the best_fit chart class handles the visualization)
        pass
