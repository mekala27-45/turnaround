"""What the checklist's last lines rest on, measured rather than claimed.

``--python`` runs ruff, mypy strict and the whole pytest suite with coverage and writes
results/quality.json: the coverage percentage, whether ruff and mypy are clean, the API tests'
counts (the independent connection, audit ordering and out of process tests), the LibreOffice
recalculation test's outcome, and every test the suite skipped with its reason.

``--web`` reads the Playwright JSON report (web/test-results/results.json, written by
`npm --prefix web run test:e2e`) and writes results/web_tests.json with the counts and titles.

    uv run python scripts/quality_report.py --python --web
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECALC_TEST = "test_recalculated_summary_equals_the_metric_values"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def junit_cases(path: Path) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    for case in ET.parse(path).getroot().iter("testcase"):
        outcome, reason = "passed", ""
        for child in case:
            if child.tag in {"failure", "error"}:
                outcome = "failed"
            elif child.tag == "skipped":
                outcome, reason = "skipped", child.get("message", "")
        cases.append(
            {
                "file": case.get("classname", ""),
                "name": case.get("name", ""),
                "outcome": outcome,
                "reason": reason,
            }
        )
    return cases


def python_quality() -> dict[str, Any]:
    ruff = run(["uv", "run", "ruff", "check", "."])
    ruff_format = run(["uv", "run", "ruff", "format", "--check", "."])
    mypy = run(["uv", "run", "mypy"])
    with tempfile.TemporaryDirectory() as tmp:
        junit = Path(tmp) / "junit.xml"
        cov = Path(tmp) / "coverage.json"
        tests = run(
            [
                "uv",
                "run",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "--cov",
                f"--cov-report=json:{cov}",
                f"--junitxml={junit}",
            ]
        )
        cases = junit_cases(junit) if junit.exists() else []
        coverage = json.loads(cov.read_text())["totals"]["percent_covered"] if cov.exists() else None
    api = [c for c in cases if c["file"].startswith("tests.api")]
    recalc = [c for c in cases if c["name"] == RECALC_TEST]
    return {
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "ruff": "clean" if ruff.returncode == 0 and ruff_format.returncode == 0 else "problems",
        "mypy": "clean" if mypy.returncode == 0 else "problems",
        "coverage": None if coverage is None else round(float(coverage), 1),
        "tests": {
            "passed": sum(c["outcome"] == "passed" for c in cases),
            "failed": sum(c["outcome"] == "failed" for c in cases),
            "skipped": sum(c["outcome"] == "skipped" for c in cases),
            "exit_code": tests.returncode,
        },
        "api_tests": {
            "passed": sum(c["outcome"] == "passed" for c in api),
            "failed": sum(c["outcome"] == "failed" for c in api),
            "names": sorted(c["name"] for c in api),
        },
        "libreoffice_recalc": recalc[0]["outcome"] if recalc else "not collected",
        "skips": [
            {"test": f"{c['file']}::{c['name']}", "reason": c["reason"]}
            for c in cases
            if c["outcome"] == "skipped"
        ],
    }


def web_quality(report: Path) -> dict[str, Any]:
    if not report.exists():
        raise SystemExit(f"{report} is missing: run `npm --prefix web run test:e2e` first")
    data = json.loads(report.read_text(encoding="utf-8"))
    titles: list[dict[str, str]] = []

    def walk(suite: dict[str, Any], prefix: str) -> None:
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                results = test.get("results", [])
                status = results[-1].get("status", "unknown") if results else "unknown"
                titles.append(
                    {
                        "title": f"{prefix}{spec.get('title', '')}",
                        "project": test.get("projectName", ""),
                        "status": status,
                    }
                )
        for child in suite.get("suites", []):
            walk(child, f"{prefix}{child.get('title', '')} > " if child.get("title") else prefix)

    for suite in data.get("suites", []):
        walk(suite, "")
    return {
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "passed": sum(t["status"] == "passed" for t in titles),
        "failed": sum(t["status"] in {"failed", "timedOut", "interrupted"} for t in titles),
        "skipped": sum(t["status"] == "skipped" for t in titles),
        "tests": titles,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", action="store_true")
    parser.add_argument("--web", action="store_true")
    parser.add_argument("--web-report", default=str(ROOT / "web" / "test-results" / "results.json"))
    args = parser.parse_args()
    if not (args.python or args.web):
        parser.error("pass --python, --web or both")
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    status = 0
    if args.python:
        quality = python_quality()
        (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in quality.items() if k != "skips"}, indent=1))
        status |= int(
            quality["tests"]["failed"] > 0 or quality["ruff"] != "clean" or quality["mypy"] != "clean"
        )
    if args.web:
        web = web_quality(Path(args.web_report))
        (out / "web_tests.json").write_text(json.dumps(web, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in web.items() if k != "tests"}, indent=1))
        status |= int(web["failed"] > 0)
    return status


if __name__ == "__main__":
    sys.exit(main())
