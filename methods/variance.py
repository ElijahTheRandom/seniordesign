import numpy as np
    
class Variance:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "variance"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if self.data is None:
            return "Variance requires at least 2 data points"
        import numpy as _np
        flat = _np.asarray(self.data).flatten()
        if len(flat) < 2:
            return "Variance requires at least 2 data points"
        return None

    def _generate_return_structure(self, value):
        # Check whether this statistic is valid for the given data selection
        return {
            "id": self.stat_id,
            "ok": True,
            "value": value,
            "error": None,
            "loss_of_precision": False,
            "params_used": self.params
        }

    def _generate_return_structure_error(self, error_message):
        return {
            "id": self.stat_id,
            "ok": False,
            "value": None,
            "error": error_message,
            "loss_of_precision": False,
            "params_used": self.params
        }

    def compute(self):
        # Perform the statistical computation and return a standardized result dictionary
        reason = self._applicable()
        if reason is not None:
            return self._generate_return_structure_error(reason)
        
        try:
            # Flatten 2D data (one column arrives as shape (1, N))
            array = np.asarray(self.data, dtype = float).flatten()
            variance = float(np.var(array, ddof = 1))
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        results = self._generate_return_structure(variance)
        return results

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # Graphic is not required for the variance
        pass
