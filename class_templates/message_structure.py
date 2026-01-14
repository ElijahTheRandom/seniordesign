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