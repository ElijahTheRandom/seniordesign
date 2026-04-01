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

class BestFit:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.type = "best_fit"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if "path" not in self.params or not self.params["path"]:
            return "No output path provided"
        return None

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
        x = np.array(self.data[0], dtype = float)
        y = np.array(self.data[1], dtype = float)

        slope, intercept = np.polyfit(x, y, 1)

        padding = (x.max() - x.min()) * 0.2

        xFit = np.linspace(x.min() - padding, x.max() + padding, 100, endpoint = False)
        yFit = slope * xFit + intercept

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x = self.data[0],
            y = self.data[1],
            mode = "markers",
            marker = dict(color = "#e4781d", size = 10),
            name = "Data Markers"
        ))

        fig.add_trace(go.Scatter(
            x = xFit,
            y = yFit,
            mode = "lines",
            line = dict(color = "#f59403", width = 3),
            name = "Line of Best Fit"
        ))

        fig.update_layout(
            plot_bgcolor = "black",
            paper_bgcolor = "black",
            font = dict(color = "white"),
            title = ""
        )

        fig.update_xaxes(gridcolor = "#222222", dtick = 1)
        fig.update_yaxes(gridcolor = "#222222", dtick = 1)

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
