import os
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

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

class ScatPlot:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.type = "scat_plot"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if "path" not in self.params or not self.params["path"]:
            return "No output path provided"
        if self.data is None or len(self.data) < 2:
            return "Scatter plot requires two numeric columns (x and y)."
        try:
            x_len = len(self.data[0])
            y_len = len(self.data[1])
        except TypeError:
            return "Scatter plot requires two sequence-like numeric columns."
        if x_len != y_len:
            return (
                f"Scatter plot requires x and y of equal length "
                f"(got x={x_len}, y={y_len})."
            )
        return None

    def _coerce_numeric(self):
        """Coerce x and y to float numpy arrays; raise ValueError on non-numeric."""
        try:
            x = np.asarray(self.data[0], dtype=float)
            y = np.asarray(self.data[1], dtype=float)
        except (ValueError, TypeError):
            raise ValueError("Scatter plot requires numeric data for both columns.")
        return x, y

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
        x, y = self._coerce_numeric()

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x = x,
            y = y,
            mode = "markers",
            marker = dict(
                color = "#e4781d",
                size = 7
            ),
            name = "Data Markers"
        ))

        fig.update_layout(
            plot_bgcolor = "black",
            paper_bgcolor = "black",
            font = dict(color = "white"),
            title = ""
        )

        fig.update_xaxes(gridcolor = "#4F4D4D")
        fig.update_yaxes(gridcolor = "#4f4d4d")

        buffer = BytesIO()
        fig.write_image(buffer, format = "png")
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
