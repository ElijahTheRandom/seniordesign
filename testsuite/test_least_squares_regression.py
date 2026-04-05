# test_least_squares_regression.py
# Tests for LeastSquaresRegression in seniordesign/methods/least_squares_regression.py
# Run from seniordesign/ root: pytest testsuite/test_least_squares_regression.py -v

import sys
import os
import math
import base64
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "methods"))
from least_squares_regression import LeastSquaresRegression


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def meta():
    return {"source": "test"}


def make_lsr(data, meta=None, params=None):
    return LeastSquaresRegression(data, meta or {"source": "test"}, params)


# Perfect-line dataset: y = 2x + 3
PERFECT_X = [1.0, 2.0, 3.0, 4.0, 5.0]
PERFECT_Y = [5.0, 7.0, 9.0, 11.0, 13.0]  # y = 2x + 3


# ===========================================================================
# _applicable()
# ===========================================================================

class TestApplicable:
    def test_true_for_valid_2_col(self, meta):
        assert LeastSquaresRegression([[1, 2, 3], [4, 5, 6]], meta)._applicable() is True

    def test_false_for_none(self, meta):
        assert LeastSquaresRegression(None, meta)._applicable() is False

    def test_false_for_single_column(self, meta):
        assert LeastSquaresRegression([[1, 2, 3]], meta)._applicable() is False

    def test_false_for_unequal_length_columns(self, meta):
        assert LeastSquaresRegression([[1, 2, 3], [4, 5]], meta)._applicable() is False

    def test_false_for_empty_data(self, meta):
        assert LeastSquaresRegression([], meta)._applicable() is False

    def test_true_for_two_points(self, meta):
        assert LeastSquaresRegression([[1, 2], [3, 4]], meta)._applicable() is True


# ===========================================================================
# compute() – normal cases
# ===========================================================================

class TestComputeNormal:
    def test_ok_true(self, meta):
        result = make_lsr([PERFECT_X, PERFECT_Y], meta).compute()
        assert result["ok"] is True

    def test_stat_id(self, meta):
        result = make_lsr([PERFECT_X, PERFECT_Y], meta).compute()
        assert result["id"] == "least_squares_regression"

    def test_error_none_on_success(self, meta):
        result = make_lsr([PERFECT_X, PERFECT_Y], meta).compute()
        assert result["error"] is None

    def test_result_keys(self, meta):
        result = make_lsr([PERFECT_X, PERFECT_Y], meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())

    def test_value_is_dict(self, meta):
        """value should be a dict containing regression outputs."""
        result = make_lsr([PERFECT_X, PERFECT_Y], meta).compute()
        assert isinstance(result["value"], dict)

    def test_value_dict_keys(self, meta):
        expected_keys = {"slope", "intercept", "r_squared", "equation", "chart"}
        result = make_lsr([PERFECT_X, PERFECT_Y], meta).compute()
        assert expected_keys == set(result["value"].keys())

    def test_slope_perfect_line(self, meta):
        """Slope of y=2x+3 should be exactly 2."""
        result = make_lsr([PERFECT_X, PERFECT_Y], meta).compute()
        assert math.isclose(result["value"]["slope"], 2.0, rel_tol=1e-9)

    def test_intercept_perfect_line(self, meta):
        """Intercept of y=2x+3 should be exactly 3."""
        result = make_lsr([PERFECT_X, PERFECT_Y], meta).compute()
        assert math.isclose(result["value"]["intercept"], 3.0, rel_tol=1e-9)

    def test_r_squared_perfect_line(self, meta):
        """R² of a perfect linear relationship should be 1.0."""
        result = make_lsr([PERFECT_X, PERFECT_Y], meta).compute()
        assert math.isclose(result["value"]["r_squared"], 1.0, abs_tol=1e-9)

    def test_equation_string_format(self, meta):
        """Equation string should start with 'y ='."""
        result = make_lsr([PERFECT_X, PERFECT_Y], meta).compute()
        assert result["value"]["equation"].startswith("y =")

    def test_chart_is_base64_string(self, meta):
        """chart field should be a non-empty base64-decodable string."""
        result = make_lsr([PERFECT_X, PERFECT_Y], meta).compute()
        chart = result["value"]["chart"]
        assert isinstance(chart, str) and len(chart) > 0
        # Verify it's valid base64 (will raise if not)
        decoded = base64.b64decode(chart)
        # PNG magic bytes: 0x89 50 4E 47
        assert decoded[:4] == b'\x89PNG'

    def test_slope_negative(self, meta):
        """Negative slope should be computed correctly."""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [10.0, 8.0, 6.0, 4.0, 2.0]  # y = -2x + 12
        result = make_lsr([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"]["slope"], -2.0, rel_tol=1e-9)

    def test_matches_numpy_polyfit(self, meta):
        """Slope and intercept should match numpy.polyfit(x, y, 1) directly."""
        rng = np.random.default_rng(seed=42)
        x = rng.uniform(0, 10, 50).tolist()
        y = (2.5 * np.array(x) + rng.normal(0, 0.5, 50)).tolist()
        slope_ref, intercept_ref = np.polyfit(x, y, 1)

        result = make_lsr([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"]["slope"], float(slope_ref), rel_tol=1e-9)
        assert math.isclose(result["value"]["intercept"], float(intercept_ref), rel_tol=1e-9)


# ===========================================================================
# compute() – edge cases
# ===========================================================================

class TestComputeEdgeCases:
    def test_two_point_regression(self, meta):
        """Two points define a perfect line; R² should be 1."""
        result = make_lsr([[1.0, 2.0], [3.0, 5.0]], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"]["r_squared"], 1.0, abs_tol=1e-9)

    def test_horizontal_line(self, meta):
        """All y values equal → slope ≈ 0, R² = 0 (ss_tot = 0 branch)."""
        x = [1.0, 2.0, 3.0, 4.0]
        y = [5.0, 5.0, 5.0, 5.0]
        result = make_lsr([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"]["slope"], 0.0, abs_tol=1e-9)
        assert math.isclose(result["value"]["r_squared"], 0.0, abs_tol=1e-9)

    def test_large_dataset(self, meta):
        """Regression on 1,000-point dataset should succeed without errors."""
        rng = np.random.default_rng(seed=7)
        x = rng.uniform(-100, 100, 1000).tolist()
        y = (3.0 * np.array(x) - 7.0 + rng.normal(0, 1, 1000)).tolist()
        result = make_lsr([x, y], meta).compute()
        assert result["ok"] is True
        # Slope should be close to 3
        assert math.isclose(result["value"]["slope"], 3.0, abs_tol=0.1)

    def test_negative_x_values(self, meta):
        x = [-3.0, -2.0, -1.0, 0.0, 1.0]
        y = [-5.0, -3.0, -1.0, 1.0, 3.0]  # y = 2x + 1
        result = make_lsr([x, y], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"]["slope"], 2.0, rel_tol=1e-9)


# ===========================================================================
# compute() – error handling
# ===========================================================================

class TestComputeErrors:
    def test_none_data(self, meta):
        result = make_lsr(None, meta).compute()
        assert result["ok"] is False
        assert result["error"] is not None
        assert result["value"] is None

    def test_single_column(self, meta):
        result = make_lsr([[1, 2, 3]], meta).compute()
        assert result["ok"] is False

    def test_unequal_length_columns(self, meta):
        result = make_lsr([[1, 2, 3], [4, 5]], meta).compute()
        assert result["ok"] is False

    def test_empty_data(self, meta):
        result = make_lsr([], meta).compute()
        assert result["ok"] is False

    def test_non_numeric_strings(self, meta):
        result = make_lsr([["a", "b"], ["c", "d"]], meta).compute()
        assert result["ok"] is False

    def test_error_stat_id_preserved(self, meta):
        result = make_lsr(None, meta).compute()
        assert result["id"] == "least_squares_regression"

    def test_error_result_keys(self, meta):
        result = make_lsr(None, meta).compute()
        assert {"id", "ok", "value", "error", "loss_of_precision", "params_used"} == set(result.keys())
