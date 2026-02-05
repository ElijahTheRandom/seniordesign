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
        # Check whether this statistic is valid for the given data selection
        if self.data == None or len(self.data) == 0:
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
            "loss_of_precision": False,
            "params_used": self.params
        }

    def compute(self):
        # Perform the statistical computation and return a standardized result dictionary
        _applicable = self._applicable()
        if not _applicable:
            return self._generate_return_structure_error(_applicable)
        
        # Placeholder for the main computation logic

        n = self.data[0]
        p = self.data[1]
        kMin = self.data[2]
        kMax = self.data[3]

        if kMax is None:
            kMax = n
        
        k = np.arange(kMin, kMax + 1)
        table = {
            "k": k,
            "P(X = k)": binom.pmf(k, n, p),
            "P(X <= k)": binom.cdf(k, n, p),
            "P(X >= k)": binom.sf(k - 1, n, p)
        }

        tableStructure = self.create_graphic(table)
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
