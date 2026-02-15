import numpy as np
from scipy.stats import variation
from class_templates import message_structure

class CoefficientVariation:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "cv"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if self.data is None or len(self.data) == 0:
            return False
        elif np.mean(self.data) == 0: # Coefficient of variation is not defined when the mean is zero
            return False
        return True


    def _generate_return_structure(self, value):
        # Check whether this statistic is valid for the given data selection
        results = {
            "id": self.stat_id,
            "ok": True,
            "value": value,
            "error": None,
            "loss_precision": False,
            "params_used": self.params
        }
        return results

    def _generate_return_structure_error(self, error_message):
        results = {
            "id": self.stat_id,
            "ok": False,
            "value": None,
            "error": error_message,
            "loss_precision": False,
            "params_used": self.params
        }
        return results

    def compute(self):
        # Perform the statistical computation and return a standardized result dictionary
        _applicable = self._applicable()
        if not _applicable:
            return self._generate_return_structure_error("No numerical data provided")
        
        # Main Computation Logic
        try:
            data_array = np.asarray(self.data, dtype = float)
            cv_value = float(variation(data_array))
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        return self._generate_return_structure(cv_value)


    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # No graph generated for the coefficient of variation calculation
        pass