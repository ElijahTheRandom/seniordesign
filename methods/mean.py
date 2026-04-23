import numpy as np

class Mean:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "mean"
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

        # Placeholder for the main computation logic
        try:
            data_array = np.asarray(self.data, dtype = float)
            mean_value = float(np.mean(data_array))
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        precision_note = False
        if np.isnan(mean_value):
            precision_note = (
                "NaN result: the mean is undefined. Inputs likely contained NaN, "
                "or an undefined operation (0/0, inf-inf) occurred during summation. "
                "Clean the data before re-running."
            )
        elif np.isinf(mean_value):
            precision_note = (
                "Overflow detected: the mean is infinite. Values exceed the float64 "
                "range (~1.8e308) or the running sum overflowed mid-computation."
            )
        elif np.abs(data_array).max() > 1e15:
            precision_note = (
                "Large-magnitude values detected (>1e15). Floating-point summation "
                "may lose precision beyond 15-16 significant digits — Enhanced "
                "Precision will display digits past that point but they reflect "
                "rounding error rather than computed signal."
            )
        elif mean_value != 0 and abs(mean_value) < 2.2250738585072014e-308:
            precision_note = (
                f"Subnormal result (|mean| ≈ {abs(mean_value):.3g}, below ~2.2e-308). "
                "Float64 loses bits of precision in the subnormal range; treat "
                "low-order digits as noise."
            )
        else:
            finite = data_array[np.isfinite(data_array)]
            nonzero = np.abs(finite[finite != 0])
            if nonzero.size > 1:
                ratio = float(nonzero.max() / nonzero.min())
                if ratio > 1e15:
                    precision_note = (
                        f"Mixed-magnitude inputs (largest/smallest ≈ {ratio:.2g}). "
                        "Float64 summation order materially affects the result when "
                        "terms span this many orders of magnitude."
                    )

        result = self._generate_return_structure(mean_value)
        result["loss_of_precision"] = precision_note
        return result


    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # No graph generated for the mean calculation
        pass
