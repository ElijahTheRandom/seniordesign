import numpy as np


class MethodName:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "method_name"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        pass

    def _generate_return_structure(self):
        # Check whether this statistic is valid for the given data selection
        pass

    def compute(self):
        # Perform the statistical computation and return a standardized result dictionary
        _applicable = self._applicable()
        if not _applicable:
            return {
                "stat_id": self.stat_id,
                "error": "Statistic not applicable to the selected data.",
            }
        
        results = self._generate_return_structure()
        return results

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        pass
