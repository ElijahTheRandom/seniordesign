import numpy as np
from scipy.stats import variation

class CoefficientVariation:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "coefficient_variation"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if self.data is None or len(self.data) == 0:
            return "Coefficient of variation is undefined for empty data or data with a mean of zero"
        try:
            flat = np.asarray(self.data, dtype=float).flatten()
            if len(flat) == 0 or np.mean(flat) == 0:
                return "Coefficient of variation is undefined for empty data or data with a mean of zero"
        except (ValueError, TypeError):
            return "Coefficient of variation is undefined for empty data or data with a mean of zero"
        return None


    def _generate_return_structure(self, value):
        # Check whether this statistic is valid for the given data selection
        results = {
            "id": self.stat_id,
            "ok": True,
            "value": value,
            "error": None,
            "loss_of_precision": False,
            "params_used": self.params
        }
        return results

    def _generate_return_structure_error(self, error_message):
        results = {
            "id": self.stat_id,
            "ok": False,
            "value": None,
            "error": error_message,
            "loss_of_precision": False,
            "params_used": self.params
        }
        return results

    def compute(self):
        # Perform the statistical computation and return a standardized result dictionary
        reason = self._applicable()
        if reason is not None:
            return self._generate_return_structure_error(reason)
        
        # Main Computation Logic
        try:
            data_array = np.asarray(self.data, dtype = float).flatten()
            cv_value = float(variation(data_array))
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        return self._generate_return_structure(cv_value)


    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # No graph generated for the coefficient of variation calculation
        pass


# Backwards compatibility: preserve the old misspelled class name
CoefficentVariation = CoefficientVariation