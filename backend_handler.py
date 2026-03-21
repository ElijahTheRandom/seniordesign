
from datetime import datetime
import os
import re

import json


import queue
import threading
import uuid


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
        # Defer heavy imports (matplotlib, plotly, numpy, sklearn) until
        # first use so they don't slow down app boot.
        self._statistical_methods = None
        self._chart_generation_methods = None

    @property
    def statistical_methods(self):
        if self._statistical_methods is None:
            from methods.methods import methods_list
            self._statistical_methods = methods_list
        return self._statistical_methods

    @property
    def chart_generation_methods(self):
        if self._chart_generation_methods is None:
            from charts.charts import charts_list
            self._chart_generation_methods = charts_list
        return self._chart_generation_methods

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
        Compute each method via a task queue, dispatching work to up to
        max_threads concurrent worker threads. Results are returned in the
        same order as method_requests.

        :param self: self
        :param method_requests: List of (method_id, method_params) tuples
        :param data: Data for computations
        :param metadata: Metadata for computations
        :param max_threads: Maximum number of concurrent threads
        """
        task_queue = queue.Queue()
        results_lock = threading.Lock()
        results = {}

        # Enqueue all tasks with their original index so order can be restored
        for idx, (method_id, method_params) in enumerate(method_requests):
            method_data = data[method_id] if isinstance(data, dict) and method_id in data else data
            method_metadata = metadata[method_id] if isinstance(metadata, dict) and method_id in metadata else metadata
            task_queue.put((idx, method_id, method_params, method_data, method_metadata))

        # Add one sentinel (None) per thread to signal shutdown
        num_threads = min(max_threads, len(method_requests)) if method_requests else 0
        for _ in range(num_threads):
            task_queue.put(None)

        def thread_worker():
            while True:
                task = task_queue.get()
                if task is None:          # sentinel: no more work for this thread
                    task_queue.task_done()
                    break
                idx, method_id, method_params, method_data, method_metadata = task
                try:
                    result = self.worker(method_id, method_data, method_metadata, method_params)
                except Exception as exc:
                    result = self._generate_error_result(method_id, str(exc), method_params)
                with results_lock:
                    results[idx] = result
                task_queue.task_done()

        threads = [threading.Thread(target=thread_worker, daemon=True) for _ in range(num_threads)]
        for t in threads:
            t.start()

        # Block until every task (including sentinels) has been marked done
        task_queue.join()

        for t in threads:
            t.join()

        # Return results in original request order
        return [results[i] for i in range(len(method_requests))]

    def _generate_error_result(self, method_name, error_message, params):
        return {
            "id": method_name,
            "ok": False,
            "value": None,
            "error": error_message,
            "loss_of_precision": False,
            "params_used": params or {}
        }

    def _sanitize_for_filename(self, value, default="dataset", max_length=100):
        """
        Sanitize an arbitrary value so it is safe to use as a filename component.

        - Converts the value to string.
        - Strips any directory components.
        - Replaces characters not in [A-Za-z0-9._-] with underscores.
        - Truncates the result to max_length characters.
        - Falls back to `default` if the result is empty after sanitization.
        """
        if value is None:
            return default

        # Ensure we are working with a string representation
        text = str(value)

        # Strip any directory components
        text = os.path.basename(text)

        # Allow only safe characters; replace others with "_"
        text = re.sub(r"[^A-Za-z0-9._-]", "_", text)

        # Enforce maximum length
        if len(text) > max_length:
            text = text[:max_length]

        # Avoid empty names
        if not text:
            return default

        return text

    def _create_run_folder(self, message):
        """
        Create a unique persistence folder for this run.

        The folder is placed under results_cache/ and named with the
        dataset id, version, a timestamp, and a short UUID to guarantee
        uniqueness across concurrent or rapid-fire runs.

        :param message: Message object (used for dataset_id / dataset_version)
        :return: Absolute path to the newly created run folder
        """
        results_cache_dir = "results_cache"
        os.makedirs(results_cache_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uid = uuid.uuid4().hex[:8]
        safe_dataset_id = self._sanitize_for_filename(getattr(message, "dataset_id", None))
        safe_dataset_version = self._sanitize_for_filename(getattr(message, "dataset_version", None), default="v", max_length=50)
        folder_name = f"{safe_dataset_id}_v{safe_dataset_version}_{timestamp}_{short_uid}"
        run_folder = os.path.join(results_cache_dir, folder_name)
        os.makedirs(run_folder, exist_ok=True)

        return run_folder

    def _save_run_json(self, message, run_folder):
        """
        Serialize the completed message (including results and chart paths)
        to a JSON file inside the run folder.

        :param message: Fully populated Message object
        :param run_folder: Path to the persistence folder for this run
        :return: Path to the saved JSON file
        """
        results_dict = message.to_dict()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"results_{timestamp}.json"
        json_filepath = os.path.join(run_folder, json_filename)
        with open(json_filepath, "w") as f:
            json.dump(results_dict, f, indent=4, default=str)

        return json_filepath


    def _generate_charts(self, graphics_requests, data, metadata, results_folder):
        # Generate charts in parallel threads — each chart writes to its own file
        # so there are no shared-state conflicts.

        results_lock = threading.Lock()
        results_dict = {}

        def _gen_one(idx, graphic_request):
            chart_type = graphic_request.get("type")
            chart_params = {k: v for k, v in graphic_request.items() if k != "type"}

            if "path" in chart_params:
                original_filename = os.path.basename(chart_params["path"])
                chart_params["path"] = os.path.join(results_folder, original_filename)
            else:
                chart_params["path"] = os.path.join(results_folder, f"{chart_type}_{idx}.png")

            chart_class = self.chart_generation_methods.get(chart_type)
            if chart_class:
                chart_instance = chart_class(data, metadata, chart_params)
                chart_result = chart_instance.create_graphic()
            else:
                chart_result = {
                    "type": chart_type,
                    "ok": False,
                    "path": None,
                    "error": f"Chart type {chart_type} not found.",
                    "params_used": chart_params,
                }
            with results_lock:
                results_dict[idx] = chart_result

        threads = []
        for idx, graphic_request in enumerate(graphics_requests):
            t = threading.Thread(target=_gen_one, args=(idx, graphic_request), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return [results_dict[i] for i in range(len(graphics_requests))]


    def _save_embedded_charts(self, results, run_folder):
        """
        Some methods (e.g. LeastSquaresRegression) produce a PNG chart and embed
        it as a base64 string under result["value"]["chart"].  This step saves
        those PNGs into the run folder and replaces the base64 payload with the
        file path, matching the behaviour of the charts pipeline.
        """
        import base64
        import binascii
        for result in results:
            if not isinstance(result, dict):
                continue
            value = result.get("value")
            if not isinstance(value, dict) or "chart" not in value:
                continue
            chart_data = value["chart"]
            if not isinstance(chart_data, str):
                continue
            filename = f"{result.get('id', 'method_chart')}_chart.png"
            filepath = os.path.join(run_folder, filename)
            try:
                decoded_chart = base64.b64decode(chart_data)
            except (binascii.Error, ValueError):
                # Invalid base64 payload; skip this chart instead of aborting the whole request.
                continue
            with open(filepath, "wb") as f:
                f.write(decoded_chart)
            value["chart"] = filepath

    def handle_request(self, request):
        """
        Persistence flow
        ----------------
        1. Perform computations (threaded)
        2. Create a unique persistence folder for this run
        2.5 Save any charts embedded in method results as image files
        3. Generate charts, saving images into the persistence folder
        4. Save the complete message (results + chart paths) as JSON
        5. Return the message
        """

        # --- 1. Computations ---
        methods, data, metadata = self._get_methods(request)
        method_requests = self._get_method_requests(methods)
        max_threads = 4  # arbitrary limit, can be changed to a user configurable value later
        results = self._threads_compute(method_requests, data, metadata, max_threads)
        final_result_message = self._package_results(request, results)

        # --- 2. Create unique persistence folder ---
        run_folder = self._create_run_folder(final_result_message)
        final_result_message.run_folder = run_folder

        # --- 2.5. Save embedded method charts (e.g. LSR) into the persistence folder ---
        self._save_embedded_charts(final_result_message.results, run_folder)

        # --- 3. Generate charts into the persistence folder ---
        chart_results = self._generate_charts(
            final_result_message.graphics,
            final_result_message.data,
            final_result_message.metadata,
            run_folder,
        )
        final_result_message.graphics = chart_results

        # --- 4. Save complete message as JSON ---
        self._save_run_json(final_result_message, run_folder)

        # --- 5. Return the message ---
        return final_result_message


    def worker(self, method_name, data, metadata, params):
        method_class = self.statistical_methods.get(method_name)
        if method_class:
            method_instance = method_class(data, metadata, params)
            return method_instance.compute()

        return self._generate_error_result(method_name, f"Method {method_name} not found.", params)
