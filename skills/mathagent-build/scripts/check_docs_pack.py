#!/usr/bin/env python3
"""Read-only integrity check for the mathagent-build governance pack.

Exit codes: 0 = all checks pass, 1 = violations found, 2 = usage error.
Stdlib only; no network; never writes anything.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Package-internal names (whitelisted extensions only).
MANIFEST = [
    "AGENTS.md",
    "docs/agents/README.md",
    "docs/agents/00-base.md",
    "docs/agents/10-role-ui.md",
    "docs/agents/11-role-core.md",
    "docs/agents/12-role-ai.md",
    "docs/agents/13-role-release.md",
    "docs/agents/20-sop-ui-change.md",
    "docs/agents/21-sop-release.md",
    "config/.pre-commit-config.yaml",
    "config/ci.yml",
    "config/PULL_REQUEST_TEMPLATE.md",
    "config/CODEOWNERS.txt",
    "config/dependency-whitelist.txt",
    "config/gitignore.append.txt",
]

# Landed names inside the target repository (renamed on install, see SKILL.md §1).
LANDED = [
    "AGENTS.md",
    "docs/agents/00-base.md",
    ".pre-commit-config.yaml",
    ".github/workflows/ci.yml",
    ".github/CODEOWNERS",
    ".gitignore",
]

FORBIDDEN_STACK = [
    "vue", "react", "electron", "tauri", "pywebview", "webview2",
    "rust", "pyo3", "maturin", "pybind11",
]
ALLOWED_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".txt", ".sh", ".toml"}
SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{12,}"), "looks like an API key"),
    (re.compile(r"AKIA[0-9A-Z]{12,}"), "looks like an AWS key id"),
    (re.compile(r"(?i)(api[_-]?key|password|secret)\s*[:=]\s*[\"'][^\"'<{][^\"']{7,}"), "hardcoded credential"),
]
MAX_LINES = 200


def text_files(root):
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in ALLOWED_SUFFIXES:
            yield p


def read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def run_checks(kit, target, max_lines):
    checks = []

    def add(cid, ok, detail):
        checks.append({"id": cid, "status": "pass" if ok else "fail", "detail": detail})

    missing = [f for f in MANIFEST if not (kit / f).is_file()]
    add("K1-manifest", not missing, "missing: " + ", ".join(missing) if missing else f"{len(MANIFEST)} files present")

    long_files = []
    for p in text_files(kit):
        n = len(read(p).splitlines())
        if n > max_lines:
            long_files.append(f"{p.relative_to(kit).as_posix()}={n}")
    add("K2-line-limit", not long_files, f">{max_lines} lines: " + ", ".join(long_files) if long_files else f"all files <= {max_lines} lines")

    bad_ext = []
    for p in sorted(kit.rglob("*")):
        if p.is_file() and p.suffix.lower() not in ALLOWED_SUFFIXES:
            bad_ext.append(p.relative_to(kit).as_posix())
    add("K3-ext-whitelist", not bad_ext, "non-whitelisted extension: " + ", ".join(bad_ext) if bad_ext else "all files use .md/.yaml/.txt/.py/.json")

    wl = kit / "config/dependency-whitelist.txt"
    hits = []
    if wl.is_file():
        low = read(wl).lower()
        hits = [w for w in FORBIDDEN_STACK if re.search(rf"\b{re.escape(w)}\b", low)]
    add("K4-stack-lock", not hits, "forbidden dependency: " + ", ".join(hits) if hits else "whitelist free of banned stack")

    bad_onefile = []
    for p in text_files(kit):
        for i, line in enumerate(read(p).splitlines(), 1):
            if "onefile" in line.lower() and "禁止" not in line and "❌" not in line:
                bad_onefile.append(f"{p.relative_to(kit).as_posix()}:{i}")
    add("K5-onedir", not bad_onefile, "onefile mentioned without ban: " + ", ".join(bad_onefile) if bad_onefile else "onefile only appears as a ban")

    secrets = []
    for p in text_files(kit):
        for i, line in enumerate(read(p).splitlines(), 1):
            for rx, why in SECRET_PATTERNS:
                if rx.search(line):
                    secrets.append(f"{p.relative_to(kit).as_posix()}:{i} ({why})")
    add("K6-secrets", not secrets, "; ".join(secrets) if secrets else "no credential literals")

    gi = kit / "config/gitignore.append.txt"
    gi_text = read(gi) if gi.is_file() else ""
    need = [".env", "*.key", "secrets/", "config.local.ini"]
    miss = [n for n in need if n not in gi_text]
    add("K7-gitignore", not miss, "missing patterns: " + ", ".join(miss) if miss else "covers .env/ *.key secrets/ config.local.ini")

    http = [p.relative_to(kit).as_posix() for p in text_files(kit) if "http://" in read(p)]
    add("K8-https-only", not http, "plain http:// in: " + ", ".join(http) if http else "no plain http://")

    cov_missing = []
    for doc in [kit / "docs/agents/README.md", kit / "docs/agents/00-base.md"]:
        if not doc.is_file():
            cov_missing.append(doc.name + " absent")
            continue
        body = read(doc)
        for num in ("80%", "90%"):
            if num not in body:
                cov_missing.append(f"{doc.name} lacks {num}")
    add("K9-coverage", not cov_missing, "; ".join(cov_missing) if cov_missing else "80%/90% thresholds documented")

    if target:
        absent = [f for f in LANDED if not (target / f).is_file()]
        add("K10-landed", not absent, "missing in target: " + ", ".join(absent) if absent else f"{len(LANDED)} landed files present")
        agents = target / "AGENTS.md"
        ref = "docs/agents/README.md" in read(agents) if agents.is_file() else False
        add("K11-entry-link", ref, "AGENTS.md must link docs/agents/README.md" if not ref else "AGENTS.md links the usage chapter")

    passed = sum(1 for c in checks if c["status"] == "pass")
    return checks, passed


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Read-only integrity check for the mathagent-build governance pack.",
        epilog="Exit codes: 0 pass, 1 violations, 2 usage error.",
    )
    ap.add_argument("--kit", default=None, help="path to assets/docs-pack (default: ../assets/docs-pack next to this script)")
    ap.add_argument("--target", default=None, help="optional target repository to verify the landed files")
    ap.add_argument("--max-lines", type=int, default=MAX_LINES, help="per-file line limit (default 200)")
    ap.add_argument("--list", action="store_true", help="print the required file manifest and exit")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON on stdout")
    args = ap.parse_args(argv)

    kit = Path(args.kit) if args.kit else Path(__file__).resolve().parent.parent / "assets" / "docs-pack"
    if args.list:
        print("\n".join(MANIFEST))
        return 0
    if not kit.is_dir():
        print(f"error: kit directory not found: {kit}", file=sys.stderr)
        return 2
    target = Path(args.target) if args.target else None
    if target is not None and not target.is_dir():
        print(f"error: target directory not found: {target}", file=sys.stderr)
        return 2

    try:
        checks, passed = run_checks(kit.resolve(), target.resolve() if target else None, args.max_lines)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    total = len(checks)
    failed = total - passed
    score = round(100 * passed / total, 1) if total else 0.0
    result = {
        "status": "pass" if failed == 0 else "fail",
        "kit": str(kit.resolve()),
        "target": str(target.resolve()) if target else None,
        "score": score,
        "checks": checks,
        "violations": [c["detail"] for c in checks if c["status"] == "fail"],
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"mathagent-build pack check: {result['status']} (score {score})")
        for c in checks:
            print(f"  [{c['status'].upper():4}] {c['id']}: {c['detail']}")
        if failed:
            print("\nviolations:")
            for v in result["violations"]:
                print(f"  - {v}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
