
from datetime import datetime
import os

import json
from methods.mean import Mean
from methods.median import Median
from methods.binomial import Binomial
from methods.standardDeviation import StandardDeviation
from methods.least_squares_regression import LeastSquaresRegression
from methods.chisquared import ChiSquared
from class_templates.message_structure import Message

from concurrent.futures import ThreadPoolExecutor

statistical_methods = {
    "mean": Mean,
    "median": Median,
    "binomial": Binomial,
    "std": StandardDeviation,
    "least_squares_regression": LeastSquaresRegression,
    "chi_squared": ChiSquared
}

class BackendHandler:
    """
    Handle backend requests for statistical computations.

    The BackendHandler class processes incoming requests encapsulated in Message objects,
    extracts the requested statistical methods along with the associated data and metadata,
    and computes the results using the appropriate statistical classes. Each computation
    is performed in its own thread to optimize performance, with a limit on the maximum
    number of concurrent threads. Finally, the results are packaged back into the Message
    structure and returned to the caller.
    """

    def __init__(self):
        pass

    def _package_results(self, message, results):
        """
        Put results back into the message structure
        
        :param self: self
        :param Message message: Message object
        :param results: Results to be packaged into the message

        :return: Message with results included
        """
        message.results = results
        return message
    
    def _get_methods(self, request):
        """
        Get method names, data, and metadata from the request message
        
        :param self: self
        :param Message message: Message object or dict

        :return: methods, data, metadata
        """

        methods = request.methods
        data = request.data
        metadata = request.metadata

        
        return methods, data, metadata
    
    def _get_method_requests(self, methods):
        method_requests = []
        for method_entry in methods:
            if isinstance(method_entry, dict):
                method_id = method_entry["id"] if "id" in method_entry else None
                method_params = method_entry["params"] if "params" in method_entry else {}
            else:
                method_id = method_entry
                method_params = {}

            if method_id:
                method_requests.append((method_id, method_params))
        
        return method_requests
    
    def _threads_compute(self, method_requests, data, metadata, max_threads):
        """
        Compute each method in its own thread and collect results

        :param self: self
        :param method_requests: List of (method_id, method_params) tuples
        :param data: Data for computations
        :param metadata: Metadata for computations
        :param max_threads: Maximum number of concurrent threads
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = []
            for method_id, method_params in method_requests:
                if isinstance(data, dict) and method_id in data:
                    method_data = data[method_id]
                else:
                    method_data = data

                if isinstance(metadata, dict) and method_id in metadata:
                    method_metadata = metadata[method_id]
                else:
                    method_metadata = metadata

                futures.append(
                    (method_id, method_params, executor.submit(self.worker, method_id, method_data, method_metadata, method_params))
                )

            for method_id, method_params, future in futures:
                try:
                    result = future.result()
                except Exception as exc:
                    result = self._generate_error_result(method_id, str(exc), method_params)
                results.append(result)

            return results

    def _generate_error_result(self, method_name, error_message, params):
        return {
            "id": method_name,
            "ok": False,
            "value": None,
            "error": error_message,
            "loss_of_precision": False,
            "params_used": params or {}
        }


    def _save_run_results(self, result):
        # create a local cache for the results of each run if a cache doesnt exist already
        # Save the results of each run to a folder within this cache with the dataset_id and dataset_version number 
        # The results should turn the message to a Dict via the message's to_dict method, then save the dict as a JSON file in the appropriate folder with a timestamp in the filename
        # The generated chart images should also be saved in this folder, and the path to the chart in the result message should reflect this saved location

        results_cache_dir = "results_cache"
        os.makedirs(results_cache_dir, exist_ok=True)

        results_folder = os.path.join(results_cache_dir, f"{result.dataset_id}_v{result.dataset_version}")
        os.makedirs(results_folder, exist_ok=True)

        results_msg = result.to_dict()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_filename = f"results_{timestamp}.json"
        results_filepath = os.path.join(results_folder, results_filename)
        with open(results_filepath, "w") as f:
            json.dump(results_msg, f, indent=4)



    def handle_request(self, request):
        # Extract method names, data, metadata, and parameters from the request
        # for each method name, instantiate the corresponding class and compute the result
        # Each corresponding computation should run in its own thread if available
        # Max threads should be limited to 4 concurrent threads

        # the output results should be packaged back into the message class
        # then sent back to the caller

        methods, data, metadata = self._get_methods(request)
        method_requests = self._get_method_requests(methods)

        max_threads = 4 #arbitrary limit, can be changed to a user configurable value later

        results = self._threads_compute(method_requests, data, metadata, max_threads)
        final_result_message = self._package_results(request, results)

        return final_result_message


    def worker(self, method_name, data, metadata, params):
        method_class = statistical_methods.get(method_name)
        if method_class:
            method_instance = method_class(data, metadata, params)
            return method_instance.compute()

        return self._generate_error_result(method_name, f"Method {method_name} not found.", params)
