import numpy as np
from scipy.stats import pearsonr

class PearsonCoefficient:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "pearson"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Pearson requires exactly 2 columns of equal length
        if self.data is None or len(self.data) < 2:
            return "Pearson correlation requires exactly 2 columns of equal length"
        if len(self.data[0]) != len(self.data[1]):
            return "Pearson correlation requires exactly 2 columns of equal length"
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
            pearson_corr, p_value = pearsonr(data1, data2)
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        precision_note = False
        all_vals = np.concatenate([data1, data2])
        if np.abs(all_vals).max() > 1e12:
            precision_note = (
                "Large-magnitude values detected (>1e12). Pearson correlation involves "
                "sums of squared values; intermediate products may lose precision near float64 limits."
            )
        elif float(np.std(data1)) < abs(float(np.mean(data1))) * 1e-8 and abs(float(np.mean(data1))) > 1:
            precision_note = (
                "Near-constant x values detected. Pearson correlation is ill-conditioned "
                "when one variable has very low variance relative to its mean."
            )

        result = self._generate_return_structure(float(pearson_corr))
        result["loss_of_precision"] = precision_note
        return result

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # There is no graphic for the Pearson correlation
        pass
