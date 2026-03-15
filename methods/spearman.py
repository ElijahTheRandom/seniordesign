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
        # Check whether this statistic is valid for the given data selection
        if self.data == None or len(self.data) < 2 or len(self.data[0]) != len(self.data[1]) or np.sum(self.data[0]) != np.sum(self.data[1]):
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
            return self._generate_return_structure_error(_applicable)
        
        # Placeholder for the main computation logic

        data1 = np.array(self.data[0])
        data2 = np.array(self.data[1])

        spearman_corr, p_value = spearmanr(data1, data2)
        results = self._generate_return_structure(spearman_corr)
        return results

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        # There is no graphic for the Spearman correlation
        pass
