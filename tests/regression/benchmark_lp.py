"""Run from the checkout with python -m tests.regression.benchmark_lp."""

import json
import platform
from math import isclose
from statistics import median
from time import perf_counter

import numpy as np
import scipy
from scipy import sparse

from mathagent.core.lp_types import Constraint, Problem, Variable
from mathagent.solvers import solve

from .lp_fixtures import EXPECTED, load_case


def regression_report():
    records = []
    for case, expected in EXPECTED.items():
        result = solve(load_case(case))
        assert result.solve_status == expected["status"], case
        assert (result.objective is None) == (expected["objective"] is None), case
        error = None
        if result.objective is not None:
            error = abs(result.objective - expected["objective"])
            assert isclose(error, 0.0, abs_tol=1e-9), case
        records.append(
            {
                "case": case,
                "status": result.solve_status,
                "objective": result.objective,
                "objective_error": error,
                "max_violation": result.max_violation,
                "iterations": result.metrics.iterations,
                "compile_ms": 1000 * result.metrics.compile_seconds,
                "solve_ms": 1000 * result.metrics.solve_seconds,
                "verify_ms": 1000 * result.metrics.verify_seconds,
            }
        )
    return records


def make_benchmark(layout):
    # Each block is J + I, where J contains ones. Its row and column sums
    # are k+1, so summing the inequalities bounds sum(x) by n. x=1 attains n.
    if layout == "dense":
        n = block_size = 256
        matrix = np.ones((n, n)) + np.eye(n)
        storage_bytes = matrix.nbytes
        nonzeros = matrix.size
    else:
        n, block_size = 10_000, 10
        block = np.ones((block_size, block_size)) + np.eye(block_size)
        matrix = sparse.kron(sparse.eye(n // block_size), block, format="csr")
        storage_bytes = (
            matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes
        )
        nonzeros = matrix.nnz
    problem = Problem(
        variables=tuple(Variable(f"x{i}", lower=0.0) for i in range(n)),
        objective=np.ones(n),
        matrix=matrix,
        constraints=tuple(Constraint(f"r{i}", "<=") for i in range(n)),
        rhs=np.full(n, block_size + 1.0),
        direction="max",
    )
    return problem, storage_bytes, nonzeros


def benchmark(layout):
    problem, size, nonzeros = make_benchmark(layout)
    n = len(problem.variables)
    expected = float(n)
    assert solve(problem).solve_status == "optimal"
    samples = []
    elapsed = []
    for _ in range(5):
        start = perf_counter()
        result = solve(problem)
        elapsed.append(perf_counter() - start)
        assert result.solve_status == "optimal", result
        assert isclose(result.objective, expected, rel_tol=1e-10)
        assert isclose(result.max_violation, 0.0, abs_tol=1e-8)
        samples.append(result)
    return {
        "layout": layout,
        "shape": [n, n],
        "nonzeros": nonzeros,
        "input_matrix_bytes": size,
        "objective": samples[-1].objective,
        "max_objective_error": max(abs(r.objective - expected) for r in samples),
        "max_violation": max(r.max_violation for r in samples),
        "median_iterations": median(r.metrics.iterations for r in samples),
        "median_compile_ms": 1000 * median(r.metrics.compile_seconds for r in samples),
        "median_solve_ms": 1000 * median(r.metrics.solve_seconds for r in samples),
        "median_verify_ms": 1000 * median(r.metrics.verify_seconds for r in samples),
        "median_total_ms": 1000 * median(elapsed),
    }


def main():
    report = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "warmups": 1,
        "timed_runs": 5,
        "reference_cases": regression_report(),
        "benchmarks": [benchmark("dense"), benchmark("sparse")],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
