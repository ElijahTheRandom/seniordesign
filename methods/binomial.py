import numpy as np
from scipy.stats import binom
import pandas as pd

class Binomial:
    def __init__(self, data, metadata, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = "binomial"
        self.data = data
        self.metadata = metadata
        self.params = params or {}

    def _applicable(self):
        # Binomial requires exactly 4 inputs: n, p, kMin, kMax
        if self.data is None:
            return False
        arr = np.asarray(self.data).flatten()
        if len(arr) < 3:
            return False
        return True

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
        _applicable = self._applicable()
        if not _applicable:
            return self._generate_return_structure_error(
                "Binomial requires at least 3 values: n (trials), p (probability), kMin. "
                "Optionally provide kMax as a 4th value."
            )
        
        try:
            arr = np.asarray(self.data).flatten()

            n = int(arr[0])
            p = float(arr[1])
            kMin = int(arr[2])
            kMax = int(arr[3]) if len(arr) > 3 else n

            if not (0 <= p <= 1):
                return self._generate_return_structure_error(
                    f"Probability p must be between 0 and 1, got {p}"
                )
            
            k = np.arange(kMin, kMax + 1)
            table = {
                "k": k,
                "P(X = k)": binom.pmf(k, n, p),
                "P(X <= k)": binom.cdf(k, n, p),
                "P(X >= k)": binom.sf(k - 1, n, p)
            }

            tableStructure = self.create_graphic(table)
        except Exception as e:
            return self._generate_return_structure_error(str(e))

        results = self._generate_return_structure(tableStructure)
        return results

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        df = pd.DataFrame({
            "k": results["k"],
            "P(X = k)": results["P(X = k)"],
            "P(X <= k)": results["P(X <= k)"],
            "P(X >= k)": results["P(X >= k)"]
        })
        return df
