# test_standardDeviation.py
# Tests for StandardDeviation in seniordesign/methods/standardDeviation.py
# Run from seniordesign/ root: pytest testsuite/test_standardDeviation.py -v

import sys
import os
import math
import numpy as np
import pytest
import types

# Stub the missing class_templates dependency
_stub = types.ModuleType("class_templates")
_stub.message_structure = object
sys.modules.setdefault("class_templates", _stub)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "methods"))
from standardDeviation import StandardDeviation


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def meta():
    return {"source": "test"}


def make_std(data, meta=None, params=None):
    return StandardDeviation(data, meta or {"source": "test"}, params)


# ===========================================================================
# _applicable()
# ===========================================================================

class TestApplicable:
    def test_true_for_valid_list(self, meta):
        assert StandardDeviation([1, 2, 3], meta)._applicable() is None

    def test_false_for_none(self, meta):
        assert StandardDeviation(None, meta)._applicable() is not None

    def test_false_for_empty_list(self, meta):
        assert StandardDeviation([], meta)._applicable() is not None

    def test_true_for_single_element(self, meta):
        assert StandardDeviation([5], meta)._applicable() is None

    def test_true_for_numpy_array(self, meta):
        assert StandardDeviation(np.array([10, 20, 30]), meta)._applicable() is None


# ===========================================================================
# compute() – normal cases
# ===========================================================================

class TestComputeNormal:
    def test_ok_true(self, meta):
        result = make_std([1, 2, 3, 4, 5], meta).compute()
        assert result["ok"] is True

    def test_stat_id(self, meta):
        result = make_std([1, 2, 3], meta).compute()
        assert result["id"] == "standard_deviation"

    def test_value_is_float(self, meta):
        result = make_std([1, 2, 3], meta).compute()
        assert isinstance(result["value"], float)

    def test_error_none_on_success(self, meta):
        result = make_std([1, 2, 3], meta).compute()
        assert result["error"] is None

    def test_result_keys(self, meta):
        result = make_std([1, 2, 3], meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())

    def test_known_std_simple(self, meta):
        """std of [2, 4, 4, 4, 5, 5, 7, 9] = 2.0 (population std, ddof=0)."""
        # numpy default ddof=0
        data = [2, 4, 4, 4, 5, 5, 7, 9]
        expected = float(np.std(data))
        result = make_std(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_matches_numpy_std(self, meta):
        """Result should match numpy.std(data) (population std, ddof=0)."""
        rng = np.random.default_rng(seed=42)
        data = rng.normal(10, 3, 500).tolist()
        expected = float(np.std(data))
        result = make_std(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_std_non_negative(self, meta):
        """Standard deviation is always ≥ 0."""
        result = make_std([5, 10, 15], meta).compute()
        assert result["ok"] is True
        assert result["value"] >= 0.0

    def test_identical_values_std_is_zero(self, meta):
        """Std of constant data should be 0."""
        result = make_std([7, 7, 7, 7, 7], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0, abs_tol=1e-12)

    def test_negative_numbers(self, meta):
        data = [-10, -5, 0, 5, 10]
        expected = float(np.std(data))
        result = make_std(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_numpy_array_input(self, meta):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        expected = float(np.std(data))
        result = make_std(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_params_passed_through(self, meta):
        params = {"ddof": 0}
        result = make_std([1, 2, 3], meta, params).compute()
        assert result["params_used"] == params


# ===========================================================================
# compute() – edge cases
# ===========================================================================

class TestComputeEdgeCases:
    def test_single_element(self, meta):
        """Std of a single element is 0 (no deviation from itself)."""
        result = make_std([42], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0, abs_tol=1e-12)

    def test_two_elements(self, meta):
        data = [3, 7]
        expected = float(np.std(data))
        result = make_std(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_large_values(self, meta):
        data = [10**9, 2 * 10**9, 3 * 10**9]
        expected = float(np.std(np.array(data, dtype=float)))
        result = make_std(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_large_dataset(self, meta):
        rng = np.random.default_rng(seed=99)
        data = rng.normal(0, 5, 100_000).tolist()
        expected = float(np.std(data))
        result = make_std(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_float_values(self, meta):
        data = [0.1, 0.2, 0.3, 0.4, 0.5]
        expected = float(np.std(data))
        result = make_std(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)


# ===========================================================================
# compute() – error handling
# ===========================================================================

class TestComputeErrors:
    def test_none_data(self, meta):
        result = make_std(None, meta).compute()
        assert result["ok"] is False
        assert result["error"] is not None
        assert result["value"] is None

    def test_empty_list(self, meta):
        result = make_std([], meta).compute()
        assert result["ok"] is False

    def test_non_numeric_strings(self, meta):
        result = make_std(["a", "b", "c"], meta).compute()
        assert result["ok"] is False

    def test_mixed_strings_and_numbers(self, meta):
        result = make_std([1, "two", 3], meta).compute()
        assert result["ok"] is False

    def test_error_stat_id_preserved(self, meta):
        result = make_std(None, meta).compute()
        assert result["id"] == "standard_deviation"

    def test_error_result_keys(self, meta):
        result = make_std(None, meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())


# ===========================================================================
# Statistical correctness – parametrized
# ===========================================================================

class TestStatisticalCorrectness:
    @pytest.mark.parametrize("data,expected_std", [
        ([2, 4, 4, 4, 5, 5, 7, 9], 2.0),    # classic textbook example
        ([0, 0, 0, 0], 0.0),                  # constant
        ([1, -1], 1.0),                        # symmetric around 0
        ([10], 0.0),                           # single element
    ])
    def test_known_expected_values(self, data, expected_std, meta):
        result = make_std(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected_std, abs_tol=1e-9)
