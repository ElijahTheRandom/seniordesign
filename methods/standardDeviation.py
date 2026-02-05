import numpy as np
from class_templates import message_structure

class StandardDeviation:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "std"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if self.data is None or len(self.data) == 0:
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
            std_value = float(np.std(data_array))
        except Exception as e:
            return self._generate_return_structure_error(str(e))
        
        return self._generate_return_structure(std_value)


    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # No graph generated for the standard deviation calculation
        pass