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

class HorBar:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.type = "hor_bar"
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

        values = self.params.get("values")
        if values is None:
            data_array = np.asarray(self.data)
            if data_array.ndim > 1:
                values = data_array[0].tolist()
            else:
                values = data_array.tolist()
            try:
                values = [float(v) for v in values]
            except (ValueError, TypeError):
                raise ValueError("Bar chart requires numeric data for values.")

        labels = self.params.get("labels")
        if labels is None:
            if isinstance(self.metadata, (list, tuple)) and len(self.metadata) == len(values):
                labels = list(self.metadata)
            else:
                labels = [str(i) for i in range(len(values))]

        figure = go.Figure()

        figure.add_trace(go.Bar(
            x = values[::-1],
            y = labels[::-1],
            orientation = 'h',
            text = values[::-1],
            textposition = "outside",
            marker = dict(
                color = "#e4781d",
                line = dict (width = 1, color = "#e4781d")
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
            font = dict(color = "white", family = "Arial", size = 15),
            xaxis = dict(showgrid = True, gridcolor = "white"),
            yaxis = dict(showgrid = False, automargin = True, ticklabelstandoff = 10),
            height = 500
        )

        buffer = BytesIO()

        figure.write_image(buffer, format = "png", scale = 2)

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
