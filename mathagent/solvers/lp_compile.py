"""Compile a caller-owned continuous LP without modifying its arrays.

Float64 dense arrays and canonical CSR inputs may be borrowed for the duration of
the synchronous solve. Callers must keep inputs stable until it returns. Original
row order and coefficients remain available for the independent feasibility check.
"""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from numbers import Real
from typing import TypeAlias, cast

import numpy as np
import numpy.typing as npt
from scipy import sparse  # type: ignore[import-untyped]  # Official SciPy wheels lack stubs.

from mathagent.core.lp_types import FloatArray, Issue, Problem, SolveStatus

Matrix: TypeAlias = FloatArray | sparse.csr_matrix
IndexArray: TypeAlias = npt.NDArray[np.intp]


class CompileError(ValueError):
    """A numerical input issue with a zero-based source location."""

    def __init__(
        self, issue: Issue, status: SolveStatus = SolveStatus.INVALID_INPUT
    ) -> None:
        super().__init__(issue.message)
        self.issue = issue
        self.status = status


@dataclass(frozen=True, slots=True)
class CompiledLP:
    problem: Problem
    variable_ids: tuple[str, ...]
    constraint_ids: tuple[str, ...]
    objective: FloatArray
    matrix: Matrix
    rhs: FloatArray
    sign: int
    constant: float
    c: FloatArray
    A_ub: Matrix | None
    b_ub: FloatArray | None
    A_eq: Matrix | None
    b_eq: FloatArray | None
    bounds: FloatArray
    ub_row_indices: IndexArray
    eq_row_indices: IndexArray


def _fail(
    code: str,
    field: str,
    message: str,
    row: int | None = None,
    column: int | None = None,
    entity_id: str | None = None,
) -> CompileError:
    return CompileError(Issue(code, field, message, row, column, entity_id))


def _check_ids(ids: tuple[str, ...], field: str) -> None:
    seen: set[str] = set()
    for index, value in enumerate(ids):
        row = index if field == "constraints" else None
        column = index if field == "variables" else None
        if not isinstance(value, str) or not value.strip():
            raise _fail("invalid_id", field, "ID 必须是非空字符串", row, column)
        if value in seen:
            raise _fail("duplicate_id", field, "ID 重复", row, column, value)
        seen.add(value)


def _finite_index(values: FloatArray) -> tuple[int, ...] | None:
    # Limit transient boolean storage, also for non-contiguous dense input.
    if not values.size:
        return None
    width = values.shape[1] if values.ndim == 2 else 1
    block_rows = max(1, (1024 * 1024) // max(width, 1))
    for start in range(0, values.shape[0], block_rows):
        finite = np.isfinite(values[start : start + block_rows])
        if not finite.all():
            where = tuple(
                int(i) for i in np.unravel_index(finite.argmin(), finite.shape)
            )
            return (start + where[0], *where[1:])
    return None


def _vector(data: npt.ArrayLike, field: str, ids: tuple[str, ...]) -> FloatArray:
    try:
        source = np.asarray(data)
    except (TypeError, ValueError, OverflowError) as exc:
        raise _fail("invalid_vector", field, "向量必须是一维数值序列") from exc
    if source.shape != (len(ids),):
        i = min(source.size, len(ids)) if source.ndim == 1 else None
        row, col = (i, None) if field == "rhs" else (None, i)
        entity_id = ids[i] if i is not None and i < len(ids) else None
        raise _fail(
            "size_mismatch",
            field,
            f"需要长度 {len(ids)} 的一维向量",
            row,
            col,
            entity_id,
        )
    if source.dtype.kind not in "iuf":
        index = _invalid_dtype_index(data)
        i = index[0] if index else None
        row, col = (i, None) if field == "rhs" else (None, i)
        raise _fail(
            "invalid_number",
            field,
            "系数必须是实数",
            row,
            col,
            ids[i] if i is not None else None,
        )
    with np.errstate(over="ignore", invalid="ignore"):
        values = np.asarray(source, dtype=np.float64)
    invalid = _finite_index(values)
    if invalid is not None:
        i = invalid[0]
        row, col = (i, None) if field == "rhs" else (None, i)
        raise _fail("nonfinite", field, "系数必须是有限实数", row, col, ids[i])
    return values


def _invalid_dtype_index(data: npt.ArrayLike) -> tuple[int, ...] | None:
    # Error path only. Object conversion preserves individual types in mixed Python lists.
    objects = np.asarray(data, dtype=object)
    for index, item in np.ndenumerate(objects):
        if not isinstance(item, Real) and (not isinstance(item, complex) or item.imag):
            return tuple(index)
    return (0,) * objects.ndim if objects.size else None


def _matrix(
    problem: Problem, constraint_ids: tuple[str, ...], variables: int
) -> Matrix:
    shape = (len(constraint_ids), variables)
    data = problem.matrix
    source: npt.NDArray[np.generic] | sparse.spmatrix
    row: int | None
    col: int | None
    where: tuple[int, ...] | None
    if sparse.issparse(data):
        source = cast(sparse.spmatrix, data)
        if source.format in {"csr", "csc", "bsr"}:
            # SciPy's full check may rebind the internal arrays. Validate a
            # shallow wrapper before any conversion enters native sparse code.
            try:
                copy(source).check_format(full_check=True)
            except ValueError as exc:
                raise _fail("invalid_sparse_structure", "matrix", str(exc)) from exc
    else:
        try:
            source = np.asarray(data)
        except (TypeError, ValueError, OverflowError) as exc:
            if isinstance(data, (list, tuple)):
                for row, entries in enumerate(data):
                    if (
                        isinstance(entries, (list, tuple, np.ndarray))
                        and np.ndim(entries) == 1
                        and len(entries) != variables
                    ):
                        entity_id = constraint_ids[row] if row < shape[0] else None
                        raise _fail(
                            "size_mismatch",
                            "matrix",
                            f"此行需要 {variables} 列",
                            row,
                            min(len(entries), variables),
                            entity_id,
                        ) from exc
            raise _fail(
                "invalid_matrix", "matrix", "约束矩阵必须是规则的二维数组"
            ) from exc
        if shape[0] == 0 and source.shape == (0,):
            source = source.reshape(shape)
    if source.shape != shape:
        row = col = None
        if len(source.shape) == 2:
            if source.shape[1] != variables:
                col = min(source.shape[1], variables)
                row = 0 if shape[0] and source.shape[0] else None
            elif source.shape[0] != shape[0]:
                row = min(source.shape[0], shape[0])
        entity_id = constraint_ids[row] if row is not None and row < shape[0] else None
        raise _fail(
            "size_mismatch",
            "matrix",
            f"约束矩阵需要形状 {shape}，得到 {source.shape}",
            row,
            col,
            entity_id,
        )
    if source.dtype.kind not in "iuf":
        if sparse.issparse(source):
            coo = cast(sparse.spmatrix, source).tocoo(copy=False)
            bad = _invalid_dtype_index(coo.data)
            where = (int(coo.row[bad[0]]), int(coo.col[bad[0]])) if bad else None
        else:
            where = _invalid_dtype_index(data)
        row, col = where if where else (None, None)
        raise _fail(
            "invalid_number",
            "matrix",
            "矩阵系数必须是实数",
            row,
            col,
            constraint_ids[row] if row is not None else None,
        )
    if sparse.issparse(source):
        # Cast before CSR consolidation to avoid integer overflow when summing duplicates.
        with np.errstate(over="ignore", invalid="ignore"):
            csr = sparse.csr_matrix(source.astype(np.float64, copy=False), copy=False)
            if not csr.has_canonical_format:
                csr = csr.copy()
                csr.sum_duplicates()
        invalid = _finite_index(csr.data)
        if invalid is not None:
            k = invalid[0]
            row = int(np.searchsorted(csr.indptr, k, side="right") - 1)
            raise _fail(
                "nonfinite",
                "matrix",
                "矩阵系数必须有限",
                row,
                int(csr.indices[k]),
                constraint_ids[row],
            )
        return csr
    with np.errstate(over="ignore", invalid="ignore"):
        dense = np.asarray(source, dtype=np.float64)
    bad = _finite_index(dense)
    if bad is not None:
        row, col = bad
        raise _fail(
            "nonfinite", "matrix", "矩阵系数必须有限", row, col, constraint_ids[row]
        )
    return dense


def _bounds(problem: Problem) -> FloatArray:
    bounds = np.empty((len(problem.variables), 2), dtype=np.float64)
    for i, var in enumerate(problem.variables):
        for side, value in enumerate((var.lower, var.upper)):
            open_bound = -np.inf if side == 0 else np.inf
            if value is None:
                bounds[i, side] = open_bound
                continue
            if not isinstance(value, Real):
                raise _fail(
                    "invalid_bound",
                    "bounds",
                    "边界必须是实数",
                    column=i,
                    entity_id=var.id,
                )
            try:
                bound = float(value)
            except OverflowError as exc:
                raise _fail(
                    "invalid_bound",
                    "bounds",
                    "边界超出浮点范围",
                    column=i,
                    entity_id=var.id,
                ) from exc
            if np.isnan(bound) or bound == -open_bound:
                raise _fail(
                    "invalid_bound",
                    "bounds",
                    "边界为 NaN 或无穷方向错误",
                    column=i,
                    entity_id=var.id,
                )
            bounds[i, side] = bound
    crossed = bounds[:, 0] > bounds[:, 1]
    if crossed.any():
        i = int(crossed.argmax())
        issue = Issue(
            "contradictory_bounds",
            "bounds",
            "变量下界大于上界",
            None,
            i,
            problem.variables[i].id,
        )
        raise CompileError(issue, SolveStatus.INFEASIBLE)
    return bounds


def _rows(
    matrix: Matrix, rhs: FloatArray, indices: IndexArray
) -> tuple[Matrix | None, FloatArray | None]:
    if not len(indices):
        return None, None
    if len(indices) == len(rhs):
        return matrix, rhs
    return matrix[indices], rhs[indices]


def compile_problem(problem: Problem) -> CompiledLP:
    """Build float64 HiGHS inputs in O(rows + columns + stored coefficients)."""
    variable_ids = tuple(v.id for v in problem.variables)
    constraint_ids = tuple(c.id for c in problem.constraints)
    if not variable_ids:
        raise _fail("empty_variables", "variables", "至少需要一个变量")
    _check_ids(variable_ids, "variables")
    _check_ids(constraint_ids, "constraints")
    if problem.direction not in ("min", "max"):
        raise _fail("invalid_direction", "direction", "目标方向应为 min 或 max")
    if not isinstance(problem.constant, Real):
        raise _fail("invalid_number", "constant", "目标常数必须是有限实数")
    try:
        constant = float(problem.constant)
    except OverflowError as exc:
        raise _fail("nonfinite", "constant", "目标常数超出浮点范围") from exc
    if not np.isfinite(constant):
        raise _fail("nonfinite", "constant", "目标常数必须有限")

    objective = _vector(problem.objective, "objective", variable_ids)
    matrix = _matrix(problem, constraint_ids, len(variable_ids))
    rhs = _vector(problem.rhs, "rhs", constraint_ids)
    senses = np.empty(len(constraint_ids), dtype=np.int8)
    sense_codes = {"<=": 1, ">=": -1, "=": 0}
    for row, constraint in enumerate(problem.constraints):
        if constraint.sense not in sense_codes:
            raise _fail(
                "invalid_sense",
                "constraints",
                "约束关系应为 <=、>= 或 =",
                row=row,
                entity_id=constraint.id,
            )
        senses[row] = sense_codes[constraint.sense]
    bounds = _bounds(problem)
    ub_indices = np.flatnonzero(senses)
    eq_indices = np.flatnonzero(senses == 0)
    a_ub, b_ub = _rows(matrix, rhs, ub_indices)
    a_eq, b_eq = _rows(matrix, rhs, eq_indices)
    if a_ub is not None and b_ub is not None and (senses < 0).any():
        signs = senses[ub_indices]
        if a_ub is matrix:
            a_ub = a_ub.copy()
        if sparse.issparse(a_ub):
            a_ub.data *= np.repeat(signs, np.diff(a_ub.indptr))
        else:
            np.multiply(a_ub, signs[:, None], out=a_ub)
        b_ub = b_ub * signs
    sign = 1 if problem.direction == "min" else -1
    return CompiledLP(
        problem,
        variable_ids,
        constraint_ids,
        objective,
        matrix,
        rhs,
        sign,
        constant,
        objective if sign == 1 else -objective,
        a_ub,
        b_ub,
        a_eq,
        b_eq,
        bounds,
        ub_indices,
        eq_indices,
    )
