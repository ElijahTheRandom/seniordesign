# test_spearman.py
# Tests for SpearmanCoefficient in seniordesign/methods/spearman.py
# Run from seniordesign/ root: pytest testsuite/test_spearman.py -v

import sys
import os
import math
import numpy as np
import pytest
from scipy.stats import spearmanr

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "methods"))
from spearman import SpearmanCoefficient


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def meta():
    return {"source": "test"}


def make_spearman(data, meta=None, params=None):
    return SpearmanCoefficient(data, meta or {"source": "test"}, params)


# ===========================================================================
# _applicable()
# ===========================================================================

class TestApplicable:
    def test_true_for_valid_2_col(self, meta):
        assert SpearmanCoefficient([[1, 2, 3], [4, 5, 6]], meta)._applicable() is None

    def test_false_for_none(self, meta):
        assert SpearmanCoefficient(None, meta)._applicable() is not None

    def test_false_for_single_column(self, meta):
        assert SpearmanCoefficient([[1, 2, 3]], meta)._applicable() is not None

    def test_false_for_unequal_lengths(self, meta):
        assert SpearmanCoefficient([[1, 2, 3], [4, 5]], meta)._applicable() is not None

    def test_false_for_empty_list(self, meta):
        assert SpearmanCoefficient([], meta)._applicable() is not None

    def test_true_for_two_points(self, meta):
        assert SpearmanCoefficient([[1, 2], [3, 4]], meta)._applicable() is None


# ===========================================================================
# compute() – normal cases
# ===========================================================================

class TestComputeNormal:
    def test_ok_true(self, meta):
        result = make_spearman([[1, 2, 3, 4], [5, 6, 7, 8]], meta).compute()
        assert result["ok"] is True

    def test_stat_id(self, meta):
        result = make_spearman([[1, 2, 3], [4, 5, 6]], meta).compute()
        assert result["id"] == "spearman"

    def test_value_is_float(self, meta):
        result = make_spearman([[1, 2, 3], [4, 5, 6]], meta).compute()
        assert isinstance(result["value"], float)

    def test_error_none_on_success(self, meta):
        result = make_spearman([[1, 2, 3], [4, 5, 6]], meta).compute()
        assert result["error"] is None

    def test_result_keys(self, meta):
        result = make_spearman([[1, 2, 3], [4, 5, 6]], meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())

    def test_perfect_positive_monotone(self, meta):
        """Perfectly monotone increasing data should give r = 1.0."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        result = make_spearman([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 1.0, abs_tol=1e-9)

    def test_perfect_negative_monotone(self, meta):
        """Perfectly monotone decreasing data should give r = -1.0."""
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]
        result = make_spearman([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], -1.0, abs_tol=1e-9)

    def test_matches_scipy_spearmanr(self, meta):
        """Result should match scipy.stats.spearmanr exactly."""
        rng = np.random.default_rng(seed=321)
        x = rng.normal(0, 1, 100).tolist()
        y = (0.8 * np.array(x) + rng.normal(0, 0.5, 100)).tolist()
        expected = float(spearmanr(x, y)[0])

        result = make_spearman([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_r_bounded_between_minus1_and_1(self, meta):
        rng = np.random.default_rng(seed=55)
        x = rng.uniform(0, 100, 50).tolist()
        y = rng.uniform(0, 100, 50).tolist()
        result = make_spearman([x, y], meta).compute()
        assert result["ok"] is True
        assert -1.0 <= result["value"] <= 1.0

    def test_symmetric(self, meta):
        """spearman(x, y) should equal spearman(y, x)."""
        x = [1, 3, 5, 7, 9]
        y = [2, 1, 4, 3, 5]
        r_xy = make_spearman([x, y], meta).compute()["value"]
        r_yx = make_spearman([y, x], meta).compute()["value"]
        assert math.isclose(r_xy, r_yx, rel_tol=1e-12)

    def test_nonlinear_but_monotone(self, meta):
        """Spearman captures monotone non-linear relationships (r should be high)."""
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        y = [v ** 3 for v in x]  # cubic, perfectly monotone
        result = make_spearman([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 1.0, abs_tol=1e-9)

    def test_difference_from_pearson_on_nonlinear(self, meta):
        """For non-linear monotone data, Spearman and Pearson may differ.
        Spearman should give 1.0; Pearson should be < 1.0."""
        from pearson import PearsonCoefficient
        x = list(range(1, 11))
        y = [v ** 2 for v in x]  # quadratic

        sp_result = make_spearman([x, y], meta).compute()
        pe_result = PearsonCoefficient([x, y], meta).compute()
        assert sp_result["value"] > pe_result["value"]


# ===========================================================================
# compute() – edge cases
# ===========================================================================

class TestComputeEdgeCases:
    def test_two_point_correlation(self, meta):
        result = make_spearman([[1.0, 2.0], [3.0, 5.0]], meta).compute()
        assert result["ok"] is True
        assert math.isclose(abs(result["value"]), 1.0, abs_tol=1e-9)

    def test_float_inputs(self, meta):
        x = [0.1, 0.2, 0.3, 0.4]
        y = [0.4, 0.3, 0.2, 0.1]
        expected = float(spearmanr(x, y)[0])
        result = make_spearman([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_tied_ranks(self, meta):
        """Tied values in ranks should be handled gracefully."""
        x = [1, 1, 2, 3, 3]
        y = [5, 6, 7, 8, 9]
        expected = float(spearmanr(x, y)[0])
        result = make_spearman([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_large_dataset(self, meta):
        rng = np.random.default_rng(seed=2025)
        x = rng.normal(0, 5, 10_000).tolist()
        y = (0.6 * np.array(x) + rng.normal(0, 2, 10_000)).tolist()
        expected = float(spearmanr(x, y)[0])
        result = make_spearman([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)


# ===========================================================================
# compute() – error handling
# ===========================================================================

class TestComputeErrors:
    def test_none_data(self, meta):
        result = make_spearman(None, meta).compute()
        assert result["ok"] is False
        assert result["error"] is not None
        assert result["value"] is None

    def test_single_column(self, meta):
        result = make_spearman([[1, 2, 3]], meta).compute()
        assert result["ok"] is False

    def test_unequal_lengths(self, meta):
        result = make_spearman([[1, 2, 3], [4, 5]], meta).compute()
        assert result["ok"] is False

    def test_empty_list(self, meta):
        result = make_spearman([], meta).compute()
        assert result["ok"] is False

    def test_non_numeric_strings(self, meta):
        result = make_spearman([["a", "b"], ["c", "d"]], meta).compute()
        assert result["ok"] is False

    def test_error_stat_id_preserved(self, meta):
        result = make_spearman(None, meta).compute()
        assert result["id"] == "spearman"

    def test_error_result_keys(self, meta):
        result = make_spearman(None, meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())
