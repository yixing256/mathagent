"""Load external, hand-checked LP fixtures without calling solver code."""

import json
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix

from mathagent.core.lp_types import Constraint, Problem, Variable

ROOT = Path(__file__).resolve().parent
MODELS = json.loads((ROOT / "cases/lp_models.json").read_text(encoding="utf-8"))
EXPECTED = json.loads((ROOT / "expected/lp_results.json").read_text(encoding="utf-8"))


def load_case(case_id: str) -> Problem:
    overrides = MODELS["cases"][case_id]
    data = MODELS[overrides["model"]] | overrides
    variables = tuple(Variable(*row) for row in data["variables"])
    matrix = np.asarray(data["matrix"], dtype=np.float64)
    if not matrix.size:
        matrix = matrix.reshape(0, len(variables))
    return Problem(
        variables=variables,
        objective=np.array(data["objective"]),
        matrix=csr_matrix(matrix) if data.get("sparse") else matrix,
        constraints=tuple(Constraint(*row) for row in data["constraints"]),
        rhs=np.array(data["rhs"]),
        direction=data["direction"],
        constant=data.get("constant", 0.0),
        objective_unit=data["objective_unit"],
    )
