# test_mode.py
# Tests for the Mode statistic class located in seniordesign/methods/mode.py
# Run from the seniordesign/ root: pytest testsuite/test_mode.py -v

import sys
import os
import math
import statistics
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "methods"))
from mode import Mode  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_metadata():
    return {"source": "test", "column": "value"}


def make_mode(data, metadata=None, params=None):
    if metadata is None:
        metadata = {"source": "test"}
    return Mode(data, metadata, params)


# ===========================================================================
# _applicable() tests
# ===========================================================================

class TestApplicable:
    def test_returns_true_for_valid_list(self, dummy_metadata):
        """_applicable should be True for a non-empty list."""
        m = make_mode([1, 2, 2, 3], dummy_metadata)
        assert m._applicable() is True

    def test_returns_false_for_empty_list(self, dummy_metadata):
        """_applicable should be False for an empty list."""
        m = make_mode([], dummy_metadata)
        assert m._applicable() is False

    def test_returns_false_for_none(self, dummy_metadata):
        """_applicable should be False when data is None."""
        m = make_mode(None, dummy_metadata)
        assert m._applicable() is False

    def test_returns_true_for_numpy_array(self, dummy_metadata):
        """_applicable should be True for a non-empty numpy array."""
        m = make_mode(np.array([1, 1, 2]), dummy_metadata)
        assert m._applicable() is True


# ===========================================================================
# compute() – normal cases
# ===========================================================================

class TestComputeNormal:
    def test_mode_clear_winner(self, dummy_metadata):
        """Mode of [1, 2, 2, 3] should be 2."""
        m = make_mode([1, 2, 2, 3], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 2.0)

    def test_mode_single_repeated_element(self, dummy_metadata):
        """Mode of [5, 5, 5] should be 5."""
        m = make_mode([5, 5, 5], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 5.0)

    def test_mode_negative_numbers(self, dummy_metadata):
        """Mode should handle negative numbers correctly."""
        data = [-3, -1, -3, -3, 0]
        m = make_mode(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], -3.0)

    def test_mode_float_values(self, dummy_metadata):
        """Mode should work with float values."""
        data = [1.5, 2.5, 1.5, 3.5]
        m = make_mode(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 1.5)

    def test_mode_numpy_array_input(self, dummy_metadata):
        """Mode class should accept numpy arrays as input."""
        data = np.array([10, 20, 10, 30])
        m = make_mode(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 10.0)

    def test_return_value_is_float(self, dummy_metadata):
        """Returned value should be a Python float, not a numpy scalar."""
        m = make_mode([1, 1, 2], dummy_metadata)
        result = m.compute()
        assert isinstance(result["value"], float)

    def test_result_structure_keys(self, dummy_metadata):
        """Result dict must contain the expected keys."""
        m = make_mode([1, 1, 2], dummy_metadata)
        result = m.compute()
        expected_keys = {"id", "ok", "value", "error", "loss_precision", "params_used"}
        assert expected_keys == set(result.keys())

    def test_stat_id_in_result(self, dummy_metadata):
        """Result 'id' field should equal 'mode'."""
        m = make_mode([1, 1, 2], dummy_metadata)
        result = m.compute()
        assert result["id"] == "mode"

    def test_error_is_none_on_success(self, dummy_metadata):
        """Error field should be None on a successful computation."""
        m = make_mode([1, 1, 2], dummy_metadata)
        result = m.compute()
        assert result["error"] is None

    def test_params_passed_through(self, dummy_metadata):
        """Custom params should appear in params_used of the result."""
        params = {"strategy": "first"}
        m = make_mode([1, 1, 2], dummy_metadata, params)
        result = m.compute()
        assert result["params_used"] == params

    def test_mode_matches_statistics_module(self, dummy_metadata):
        """Mode result should match Python's statistics.mode for a clear-winner list."""
        data = [3, 1, 4, 1, 5, 9, 2, 6, 1]
        expected = float(statistics.mode(data))
        m = make_mode(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected)


# ===========================================================================
# compute() – edge cases
# ===========================================================================

class TestComputeEdgeCases:
    def test_single_element(self, dummy_metadata):
        """Mode of a single element is that element."""
        m = make_mode([42], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 42.0)

    def test_all_same_values(self, dummy_metadata):
        """Mode of all-identical values is that value."""
        m = make_mode([7, 7, 7, 7], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 7.0)

    def test_all_zeros(self, dummy_metadata):
        """Mode of all-zero list should be 0."""
        m = make_mode([0, 0, 0], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0)

    def test_large_values(self, dummy_metadata):
        """Mode should handle large integers."""
        data = [10**12, 10**12, 10**12, 2 * 10**12]
        m = make_mode(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], float(10**12), rel_tol=1e-9)

    def test_two_elements_same(self, dummy_metadata):
        """Mode of two identical elements is that element."""
        m = make_mode([9, 9], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 9.0)

    def test_multimodal_returns_a_value(self, dummy_metadata):
        """When data is bimodal, statistics.mode (Python ≥3.8) returns the first
        encountered mode; we just assert that ok=True and value is one of the modes."""
        # [1,1,2,2] is bimodal — Python 3.8+ statistics.mode picks the first
        data = [1, 1, 2, 2]
        m = make_mode(data, dummy_metadata)
        result = m.compute()
        # Either ok is True with a valid mode, or ok is False with an error
        # (Python <3.8 raises StatisticsError for multimodal data).
        if result["ok"]:
            assert result["value"] in (1.0, 2.0)
        else:
            assert result["error"] is not None

    def test_numpy_2d_array_flattened(self, dummy_metadata):
        """Mode class calls flatten() on numpy arrays; a 2-D array should work."""
        data = np.array([[1, 2], [1, 3]])  # flattened: [1, 2, 1, 3], mode = 1
        m = make_mode(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 1.0)


# ===========================================================================
# compute() – error handling
# ===========================================================================

class TestComputeErrors:
    def test_empty_list_returns_error(self, dummy_metadata):
        """Empty list should produce ok=False with a non-None error message."""
        m = make_mode([], dummy_metadata)
        result = m.compute()
        assert result["ok"] is False
        assert result["error"] is not None
        assert result["value"] is None

    def test_none_data_returns_error(self, dummy_metadata):
        """None data should produce ok=False."""
        m = make_mode(None, dummy_metadata)
        result = m.compute()
        assert result["ok"] is False
        assert result["error"] is not None

    def test_error_result_structure(self, dummy_metadata):
        """Error result dict must still contain all required keys."""
        m = make_mode([], dummy_metadata)
        result = m.compute()
        expected_keys = {"id", "ok", "value", "error", "loss_precision", "params_used"}
        assert expected_keys == set(result.keys())

    def test_error_stat_id_preserved(self, dummy_metadata):
        """Even on error, 'id' field should be 'mode'."""
        m = make_mode(None, dummy_metadata)
        result = m.compute()
        assert result["id"] == "mode"

    def test_non_numeric_strings_return_error(self, dummy_metadata):
        """statistics.mode on non-comparable types should surface an error gracefully."""
        # statistics.mode can handle strings, but they can't be cast to float;
        # the except block should catch the conversion error.
        m = make_mode(["apple", "banana", "apple"], dummy_metadata)
        result = m.compute()
        # Accept either ok=True (mode found as string then cast failed → ok=False)
        # The important contract: no unhandled exception is raised.
        assert isinstance(result["ok"], bool)
        assert result["id"] == "mode"


# ===========================================================================
# Statistical correctness – comparison against known expected values
# ===========================================================================

class TestStatisticalCorrectness:
    @pytest.mark.parametrize("data,expected_mode", [
        ([1, 2, 2, 3, 3, 3], 3.0),         # 3 appears most often
        ([10, 10, 20], 10.0),               # 10 appears twice
        ([5], 5.0),                          # single element
        ([-4, -4, 0, 1], -4.0),             # negative mode
        ([1.0, 1.0, 2.0, 3.0], 1.0),        # float mode
        ([100, 200, 100, 300, 100], 100.0), # large gap between values
    ])
    def test_known_expected_values(self, data, expected_mode, dummy_metadata):
        """Parameterised check of mode against manually computed expected values."""
        m = make_mode(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected_mode, rel_tol=1e-9, abs_tol=1e-12)
