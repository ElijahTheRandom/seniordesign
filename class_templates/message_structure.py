import numpy as np

class Message:
    def __init__(self, dataset_id=None, dataset_version=None, metadata=None,
                 selection=None, methods=None, graphics=None, data=None, results=None):
        self.dataset_id = dataset_id
        self.dataset_version = dataset_version
        self.metadata = metadata or []

        self.selection = selection or {
            "rows": [],
            "cols": [],
        }

        self.methods = methods or []  # List of method dicts with 'id' and 'params'
        self.graphics = graphics or []  # List of graphic request dicts

        self.data = data or []  # 2D list representing the raw data

        self.results = results or []  # List of result dicts for each method

        #i want to go through each of these and convert to numpy arrays where applicable
        self._to_numpy()

    def _to_numpy(self):
        if self.data:
            self.data = np.array(self.data)
        if self.selection and "rows" in self.selection:
            self.selection["rows"] = [np.array(r) for r in self.selection["rows"]]
        if self.selection and "cols" in self.selection:
            self.selection["cols"] = np.array(self.selection["cols"])


    def to_dict(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "metadata": self.metadata,
            "selection": self.selection,
            "methods": self.methods,
            "graphics": self.graphics,
            "data": self.data,
            "results": self.results,
        }
    
"""
message = {
    # Dataset context
    "dataset_id": "ds_001", #4.5
    "dataset_version": 3, #4.5
    "metadata": [], #4.5


    # Data selection
    "selection": { #2.10, 4.5, 3.9
        "rows": [[0, 1, 2, 3],[0,1,2,3]], # which rows for each selected column
        "cols": [1,2], # selecting columns 1 and 2
    },

    # Requested analyses
    "methods": [ #1.8
        {"id": "std_dev", "params": {}}, #format: id STRING, params DICT
        {"id": "correlation", "params": {"with_col": 3}}  # examples
    ],

    # Requested Graphs
    "graphics": [ #3.6
        {
            "type": "scatter", 
            "x_col": 2, 
            "y_col": 3, 
            "path": "exports/scatter_plot.jpg"
        }
    ],

    # Raw data
    "data": [ # outside array is rows, inside array is cols
        # this is the actual data that the "selection" field is referring to
        [0, 1, 2, 3],
        [4, 5, 6, 7],
    ],


    # Backend results
    "results": [ #1.10, but also should be compiled on front end
        {
            "id": "std_dev",
            "ok": True, # 4.10, 5.6
            "value": 2.58, # 1.6
            "error": None, # 4.10, 5.6
            "loss_of_precision": False, #4.10
            "params_used": 100, # parameters used for the computation
        },
    ],


}
"""