"""Check the worker-facing contract for each possible exit from HiGHS."""

import pickle
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.optimize import OptimizeResult
from scipy.sparse import csr_matrix

from mathagent.core.lp_types import (
    Constraint,
    Problem,
    SolveOptions,
    SolveStatus,
    Variable,
)
from mathagent.solvers import lp_backend, solve


@pytest.fixture
def model():
    return Problem(
        (Variable("甲", "批", 0, 2),),
        [3],
        [[1]],
        (Constraint("机时", "<=", "小时"),),
        [4],
        "max",
        7,
        "万元",
    )


def test_real_solver_across_worker_serialization(model):
    result = pickle.loads(pickle.dumps(solve(pickle.loads(pickle.dumps(model)))))
    assert result.solve_status is SolveStatus.OPTIMAL
    assert result.values == {"甲": pytest.approx(2.0)}
    assert result.objective == pytest.approx(13.0)
    assert result.objective_unit == "万元"
    assert result.metrics.method == "highs-ds"
    assert result.metrics.backend_version
    assert result.metrics.raw_status == 0
    assert result.metrics.raw_message
    assert result.metrics.iterations is not None
    assert result.metrics.compile_seconds > 0
    assert result.metrics.solve_seconds > 0
    assert result.metrics.verify_seconds > 0


@pytest.mark.parametrize(
    "seconds", [0, -1, float("nan"), float("inf"), True, "5", 10**400]
)
def test_bad_limit_is_locatable(model, seconds):
    result = solve(model, SolveOptions(seconds))
    assert result.solve_status is SolveStatus.INVALID_INPUT
    assert result.issues[0].field == "time_limit_seconds"
    assert result.objective is None


@pytest.mark.parametrize(
    ("code", "success", "expected"),
    [
        (1, False, SolveStatus.LIMIT_REACHED),
        (2, False, SolveStatus.INFEASIBLE),
        (3, False, SolveStatus.UNBOUNDED),
        (4, False, SolveStatus.NUMERICAL_FAILURE),
        (99, False, SolveStatus.NUMERICAL_FAILURE),
        (None, True, SolveStatus.NUMERICAL_FAILURE),
        (False, True, SolveStatus.NUMERICAL_FAILURE),
        (0, False, SolveStatus.NUMERICAL_FAILURE),
        (3, True, SolveStatus.NUMERICAL_FAILURE),
    ],
)
def test_status_mapping_suppresses_stale_candidates(
    monkeypatch, model, code, success, expected
):
    def backend(c, **kwargs):
        np.testing.assert_allclose(c, [-3])
        np.testing.assert_allclose(kwargs["bounds"], [[0, 2]])
        assert kwargs["method"] == "highs-ds"
        assert kwargs["options"]["time_limit"] == pytest.approx(2.5)
        return OptimizeResult(
            status=code, success=success, message="raw", nit=-1, x=[2], fun=-6
        )

    monkeypatch.setattr(lp_backend, "linprog", backend)
    result = solve(model, SolveOptions(2.5))
    assert result.solve_status is expected
    assert result.objective is None
    assert not result.values
    assert result.metrics.iterations is None
    assert result.metrics.raw_message == "raw"


def test_invalid_input_skips_backend_and_precheck_knows_zero_iterations(
    monkeypatch, model
):
    monkeypatch.setattr(
        lp_backend, "linprog", lambda *a, **kw: pytest.fail("unexpected backend call")
    )
    result = solve(replace(model, variables=(Variable("甲", lower=2, upper=1),)))
    assert result.solve_status is SolveStatus.INFEASIBLE
    assert result.metrics.iterations == 0
    assert result.metrics.raw_status is None
    invalid = solve(replace(model, objective=[1, 2]))
    assert invalid.solve_status is SolveStatus.INVALID_INPUT
    assert invalid.metrics.iterations is None


def test_backend_exception_is_structured(monkeypatch, model):
    def failing(*args, **kwargs):
        raise RuntimeError("unavailable")

    monkeypatch.setattr(lp_backend, "linprog", failing)
    result = solve(model)
    assert result.solve_status is SolveStatus.NUMERICAL_FAILURE
    assert result.metrics.raw_message == "unavailable"
    assert result.objective is None


def test_reports_false_success_from_backend(monkeypatch, model):
    raw = {"status": 0, "success": True, "message": "done", "x": [5.0], "fun": -15.0}
    monkeypatch.setattr(
        lp_backend, "linprog", lambda *a, **kw: SimpleNamespace(get=raw.get)
    )
    result = solve(model)
    assert result.solve_status is SolveStatus.NUMERICAL_FAILURE
    assert result.objective is None
    assert not result.values
    assert any(issue.entity_id in {"机时", "甲"} for issue in result.issues)
    assert result.metrics.raw_status == 0


def test_native_model_error_is_not_a_mathematical_infeasibility(monkeypatch, model):
    raw = OptimizeResult(
        status=2, success=False, message="(HiGHS Status 2: Model error)"
    )
    monkeypatch.setattr(lp_backend, "linprog", lambda *a, **kw: raw)
    assert solve(model).solve_status is SolveStatus.NUMERICAL_FAILURE


@pytest.mark.parametrize("factory", [np.array, csr_matrix])
@pytest.mark.parametrize("sense", ["<=", "="])
@pytest.mark.parametrize("coef", [2e15, 1e-10])
def test_rescale_extreme_constraints_in_original_units(model, factory, sense, coef):
    original = factory([[coef]])
    p = replace(
        model, matrix=original, constraints=(Constraint("capacity", sense),), rhs=[coef]
    )
    result = solve(p)
    assert result.solve_status is SolveStatus.OPTIMAL
    assert result.values["甲"] == pytest.approx(1)
    assert result.diagnostics[0].actual == pytest.approx(coef, rel=1e-14, abs=0)
    np.testing.assert_array_equal(original @ np.ones(1), [coef])


@pytest.mark.parametrize("coefficient", [1e-14, 1e20])
def test_rescale_objective_and_restore_units(model, coefficient):
    result = solve(replace(model, objective=[coefficient], constant=0))
    assert result.solve_status is SolveStatus.OPTIMAL
    assert result.values["甲"] == pytest.approx(2)
    assert result.objective == pytest.approx(2 * coefficient, rel=1e-14, abs=0)


@pytest.mark.parametrize(
    ("objective", "matrix", "rhs", "variables", "code"),
    [
        ([1], [[1]], [1e21], (Variable("v"),), "unsafe_row_scale"),
        ([1], [[1]], [1], (Variable("v", upper=1e21),), "unsafe_bound_scale"),
        ([1, 1], [[1, 1e-12]], [1], (Variable("a"), Variable("b")), "unsafe_row_scale"),
        (
            [1e-18, 1],
            [[1, 2]],
            [1],
            (Variable("a"), Variable("b")),
            "unsafe_objective_scale",
        ),
    ],
)
def test_extreme_units_cannot_generate_false_business_status(
    objective, matrix, rhs, variables, code
):
    p = Problem(
        variables, objective, matrix, (Constraint("capacity", "<="),), rhs, "max"
    )
    result = solve(p)
    assert result.solve_status is SolveStatus.NUMERICAL_FAILURE
    assert result.objective is None and result.metrics.raw_status is None
    assert result.issues[0].code == code


def test_constant_row_with_large_rhs_preserves_sign(model):
    infeasible = replace(model, matrix=[[0]], rhs=[-1e21])
    assert solve(infeasible).solve_status is SolveStatus.INFEASIBLE
