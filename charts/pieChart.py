import os
import numpy as np
import plotly.graph_objects as go
import plotly.colors as pc
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

class PieChart:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.type = "pie_chart"
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

    def color_pallette(self, n, base = "#e4781d"):
            base = base.lstrip("#")

            r = int(base[0:2], 16)
            g = int(base[2:4], 16)
            b = int(base[4:6], 16)

            colors = []

            for i in range(n):
                factor = i / max(n - 1, 1)

                # blend toward white for lighter shades
                r2 = int(r + (255 - r) * factor * 0.6)
                g2 = int(g + (255 - g) * factor * 0.6)
                b2 = int(b + (255 - b) * factor * 0.6)

                colors.append(f"#{r2:02x}{g2:02x}{b2:02x}")

            return colors
    
    def _create_chart(self):
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
                raise ValueError("Pie chart requires numeric data for values.")

        labels = self.params.get("labels")
        if labels is None:
            if isinstance(self.metadata, (list, tuple)) and len(self.metadata) >= len(values):
                labels = list(self.metadata[:len(values)])
            else:
                labels = [str(i) for i in range(len(values))]

        colors = self.color_pallette(len(labels))

        fig = go.Figure(go.Pie(
            labels = labels,
            values = values,
            hole = 0.45,
            marker = dict(colors = colors),
            textinfo = "percent+label",
            textposition = "outside"
        ))

        fig.update_layout(
            title = "",
            template = "plotly_dark",
            paper_bgcolor = "black",
            font = dict(color = "white")
        )

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
