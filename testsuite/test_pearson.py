# test_pearson.py
# Tests for PearsonCoefficient in seniordesign/methods/pearson.py
# Run from seniordesign/ root: pytest testsuite/test_pearson.py -v

import sys
import os
import math
import numpy as np
import pytest
from scipy.stats import pearsonr

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "methods"))
from pearson import PearsonCoefficient


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def meta():
    return {"source": "test"}


def make_pearson(data, meta=None, params=None):
    return PearsonCoefficient(data, meta or {"source": "test"}, params)


# ===========================================================================
# _applicable()
# ===========================================================================

class TestApplicable:
    def test_true_for_valid_2_col(self, meta):
        assert PearsonCoefficient([[1, 2, 3], [4, 5, 6]], meta)._applicable() is None

    def test_false_for_none(self, meta):
        assert PearsonCoefficient(None, meta)._applicable() is not None

    def test_false_for_single_column(self, meta):
        assert PearsonCoefficient([[1, 2, 3]], meta)._applicable() is not None

    def test_false_for_unequal_lengths(self, meta):
        assert PearsonCoefficient([[1, 2, 3], [4, 5]], meta)._applicable() is not None

    def test_false_for_empty_list(self, meta):
        assert PearsonCoefficient([], meta)._applicable() is not None

    def test_true_for_two_points(self, meta):
        assert PearsonCoefficient([[1, 2], [3, 4]], meta)._applicable() is None


# ===========================================================================
# compute() – normal cases
# ===========================================================================

class TestComputeNormal:
    def test_ok_true(self, meta):
        result = make_pearson([[1, 2, 3], [4, 5, 6]], meta).compute()
        assert result["ok"] is True

    def test_stat_id(self, meta):
        result = make_pearson([[1, 2, 3], [4, 5, 6]], meta).compute()
        assert result["id"] == "pearson"

    def test_value_is_float(self, meta):
        result = make_pearson([[1, 2, 3], [4, 5, 6]], meta).compute()
        assert isinstance(result["value"], float)

    def test_error_none_on_success(self, meta):
        result = make_pearson([[1, 2, 3], [4, 5, 6]], meta).compute()
        assert result["error"] is None

    def test_result_keys(self, meta):
        result = make_pearson([[1, 2, 3], [4, 5, 6]], meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())

    def test_perfect_positive_correlation(self, meta):
        """Perfectly correlated data should give r = 1.0."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        result = make_pearson([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 1.0, abs_tol=1e-9)

    def test_perfect_negative_correlation(self, meta):
        """Perfectly anti-correlated data should give r = -1.0."""
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]
        result = make_pearson([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], -1.0, abs_tol=1e-9)

    def test_no_correlation(self, meta):
        """Independent data should have r close to 0."""
        # Hand-crafted uncorrelated pair
        x = [1, 2, 3, 4]
        y = [2, 4, 1, 3]   # mean=3, no linear trend
        result = make_pearson([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0, abs_tol=1e-9)

    def test_matches_scipy_pearsonr(self, meta):
        """Result should match scipy.stats.pearsonr exactly."""
        rng = np.random.default_rng(seed=123)
        x = rng.normal(0, 1, 100).tolist()
        y = (0.7 * np.array(x) + rng.normal(0, 0.5, 100)).tolist()
        expected = float(pearsonr(x, y)[0])

        result = make_pearson([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_r_bounded_between_minus1_and_1(self, meta):
        """Pearson r is always in [-1, 1]."""
        rng = np.random.default_rng(seed=77)
        x = rng.uniform(0, 100, 50).tolist()
        y = rng.uniform(0, 100, 50).tolist()
        result = make_pearson([x, y], meta).compute()
        assert result["ok"] is True
        assert -1.0 <= result["value"] <= 1.0

    def test_symmetric(self, meta):
        """pearson(x, y) should equal pearson(y, x)."""
        x = [1, 3, 5, 7, 9]
        y = [2, 4, 3, 8, 6]
        r_xy = make_pearson([x, y], meta).compute()["value"]
        r_yx = make_pearson([y, x], meta).compute()["value"]
        assert math.isclose(r_xy, r_yx, rel_tol=1e-12)


# ===========================================================================
# compute() – edge cases
# ===========================================================================

class TestComputeEdgeCases:
    def test_two_point_correlation(self, meta):
        """Two points always define r = ±1."""
        result = make_pearson([[1.0, 2.0], [3.0, 5.0]], meta).compute()
        assert result["ok"] is True
        assert math.isclose(abs(result["value"]), 1.0, abs_tol=1e-9)

    def test_float_inputs(self, meta):
        x = [0.1, 0.2, 0.3]
        y = [0.4, 0.5, 0.6]
        expected = float(pearsonr(x, y)[0])
        result = make_pearson([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_large_dataset(self, meta):
        rng = np.random.default_rng(seed=2025)
        x = rng.normal(0, 5, 10_000).tolist()
        y = (0.9 * np.array(x) + rng.normal(0, 1, 10_000)).tolist()
        expected = float(pearsonr(x, y)[0])
        result = make_pearson([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)


# ===========================================================================
# compute() – error handling
# ===========================================================================

class TestComputeErrors:
    def test_none_data(self, meta):
        result = make_pearson(None, meta).compute()
        assert result["ok"] is False
        assert result["error"] is not None
        assert result["value"] is None

    def test_single_column(self, meta):
        result = make_pearson([[1, 2, 3]], meta).compute()
        assert result["ok"] is False

    def test_unequal_lengths(self, meta):
        result = make_pearson([[1, 2, 3], [4, 5]], meta).compute()
        assert result["ok"] is False

    def test_empty_list(self, meta):
        result = make_pearson([], meta).compute()
        assert result["ok"] is False

    def test_non_numeric_strings(self, meta):
        result = make_pearson([["a", "b"], ["c", "d"]], meta).compute()
        assert result["ok"] is False

    def test_error_stat_id_preserved(self, meta):
        result = make_pearson(None, meta).compute()
        assert result["id"] == "pearson"

    def test_error_result_keys(self, meta):
        result = make_pearson(None, meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())


# ===========================================================================
# Statistical correctness – parametrized
# ===========================================================================

class TestStatisticalCorrectness:
    @pytest.mark.parametrize("x,y,expected_r", [
        ([1, 2, 3, 4, 5], [2, 4, 6, 8, 10], 1.0),   # perfect positive
        ([1, 2, 3, 4, 5], [10, 8, 6, 4, 2], -1.0),  # perfect negative
        ([1, 2, 3, 4], [2, 4, 1, 3], 0.0),            # zero correlation
    ])
    def test_known_expected_r(self, x, y, expected_r, meta):
        result = make_pearson([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected_r, abs_tol=1e-9)
