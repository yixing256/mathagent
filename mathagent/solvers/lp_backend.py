"""SciPy HiGHS dual-simplex adapter. The service owns cancellation and worker lifetime."""

from __future__ import annotations

from dataclasses import replace
from math import isfinite
from numbers import Integral, Real
from time import perf_counter

import scipy  # type: ignore[import-untyped]  # Approved SciPy versions have no py.typed.
from scipy.optimize import linprog  # type: ignore[import-untyped]  # Public SciPy entry point.

from mathagent.core.lp_types import (
    Issue,
    Metrics,
    Problem,
    Solution,
    SolveOptions,
    SolveStatus,
)

from ._highs_scale import prepare_highs
from .lp_compile import CompileError, compile_problem
from .lp_verify import verify


def _time_limit(options: SolveOptions) -> float | None:
    value = options.time_limit_seconds
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        seconds = float(value)
    except OverflowError:
        return None
    return seconds if isfinite(seconds) and seconds > 0 else None


def _integer(value: object) -> int | None:
    if isinstance(value, Integral) and not isinstance(value, bool):
        return int(value)
    return None


def solve_lp(problem: Problem, options: SolveOptions | None) -> Solution:
    started = perf_counter()
    metrics = Metrics(backend_version=scipy.__version__)
    seconds = _time_limit(options if options is not None else SolveOptions())
    if seconds is None:
        issue = Issue(
            "invalid_time_limit", "time_limit_seconds", "求解时限必须为正的有限秒数。"
        )
        return Solution(SolveStatus.INVALID_INPUT, metrics, issues=(issue,))
    try:
        original = compile_problem(problem)
        model, objective_factor = prepare_highs(original)
    except CompileError as error:
        metrics = replace(
            metrics,
            compile_seconds=perf_counter() - started,
            iterations=0 if error.status is SolveStatus.INFEASIBLE else None,
        )
        return Solution(error.status, metrics, issues=(error.issue,))

    solve_start = perf_counter()
    metrics = replace(metrics, compile_seconds=solve_start - started)
    try:
        result = linprog(
            model.c,
            A_ub=model.A_ub,
            b_ub=model.b_ub,
            A_eq=model.A_eq,
            b_eq=model.b_eq,
            bounds=model.bounds,
            method=metrics.method,
            options={"time_limit": seconds},
        )
    except (ValueError, RuntimeError, ArithmeticError) as error:
        metrics = replace(
            metrics, solve_seconds=perf_counter() - solve_start, raw_message=str(error)
        )
        issue = Issue("backend_error", "backend", str(error))
        return Solution(SolveStatus.NUMERICAL_FAILURE, metrics, issues=(issue,))

    verify_start = perf_counter()
    raw_status = _integer(result.get("status"))
    iterations = _integer(result.get("nit"))
    metrics = replace(
        metrics,
        solve_seconds=verify_start - solve_start,
        iterations=iterations if iterations is not None and iterations >= 0 else None,
        raw_status=raw_status,
        raw_message=result.get("message"),
    )
    if raw_status != 0 or not result.get("success"):
        status = {
            1: SolveStatus.LIMIT_REACHED,
            2: SolveStatus.INFEASIBLE,
            3: SolveStatus.UNBOUNDED,
        }.get(
            raw_status if raw_status is not None else -1, SolveStatus.NUMERICAL_FAILURE
        )
        # SciPy 1.x maps both HiGHS ModelError (2) and Infeasible (8) to 2.
        if result.get("success") or (
            raw_status == 2
            and "(highs status 2:" in (metrics.raw_message or "").lower()
        ):
            status = SolveStatus.NUMERICAL_FAILURE
        issue = Issue(
            status.value,
            "backend",
            metrics.raw_message or "求解器未返回可验证的最优解。",
        )
        return Solution(status, metrics, issues=(issue,))

    checked = verify(
        problem, original, result.get("x"), result.get("fun"), objective_factor
    )
    metrics = replace(metrics, verify_seconds=perf_counter() - verify_start)
    status = SolveStatus.NUMERICAL_FAILURE if checked.issues else SolveStatus.OPTIMAL
    return Solution(
        status,
        metrics,
        values=checked.values,
        objective=checked.objective,
        objective_unit=problem.objective_unit,
        diagnostics=checked.diagnostics,
        issues=checked.issues,
        max_violation=checked.max_violation,
    )
