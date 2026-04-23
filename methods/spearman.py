import numpy as np
from scipy.stats import spearmanr

class SpearmanCoefficient:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "spearman"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Spearman requires exactly 2 columns of equal length
        if self.data is None or len(self.data) < 2:
            return "Spearman correlation requires exactly 2 columns of equal length"
        if len(self.data[0]) != len(self.data[1]):
            return "Spearman correlation requires exactly 2 columns of equal length"
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
        
        try:
            data1 = np.array(self.data[0], dtype=float)
            data2 = np.array(self.data[1], dtype=float)
            spearman_corr, p_value = spearmanr(data1, data2)
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        spearman_corr = float(spearman_corr)

        precision_note = False
        if np.isnan(spearman_corr):
            # spearmanr returns NaN when a column is constant (all tied ranks)
            # or when input contains NaN values. Distinguish the two so the
            # user knows what to fix.
            has_nan = np.isnan(data1).any() or np.isnan(data2).any()
            if has_nan:
                precision_note = (
                    "NaN result: the input contains NaN values that propagated "
                    "through the Spearman computation. Clean the data before re-running."
                )
            elif np.std(data1) == 0 or np.std(data2) == 0:
                precision_note = (
                    "Spearman is undefined when one variable has no variance "
                    "(all values tied). Select a column with at least two distinct values."
                )
            else:
                precision_note = (
                    "Spearman returned NaN. The input may be degenerate (constant ranks "
                    "or undefined entries); inspect the selected columns."
                )
        elif np.abs(np.concatenate([data1, data2])).max() > 1e15:
            precision_note = (
                "Large-magnitude values detected (>1e15). Spearman ranks are robust "
                "to scale, but the underlying values already exceed float64's 15-16 "
                "significant-digit precision — equality checks for tied ranks may "
                "behave unexpectedly."
            )

        result = self._generate_return_structure(spearman_corr)
        result["loss_of_precision"] = precision_note
        return result

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # There is no graphic for the Spearman correlation
        pass
