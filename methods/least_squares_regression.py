import base64

import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

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
            return False
        return True

    def _generate_return_structure(self, value):
        # Check whether this statistic is valid for the given data selection
        return {
            "id": self.stat_id,
            "ok": True,
            "value": value,
            "error": None,
            "loss_of_precision": False,  # Could be the regression error
            "params_used": len(self.data[0]) + len(self.data[1])
        }

    def _generate_return_structure_error(self, error_message):
        return {
            "id": self.stat_id,
            "ok": False,
            "value": None,
            "error": error_message,
            "loss_of_precision": False,
            "params_used": len(self.data[0]) + len(self.data[1])
        }

    def compute(self):
        # Perform the statistical computation and return a standardized result dictionary
        _applicable = self._applicable()
        if not _applicable:
            return self._generate_return_structure_error("There must be an equal collection of xs and ys in the dataset")
        
        # Placeholder for the main computation logic

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

        # Line for the plot
        xFit = np.linspace(x.min(), x.max(), 200)
        yFit = slope * xFit + intercept

        chart_b64 = self.create_graphic(x, y, xFit, yFit)

        value = {
            "slope": float(slope),
            "intercept": float(intercept),
            "r_squared": float(r_squared),
            "equation": f"y = {slope:.4f}x + {intercept:.4f}",
            "chart": chart_b64,
        }

        results = self._generate_return_structure(value)
        return results

    def create_graphic(self, xs, ys, xLine, yLine):
        # Generate a chart or visualization object for the computed results
        # Use the non-interactive Agg backend so this is safe to call from threads.
        plt.switch_backend("Agg")
        fig = plt.figure()
        plt.scatter(xs, ys)
        plt.plot(xLine, yLine)
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Least Squares Regression Line")

        # Save the image to memory, get it, and return it
        buffer = BytesIO()
        plt.savefig(buffer, format = "png", bbox_inches = "tight")
        plt.close(fig)

        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
