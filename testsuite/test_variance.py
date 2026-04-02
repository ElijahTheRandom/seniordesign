# test_variance.py
# Tests for Variance in seniordesign/methods/variance.py
# Run from seniordesign/ root: pytest testsuite/test_variance.py -v

import sys
import os
import math
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "methods"))
from variance import Variance


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def meta():
    return {"source": "test"}


def make_var(data, meta=None, params=None):
    # Variance._generate_return_structure calls len(self.params), so params
    # must be a sequence. Default to empty list (not None) when not provided.
    return Variance(data, meta or {"source": "test"}, params if params is not None else [])


# ===========================================================================
# _applicable()
# ===========================================================================

class TestApplicable:
    def test_true_for_2_or_more_elements(self, meta):
        assert Variance([1, 2, 3], meta, [])._applicable() is True

    def test_false_for_none(self, meta):
        assert Variance(None, meta, [])._applicable() is False

    def test_false_for_empty_list(self, meta):
        assert Variance([], meta, [])._applicable() is False

    def test_false_for_single_element(self, meta):
        # Variance requires at least 2 data points
        assert Variance([5], meta, [])._applicable() is False

    def test_true_for_exactly_2_elements(self, meta):
        assert Variance([3, 7], meta, [])._applicable() is True

    def test_true_for_numpy_array(self, meta):
        assert Variance(np.array([1, 2, 3, 4]), meta, [])._applicable() is True


# ===========================================================================
# compute() – normal cases
# ===========================================================================

class TestComputeNormal:
    def test_ok_true(self, meta):
        result = make_var([1, 2, 3, 4, 5], meta).compute()
        assert result["ok"] is True

    def test_stat_id(self, meta):
        result = make_var([1, 2, 3], meta).compute()
        assert result["id"] == "variance"

    def test_value_is_float(self, meta):
        result = make_var([1, 2, 3], meta).compute()
        assert isinstance(result["value"], float)

    def test_error_none_on_success(self, meta):
        result = make_var([1, 2, 3], meta).compute()
        assert result["error"] is None

    def test_result_keys(self, meta):
        result = make_var([1, 2, 3], meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())

    def test_uses_ddof_1(self, meta):
        """Variance class uses ddof=1 (sample variance). Verify against numpy."""
        data = [2, 4, 4, 4, 5, 5, 7, 9]
        expected = float(np.var(data, ddof=1))
        result = make_var(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_matches_numpy_var_ddof1(self, meta):
        """Result should match numpy.var(data, ddof=1) on random data."""
        rng = np.random.default_rng(seed=42)
        data = rng.normal(10, 3, 500).tolist()
        expected = float(np.var(data, ddof=1))
        result = make_var(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_variance_non_negative(self, meta):
        result = make_var([1, 5, 9], meta).compute()
        assert result["ok"] is True
        assert result["value"] >= 0.0

    def test_identical_values_variance_is_zero(self, meta):
        """Variance of constant data should be 0."""
        result = make_var([7, 7, 7, 7], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0, abs_tol=1e-12)

    def test_negative_numbers(self, meta):
        data = [-5, -3, -1, 1, 3, 5]
        expected = float(np.var(data, ddof=1))
        result = make_var(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_float_values(self, meta):
        data = [1.5, 2.5, 3.5, 4.5]
        expected = float(np.var(data, ddof=1))
        result = make_var(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_numpy_array_input(self, meta):
        data = np.array([2.0, 4.0, 6.0, 8.0])
        expected = float(np.var(data, ddof=1))
        result = make_var(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_variance_equals_std_squared(self, meta):
        """Variance should equal (population std)² when using matching ddof."""
        # Both use ddof=1 for consistency here
        data = [3, 7, 2, 9, 4]
        var_result = make_var(data, meta).compute()
        std_val = float(np.std(data, ddof=1))
        assert result_ok := var_result["ok"]
        assert math.isclose(var_result["value"], std_val ** 2, rel_tol=1e-9)


# ===========================================================================
# compute() – edge cases
# ===========================================================================

class TestComputeEdgeCases:
    def test_two_elements(self, meta):
        """Variance of exactly 2 elements (minimum valid input)."""
        data = [3, 7]
        expected = float(np.var(data, ddof=1))  # = 8.0
        result = make_var(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_large_values(self, meta):
        data = [10**9, 2 * 10**9, 3 * 10**9]
        expected = float(np.var(np.array(data, dtype=float), ddof=1))
        result = make_var(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_large_dataset(self, meta):
        rng = np.random.default_rng(seed=77)
        data = rng.normal(0, 5, 100_000).tolist()
        expected = float(np.var(data, ddof=1))
        result = make_var(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_2d_numpy_array_flattened(self, meta):
        """2-D arrays should be flattened before variance calculation."""
        data = np.array([[1, 2], [3, 4]])
        expected = float(np.var([1, 2, 3, 4], ddof=1))
        result = make_var(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)


# ===========================================================================
# compute() – error handling
# ===========================================================================

class TestComputeErrors:
    def test_none_data(self, meta):
        result = make_var(None, meta).compute()
        assert result["ok"] is False
        assert result["error"] is not None
        assert result["value"] is None

    def test_empty_list(self, meta):
        result = make_var([], meta).compute()
        assert result["ok"] is False

    def test_single_element(self, meta):
        """Single element does not satisfy _applicable (requires >= 2 points)."""
        result = make_var([42], meta).compute()
        assert result["ok"] is False

    def test_non_numeric_strings(self, meta):
        result = make_var(["a", "b", "c"], meta).compute()
        assert result["ok"] is False

    def test_mixed_strings_and_numbers(self, meta):
        result = make_var([1, "two", 3], meta).compute()
        assert result["ok"] is False

    def test_error_stat_id_preserved(self, meta):
        result = make_var(None, meta).compute()
        assert result["id"] == "variance"

    def test_error_result_keys(self, meta):
        result = make_var(None, meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())


# ===========================================================================
# Statistical correctness – parametrized
# ===========================================================================

class TestStatisticalCorrectness:
    @pytest.mark.parametrize("data,expected_var", [
        ([2, 4, 4, 4, 5, 5, 7, 9], float(np.var([2, 4, 4, 4, 5, 5, 7, 9], ddof=1))),
        ([3, 7], 8.0),          # (7-3)²/1 = 8
        ([1, 2, 3, 4, 5], 2.5), # sample variance of 1..5
        ([10, 10, 10, 10], 0.0), # constant
    ])
    def test_known_expected_values(self, data, expected_var, meta):
        result = make_var(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected_var, abs_tol=1e-9)
