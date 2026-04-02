import os
import numpy as np
import plotly.graph_objects as go
import plotly.colors as pc
from io import BytesIO
from collections import Counter
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

    def color_pallette(self, n, base = "#e4781d"):
            base = base.lstrip("#")

            r = int(base[0:2], 16)
            g = int(base[2:4], 16)
            b = int(base[4:6], 16)

            colors = []

            for i in range(n):
                factor = i / max(n - 1, 1)

                # blend toward white for lighter shades
                r2 = int(r + (255 - r) * factor * 0.8)
                g2 = int(g + (255 - g) * factor * 0.8)
                b2 = int(b + (255 - b) * factor * 0.8)

                colors.append(f"#{r2:02x}{g2:02x}{b2:02x}")

            return colors
    
    def _is_numeric_data(self):
        """Check if the data contains numeric values that should be used directly."""
        try:
            if self.params.get("values"):
                test_values = self.params["values"]
            else:
                data_array = np.asarray(self.data)
                if data_array.ndim > 1:
                    test_values = data_array.flatten()
                else:
                    test_values = data_array
            
            # Try to convert first few values to float
            for val in test_values[:min(5, len(test_values))]:
                float(val)
            return True
        except (ValueError, TypeError):
            return False
    
    def _create_chart(self):
        # Check if we should count label frequencies instead of using raw values
        if self.params.get("count_labels", False) or not self._is_numeric_data():
            # Count frequency of each unique label
            data_list = []
            
            if self.params.get("values"):
                data_list = self.params["values"]
            else:
                data_array = np.asarray(self.data)
                if data_array.ndim > 1:
                    data_list = data_array.flatten().tolist()
                else:
                    data_list = data_array.tolist()
            
            # Count frequencies
            label_counts = Counter(data_list)
            labels = list(label_counts.keys())
            values = list(label_counts.values())
        else:
            # Original numeric value processing
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
            else:
                values = list(values)
                try:
                    values = [float(v) for v in values]
                except (ValueError, TypeError):
                    raise ValueError("Pie chart requires numeric data for values.")

            labels = self.params.get("labels")
            if labels is not None:
                if len(labels) != len(values):
                    raise ValueError("Pie chart requires labels to align with values length.")

                # Sum values by label so duplicate labels aggregate into one slice
                label_totals = {}
                for lbl, val in zip(labels, values):
                    label_totals[lbl] = label_totals.get(lbl, 0.0) + val

                labels = list(label_totals.keys())
                values = list(label_totals.values())
            else:
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


        # Keep legend readable for larger label sets (up to ~35 items)
        if len(labels) <= 10:
            legend_font_size = 13
            chart_height = 720
            legend_x = 1.02
            right_margin = 420
        elif len(labels) <= 20:
            legend_font_size = 10
            chart_height = 980
            legend_x = 1.05
            right_margin = 450
        elif len(labels) <= 35:
            legend_font_size = 8
            chart_height = 1500
            legend_x = 1.10
            right_margin = 520
        else:
            legend_font_size = 8
            chart_height = 1650
            legend_x = 1.12
            right_margin = 560

        fig.update_layout(
            title = "",
            template = "plotly_dark",
            paper_bgcolor = "black",
            font = dict(color = "white"),
            width = 1300,
            height = chart_height,
            margin = dict(l = 40, r = right_margin, t = 30, b = 30),
            legend = dict(
                font = dict(size = legend_font_size, color = "white"),
                orientation = "v",
                x = legend_x,
                y = 0.99,
                xanchor = "left",
                yanchor = "top",
                bordercolor = "white",
                borderwidth = 1,
                bgcolor = "rgba(0,0,0,0)",
                traceorder = "normal"
            )
        )

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
