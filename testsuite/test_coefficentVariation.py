# test_coefficentVariation.py
# Tests for CoefficientVariation (and legacy alias CoefficentVariation)
# in seniordesign/methods/coefficentVariation.py
# Run from seniordesign/ root: pytest testsuite/test_coefficentVariation.py -v

import sys
import os
import math
import numpy as np
import pytest
import types
from scipy.stats import variation

# Stub the missing class_templates dependency
_stub = types.ModuleType("class_templates")
_stub.message_structure = object
sys.modules.setdefault("class_templates", _stub)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "methods"))
from coefficentVariation import CoefficientVariation, CoefficentVariation


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def meta():
    return {"source": "test"}


def make_cv(data, meta=None, params=None):
    return CoefficientVariation(data, meta or {"source": "test"}, params)


# ===========================================================================
# _applicable()
# ===========================================================================

class TestApplicable:
    def test_true_for_positive_data(self, meta):
        assert CoefficientVariation([1, 2, 3], meta)._applicable() is True

    def test_false_for_none(self, meta):
        assert CoefficientVariation(None, meta)._applicable() is False

    def test_false_for_empty_list(self, meta):
        assert CoefficientVariation([], meta)._applicable() is False

    def test_false_when_mean_is_zero(self, meta):
        # CV is undefined when mean = 0
        assert CoefficientVariation([-1, 0, 1], meta)._applicable() is False

    def test_false_for_non_numeric_strings(self, meta):
        assert CoefficientVariation(["a", "b"], meta)._applicable() is False

    def test_true_for_numpy_array(self, meta):
        assert CoefficientVariation(np.array([10, 20, 30]), meta)._applicable() is True


# ===========================================================================
# compute() – normal cases
# ===========================================================================

class TestComputeNormal:
    def test_ok_true_for_valid_data(self, meta):
        result = make_cv([1, 2, 3, 4, 5], meta).compute()
        assert result["ok"] is True

    def test_stat_id(self, meta):
        result = make_cv([1, 2, 3], meta).compute()
        assert result["id"] == "coefficient_variation"

    def test_value_is_float(self, meta):
        result = make_cv([10, 20, 30], meta).compute()
        assert isinstance(result["value"], float)

    def test_error_none_on_success(self, meta):
        result = make_cv([10, 20, 30], meta).compute()
        assert result["error"] is None

    def test_result_keys(self, meta):
        result = make_cv([1, 2, 3], meta).compute()
        assert {"id", "ok", "value", "error", "loss_precision", "params_used"} == set(result.keys())

    def test_matches_scipy_variation(self, meta):
        """CV should match scipy.stats.variation (std/mean)."""
        data = [10, 20, 30, 40, 50]
        expected = float(variation(np.array(data, dtype=float)))
        result = make_cv(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_identical_values_cv_is_zero(self, meta):
        """CV of constant data should be 0 (no variation)."""
        result = make_cv([5, 5, 5, 5], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0, abs_tol=1e-9)

    def test_params_passed_through(self, meta):
        params = {"ddof": 1}
        result = make_cv([1, 2, 3], meta, params).compute()
        assert result["params_used"] == params

    def test_numpy_array_input(self, meta):
        data = np.array([4.0, 8.0, 12.0, 16.0])
        expected = float(variation(data))
        result = make_cv(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_large_dataset(self, meta):
        """CV on a large seeded dataset should match scipy reference."""
        rng = np.random.default_rng(seed=99)
        data = (rng.random(10_000) + 1.0).tolist()  # all positive, mean ≠ 0
        expected = float(variation(np.array(data, dtype=float)))
        result = make_cv(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)


# ===========================================================================
# compute() – edge cases
# ===========================================================================

class TestComputeEdgeCases:
    def test_single_element(self, meta):
        """Single-element list: std=0, mean>0 → CV=0."""
        result = make_cv([7], meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], 0.0, abs_tol=1e-9)

    def test_two_elements(self, meta):
        data = [3, 7]
        expected = float(variation(np.array(data, dtype=float)))
        result = make_cv(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_all_positive_floats(self, meta):
        data = [0.1, 0.2, 0.3, 0.4]
        expected = float(variation(np.array(data, dtype=float)))
        result = make_cv(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)

    def test_2d_numpy_array_flattened(self, meta):
        """2-D numpy arrays should be flattened before CV calculation."""
        data = np.array([[1, 2], [3, 4]])
        expected = float(variation(data.flatten().astype(float)))
        result = make_cv(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)


# ===========================================================================
# compute() – error handling
# ===========================================================================

class TestComputeErrors:
    def test_none_data(self, meta):
        result = make_cv(None, meta).compute()
        assert result["ok"] is False
        assert result["error"] is not None
        assert result["value"] is None

    def test_empty_list(self, meta):
        result = make_cv([], meta).compute()
        assert result["ok"] is False

    def test_mean_zero_data(self, meta):
        # [-2, -1, 0, 1, 2] has mean 0 → CV undefined
        result = make_cv([-2, -1, 0, 1, 2], meta).compute()
        assert result["ok"] is False
        assert result["error"] is not None

    def test_non_numeric_strings(self, meta):
        result = make_cv(["x", "y"], meta).compute()
        assert result["ok"] is False

    def test_error_stat_id_preserved(self, meta):
        result = make_cv(None, meta).compute()
        assert result["id"] == "coefficient_variation"

    def test_error_result_keys(self, meta):
        result = make_cv(None, meta).compute()
        assert {"id", "ok", "value", "error", "loss_precision", "params_used"} == set(result.keys())


# ===========================================================================
# Backwards-compatibility alias
# ===========================================================================

class TestLegacyAlias:
    def test_misspelled_alias_exists(self):
        """CoefficentVariation (old misspelling) should still be importable."""
        assert CoefficentVariation is CoefficientVariation

    def test_alias_computes_correctly(self, meta):
        data = [10, 20, 30]
        result = CoefficentVariation(data, meta).compute()
        assert result["ok"] is True
        expected = float(variation(np.array(data, dtype=float)))
        assert math.isclose(result["value"], expected, rel_tol=1e-9)


# ===========================================================================
# Statistical correctness – parametrized
# ===========================================================================

class TestStatisticalCorrectness:
    @pytest.mark.parametrize("data", [
        [1, 2, 3, 4, 5],
        [100, 150, 200],
        [0.5, 1.0, 1.5, 2.0],
        [10, 10, 10, 20],
    ])
    def test_matches_scipy_parametrized(self, data, meta):
        expected = float(variation(np.array(data, dtype=float)))
        result = make_cv(data, meta).compute()
        assert result["ok"] is True
        assert math.isclose(result["value"], expected, rel_tol=1e-9)
