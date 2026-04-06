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
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x = self.data[0],
            y = self.data[1],
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
