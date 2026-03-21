import numpy as np
from scipy.stats import chisquare

class ChiSquared:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "chisquared"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if self.data is None:
            return False
        arr = np.asarray(self.data)
        flat = arr.flatten()
        # Need at least 2 observed values for chi-squared
        if len(flat) < 2:
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
            return self._generate_return_structure_error("Chi-Square requires at least 2 categories of observed data")
        
        try:
            arr = np.asarray(self.data, dtype=float)

            if arr.ndim == 2 and arr.shape[0] >= 2:
                observed = arr[0]
                expected = arr[1]
            else:
                # Single group: test against uniform expected frequencies
                observed = arr.flatten()
                expected = np.full_like(observed, observed.mean())

            chiSquared, pValue = chisquare(f_obs = observed, f_exp = expected)
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        results = self._generate_return_structure(float(chiSquared))
        return results

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # There is no graphic for the chi square distribution
        pass
