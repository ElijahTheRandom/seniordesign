# test_percentile.py
# Tests for Percentile in seniordesign/methods/percentile.py
# Run from seniordesign/ root: pytest testsuite/test_percentile.py -v

import sys
import os
import math
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "methods"))
from percentile import Percentile


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def meta():
    return {"source": "test"}


def make_pct(data, meta=None, params=None):
    return Percentile(data, meta or {"source": "test"}, params)


# ===========================================================================
# _applicable()
# ===========================================================================

class TestApplicable:
    def test_true_for_valid_list(self, meta):
        assert Percentile([1, 2, 3], meta)._applicable() is True

    def test_false_for_none(self, meta):
        assert Percentile(None, meta)._applicable() is False

    def test_true_for_empty_list(self, meta):
        # _applicable only checks for None; empty list passes through to compute()
        assert Percentile([], meta)._applicable() is True

    def test_true_for_numpy_array(self, meta):
        assert Percentile(np.array([10, 20, 30]), meta)._applicable() is True


# ===========================================================================
# compute() – normal cases
# ===========================================================================

class TestComputeNormal:
    def test_ok_true(self, meta):
        result = make_pct([1, 2, 3, 4, 5], meta, [50]).compute()
        assert result["ok"] is True

    def test_stat_id(self, meta):
        result = make_pct([1, 2, 3], meta, [50]).compute()
        assert result["id"] == "percentile"

    def test_value_is_list(self, meta):
        """value should be a list of floats, one per requested percentile."""
        result = make_pct([1, 2, 3, 4, 5], meta, [25, 50, 75]).compute()
        assert isinstance(result["value"], list)
        assert len(result["value"]) == 3

    def test_error_none_on_success(self, meta):
        result = make_pct([1, 2, 3], meta, [50]).compute()
        assert result["error"] is None

    def test_result_keys(self, meta):
        result = make_pct([1, 2, 3], meta, [50]).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())

    def test_median_as_50th_percentile(self, meta):
        """50th percentile should equal numpy median."""
        data = [1, 2, 3, 4, 5]
        result = make_pct(data, meta, [50]).compute()
        expected = float(np.percentile(data, 50))
        assert result["ok"] is True
        assert math.isclose(result["value"][0], expected)

    def test_0th_percentile_is_min(self, meta):
        data = [10, 20, 30, 40, 50]
        result = make_pct(data, meta, [0]).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"][0], 10.0)

    def test_100th_percentile_is_max(self, meta):
        data = [10, 20, 30, 40, 50]
        result = make_pct(data, meta, [100]).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"][0], 50.0)

    def test_multiple_percentiles_order(self, meta):
        """Multiple percentiles should be returned in the same order as requested."""
        data = list(range(1, 101))  # 1..100
        result = make_pct(data, meta, [25, 50, 75]).compute()
        assert result["ok"] is True
        vals = result["value"]
        assert vals[0] < vals[1] < vals[2]

    def test_matches_numpy_percentile(self, meta):
        """Each returned value should match numpy.percentile exactly."""
        rng = np.random.default_rng(seed=42)
        data = rng.normal(50, 10, 1000).tolist()
        pcts = [10, 25, 50, 75, 90]
        expected = [float(np.percentile(data, p)) for p in pcts]

        result = make_pct(data, meta, pcts).compute()
        assert result["ok"] is True
        for got, exp in zip(result["value"], expected):
            assert math.isclose(got, exp, rel_tol=1e-9)

    def test_single_percentile_returns_list_of_one(self, meta):
        result = make_pct([5, 10, 15, 20], meta, [50]).compute()
        assert result["ok"] is True
        assert isinstance(result["value"], list)
        assert len(result["value"]) == 1

    def test_numpy_array_input(self, meta):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = make_pct(data, meta, [50]).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"][0], 3.0)

    def test_params_used_in_result(self, meta):
        """params_used is overwritten by the percentile array inside compute()."""
        # After compute() self.params is the numpy array of percentile values
        result = make_pct([1, 2, 3], meta, [25, 75]).compute()
        assert result["ok"] is True


# ===========================================================================
# compute() – edge cases
# ===========================================================================

class TestComputeEdgeCases:
    def test_single_element_data(self, meta):
        """Single-element dataset: any percentile returns that element."""
        result = make_pct([42], meta, [0, 50, 100]).compute()
        assert result["ok"] is True
        for val in result["value"]:
            assert math.isclose(val, 42.0)

    def test_all_same_values(self, meta):
        """All-identical data: every percentile equals that value."""
        result = make_pct([7, 7, 7, 7], meta, [25, 50, 75]).compute()
        assert result["ok"] is True
        for val in result["value"]:
            assert math.isclose(val, 7.0)

    def test_float_data(self, meta):
        data = [0.1, 0.5, 0.9, 1.3]
        expected = float(np.percentile(data, 50))
        result = make_pct(data, meta, [50]).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"][0], expected)

    def test_2d_numpy_array_flattened(self, meta):
        """2-D arrays should be flattened before percentile calculation."""
        data = np.array([[1, 2], [3, 4]])
        expected = float(np.percentile([1, 2, 3, 4], 50))
        result = make_pct(data, meta, [50]).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"][0], expected)

    def test_large_dataset(self, meta):
        rng = np.random.default_rng(seed=7)
        data = rng.normal(0, 1, 50_000).tolist()
        pcts = [1, 5, 25, 50, 75, 95, 99]
        result = make_pct(data, meta, pcts).compute()
        assert result["ok"] is True
        assert len(result["value"]) == len(pcts)


# ===========================================================================
# compute() – error handling
# ===========================================================================

class TestComputeErrors:
    def test_none_data(self, meta):
        result = make_pct(None, meta, [50]).compute()
        assert result["ok"] is False
        assert result["error"] is not None
        assert result["value"] is None

    def test_no_params_given(self, meta):
        """Empty params → no percentile values specified → error."""
        result = make_pct([1, 2, 3], meta, []).compute()
        assert result["ok"] is False
        assert result["error"] is not None

    def test_none_params_gives_error(self, meta):
        """None params → empty numpy array → no percentile values error."""
        result = make_pct([1, 2, 3], meta, None).compute()
        assert result["ok"] is False

    def test_non_numeric_data_strings(self, meta):
        result = make_pct(["a", "b", "c"], meta, [50]).compute()
        assert result["ok"] is False

    def test_error_stat_id_preserved(self, meta):
        result = make_pct(None, meta, [50]).compute()
        assert result["id"] == "percentile"

    def test_error_result_keys(self, meta):
        result = make_pct(None, meta, [50]).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())


# ===========================================================================
# Statistical correctness – parametrized
# ===========================================================================

class TestStatisticalCorrectness:
    @pytest.mark.parametrize("data,pct,expected", [
        ([1, 2, 3, 4, 5], [0], 1.0),
        ([1, 2, 3, 4, 5], [100], 5.0),
        ([1, 2, 3, 4, 5], [50], 3.0),
        ([10, 20, 30, 40], [25], 17.5),
        ([10, 20, 30, 40], [75], 32.5),
    ])
    def test_known_values(self, data, pct, expected, meta):
        result = make_pct(data, meta, pct).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"][0], expected, abs_tol=1e-9)
