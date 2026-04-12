import os
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import plotly.graph_objects as go
import plotly.io as pio
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

    def _format_value(self, val):
        """Format value as millions or billions or trillions if appropriate."""
        val_num = np.float64(val)
        if val_num >= 1e12:
            return f"{val_num / 1e12:.3f}T"
        elif val_num >= 1e9:
            return f"{val_num / 1e9:.3f}B"
        elif val_num >= 1e6:
            return f"{val_num / 1e6:.3f}M"
        elif val_num >= 1e3:
            return f"{val_num / 1e3:.3f}K"
        else:
            if abs(val_num - int(val_num)) < 1e-6:
                return str(int(val_num))
            else:
                return f"{val_num:.2f}"

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
                np.float64(val)
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
                    values = [np.float64(v) for v in values]
                except (ValueError, TypeError):
                    raise ValueError("Bar chart requires numeric data for values.")
            else:
                values = list(values)
                try:
                    values = [np.float64(v) for v in values]
                except (ValueError, TypeError):
                    raise ValueError("Bar chart requires numeric data for values.")

            labels = self.params.get("labels")
            if labels is not None:
                if len(labels) != len(values):
                    raise ValueError("Bar chart requires labels to align with values length.")

                # Sum values by label so duplicates aggregate
                label_totals = {}
                for lbl, val in zip(labels, values):
                    label_totals[lbl] = label_totals.get(lbl, 0.0) + val

                labels = list(label_totals.keys())
                values = list(label_totals.values())
            else:
                if isinstance(self.metadata, (list, tuple)) and len(self.metadata) == len(values):
                    labels = list(self.metadata)
                else:
                    labels = [str(i) for i in range(len(values))]

        figure = go.Figure()

        # Format values for display
        formatted_values = [self._format_value(v) for v in values[::-1]]
        
        # Dynamic font size for x-axis labels (category labels) and value labels
        num_labels = len(labels)
        if num_labels <= 10:
            dynamic_font_size = 14
        elif num_labels <= 20:
            dynamic_font_size = 14
        elif num_labels <= 35:
            dynamic_font_size = 10
        elif num_labels <= 50:
            dynamic_font_size = 8
        else:
            dynamic_font_size = 6

        showValueLabels = num_labels <= 30
        figure.add_trace(go.Bar(
            x = values[::-1],
            y = labels[::-1],
            orientation = 'h',
            text = formatted_values if showValueLabels else None,
            textposition = "auto" if showValueLabels else "none",
            textfont = dict(size = 14, color = "white", family = "Arial Black, Arial, sans-serif"),
            marker = dict(
                color = "#e4781d",
                line = dict (width = 1, color = "#e4781d")
            )
        ))


        figure.update_layout(
            template = "plotly_dark",
            paper_bgcolor = "black",
            plot_bgcolor = "black",
            font = dict(color = "white"),
            xaxis = dict(showgrid = True, gridcolor = "white"),
            yaxis = dict(
                showgrid = False,
                automargin = True,
                ticklabelstandoff = 10,
                tickfont = dict(size = dynamic_font_size),
                tickmode = "array",
                tickvals = labels[::-1],
                ticktext = labels[::-1]
            ),
            width = 700,
            height = 500.,
            margin = dict(l = 100, r = 100, t = 10, b = 10)
        )

        buffer = BytesIO()

        figure.write_image(buffer, format = "png", scale = 2)

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
