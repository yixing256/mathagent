"""Run the release numeric smoke and emit a JSON report and process exit code."""

import json
from dataclasses import asdict

from mathagent.solvers.smoke import run_numeric_smoke


def main() -> int:
    report = run_numeric_smoke()
    print(json.dumps({"passed": report.passed, **asdict(report)}, ensure_ascii=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
