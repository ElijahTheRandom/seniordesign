import math
import statistics

class Mode:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "mode"
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
            flat = self.data.flatten() if hasattr(self.data, 'flatten') else self.data
            raw_mode = statistics.mode(flat)
            # Keep numeric values as float; leave strings as-is
            try:
                mode_value = float(raw_mode)
            except (ValueError, TypeError):
                mode_value = raw_mode
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        # Mode is selection-based (no float arithmetic), so the only real
        # precision concern is whether the raw inputs already carry Inf/NaN
        # — which means the dataset itself overflowed before reaching us.
        precision_note = False
        try:
            for v in flat:
                if isinstance(v, (int, float)) and not math.isfinite(v):
                    precision_note = (
                        "Non-finite values detected in input (Inf or NaN). The mode "
                        "itself is well-defined, but the underlying data has already "
                        "overflowed or carries undefined entries — downstream "
                        "statistics on this column will be unreliable."
                    )
                    break
        except TypeError:
            pass

        result = self._generate_return_structure(mode_value)
        result["loss_of_precision"] = precision_note
        return result


    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # No graph generated for the mode calculation
        pass
