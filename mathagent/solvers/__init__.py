"""Synchronous numerical entry point used by the worker process."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mathagent.core.lp_types import Problem, Solution, SolveOptions


def solve(problem: Problem, options: SolveOptions | None = None) -> Solution:
    """Solve a continuous LP using the supplied limit, or the 30-second default."""
    from .lp_backend import solve_lp

    return solve_lp(problem, options)
