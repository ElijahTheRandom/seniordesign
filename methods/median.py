import numpy as np

class Median:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "median"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection
        if self.data is None or len(self.data) == 0:
            return "No numerical data provided"
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
            data_array = np.asarray(self.data, dtype = float)
            median_value = float(np.median(data_array))
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        precision_note = False
        if np.isinf(median_value):
            precision_note = (
                "Overflow detected: the median is infinite. The selected data "
                "contains values outside the float64 range (~1.8e308)."
            )
        elif np.isnan(median_value):
            precision_note = (
                "NaN result: the input contains NaN values that propagated through "
                "the median computation. Clean the data before re-running."
            )
        elif np.abs(data_array).max() > 1e15:
            precision_note = (
                "Large-magnitude values detected (>1e15). Median is sort-based and "
                "robust, but the underlying values may already exceed the 15-16 "
                "significant-digit precision of float64."
            )

        result = self._generate_return_structure(median_value)
        result["loss_of_precision"] = precision_note
        return result


    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # No graph generated for the median calculation
        pass