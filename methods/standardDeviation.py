import numpy as np

class StandardDeviation:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "standard_deviation"
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
            flat = data_array.flatten()
            std_value = float(np.std(data_array, ddof=1))
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        precision_note = False
        if np.isnan(std_value):
            precision_note = (
                "NaN result: the standard deviation is undefined. Inputs likely contained "
                "NaN or the squared-deviation sum produced an undefined operation. Clean "
                "the data before re-running."
            )
        elif np.isinf(std_value):
            precision_note = (
                "Overflow detected: the standard deviation is infinite. Squared "
                "deviations exceeded the float64 range (~1.8e308)."
            )
        elif np.abs(flat).max() > 1e15:
            precision_note = (
                "Large-magnitude values detected (>1e15). Standard deviation is computed "
                "from squared deviations, which can lose precision at this scale — "
                "Enhanced Precision digits past the ~15th are unreliable."
            )
        elif std_value != 0 and std_value < 2.2250738585072014e-308:
            precision_note = (
                f"Subnormal result (std ≈ {std_value:.3g}, below ~2.2e-308). Float64 "
                "loses bits of precision in the subnormal range; treat low-order digits as noise."
            )
        else:
            mean_abs = abs(float(np.mean(flat)))
            spread = float(flat.max() - flat.min())
            if mean_abs > 1e8 and spread > 0 and spread < mean_abs * 1e-6:
                precision_note = (
                    "Catastrophic cancellation risk: values are nearly identical relative to "
                    "their magnitude. The computed standard deviation may have fewer significant "
                    "digits than expected — Enhanced Precision will expose the noisy bits."
                )

        result = self._generate_return_structure(std_value)
        result["loss_of_precision"] = precision_note
        return result


    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # No graph generated for the standard deviation calculation
        pass