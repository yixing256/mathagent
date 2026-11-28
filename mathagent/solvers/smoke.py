"""Headless numeric smoke for A's release launcher and direct module execution."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from time import perf_counter


@dataclass(frozen=True, slots=True)
class SmokeCheck:
    name: str
    passed: bool
    detail: str
    seconds: float


@dataclass(frozen=True, slots=True)
class NumericSmokeReport:
    numpy_version: str | None
    scipy_version: str | None
    checks: tuple[SmokeCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def run_numeric_smoke() -> NumericSmokeReport:
    """Load shipped native libraries and solve the same known LP in both layouts."""
    checks: list[SmokeCheck] = []
    numpy_version = scipy_version = None
    stage = "numpy_native"
    start = perf_counter()
    try:
        import numpy as np

        numpy_version = np.__version__
        matrix = np.array([[2.0, 1.0], [1.0, 3.0]])
        product = matrix @ np.array([[1.0, 2.0], [3.0, 4.0]])
        solution = np.linalg.solve(matrix, np.array([4.0, 7.0]))
        native_ok = np.allclose(product, [[5.0, 8.0], [10.0, 14.0]]) and np.allclose(
            solution, [1.0, 2.0]
        )
        checks.append(
            SmokeCheck(
                stage,
                bool(native_ok),
                "BLAS matmul / LAPACK solve",
                perf_counter() - start,
            )
        )

        stage = "scipy_native"
        start = perf_counter()
        import scipy  # type: ignore[import-untyped]
        from scipy.sparse import csr_matrix  # type: ignore[import-untyped]

        from mathagent.core.lp_types import Constraint, Problem, Variable
        from mathagent.solvers import solve

        scipy_version = scipy.__version__
        dense = np.array([[1.0, 1.0]])
        sparse = csr_matrix(dense)
        checks.append(SmokeCheck(stage, True, "SciPy CSR", perf_counter() - start))
        for stage, coefficients in (("dense_lp", dense), ("sparse_lp", sparse)):
            start = perf_counter()
            problem = Problem(
                variables=(
                    Variable("甲", "批", 0.0, 2.0),
                    Variable("乙", "批", 0.0, 3.0),
                ),
                objective=np.array([3.0, 2.0]),
                matrix=coefficients,
                constraints=(Constraint("机时", "<=", "小时"),),
                rhs=np.array([3.0]),
                direction="max",
                objective_unit="万元",
            )
            result = solve(problem)
            passed = (
                result.solve_status == "optimal"
                and result.objective is not None
                and isclose(result.objective, 8.0, abs_tol=1e-9)
                and isclose(result.values.get("甲", float("nan")), 2.0, abs_tol=1e-9)
                and isclose(result.values.get("乙", float("nan")), 1.0, abs_tol=1e-9)
            )
            detail = f"{result.solve_status}: objective={result.objective}"
            if result.metrics.raw_message:
                detail += f" ({result.metrics.raw_message})"
            checks.append(SmokeCheck(stage, passed, detail, perf_counter() - start))
    except Exception as exc:
        # A frozen release must report missing DLLs/imports through the same interface.
        checks.append(
            SmokeCheck(
                stage, False, f"{type(exc).__name__}: {exc}", perf_counter() - start
            )
        )
    return NumericSmokeReport(numpy_version, scipy_version, tuple(checks))
