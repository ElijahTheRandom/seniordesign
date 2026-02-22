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

class ChartName:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.type = "chart_name"
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
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x = self.params[1],
            y = self.params[1],
            mode = "markers",
            marker = dict(
                color = "#ff6600",
                size = 10
            )
        ))

        fig.update_layout(
            plot_bgcolor = "black",
            paper_bgcolor = "black",
            font = dict(color = "white"),
            title = ""
        )

        buffer = BytesIO()
        fig.write_image(buffer, format = "png")
        buffer.seek(0)
        
        return buffer

    def create_graphic(self):
        # Perform the statistical computation and return a standardized result dictionary
        _applicable = self._applicable()
        if not _applicable:
            return self._generate_return_structure_error(_applicable)
        
        try:
            chart = self._create_chart()
            output_path = self.params["path"]
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            chart.savefig(output_path, bbox_inches="tight")
        except Exception as exc:
            return self._generate_return_structure_error(str(exc))

        return self._generate_return_structure()
