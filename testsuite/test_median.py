# test_median.py
# Tests for the Median statistic class located in seniordesign/methods/median.py
# Run from the seniordesign/ root: pytest testsuite/test_median.py -v

import sys
import os
import math
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "methods"))

# NOTE: median.py imports `from class_templates import message_structure`.
# That import is not used anywhere in the class body, so we mock it here to
# allow tests to run without the class_templates module being present.
import types
_stub = types.ModuleType("class_templates")
_stub.message_structure = object
sys.modules.setdefault("class_templates", _stub)

from median import Median  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_metadata():
    return {"source": "test", "column": "value"}


def make_median(data, metadata=None, params=None):
    if metadata is None:
        metadata = {"source": "test"}
    return Median(data, metadata, params)


# ===========================================================================
# _applicable() tests
# ===========================================================================

class TestApplicable:
    def test_returns_true_for_valid_list(self, dummy_metadata):
        """_applicable should be True for a non-empty list."""
        m = make_median([1, 2, 3], dummy_metadata)
        assert m._applicable() is True

    def test_returns_false_for_empty_list(self, dummy_metadata):
        """_applicable should be False for an empty list."""
        m = make_median([], dummy_metadata)
        assert m._applicable() is False

    def test_returns_false_for_none(self, dummy_metadata):
        """_applicable should be False when data is None."""
        m = make_median(None, dummy_metadata)
        assert m._applicable() is False

    def test_returns_true_for_numpy_array(self, dummy_metadata):
        """_applicable should be True for a non-empty numpy array."""
        m = make_median(np.array([5, 10, 15]), dummy_metadata)
        assert m._applicable() is True


# ===========================================================================
# compute() – normal cases
# ===========================================================================

class TestComputeNormal:
    def test_median_odd_length(self, dummy_metadata):
        """Median of an odd-length sorted list is the middle element."""
        # [1,2,3,4,5] → median = 3
        m = make_median([1, 2, 3, 4, 5], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 3.0)

    def test_median_even_length(self, dummy_metadata):
        """Median of an even-length list is the average of the two middle elements."""
        # [1,2,3,4] → median = 2.5
        m = make_median([1, 2, 3, 4], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 2.5)

    def test_median_unsorted_input(self, dummy_metadata):
        """Median computation should work even if the input is unsorted."""
        data = [5, 1, 3, 2, 4]  # sorted → [1,2,3,4,5], median = 3
        m = make_median(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 3.0)

    def test_median_negative_numbers(self, dummy_metadata):
        """Median should handle negative numbers correctly."""
        data = [-30, -10, -20]  # sorted → [-30,-20,-10], median = -20
        m = make_median(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], -20.0)

    def test_median_mixed_sign(self, dummy_metadata):
        """Median of a symmetric mixed-sign list should be 0."""
        data = [-2, -1, 0, 1, 2]
        m = make_median(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0)

    def test_median_floats(self, dummy_metadata):
        """Median of float values matches numpy reference."""
        data = [1.1, 2.2, 3.3, 4.4, 5.5]
        m = make_median(data, dummy_metadata)
        result = m.compute()
        expected = float(np.median(data))
        assert result["ok"] is True
        assert math.isclose(result["value"], expected)

    def test_median_numpy_array_input(self, dummy_metadata):
        """Median class should accept numpy arrays as input."""
        data = np.array([10.0, 30.0, 20.0])
        m = make_median(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 20.0)

    def test_return_value_is_float(self, dummy_metadata):
        """Returned value should be a Python float, not a numpy scalar."""
        m = make_median([4, 8, 15], dummy_metadata)
        result = m.compute()
        assert isinstance(result["value"], float)

    def test_result_structure_keys(self, dummy_metadata):
        """Result dict must contain the expected keys."""
        m = make_median([1, 2, 3], dummy_metadata)
        result = m.compute()
        expected_keys = {"id", "ok", "value", "error", "loss_precision", "params_used"}
        assert expected_keys == set(result.keys())

    def test_stat_id_in_result(self, dummy_metadata):
        """Result 'id' field should equal 'median'."""
        m = make_median([1, 2, 3], dummy_metadata)
        result = m.compute()
        assert result["id"] == "median"

    def test_error_is_none_on_success(self, dummy_metadata):
        """Error field should be None on a successful computation."""
        m = make_median([1, 2, 3], dummy_metadata)
        result = m.compute()
        assert result["error"] is None

    def test_params_passed_through(self, dummy_metadata):
        """Custom params should appear in params_used of the result."""
        params = {"interpolation": "linear"}
        m = make_median([1, 2, 3], dummy_metadata, params)
        result = m.compute()
        assert result["params_used"] == params


# ===========================================================================
# compute() – edge cases
# ===========================================================================

class TestComputeEdgeCases:
    def test_single_element(self, dummy_metadata):
        """Median of a single element should equal that element."""
        m = make_median([99], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 99.0)

    def test_two_elements(self, dummy_metadata):
        """Median of two elements is their average."""
        m = make_median([3, 7], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 5.0)

    def test_all_same_values(self, dummy_metadata):
        """Median of identical values equals that value."""
        m = make_median([5, 5, 5, 5], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 5.0)

    def test_all_zeros(self, dummy_metadata):
        """Median of all zeros should be 0.0."""
        m = make_median([0, 0, 0, 0], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0)

    def test_large_values(self, dummy_metadata):
        """Median should handle large integers without overflow."""
        data = [10**12, 2 * 10**12, 3 * 10**12]
        m = make_median(data, dummy_metadata)
        result = m.compute()
        expected = float(np.median(np.array(data, dtype=float)))
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_large_dataset(self, dummy_metadata):
        """Median of a large seeded-random dataset matches numpy's result."""
        rng = np.random.default_rng(seed=42)
        data = rng.random(100_000).tolist()
        expected = float(np.median(data))

        m = make_median(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_very_small_floats(self, dummy_metadata):
        """Median should handle very small floating-point numbers."""
        data = [1e-300, 2e-300, 3e-300]
        m = make_median(data, dummy_metadata)
        result = m.compute()
        expected = float(np.median(np.array(data, dtype=float)))
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_duplicate_values_even_length(self, dummy_metadata):
        """Even-length list with duplicates — median is the average of inner pair."""
        # sorted: [1,1,3,3] → median = (1+3)/2 = 2.0
        m = make_median([3, 1, 1, 3], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 2.0)


# ===========================================================================
# compute() – error handling
# ===========================================================================

class TestComputeErrors:
    def test_empty_list_returns_error(self, dummy_metadata):
        """Empty list should produce ok=False with a non-None error message."""
        m = make_median([], dummy_metadata)
        result = m.compute()
        assert result["ok"] is False
        assert result["error"] is not None
        assert result["value"] is None

    def test_none_data_returns_error(self, dummy_metadata):
        """None data should produce ok=False."""
        m = make_median(None, dummy_metadata)
        result = m.compute()
        assert result["ok"] is False
        assert result["error"] is not None

    def test_non_numeric_strings_return_error(self, dummy_metadata):
        """Non-numeric string data should produce ok=False."""
        m = make_median(["x", "y", "z"], dummy_metadata)
        result = m.compute()
        assert result["ok"] is False
        assert result["error"] is not None

    def test_mixed_strings_and_numbers_return_error(self, dummy_metadata):
        """Mixed list with strings and numbers should not silently succeed."""
        m = make_median([1, "two", 3], dummy_metadata)
        result = m.compute()
        assert result["ok"] is False

    def test_error_result_structure(self, dummy_metadata):
        """Error result dict must still contain all required keys."""
        m = make_median([], dummy_metadata)
        result = m.compute()
        expected_keys = {"id", "ok", "value", "error", "loss_precision", "params_used"}
        assert expected_keys == set(result.keys())

    def test_error_stat_id_preserved(self, dummy_metadata):
        """Even on error, 'id' field should be 'median'."""
        m = make_median(None, dummy_metadata)
        result = m.compute()
        assert result["id"] == "median"


# ===========================================================================
# Statistical correctness – comparison against numpy reference values
# ===========================================================================

class TestStatisticalCorrectness:
    @pytest.mark.parametrize("data,expected", [
        ([1, 2, 3, 4, 5], 3.0),          # odd-length, simple
        ([1, 2, 3, 4], 2.5),              # even-length average
        ([7], 7.0),                        # single element
        ([-5, 0, 5], 0.0),                # symmetric around zero
        ([10, 20, 30, 40], 25.0),         # even-length, tens
        ([1.5, 2.5, 3.5], 2.5),           # floats, odd
    ])
    def test_known_expected_values(self, data, expected, dummy_metadata):
        """Parameterised check of median against manually computed expected values."""
        m = make_median(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9, abs_tol=1e-12)

    def test_matches_numpy_median_for_random_data(self, dummy_metadata):
        """Median result should exactly match numpy's median for a seeded random array."""
        rng = np.random.default_rng(seed=2024)
        data = rng.integers(low=-500, high=500, size=501).tolist()
        expected = float(np.median(data))

        m = make_median(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)
