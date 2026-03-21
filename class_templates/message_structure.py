import numpy as np

class Message:
    def __init__(self, dataset_id=None, dataset_version=None, metadata=None,
                 selection=None, methods=None, graphics=None, data=None, results=None,
                 run_folder=None):
        self.dataset_id = dataset_id
        self.dataset_version = dataset_version
        self.metadata = metadata or []

        self.selection = selection or {
            "rows": [],
            "cols": [],
        }

        self.methods = methods or []  # List of method dicts with 'id' and 'params'
        self.graphics = graphics or []  # List of graphic request dicts

        self._data_raw = data or []  # Raw data (list); converted to numpy lazily
        self._data_np = None         # Cached numpy conversion

        self.results = results or []  # List of result dicts for each method

        self.run_folder = run_folder  # Path to the results_cache folder for this run

    @property
    def data(self):
        """Lazily convert raw data to a numpy array on first access."""
        if self._data_np is None and len(self._data_raw) > 0:
            self._data_np = np.array(self._data_raw)
        return self._data_np if self._data_np is not None else self._data_raw

    @data.setter
    def data(self, value):
        """Allow direct assignment (e.g. from deserialization)."""
        if isinstance(value, np.ndarray):
            self._data_np = value
            self._data_raw = value
        else:
            self._data_raw = value
            self._data_np = None


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
            "output":{
                    "type": self.type,
                    "ok": False,
                    "path": self.params.get("path"),
                    "error": error_message,
                    "params_used": self.params,
            }
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