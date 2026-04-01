import numpy as np


class Percentile:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "percentile"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if self.data is None:
            return "No numerical data provided"
        return None

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
        reason = self._applicable()
        if reason is not None:
            return self._generate_return_structure_error(reason)
        
        for p in self.params:
            if p < 0 or p > 100:
                return self._generate_return_structure_error(f"Percentile {p} is out of range [0, 100]")
            
        try:
            param_array = np.asarray(self.params)
            if param_array.size == 0:
                return self._generate_return_structure_error("No percentile values specified")

            flat_data = np.asarray(self.data, dtype=float).flatten()

<<<<<<< HEAD
            percentile_results = []
            for p in param_array.flatten():
                computed = float(np.percentile(flat_data, p))

                # Format ordinal suffix
                p_int = int(p) if float(p).is_integer() else p
                ordinal = f"{p_int}th"
                if isinstance(p_int, int):
                    if 10 <= p_int % 100 <= 20:
                        ordinal = f"{p_int}th"
                    elif p_int % 10 == 1:
                        ordinal = f"{p_int}st"
                    elif p_int % 10 == 2:
                        ordinal = f"{p_int}nd"
                    elif p_int % 10 == 3:
                        ordinal = f"{p_int}rd"
                    else:
                        ordinal = f"{p_int}th"

                percentile_results.append(f"{ordinal}: {computed:.2f}")
=======
            percentiles = []
            for i in range(len(param_array)):
                appendPercentile = float(np.percentile(flat_data, param_array[i]))
                percentiles.append(appendPercentile)
>>>>>>> 2b46729 (big method fixer)
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        results = self._generate_return_structure(percentile_results)
        return results

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # No graph is created for percentiles
        pass
