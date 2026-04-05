# test_mean.py
# Tests for the Mean statistic class located in seniordesign/methods/mean.py
# Run from the seniordesign/ root: pytest testsuite/test_mean.py -v

import sys
import os
import math
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Path setup – allows pytest to find the methods package regardless of CWD
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "methods"))
from mean import Mean  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_metadata():
    """Minimal metadata dict shared across tests."""
    return {"source": "test", "column": "value"}


def make_mean(data, metadata=None, params=None):
    """Helper: construct a Mean instance with sensible defaults."""
    if metadata is None:
        metadata = {"source": "test"}
    return Mean(data, metadata, params)


# ===========================================================================
# _applicable() tests
# ===========================================================================

class TestApplicable:
    def test_returns_true_for_valid_list(self, dummy_metadata):
        """_applicable should be True when data is a non-empty list."""
        m = Mean([1, 2, 3], dummy_metadata)
        assert m._applicable() is True

    def test_returns_false_for_empty_list(self, dummy_metadata):
        """_applicable should be False when data is an empty list."""
        m = Mean([], dummy_metadata)
        assert m._applicable() is False

    def test_returns_false_for_none(self, dummy_metadata):
        """_applicable should be False when data is None."""
        m = Mean(None, dummy_metadata)
        assert m._applicable() is False

    def test_returns_true_for_numpy_array(self, dummy_metadata):
        """_applicable should be True for a non-empty numpy array."""
        m = Mean(np.array([10, 20, 30]), dummy_metadata)
        assert m._applicable() is True


# ===========================================================================
# compute() – normal cases
# ===========================================================================

class TestComputeNormal:
    def test_mean_of_simple_integers(self, dummy_metadata):
        """Mean of [1, 2, 3, 4, 5] should be 3.0."""
        m = make_mean([1, 2, 3, 4, 5], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 3.0)

    def test_mean_of_floats(self, dummy_metadata):
        """Mean of floating-point values matches numpy reference."""
        data = [1.5, 2.5, 3.5, 4.5]
        m = make_mean(data, dummy_metadata)
        result = m.compute()
        expected = float(np.mean(data))
        assert result["ok"] is True
        assert math.isclose(result["value"], expected)

    def test_mean_of_negative_numbers(self, dummy_metadata):
        """Mean should handle negative numbers correctly."""
        data = [-10, -20, -30]
        m = make_mean(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], -20.0)

    def test_mean_of_mixed_sign_numbers(self, dummy_metadata):
        """Mean of a mixed positive/negative list should be 0 when symmetric."""
        data = [-3, -1, 0, 1, 3]
        m = make_mean(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0)

    def test_mean_of_numpy_array(self, dummy_metadata):
        """Mean class should accept numpy arrays as input."""
        data = np.array([2.0, 4.0, 6.0, 8.0])
        m = make_mean(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 5.0)

    def test_return_value_is_float(self, dummy_metadata):
        """The returned value should be a Python float, not numpy scalar."""
        m = make_mean([10, 20, 30], dummy_metadata)
        result = m.compute()
        assert isinstance(result["value"], float)

    def test_result_structure_keys(self, dummy_metadata):
        """Result dict must contain the expected keys."""
        m = make_mean([1, 2, 3], dummy_metadata)
        result = m.compute()
        expected_keys = {"id", "ok", "value", "error", "loss_precision", "params_used"}
        assert expected_keys == set(result.keys())

    def test_stat_id_in_result(self, dummy_metadata):
        """Result 'id' field should equal 'mean'."""
        m = make_mean([1, 2], dummy_metadata)
        result = m.compute()
        assert result["id"] == "mean"

    def test_params_passed_through(self, dummy_metadata):
        """Custom params should appear in params_used of the result."""
        params = {"weighted": True}
        m = make_mean([1, 2, 3], dummy_metadata, params)
        result = m.compute()
        assert result["params_used"] == params

    def test_error_is_none_on_success(self, dummy_metadata):
        """Error field should be None on a successful computation."""
        m = make_mean([1, 2, 3], dummy_metadata)
        result = m.compute()
        assert result["error"] is None


# ===========================================================================
# compute() – edge cases
# ===========================================================================

class TestComputeEdgeCases:
    def test_single_element(self, dummy_metadata):
        """Mean of a single element should equal that element."""
        m = make_mean([42], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 42.0)

    def test_all_same_values(self, dummy_metadata):
        """Mean of identical values should equal that value."""
        data = [7, 7, 7, 7, 7]
        m = make_mean(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 7.0)

    def test_large_values(self, dummy_metadata):
        """Mean should handle large integers without overflow."""
        data = [10**12, 2 * 10**12, 3 * 10**12]
        m = make_mean(data, dummy_metadata)
        result = m.compute()
        expected = float(np.mean(np.array(data, dtype=float)))
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_large_dataset(self, dummy_metadata):
        """Mean of 100,000 uniform values should be ~0.5."""
        rng = np.random.default_rng(seed=42)  # fixed seed for reproducibility
        data = rng.random(100_000).tolist()
        m = make_mean(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.5, abs_tol=0.01)

    def test_two_elements(self, dummy_metadata):
        """Mean of two elements is their midpoint."""
        m = make_mean([3, 7], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 5.0)

    def test_zero_values(self, dummy_metadata):
        """Mean of all zeros should be 0.0."""
        m = make_mean([0, 0, 0], dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0)

    def test_mean_with_very_small_floats(self, dummy_metadata):
        """Mean should handle very small floating-point numbers."""
        data = [1e-300, 2e-300, 3e-300]
        m = make_mean(data, dummy_metadata)
        result = m.compute()
        expected = float(np.mean(np.array(data, dtype=float)))
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)


# ===========================================================================
# compute() – error handling
# ===========================================================================

class TestComputeErrors:
    def test_empty_list_returns_error(self, dummy_metadata):
        """Empty list should produce ok=False and a non-None error message."""
        m = make_mean([], dummy_metadata)
        result = m.compute()
        assert result["ok"] is False
        assert result["error"] is not None
        assert result["value"] is None

    def test_none_data_returns_error(self, dummy_metadata):
        """None data should produce ok=False and a non-None error message."""
        m = make_mean(None, dummy_metadata)
        result = m.compute()
        assert result["ok"] is False
        assert result["error"] is not None

    def test_non_numeric_strings_return_error(self, dummy_metadata):
        """List of non-numeric strings should produce ok=False."""
        m = make_mean(["a", "b", "c"], dummy_metadata)
        result = m.compute()
        assert result["ok"] is False
        assert result["error"] is not None

    def test_mixed_strings_and_numbers_return_error(self, dummy_metadata):
        """Mixed list with strings and numbers should not silently succeed."""
        m = make_mean([1, "two", 3], dummy_metadata)
        result = m.compute()
        assert result["ok"] is False

    def test_error_result_structure(self, dummy_metadata):
        """Error result dict must still contain all required keys."""
        m = make_mean([], dummy_metadata)
        result = m.compute()
        expected_keys = {"id", "ok", "value", "error", "loss_precision", "params_used"}
        assert expected_keys == set(result.keys())

    def test_error_stat_id_preserved(self, dummy_metadata):
        """Even on error, 'id' field should be 'mean'."""
        m = make_mean(None, dummy_metadata)
        result = m.compute()
        assert result["id"] == "mean"


# ===========================================================================
# Statistical correctness – comparison against numpy reference values
# ===========================================================================

class TestStatisticalCorrectness:
    @pytest.mark.parametrize("data,expected", [
        ([1, 2, 3, 4, 5], 3.0),
        ([10, 0], 5.0),
        ([100], 100.0),
        ([-5, 5], 0.0),
        ([0.1, 0.2, 0.3], 0.2),
    ])
    def test_known_expected_values(self, data, expected, dummy_metadata):
        """Parameterised check of mean against manually computed expected values."""
        m = make_mean(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9, abs_tol=1e-12)

    def test_matches_numpy_mean_for_random_data(self, dummy_metadata):
        """Mean result should exactly match numpy's mean for a seeded random array."""
        rng = np.random.default_rng(seed=2024)
        data = rng.integers(low=-1000, high=1000, size=500).tolist()
        expected = float(np.mean(data))

        m = make_mean(data, dummy_metadata)
        result = m.compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)
