"""Protect finite model coefficients from HiGHS' zero/infinity thresholds."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from mathagent.core.lp_types import FloatArray, Issue, SolveStatus

from .lp_compile import CompileError, CompiledLP, IndexArray, Matrix

# Conservative working range for the HiGHS versions distributed with SciPy 1.11–1.14.
_SMALL_MATRIX = 1e-9
_LARGE_MATRIX = 1e15
_INFINITE_BOUND = 1e20
_DUAL_TOL = 1e-7


def _unsafe_coefficients(
    values: FloatArray,
) -> np.ndarray[tuple[int, ...], np.dtype[np.bool_]]:
    magnitude = np.abs(values)
    return (magnitude >= _LARGE_MATRIX) | (
        (magnitude > 0) & (magnitude <= _SMALL_MATRIX)
    )


def _scale_rows(
    matrix: Matrix | None,
    rhs: FloatArray | None,
    original_rows: IndexArray,
    ids: tuple[str, ...],
) -> tuple[Matrix | None, FloatArray | None]:
    if matrix is None or rhs is None:
        return matrix, rhs
    flagged = np.abs(rhs) >= _INFINITE_BOUND
    # Bound temporary masks even for dense inputs larger than 100 MB.
    chunk = 262144
    if isinstance(matrix, np.ndarray):
        step = max(1, chunk // matrix.shape[1])
        for start in range(0, len(rhs), step):
            flagged[start : start + step] |= _unsafe_coefficients(
                matrix[start : start + step]
            ).any(axis=1)
    else:
        for start in range(0, len(matrix.data), chunk):
            offsets = np.flatnonzero(
                _unsafe_coefficients(matrix.data[start : start + chunk])
            )
            if offsets.size:
                flagged[
                    np.searchsorted(matrix.indptr, offsets + start, side="right") - 1
                ] = True
    if not flagged.any():
        return matrix, rhs
    scaled, limits = matrix.copy(), rhs.copy()
    for index in np.flatnonzero(flagged):
        row = (
            scaled[index]
            if isinstance(scaled, np.ndarray)
            else scaled.data[scaled.indptr[index] : scaled.indptr[index + 1]]
        )
        largest = float(np.max(np.abs(row), initial=0.0))
        if largest == 0:
            # Positive scaling preserves the truth of a constant constraint.
            largest = max(1.0, abs(float(limits[index])))
        with np.errstate(over="ignore", under="ignore"):
            original_nonzero = row != 0
            row /= largest
            limits[index] /= largest
        if (
            _unsafe_coefficients(row).any()
            or np.any(original_nonzero & (row == 0))
            or abs(limits[index]) >= _INFINITE_BOUND
            or (rhs[index] != 0 and limits[index] == 0)
        ):
            position = int(original_rows[index])
            issue = Issue(
                "unsafe_row_scale",
                "matrix",
                "请调整此约束或变量的单位后再求解。",
                row=position,
                entity_id=ids[position],
            )
            raise CompileError(issue, SolveStatus.NUMERICAL_FAILURE)
    return scaled, limits


def prepare_highs(model: CompiledLP) -> tuple[CompiledLP, float]:
    """Return backend-only positive rescalings and the factor restoring its objective."""
    too_large = np.isfinite(model.bounds) & (np.abs(model.bounds) >= _INFINITE_BOUND)
    if too_large.any():
        col = int(np.unravel_index(too_large.argmax(), too_large.shape)[0])
        issue = Issue(
            "unsafe_bound_scale",
            "bounds",
            "此有限边界超过后端数值范围，请调整变量单位。",
            column=col,
            entity_id=model.variable_ids[col],
        )
        raise CompileError(issue, SolveStatus.NUMERICAL_FAILURE)
    c = model.c
    magnitude = np.abs(c)
    smallest = float(np.min(magnitude, where=magnitude > 0, initial=np.inf))
    factor = 1.0
    if smallest <= _DUAL_TOL or magnitude.max() >= _LARGE_MATRIX:
        factor = smallest
        with np.errstate(over="ignore"):
            c = c / factor
        if np.abs(c).max() >= _LARGE_MATRIX:
            issue = Issue(
                "unsafe_objective_scale",
                "objective",
                "目标系数量级相差过大，请调整变量单位。",
            )
            raise CompileError(issue, SolveStatus.NUMERICAL_FAILURE)
    ub, bub = _scale_rows(
        model.A_ub, model.b_ub, model.ub_row_indices, model.constraint_ids
    )
    eq, beq = _scale_rows(
        model.A_eq, model.b_eq, model.eq_row_indices, model.constraint_ids
    )
    return replace(model, c=c, A_ub=ub, b_ub=bub, A_eq=eq, b_eq=beq), factor
