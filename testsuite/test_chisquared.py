# test_chisquared.py
# Tests for the ChiSquared statistic class in seniordesign/methods/chisquared.py
# Run from seniordesign/ root: pytest testsuite/test_chisquared.py -v

import sys
import os
import math
import numpy as np
import pytest
from scipy.stats import chisquare

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "methods"))
from chisquared import ChiSquared


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def meta():
    return {"source": "test"}


def make_chi(data, meta=None, params=None):
    return ChiSquared(data, meta or {"source": "test"}, params)


# ===========================================================================
# _applicable()
# ===========================================================================

class TestApplicable:
    def test_true_for_flat_list(self, meta):
        assert ChiSquared([10, 20, 30], meta)._applicable() is None

    def test_true_for_2d_array(self, meta):
        assert ChiSquared([[10, 20], [10, 20]], meta)._applicable() is None

    def test_false_for_none(self, meta):
        assert ChiSquared(None, meta)._applicable() is not None

    def test_false_for_single_value(self, meta):
        # Chi-squared needs at least 2 categories
        assert ChiSquared([5], meta)._applicable() is not None

    def test_false_for_empty_list(self, meta):
        assert ChiSquared([], meta)._applicable() is not None

    def test_true_for_numpy_array(self, meta):
        assert ChiSquared(np.array([5, 10, 15]), meta)._applicable() is None


# ===========================================================================
# compute() – normal cases (1-D / uniform expected)
# ===========================================================================

class TestComputeNormal1D:
    def test_ok_true_for_valid_data(self, meta):
        result = make_chi([10, 20, 30], meta).compute()
        assert result["ok"] is True

    def test_stat_id(self, meta):
        result = make_chi([10, 20, 30], meta).compute()
        assert result["id"] == "chisquared"

    def test_error_none_on_success(self, meta):
        result = make_chi([10, 20, 30], meta).compute()
        assert result["error"] is None

    def test_value_is_float(self, meta):
        result = make_chi([10, 20, 30], meta).compute()
        assert isinstance(result["value"], float)

    def test_result_keys(self, meta):
        result = make_chi([10, 20, 30], meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())

    def test_uniform_observed_gives_zero_chi2(self, meta):
        """When all observed frequencies are equal, chi-squared against
        uniform expected should be 0 (or very close)."""
        data = [20, 20, 20, 20]
        result = make_chi(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0, abs_tol=1e-9)

    def test_matches_scipy_1d_uniform(self, meta):
        """1-D chi-squared value should match scipy.stats.chisquare against uniform."""
        observed = [16, 18, 16, 14, 12, 12]
        arr = np.array(observed, dtype=float)
        expected_val = float(chisquare(arr, f_exp=np.full_like(arr, arr.mean()))[0])

        result = make_chi(observed, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected_val, rel_tol=1e-9)


# ===========================================================================
# compute() – 2-D (observed + expected rows)
# ===========================================================================

class TestComputeNormal2D:
    def test_2d_array_observed_vs_expected(self, meta):
        """2-row input: row 0 = observed, row 1 = expected."""
        observed = [10, 20, 30]
        expected = [15, 15, 30]
        chi_ref = float(chisquare(observed, f_exp=expected)[0])

        result = make_chi([observed, expected], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], chi_ref, rel_tol=1e-9)

    def test_2d_equal_observed_expected_gives_zero(self, meta):
        """If observed == expected, chi-squared should be 0."""
        data = [[10, 20, 30], [10, 20, 30]]
        result = make_chi(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0, abs_tol=1e-9)

    def test_2d_numpy_array_input(self, meta):
        data = np.array([[5, 10, 15], [10, 10, 10]], dtype=float)
        chi_ref = float(chisquare(data[0], f_exp=data[1])[0])
        result = make_chi(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], chi_ref, rel_tol=1e-9)


# ===========================================================================
# compute() – edge cases
# ===========================================================================

class TestComputeEdgeCases:
    def test_two_categories(self, meta):
        """Minimum valid input: two categories."""
        result = make_chi([10, 20], meta).compute()
        assert result["ok"] is True

    def test_large_dataset(self, meta):
        """Chi-squared should handle large arrays without error."""
        rng = np.random.default_rng(seed=42)
        data = rng.integers(1, 100, size=200).tolist()
        result = make_chi(data, meta).compute()
        assert result["ok"] is True
        assert result["value"] >= 0.0

    def test_non_negative_chi_squared(self, meta):
        """Chi-squared statistic is always non-negative."""
        result = make_chi([5, 10, 15, 20, 25], meta).compute()
        assert result["ok"] is True
        assert result["value"] >= 0.0


# ===========================================================================
# compute() – error handling
# ===========================================================================

class TestComputeErrors:
    def test_none_data(self, meta):
        result = make_chi(None, meta).compute()
        assert result["ok"] is False
        assert result["error"] is not None
        assert result["value"] is None

    def test_empty_list(self, meta):
        result = make_chi([], meta).compute()
        assert result["ok"] is False

    def test_single_category(self, meta):
        result = make_chi([42], meta).compute()
        assert result["ok"] is False

    def test_non_numeric_strings(self, meta):
        result = make_chi(["a", "b", "c"], meta).compute()
        assert result["ok"] is False

    def test_error_stat_id_preserved(self, meta):
        result = make_chi(None, meta).compute()
        assert result["id"] == "chisquared"

    def test_error_result_keys(self, meta):
        result = make_chi(None, meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())


# ===========================================================================
# Statistical correctness – parametrized
# ===========================================================================

class TestStatisticalCorrectness:
    @pytest.mark.parametrize("observed,expected_chi", [
        ([10, 10, 10, 10], 0.0),          # uniform → chi=0
        ([20, 0, 0, 0], None),             # extreme: computed but not zero
    ])
    def test_known_values(self, observed, expected_chi, meta):
        result = make_chi(observed, meta).compute()
        assert result["ok"] is True
        if expected_chi is not None:
            assert math.isclose(result["value"], expected_chi, abs_tol=1e-9)
        else:
            assert result["value"] > 0
