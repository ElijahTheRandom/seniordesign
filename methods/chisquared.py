import numpy as np
from scipy.stats import chisquare, chi2_contingency

class ChiSquared:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "chisquared"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Check whether this statistic is valid for the given data selection.
        # Valid layouts:
        #   - 1-D: >= 2 categories of observed counts (goodness-of-fit vs. uniform)
        #   - 2-D: contingency table with >= 2 rows AND >= 2 columns (independence test)
        if self.data is None:
            return "Chi-Square requires at least 2 categories of observed data"
        try:
            arr = np.asarray(self.data, dtype=float)
        except (TypeError, ValueError):
            return "Chi-Square requires numeric categorical/frequency counts"
        if arr.size == 0:
            return "Chi-Square requires at least 2 categories of observed data"
        if arr.ndim == 1:
            if arr.shape[0] < 2:
                return "Chi-Square requires at least 2 categories of observed data"
        elif arr.ndim == 2:
            r, c = arr.shape
            if r < 2 or c < 2:
                return (
                    "Chi-Square contingency table requires at least 2 rows and 2 columns"
                )
        else:
            return "Chi-Square requires a 1-D frequency list or a 2-D contingency table"
        if np.any(~np.isfinite(arr)):
            return "Chi-Square requires finite numeric counts (no NaN/inf)"
        if np.any(arr < 0):
            return "Chi-Square frequencies must be non-negative"
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
            arr = np.asarray(self.data, dtype=float)

            if arr.ndim == 2:
                # Contingency table: test of independence.
                # Expected frequencies are derived from row/column marginals;
                # df = (rows - 1) * (cols - 1).
                chiSquared, pValue, dof, expected = chi2_contingency(arr)
            else:
                # 1-D goodness-of-fit against uniform expected frequencies.
                # df = k - 1.
                observed = arr.flatten()
                expected = np.full_like(observed, observed.mean())
                chiSquared, pValue = chisquare(f_obs=observed, f_exp=expected)
                dof = int(observed.shape[0] - 1)
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        precision_note = False
        chi_f = float(chiSquared)
        min_expected = float(np.asarray(expected).min())
        if np.isnan(chi_f) or np.isinf(chi_f):
            precision_note = (
                "NaN/Inf chi-square statistic. The test failed numerically — most "
                "often caused by an expected frequency at or near zero, NaN inputs, "
                "or a degenerate contingency table. Clean the counts before re-running."
            )
        elif min_expected < 1e-10:
            precision_note = (
                "Near-zero expected frequency detected. Division by a value close to zero "
                "in the chi-square formula may cause numerical overflow."
            )
        elif min_expected < 5:
            precision_note = (
                f"Small expected frequency detected (minimum expected = {min_expected:.4g}). "
                "The chi-square approximation requires expected cell counts \u2265 5; "
                "results may be unreliable."
            )

        results = self._generate_return_structure(float(chiSquared))
        results["df"] = int(dof)
        results["p_value"] = float(pValue)
        results["loss_of_precision"] = precision_note
        return results

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # There is no graphic for the chi square distribution
        pass
