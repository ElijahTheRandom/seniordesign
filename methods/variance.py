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

        precision_note = False
        if np.isnan(variance):
            precision_note = (
                "NaN result: the variance is undefined. Inputs likely contained NaN "
                "or the squared-deviation sum produced an undefined operation. Clean "
                "the data before re-running."
            )
        elif np.isinf(variance):
            precision_note = (
                "Overflow detected: the variance is infinite. The sum of squared "
                "deviations exceeded the float64 range (~1.8e308)."
            )
        elif np.abs(array).max() > 1e15:
            precision_note = (
                "Large-magnitude values detected (>1e15). Sample variance uses the "
                "sum of squared deviations, which can overflow or lose precision at "
                "this scale — Enhanced Precision digits past the ~15th are unreliable."
            )
        elif variance != 0 and variance < 2.2250738585072014e-308:
            precision_note = (
                f"Subnormal result (variance ≈ {variance:.3g}, below ~2.2e-308). "
                "Float64 loses bits of precision in the subnormal range; treat "
                "low-order digits as noise."
            )
        else:
            mean_abs = abs(float(np.mean(array)))
            spread = float(array.max() - array.min())
            if mean_abs > 1e8 and spread > 0 and spread < mean_abs * 1e-6:
                precision_note = (
                    "Catastrophic cancellation risk: values are nearly identical relative to "
                    "their magnitude. The computed variance may have fewer significant digits "
                    "than expected — Enhanced Precision will expose the noisy bits."
                )

        results = self._generate_return_structure(variance)
        results["loss_of_precision"] = precision_note
        return results

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # Graphic is not required for the variance
        pass
