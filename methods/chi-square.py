import numpy as np
from scipy.stats import chisquare

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
class MethodName:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "method_name"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if self.data == None or len(self.data) < 2 or len(self.data[0]) != len(self.data[1]) or np.sum(self.data[0]) != np.sum(self.data[1]):
            return False
        return True 

    def _generate_return_structure(self, value):
        # Check whether this statistic is valid for the given data selection
        return{
            "id": self.stat_id,
            "ok": True,
            "value": value,
            "error": None,
            "loss_of_precision": False,
            "params_used": self.params
        }

    def _generate_return_structure_error(self, error_message):
        return{
            "id": self.stat_id,
            "ok": False,
            "value": None,
            "error": error_message,
            "loss_of_precision": False,
            "params_used": self.params
        }

    def compute(self):
        # Perform the statistical computation and return a standardized result dictionary
        _applicable = self._applicable()
        if not _applicable:
            return self._generate_return_structure_error(_applicable)
        
        # Placeholder for the main computation logic

        observed = np.array(self.data[0])
        expected = np.array(self.data[0])

        chiSquared, pValue = chisquare(f_obs = observed, f_exp = expected)
        results = self._generate_return_structure(chiSquared)
        return results

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # There is no graphic for the chi square distribution
        pass
