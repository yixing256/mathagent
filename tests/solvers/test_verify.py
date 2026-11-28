from dataclasses import replace

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from mathagent.core.lp_types import Constraint, Problem, Variable
from mathagent.core.tolerance import ATOL, RTOL
from mathagent.solvers.lp_compile import compile_problem
from mathagent.solvers.lp_verify import verify


def model() -> Problem:
    return Problem(
        variables=(Variable("乙", "批", -1, 3), Variable("甲", "批", None, 2)),
        objective=(2, 3),
        matrix=[[1, 1], [2, 1], [-1, 1]],
        constraints=(
            Constraint("机时", "<=", "小时"),
            Constraint("订单", ">=", "件"),
            Constraint("平衡", "=", "批"),
        ),
        rhs=(4, 5, 0),
        direction="max",
        constant=7,
        objective_unit="万元",
    )


@pytest.mark.parametrize("sparse", [False, True])
def test_reports_physical_slack_and_signed_residual(sparse: bool) -> None:
    p = model()
    if sparse:
        p = replace(p, matrix=csr_matrix(p.matrix))
    result = verify(p, compile_problem(p), [2.0, 2.0], -10.0)
    assert not result.issues
    assert result.values == pytest.approx({"甲": 2, "乙": 2})
    assert result.objective == pytest.approx(17)
    assert result.max_violation == pytest.approx(0)
    rows = {(d.entity_id, d.kind): d for d in result.diagnostics}
    assert len(rows) == 6
    lower = rows["乙", "lower_bound"]
    assert (lower.actual, lower.limit, lower.slack) == pytest.approx((2, -1, 3))
    assert rows["乙", "upper_bound"].slack == pytest.approx(1)
    assert rows["乙", "upper_bound"].unit == "批"
    orders = rows["订单", "constraint"]
    assert (orders.limit, orders.actual, orders.slack) == pytest.approx((5, 6, 1))
    assert orders.residual is None
    balance = rows["平衡", "constraint"]
    assert balance.slack is None
    assert balance.residual == pytest.approx(0)


def test_rejects_candidate_and_identifies_each_broken_entity() -> None:
    p = model()
    result = verify(p, compile_problem(p), [-2, 3], -5)
    assert result.values == {}
    assert result.objective is None
    assert {(e.entity_id, e.field, e.row, e.column) for e in result.issues} == {
        ("订单", "constraints", 1, None),
        ("平衡", "constraints", 2, None),
        ("乙", "lower_bound", None, 0),
        ("甲", "upper_bound", None, 1),
    }
    assert result.max_violation == pytest.approx(6)
    balance = next(d for d in result.diagnostics if d.entity_id == "平衡")
    assert (balance.residual, balance.violation) == pytest.approx((5, 5))
    opposite = verify(p, compile_problem(p), [3, 2], -12)
    assert opposite.diagnostics[2].residual == pytest.approx(-1)
    assert opposite.diagnostics[0].slack == pytest.approx(-1)


@pytest.mark.parametrize(
    "candidate",
    [
        None,
        [2],
        [[2, 2]],
        [[2], [2]],
        [np.inf, 2],
        [np.nan, 2],
        [1j, 2],
        ["2", 2],
        [[2], [2, 4]],
    ],
)
def test_rejects_malformed_backend_candidate(candidate: object) -> None:
    p = model()
    result = verify(p, compile_problem(p), candidate, -10)
    assert result.issues[0].field == "backend.x"
    assert (
        not result.values and result.objective is None and result.max_violation is None
    )


@pytest.mark.parametrize("bad", [np.nan, np.inf, 2j, 2 + 0j, "2"])
def test_bad_candidate_value_identifies_variable(bad: object) -> None:
    p = model()
    result = verify(p, compile_problem(p), [1.0, bad], -10)
    assert (result.issues[0].column, result.issues[0].entity_id) == (1, "甲")


def test_wrong_candidate_shape_and_object_dtype_are_distinct() -> None:
    p = model()
    compiled = compile_problem(p)
    result = verify(p, compiled, [[1.0], [2.0]], -10)
    assert result.issues[0].code == "invalid_candidate_shape"
    assert "(2, 1)" in result.issues[0].message
    assert result.issues[0].column is None
    unsupported = verify(p, compiled, np.array([1.0, 2.0], dtype=object), -10)
    assert unsupported.issues[0].code == "invalid_candidate_dtype"


@pytest.mark.parametrize("bad_fun", [None, [], [0], np.nan, np.inf, 0j, "0", True])
def test_requires_finite_real_backend_objective(bad_fun: object) -> None:
    p = model()
    result = verify(p, compile_problem(p), [2, 2], bad_fun)
    assert result.issues[0].field == "backend.fun"
    assert not result.values and result.objective is None


def test_large_constant_does_not_mask_wrong_linear_objective() -> None:
    p = replace(model(), constant=1e30)
    result = verify(p, compile_problem(p), [2, 2], 10.0)
    assert result.issues[0].code == "objective_mismatch"
    assert not result.values and result.objective is None


@pytest.mark.parametrize("limit", [0.0, 1e7])
@pytest.mark.parametrize("factor,accepted", [(0.5, True), (2.0, False)])
def test_row_tolerance_scales_in_original_units(
    limit: float, factor: float, accepted: bool
) -> None:
    x = limit + factor * (ATOL + RTOL * limit)
    p = Problem(
        (Variable("x", lower=None),), [0], [[1]], (Constraint("R", "<="),), [limit]
    )
    result = verify(p, compile_problem(p), [x], 0)
    assert (not result.issues) is accepted
    assert result.diagnostics[0].violation == pytest.approx(x - limit)
    assert result.diagnostics[0].tolerance == pytest.approx(ATOL + RTOL * abs(x))


@pytest.mark.parametrize(
    "case",
    [
        "linear_overflow",
        "constant_overflow",
        "row_product",
        "row_residual",
        "upper_slack",
    ],
)
def test_rejects_overflow_during_original_model_verification(case: str) -> None:
    x = -1e308 if case == "upper_slack" else 1e308
    coef = {"linear_overflow": 2.0, "constant_overflow": 1.0}.get(case, 0.0)
    limit = 1e308 if case == "upper_slack" else None
    p = Problem(
        (Variable("x", lower=None, upper=limit),),
        [coef],
        [[2.0 if case == "row_product" else 1.0]],
        (Constraint("r", "<="),),
        [-1e308 if case == "row_residual" else 1e308],
        constant=1e308 if case == "constant_overflow" else 0.0,
    )
    result = verify(p, compile_problem(p), [x], 0)
    assert result.issues
    assert not result.values and result.objective is None
    if case in {"row_residual", "row_product", "upper_slack"}:
        assert result.max_violation is None
