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
            cv_value = float(variation(data_array, ddof=1))
            mean_val = float(np.mean(data_array))
            std_val = float(np.std(data_array, ddof=1))
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        precision_note = False
        if np.isnan(cv_value):
            precision_note = (
                "NaN result: the coefficient of variation is undefined. Inputs likely "
                "contained NaN, or both std and mean evaluated to zero. Clean the data "
                "before re-running."
            )
        elif np.isinf(cv_value):
            precision_note = (
                "Overflow detected: the coefficient of variation is infinite. "
                "The mean is effectively zero, making CV undefined."
            )
        elif cv_value != 0 and abs(cv_value) < 2.2250738585072014e-308:
            precision_note = (
                f"Subnormal result (|CV| ≈ {abs(cv_value):.3g}, below ~2.2e-308). "
                "Float64 loses bits of precision in the subnormal range; treat "
                "low-order digits as noise."
            )
        elif std_val > 0 and abs(mean_val) < std_val * 1e-6:
            precision_note = (
                f"Near-zero mean detected (mean ≈ {mean_val:.3g}). The coefficient of "
                "variation (std/mean) is highly sensitive to small changes in the mean "
                "at this scale; the result may not be meaningful — Enhanced Precision "
                "will expose how unstable the divisor is."
            )

        result = self._generate_return_structure(cv_value)
        result["loss_of_precision"] = precision_note
        return result


    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # No graph generated for the coefficient of variation calculation
        pass


# Backwards compatibility: preserve the old misspelled class name
CoefficentVariation = CoefficientVariation