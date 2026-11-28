"""Check a HiGHS candidate against the original LP, in the model's units."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from mathagent.core.lp_types import Diagnostic, Issue, Problem
from mathagent.core.tolerance import ATOL, RTOL
from mathagent.solvers.lp_compile import CompiledLP


@dataclass(frozen=True, slots=True)
class Verification:
    values: dict[str, float]
    objective: float | None
    diagnostics: tuple[Diagnostic, ...]
    issues: tuple[Issue, ...]
    max_violation: float | None


def _real_array(value: object, shape: tuple[int, ...]) -> NDArray[np.float64] | None:
    """A numeric backend value must have its declared shape before conversion."""
    try:
        array = np.asarray(value)
        if array.shape != shape or array.dtype.kind not in "fiu":
            return None
        with np.errstate(over="ignore", invalid="ignore"):
            converted: NDArray[np.float64] = array.astype(np.float64, copy=False)
        return converted if np.isfinite(converted).all() else None
    except (ValueError, TypeError, OverflowError):
        return None


def _tolerance(actual: float, limit: float) -> float:
    return ATOL + RTOL * max(abs(actual), abs(limit))


def _candidate_issue(value: object, variable_ids: tuple[str, ...]) -> Issue:
    """Locate bad entries only on the error path, retaining original mixed-list types."""
    try:
        array = np.asarray(value)
    except (ValueError, TypeError, OverflowError):
        return Issue(
            "invalid_candidate_shape", "backend.x", "候选解须为与变量数相符的一维向量"
        )
    if array.shape != (len(variable_ids),):
        return Issue(
            "invalid_candidate_shape",
            "backend.x",
            f"候选解形状须为 ({len(variable_ids)},)，实际为 {array.shape}",
        )
    column = None
    if array.dtype.kind == "c":
        # Real-valued neighbours may have acquired complex dtype by promotion.
        invalid = ~np.isfinite(array) | (array.imag != 0)
        if invalid.any():
            column = int(invalid.argmax())
    if column is None:
        originals = np.asarray(value, dtype=object)
        column = next(
            (i for i, item in enumerate(originals) if _real_array(item, ()) is None),
            None,
        )
    if column is None:
        return Issue("invalid_candidate_dtype", "backend.x", "候选向量须为实数数值类型")
    return Issue(
        "invalid_candidate_value",
        "backend.x",
        "候选变量值须为有限实数",
        column=column,
        entity_id=variable_ids[column],
    )


def _objective(
    compiled: CompiledLP,
    x: NDArray[np.float64],
    backend_fun: object,
    objective_factor: float,
) -> tuple[float | None, Issue | None]:
    backend = _real_array(backend_fun, ())
    if backend is None:
        return None, Issue(
            "invalid_backend_objective", "backend.fun", "后端目标须为有限实数"
        )
    with np.errstate(over="ignore", invalid="ignore"):
        linear = float(compiled.objective @ x)
    restored = compiled.sign * float(backend.item()) * objective_factor
    objective = linear + compiled.constant
    if not isfinite(linear) or not isfinite(objective) or not isfinite(restored):
        return None, Issue("nonfinite_objective", "objective", "原目标复算溢出")
    if abs(linear - restored) > _tolerance(linear, restored):
        return None, Issue(
            "objective_mismatch", "backend.fun", "后端目标与原目标的线性项不一致"
        )
    return objective, None


def verify(
    problem: Problem,
    compiled: CompiledLP,
    candidate: object,
    backend_fun: object,
    objective_factor: float = 1.0,
) -> Verification:
    """Return a verified solution or structured issues without publishing a candidate.

    The tolerance in each original unit is ATOL + RTOL * max(|actual|, |limit|).
    Inequality slack is positive on the feasible side. Equality residuals are
    signed actual minus limit. Unbounded sides have no diagnostic.
    """
    x = _real_array(candidate, (len(problem.variables),))
    if x is None:
        issue = _candidate_issue(candidate, compiled.variable_ids)
        return Verification({}, None, (), (issue,), None)

    objective, objective_issue = _objective(compiled, x, backend_fun, objective_factor)
    issues = [objective_issue] if objective_issue is not None else []
    diagnostics: list[Diagnostic] = []
    max_violation = 0.0

    # One matvec on the original matrix. CSR and dense arrays share this path.
    with np.errstate(over="ignore", invalid="ignore"):
        activities = compiled.matrix @ x
    for row, (constraint, activity, rhs) in enumerate(
        zip(problem.constraints, activities, compiled.rhs, strict=True)
    ):
        actual, limit = float(activity), float(rhs)
        difference = actual - limit
        if not isfinite(difference):
            issues.append(
                Issue(
                    "nonfinite_activity",
                    "matrix",
                    "约束用量或残差溢出",
                    row=row,
                    entity_id=constraint.id,
                )
            )
            continue
        if constraint.sense == "=":
            slack, residual, violation = None, difference, abs(difference)
        else:
            slack = -difference if constraint.sense == "<=" else difference
            residual, violation = None, max(0.0, -slack)
        tolerance = _tolerance(actual, limit)
        diagnostics.append(
            Diagnostic(
                constraint.id,
                "constraint",
                constraint.unit,
                actual,
                limit,
                slack,
                residual,
                violation,
                tolerance,
            )
        )
        max_violation = max(max_violation, violation)
        if violation > tolerance:
            issues.append(
                Issue(
                    "constraint_violation",
                    "constraints",
                    "候选解违反约束",
                    row=row,
                    entity_id=constraint.id,
                )
            )

    bound_kinds: tuple[Literal["lower_bound", "upper_bound"], ...] = (
        "lower_bound",
        "upper_bound",
    )
    for side, kind in enumerate(bound_kinds):
        limits = compiled.bounds[:, side]
        for column in np.flatnonzero(np.isfinite(limits)):
            variable = problem.variables[column]
            actual, limit = float(x[column]), float(limits[column])
            slack = actual - limit if side == 0 else limit - actual
            if not isfinite(slack):
                issues.append(
                    Issue(
                        "nonfinite_bound_slack",
                        kind,
                        "变量边界余量溢出",
                        column=int(column),
                        entity_id=variable.id,
                    )
                )
                continue
            violation, tolerance = max(0.0, -slack), _tolerance(actual, limit)
            diagnostics.append(
                Diagnostic(
                    variable.id,
                    kind,
                    variable.unit,
                    actual,
                    limit,
                    slack,
                    None,
                    violation,
                    tolerance,
                )
            )
            max_violation = max(max_violation, violation)
            if violation > tolerance:
                issues.append(
                    Issue(
                        "bound_violation",
                        kind,
                        "候选解违反变量边界",
                        column=int(column),
                        entity_id=variable.id,
                    )
                )

    if issues:
        if any(
            issue.code in {"nonfinite_activity", "nonfinite_bound_slack"}
            for issue in issues
        ):
            return Verification({}, None, tuple(diagnostics), tuple(issues), None)
        return Verification({}, None, tuple(diagnostics), tuple(issues), max_violation)
    values = dict(zip(compiled.variable_ids, x.tolist(), strict=True))
    return Verification(values, objective, tuple(diagnostics), (), max_violation)
