"""Picklable contracts for continuous LPs. Rows and columns use zero-based positions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal, TypeAlias

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.sparse import sparray, spmatrix  # type: ignore[import-untyped]  # No py.typed in the approved SciPy range.

FloatArray: TypeAlias = NDArray[np.float64]
MatrixInput: TypeAlias = ArrayLike | spmatrix | sparray


@dataclass(frozen=True, slots=True)
class Variable:
    id: str
    unit: str = ""
    lower: float | None = 0.0
    upper: float | None = None


@dataclass(frozen=True, slots=True)
class Constraint:
    id: str
    sense: Literal["<=", ">=", "="]
    unit: str = ""


@dataclass(frozen=True, slots=True)
class Problem:
    """Variables label the columns of both objective and matrix; constraints label rows.

    Pass a real vector for objective/rhs and a two-dimensional dense or sparse
    matrix. Inputs are borrowed for the duration of a synchronous solve.
    """

    variables: tuple[Variable, ...]
    objective: ArrayLike
    matrix: MatrixInput
    constraints: tuple[Constraint, ...]
    rhs: ArrayLike
    direction: Literal["min", "max"] = "min"
    constant: float = 0.0
    objective_unit: str = ""


@dataclass(frozen=True, slots=True)
class SolveOptions:
    """Wall-time limit in seconds passed to HiGHS (excluding compilation/verification)."""

    time_limit_seconds: float = 30.0


class SolveStatus(StrEnum):
    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    UNBOUNDED = "unbounded"
    LIMIT_REACHED = "limit_reached"
    NUMERICAL_FAILURE = "numerical_failure"
    INVALID_INPUT = "invalid_input"


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    field: str
    message: str
    row: int | None = None
    column: int | None = None
    entity_id: str | None = None


@dataclass(frozen=True, slots=True)
class Diagnostic:
    entity_id: str
    kind: Literal["constraint", "lower_bound", "upper_bound"]
    unit: str
    actual: float
    limit: float
    slack: float | None
    residual: float | None
    violation: float
    tolerance: float


@dataclass(frozen=True, slots=True)
class Metrics:
    compile_seconds: float = 0.0
    solve_seconds: float = 0.0
    verify_seconds: float = 0.0
    iterations: int | None = None
    backend_version: str | None = None
    method: str = "highs-ds"
    raw_status: int | None = None
    raw_message: str | None = None


@dataclass(frozen=True, slots=True)
class Solution:
    """Only an optimal, verified result carries variable values and an objective."""

    solve_status: SolveStatus
    metrics: Metrics
    values: dict[str, float] = field(default_factory=dict)
    objective: float | None = None
    objective_unit: str = ""
    diagnostics: tuple[Diagnostic, ...] = ()
    issues: tuple[Issue, ...] = ()
    max_violation: float | None = None
