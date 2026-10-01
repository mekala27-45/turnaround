"""The live check: the Pages site and the Fly API opened in a real browser after the deploy.

The browser session runs on a machine that can reach both hosts (the build machine cannot): every
route loaded with the statement on it, the API's health read, one check saved through the planner
with its id shown, and the planner opened again after the machine stopped on its idle timeout, so
the first probe meets the wake up and the page either answers on the second probe or shows the
recorded session, labeled. This script turns what was seen into results/live_check.json in the
shape the manifest reads, and refuses a report that names no browser, misses a route or saved no
check.

    uv run python scripts/live_check.py --observations results/scratch/live_observations.json

The observations file:

    {"browser": "Chrome 141 on Windows 11", "checked_at": "...", "site_url": "...", "api_url": "...",
     "routes": [{"route": "/", "loaded": true, "statement": true}, ...],
     "api_health_status": "ok", "check_id": "...", "check_source": "live",
     "asleep_first_probe": "503", "asleep_outcome": "answered on the second probe"}
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "live_check.json"
ROUTES = ("/", "/explore/", "/rank/", "/rotations/", "/events/", "/planner/", "/data/", "/report/")
ASLEEP_OUTCOMES = ("answered on the second probe", "showed the recorded session, labeled")


def build_report(seen: dict[str, Any]) -> dict[str, Any]:
    if not seen.get("browser"):
        raise ValueError("the observations name no browser")
    routes = list(seen.get("routes", []))
    checked = {str(r.get("route", "")).rstrip("/") + "/" for r in routes}
    missing = [r for r in ROUTES if (r.rstrip("/") + "/") not in checked]
    if missing:
        raise ValueError(f"routes not checked: {missing}")
    if not seen.get("check_id"):
        raise ValueError("no check was saved through the planner")
    asleep = str(seen.get("asleep_outcome", ""))
    if asleep and asleep not in ASLEEP_OUTCOMES:
        raise ValueError(f"asleep_outcome must be one of {ASLEEP_OUTCOMES}")
    loaded = sum(1 for r in routes if r.get("loaded"))
    statements = sum(1 for r in routes if r.get("statement"))
    passed = (
        loaded == len(routes)
        and statements == len(routes)
        and str(seen.get("api_health_status", "")) == "ok"
        and str(seen.get("check_source", "")) == "live"
        and asleep in ASLEEP_OUTCOMES
    )
    return {
        "checked_at": seen.get("checked_at") or datetime.now(UTC).isoformat(timespec="seconds"),
        "browser": seen["browser"],
        "site_url": seen.get("site_url", ""),
        "api_url": seen.get("api_url", ""),
        "routes": routes,
        "routes_total": len(routes),
        "routes_loaded": loaded,
        "statements_present": statements,
        "api_health_status": seen.get("api_health_status", ""),
        "check_id": seen["check_id"],
        "check_source": seen.get("check_source", ""),
        "asleep_first_probe": seen.get("asleep_first_probe", ""),
        "asleep_outcome": asleep or "not observed",
        "passed": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", required=True, help="JSON written from the browser session")
    args = parser.parse_args()
    seen = json.loads(Path(args.observations).read_text(encoding="utf-8"))
    try:
        report = build_report(seen)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "routes"}, indent=1))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
