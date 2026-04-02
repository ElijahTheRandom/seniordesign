# test_binomial.py
# Tests for the Binomial statistic class in seniordesign/methods/binomial.py
# Run from seniordesign/ root: pytest testsuite/test_binomial.py -v

import sys
import os
import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import binom

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "methods"))
from binomial import Binomial


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def meta():
    return {"source": "test"}


def make_binom(data, meta=None, params=None):
    return Binomial(data, meta or {"source": "test"}, params)


# ===========================================================================
# _applicable()
# ===========================================================================

class TestApplicable:
    def test_true_for_3_element_list(self, meta):
        assert Binomial([10, 0.5, 2], meta)._applicable() is True

    def test_true_for_4_element_list(self, meta):
        assert Binomial([10, 0.5, 2, 8], meta)._applicable() is True

    def test_false_for_none(self, meta):
        assert Binomial(None, meta)._applicable() is False

    def test_false_for_2_element_list(self, meta):
        # Requires at least 3 values (n, p, kMin)
        assert Binomial([10, 0.5], meta)._applicable() is False

    def test_false_for_empty_list(self, meta):
        assert Binomial([], meta)._applicable() is False

    def test_true_for_numpy_array(self, meta):
        assert Binomial(np.array([10, 0.5, 0, 10]), meta)._applicable() is True


# ===========================================================================
# compute() – normal cases
# ===========================================================================

class TestComputeNormal:
    def test_returns_dataframe(self, meta):
        """compute() should return a value that is a pandas DataFrame."""
        result = make_binom([10, 0.5, 0, 10], meta).compute()
        assert result["ok"] is True
        assert isinstance(result["value"], pd.DataFrame)

    def test_dataframe_columns(self, meta):
        """DataFrame must have exactly the 4 expected columns."""
        result = make_binom([10, 0.5, 0, 10], meta).compute()
        expected_cols = {"k", "P(X = k)", "P(X <= k)", "P(X >= k)"}
        assert set(result["value"].columns) == expected_cols

    def test_dataframe_row_count_with_kmax(self, meta):
        """Number of rows equals kMax - kMin + 1."""
        # n=10, p=0.5, kMin=2, kMax=5 → 4 rows
        result = make_binom([10, 0.5, 2, 5], meta).compute()
        assert len(result["value"]) == 4

    def test_dataframe_row_count_without_kmax(self, meta):
        """When kMax is omitted it defaults to n, so rows = n - kMin + 1."""
        # n=5, p=0.5, kMin=2 → kMax defaults to 5 → 4 rows
        result = make_binom([5, 0.5, 2], meta).compute()
        assert len(result["value"]) == 4

    def test_k_column_range(self, meta):
        """k column should span exactly kMin … kMax inclusive."""
        result = make_binom([10, 0.3, 1, 4], meta).compute()
        assert list(result["value"]["k"]) == [1, 2, 3, 4]

    def test_pmf_values_match_scipy(self, meta):
        """P(X = k) column should match scipy binom.pmf."""
        n, p, kMin, kMax = 10, 0.3, 0, 10
        result = make_binom([n, p, kMin, kMax], meta).compute()
        df = result["value"]
        k_arr = np.arange(kMin, kMax + 1)
        expected = binom.pmf(k_arr, n, p)
        np.testing.assert_allclose(df["P(X = k)"].values, expected, rtol=1e-9)

    def test_cdf_values_match_scipy(self, meta):
        """P(X <= k) column should match scipy binom.cdf."""
        n, p, kMin, kMax = 8, 0.6, 0, 8
        result = make_binom([n, p, kMin, kMax], meta).compute()
        df = result["value"]
        k_arr = np.arange(kMin, kMax + 1)
        expected = binom.cdf(k_arr, n, p)
        np.testing.assert_allclose(df["P(X <= k)"].values, expected, rtol=1e-9)

    def test_sf_values_match_scipy(self, meta):
        """P(X >= k) column should match scipy binom.sf(k-1)."""
        n, p, kMin, kMax = 8, 0.6, 0, 8
        result = make_binom([n, p, kMin, kMax], meta).compute()
        df = result["value"]
        k_arr = np.arange(kMin, kMax + 1)
        expected = binom.sf(k_arr - 1, n, p)
        np.testing.assert_allclose(df["P(X >= k)"].values, expected, rtol=1e-9)

    def test_stat_id(self, meta):
        result = make_binom([5, 0.5, 0, 5], meta).compute()
        assert result["id"] == "binomial"

    def test_error_none_on_success(self, meta):
        result = make_binom([5, 0.5, 0, 5], meta).compute()
        assert result["error"] is None

    def test_result_keys(self, meta):
        result = make_binom([5, 0.5, 0, 5], meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())

    def test_p_equals_zero(self, meta):
        """p=0 means P(X=0)=1 for any n; all other k should have pmf≈0."""
        result = make_binom([5, 0.0, 0, 5], meta).compute()
        assert result["ok"] is True
        df = result["value"]
        assert math.isclose(df.loc[df["k"] == 0, "P(X = k)"].values[0], 1.0)
        assert math.isclose(df.loc[df["k"] == 5, "P(X = k)"].values[0], 0.0)

    def test_p_equals_one(self, meta):
        """p=1 means P(X=n)=1; all other k should have pmf≈0."""
        n = 5
        result = make_binom([n, 1.0, 0, n], meta).compute()
        assert result["ok"] is True
        df = result["value"]
        assert math.isclose(df.loc[df["k"] == n, "P(X = k)"].values[0], 1.0)
        assert math.isclose(df.loc[df["k"] == 0, "P(X = k)"].values[0], 0.0)

    def test_numpy_array_input(self, meta):
        """Input as numpy array should still work."""
        result = make_binom(np.array([10, 0.5, 0, 10]), meta).compute()
        assert result["ok"] is True


# ===========================================================================
# compute() – edge cases
# ===========================================================================

class TestComputeEdgeCases:
    def test_single_k_value(self, meta):
        """kMin == kMax should return exactly one row."""
        result = make_binom([10, 0.5, 5, 5], meta).compute()
        assert result["ok"] is True
        assert len(result["value"]) == 1

    def test_large_n(self, meta):
        """n=1000 should still produce correct results (no overflow)."""
        result = make_binom([1000, 0.5, 490, 510], meta).compute()
        assert result["ok"] is True
        df = result["value"]
        assert len(df) == 21

    def test_kmin_zero(self, meta):
        """kMin=0 is a valid boundary condition."""
        result = make_binom([10, 0.4, 0, 10], meta).compute()
        assert result["ok"] is True
        assert result["value"]["k"].min() == 0

    def test_pmf_sums_to_one(self, meta):
        """PMF over all k from 0 to n should sum to 1."""
        n = 20
        result = make_binom([n, 0.3, 0, n], meta).compute()
        total = result["value"]["P(X = k)"].sum()
        assert math.isclose(total, 1.0, abs_tol=1e-9)


# ===========================================================================
# compute() – error handling
# ===========================================================================

class TestComputeErrors:
    def test_none_data(self, meta):
        result = make_binom(None, meta).compute()
        assert result["ok"] is False
        assert result["error"] is not None
        assert result["value"] is None

    def test_too_few_elements(self, meta):
        result = make_binom([10, 0.5], meta).compute()
        assert result["ok"] is False

    def test_p_out_of_range_high(self, meta):
        result = make_binom([10, 1.5, 0, 10], meta).compute()
        assert result["ok"] is False
        assert "probability" in result["error"].lower() or "p must" in result["error"].lower()

    def test_p_out_of_range_low(self, meta):
        result = make_binom([10, -0.1, 0, 10], meta).compute()
        assert result["ok"] is False

    def test_error_stat_id_preserved(self, meta):
        result = make_binom(None, meta).compute()
        assert result["id"] == "binomial"

    def test_error_result_keys(self, meta):
        result = make_binom(None, meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())
