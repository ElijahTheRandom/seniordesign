import numpy as np
from scipy import stats

"""
    # Backend results
    "results": [ #1.10, but also should be compiled on front end
        {
            "id": "std_dev",
            "ok": True, # 4.10, 5.6
            "value": 2.58, # 1.6
            "error": None, # 4.10, 5.6
            "loss_of_precision": False, #4.10
            "params_used": 100, # parameters used for the computation
        },
    ],
"""

class Mode:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "mode"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if self.data is None or len(self.data) == 0:
            return False
        return True
        
    def _generate_return_structure(self):
        # Check whether this statistic is valid for the given data selection
        pass

    def _generate_return_structure_error(self, error_message):
        pass

    def compute(self):
        # Perform the statistical computation and return a standardized result dictionary
        _applicable = self._applicable()
        if not _applicable:
            return self._generate_return_structure_error(_applicable)
        
        # Placeholder for the main computation logic

        results = self._generate_return_structure()
        return results

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        pass
