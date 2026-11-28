"""Independent acceptance numbers from the project's MATLAB M01–M09 baseline."""

import json
from dataclasses import replace

import numpy as np
import pytest

from mathagent.solvers import solve
from mathagent.solvers.lp_compile import compile_problem

from .lp_fixtures import EXPECTED, ROOT, load_case


@pytest.mark.parametrize("case_id", EXPECTED)
def test_reference_case(case_id):
    expected = EXPECTED[case_id]
    result = solve(load_case(case_id))
    assert result.solve_status == expected["status"]
    if expected["objective"] is None:
        assert result.objective is None and not result.values
    else:
        assert result.objective == pytest.approx(expected["objective"], abs=1e-9)
        assert result.values == pytest.approx(expected["values"], abs=1e-9)
        assert result.max_violation == pytest.approx(0.0, abs=1e-9)
    if "iterations" in expected:
        assert result.metrics.iterations == expected["iterations"]
    if case_id == "M07":
        issue = result.issues[0]
        assert (issue.field, issue.row, issue.column) == ("matrix", 0, 2)
        assert issue.entity_id == "机时"
    if "machine_hours" in expected:
        rows = {(row.kind, row.entity_id): row for row in result.diagnostics}
        hours = rows["constraint", "机时"]
        assert hours.unit == "小时"
        assert hours.actual == pytest.approx(expected["machine_hours"], abs=1e-9)
        assert hours.slack == pytest.approx(0.0, abs=1e-9)
        order = rows["upper_bound", "乙"]
        assert order.unit == "批"
        assert order.slack == pytest.approx(3 - expected["values"]["乙"], abs=1e-9)
        assert order.violation == pytest.approx(0.0, abs=1e-9)


def test_production_compile_snapshot_for_model_handoff():
    snapshot = json.loads(
        (ROOT / "expected/production_compiled.json").read_text(encoding="utf-8")
    )
    compiled = compile_problem(load_case(snapshot["case"]))
    for key in ("variable_ids", "constraint_ids"):
        assert list(getattr(compiled, key)) == snapshot[key]
    for key in ("c", "A_ub", "b_ub", "bounds", "constant", "sign"):
        np.testing.assert_allclose(getattr(compiled, key), snapshot[key], atol=1e-9)
    assert compiled.A_eq is None and compiled.b_eq is None


def test_multiple_optima_on_the_capacity_line():
    # Both products pay the same unit profit, so every feasible x+y=4 is optimal.
    tied = replace(load_case("M01"), objective=[1.0, 1.0])
    result = solve(tied)
    assert result.solve_status == "optimal"
    assert result.objective == pytest.approx(4.0, abs=1e-9)
    x, y = result.values["甲"], result.values["乙"]
    assert -1e-9 <= x <= 2 + 1e-9 and -1e-9 <= y <= 3 + 1e-9
    assert x + y == pytest.approx(4.0, abs=1e-9)
