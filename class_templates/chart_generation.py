import numpy as np

"""
    "graphics": [ #3.6
        {
            "type": "scatter", 
            "x_col": 2, 
            "y_col": 3, 
            "path": "temp/scatter_plot.jpg"
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
        pass

    def _generate_return_structure(self):
        # Check whether this statistic is valid for the given data selection
        pass

    def _generate_return_structure_error(self, error_message):
        pass

    def create_graphic(self):
        # Perform the statistical computation and return a standardized result dictionary
        _applicable = self._applicable()
        if not _applicable:
            return self._generate_return_structure_error(_applicable)
        
        # Placeholder for the main computation logic

        results = self._generate_return_structure()
        return results
