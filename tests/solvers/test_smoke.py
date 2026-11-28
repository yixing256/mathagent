import builtins
import json

from mathagent.numeric_smoke import main


def test_smoke_runs_native_and_both_lp_layouts(capsys):
    assert main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["passed"]
    assert report["numpy_version"] and report["scipy_version"]
    assert [row["name"] for row in report["checks"]] == [
        "numpy_native",
        "scipy_native",
        "dense_lp",
        "sparse_lp",
    ]
    assert all(row["passed"] and row["seconds"] >= 0.0 for row in report["checks"])


def test_loader_failure_is_a_structured_failure(monkeypatch, capsys):
    original = builtins.__import__

    def missing_dll(name, *args, **kwargs):
        if name == "numpy":
            raise ImportError("test DLL is missing")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_dll)
    assert main() == 1
    report = json.loads(capsys.readouterr().out)
    assert not report["passed"]
    assert report["numpy_version"] is None
    assert report["checks"][0]["name"] == "numpy_native"
    assert "test DLL is missing" in report["checks"][0]["detail"]
