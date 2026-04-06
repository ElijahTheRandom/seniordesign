import numpy as np


class MethodName:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "method_name"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Return None if valid, or a reason string explaining why it's not
        if self.data is None or len(self.data) == 0:
            return "No numerical data provided"
        return None

    def _generate_return_structure(self, value):
        return {
            "id": self.stat_id,
            "ok": True,
            "value": value,
            "error": None,
            "loss_of_precision": False,
            "params_used": self.params,
        }

    def _generate_return_structure_error(self, error_message):
        return {
            "id": self.stat_id,
            "ok": False,
            "value": None,
            "error": error_message,
            "loss_of_precision": False,
            "params_used": self.params,
        }

    def compute(self):
        # Perform the statistical computation and return a standardized result dictionary
        reason = self._applicable()
        if reason is not None:
            return self._generate_return_structure_error(reason)
        
        # Placeholder for the main computation logic

        results = self._generate_return_structure(None)
        return results

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        pass
