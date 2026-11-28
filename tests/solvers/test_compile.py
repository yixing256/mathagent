from dataclasses import replace

import numpy as np
import pytest
from scipy import sparse

from mathagent.core.lp_types import Constraint, Problem, SolveStatus, Variable
from mathagent.solvers.lp_compile import CompileError, compile_problem


@pytest.fixture
def production():
    return Problem(
        variables=(Variable("乙", "批", None, 3.0), Variable("甲", "批", -2.0, None)),
        objective=[2, 3],
        matrix=[[1, 1], [2, -1], [3, 0]],
        constraints=(
            Constraint("机时", "<=", "时"),
            Constraint("最低产量", ">="),
            Constraint("固定量", "="),
        ),
        rhs=[3, -4, 5],
        direction="max",
        constant=7.0,
        objective_unit="万元",
    )


@pytest.mark.parametrize(
    "factory",
    [
        np.asarray,
        sparse.csr_matrix,
        sparse.coo_array,
        sparse.csc_array,
        sparse.lil_matrix,
    ],
)
def test_compilation_preserves_original_model_and_stable_ids(production, factory):
    matrix = factory(production.matrix)
    compiled = compile_problem(replace(production, matrix=matrix))

    def dense(value):
        return value.toarray() if sparse.issparse(value) else value

    assert compiled.variable_ids == ("乙", "甲")
    assert compiled.constraint_ids == ("机时", "最低产量", "固定量")
    assert compiled.sign == -1
    assert compiled.constant == pytest.approx(7)
    np.testing.assert_array_equal(compiled.ub_row_indices, [0, 1])
    np.testing.assert_array_equal(compiled.eq_row_indices, [2])
    np.testing.assert_allclose(compiled.objective, [2, 3])
    np.testing.assert_allclose(compiled.c, [-2, -3])
    np.testing.assert_allclose(dense(compiled.A_ub), [[1, 1], [-2, 1]])
    np.testing.assert_allclose(compiled.b_ub, [3, 4])
    np.testing.assert_allclose(dense(compiled.A_eq), [[3, 0]])
    np.testing.assert_allclose(compiled.b_eq, [5])
    np.testing.assert_allclose(compiled.bounds, [[-np.inf, 3], [-2, np.inf]])
    np.testing.assert_allclose(dense(compiled.matrix), production.matrix)
    np.testing.assert_allclose(dense(matrix), production.matrix)
    np.testing.assert_allclose(compiled.rhs, production.rhs)
    assert sparse.issparse(compiled.A_ub) == sparse.issparse(matrix)


@pytest.mark.parametrize("factory", [np.asarray, sparse.csr_matrix])
def test_sign_flip_all_inequalities_preserves_borrowed_arrays(production, factory):
    data = factory([[1.0, 2.0]])
    rhs = np.array([4.0])
    compiled = compile_problem(
        replace(
            production,
            matrix=data,
            constraints=(Constraint("lower", ">="),),
            rhs=rhs,
            direction="min",
        )
    )
    np.testing.assert_allclose(compiled.matrix @ [1.0, 1.0], [3.0])
    np.testing.assert_allclose(compiled.A_ub @ [1.0, 1.0], [-3.0])
    np.testing.assert_allclose(compiled.c, compiled.objective)
    np.testing.assert_allclose(rhs, [4])
    assert compiled.A_eq is compiled.b_eq is None


@pytest.mark.parametrize("empty", [[], np.empty((0, 2)), sparse.csr_matrix((0, 2))])
def test_empty_constraints_keep_explicit_shape_and_bounds(production, empty):
    compiled = compile_problem(
        replace(production, matrix=empty, constraints=(), rhs=[])
    )
    assert compiled.matrix.shape == (0, 2)
    assert compiled.A_eq is compiled.b_eq is compiled.A_ub is compiled.b_ub is None
    assert compiled.bounds.dtype == np.float64


def test_noncanonical_sparse_input_aggregates_in_float64_without_overflow():
    data = sparse.csr_matrix(
        (np.array([100, 100], dtype=np.int8), [0, 0], [0, 2]), shape=(1, 1)
    )
    problem = Problem((Variable("x"),), [1], data, (Constraint("demand", "<="),), [20])
    compiled = compile_problem(problem)
    np.testing.assert_allclose(compiled.matrix @ [1.0], [200.0])
    np.testing.assert_array_equal(data.data, [100, 100])
    assert data.nnz == 2


def test_compressed_format_check_reports_an_input_issue(production, monkeypatch):
    data = sparse.csr_matrix(production.matrix)

    def format_error(self, full_check=True):
        raise ValueError("invalid sparse indices")

    monkeypatch.setattr(sparse.csr_matrix, "check_format", format_error)
    with pytest.raises(CompileError) as error:
        compile_problem(replace(production, matrix=data))
    assert (error.value.issue.code, error.value.issue.field) == (
        "invalid_sparse_structure",
        "matrix",
    )


def test_sparse_compilation_keeps_large_shape_sparse(monkeypatch):
    n = 6000
    matrix = sparse.eye(n, format="csr", dtype=np.float64)
    problem = Problem(
        tuple(Variable(f"x{i}") for i in range(n)),
        np.ones(n),
        matrix,
        tuple(Constraint(f"r{i}", ">=" if i % 2 else "<=") for i in range(n)),
        np.ones(n),
    )

    def reject_densification(*args, **kwargs):
        pytest.fail("the sparse compiler attempted dense conversion")

    monkeypatch.setattr(sparse.csr_matrix, "toarray", reject_densification)
    compiled = compile_problem(problem)
    assert compiled.matrix.nnz == compiled.A_ub.nnz == n
    np.testing.assert_allclose(compiled.A_ub.data[:4], [1, -1, 1, -1])
    np.testing.assert_allclose(matrix.data[:4], [1, 1, 1, 1])


@pytest.mark.parametrize(
    ("updates", "field", "row", "column", "entity"),
    [
        ({"matrix": np.ones((3, 3))}, "matrix", 0, 2, "机时"),
        ({"matrix": np.ones((2, 2))}, "matrix", 2, None, "固定量"),
        ({"matrix": [1, 2]}, "matrix", None, None, None),
        ({"matrix": [[1, 2], [3], [4, 5]]}, "matrix", 1, 1, "最低产量"),
        ({"matrix": [[1, 2], [3, np.nan], [4, 5]]}, "matrix", 1, 1, "最低产量"),
        (
            {"matrix": sparse.coo_matrix(([np.inf], ([2], [1])), shape=(3, 2))},
            "matrix",
            2,
            1,
            "固定量",
        ),
        (
            {"matrix": sparse.csr_matrix(([2j], ([1], [1])), shape=(3, 2))},
            "matrix",
            1,
            1,
            "最低产量",
        ),
        ({"matrix": [[1, 2], [1, 3j], [4, 5]]}, "matrix", 1, 1, "最低产量"),
        ({"objective": [2, np.inf]}, "objective", None, 1, "甲"),
        ({"objective": [3, "oops"]}, "objective", None, 1, "甲"),
        ({"objective": [1]}, "objective", None, 1, "甲"),
        ({"objective": [[3], [4]]}, "objective", None, None, None),
        ({"rhs": [1, np.nan, 3]}, "rhs", 1, None, "最低产量"),
        ({"variables": (Variable("乙"), Variable("乙"))}, "variables", None, 1, "乙"),
        (
            {
                "constraints": (
                    Constraint("机时", "<="),
                    Constraint("机时", ">="),
                    Constraint("固定量", "="),
                )
            },
            "constraints",
            1,
            None,
            "机时",
        ),
        ({"variables": (Variable(" "), Variable("甲"))}, "variables", None, 0, None),
        (
            {"variables": (Variable("乙", lower=np.inf), Variable("甲"))},
            "bounds",
            None,
            0,
            "乙",
        ),
        (
            {"variables": (Variable("乙", lower="2"), Variable("甲"))},
            "bounds",
            None,
            0,
            "乙",
        ),
        (
            {"variables": (Variable("乙"), Variable("甲", upper=np.nan))},
            "bounds",
            None,
            1,
            "甲",
        ),
        (
            {
                "constraints": (
                    Constraint("机时", "<"),
                    Constraint("b", "="),
                    Constraint("c", "="),
                )
            },
            "constraints",
            0,
            None,
            "机时",
        ),
        ({"variables": ()}, "variables", None, None, None),
        ({"direction": "maximum"}, "direction", None, None, None),
        ({"constant": np.nan}, "constant", None, None, None),
        ({"constant": 1j}, "constant", None, None, None),
    ],
)
def test_invalid_inputs_locate_source(production, updates, field, row, column, entity):
    with pytest.raises(CompileError) as exc:
        compile_problem(replace(production, **updates))
    error = exc.value
    assert error.status is SolveStatus.INVALID_INPUT
    assert (
        error.issue.field,
        error.issue.row,
        error.issue.column,
        error.issue.entity_id,
    ) == (field, row, column, entity)


def test_contradictory_bounds_have_distinct_math_status(production):
    problem = replace(
        production, variables=(Variable("乙"), Variable("甲", lower=2, upper=1))
    )
    with pytest.raises(CompileError) as exc:
        compile_problem(problem)
    assert exc.value.status is SolveStatus.INFEASIBLE
    assert exc.value.issue.column == 1 and exc.value.issue.entity_id == "甲"
