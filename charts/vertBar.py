import os
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import plotly.graph_objects as go
import plotly.io as pio

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

class VertBar:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.type = "vert_bar"
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
        pio.renderers.default = "vscode"

        figure = go.Figure()

        figure.add_trace(go.Bar(
            x = self.params,
            y = self.data,
            text = self.data,
            textposition = "outside",
            marker = dict(
                color = "#ff9900",
                line = dict (width = 1, color = "#ff9900")
            )
        ))

        figure.update_layout(
            title = dict(
                text = "Bar Chart",
                x = 0.5,
                font = dict(color = "white", size = 20)
            ),
            template = "plotly_dark",
            paper_bgcolor = "black",
            plot_bgcolor = "black",
            font = dict(color = "white"),
            xaxis = dict(showgrid = False),
            yaxis = dict(showgrid = True, gridcolor = "gray"),
            height = 500
        )

        buffer = BytesIO()

        figure.write_image(buffer, format = "png", scale = 2)

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
