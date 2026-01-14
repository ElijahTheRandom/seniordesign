class MethodName:
    def __init__(self, stat_id, params=None):
        # Initialize the statistic with an ID and optional parameters
        self.stat_id = stat_id
        self.params = params or {}

    def applicable(self, data):
        # Check whether this statistic is valid for the given data selection
        pass

    def compute(self, data):
        # Perform the statistical computation and return a standardized result dictionary
        pass

    def create_graphic(self, results):
        # Generate a chart or visualization object for the computed results
        pass

    def summarize(self, results):
        # Produce a plain-text summary of the statistic for reporting
        pass

    def return_report(self, data):
        # Full pipeline: check applicability, compute, visualize, and summarize
        if not self.applicable(data):
            raise ValueError("Statistic not applicable to the provided data.")
        
        results = self.compute(data)
        graphic = self.create_graphic(results)
        summary = self.summarize(results)
        
        return {
            "results": results,
            "graphic": graphic,
            "summary": summary
        }
