"""Reset and rederive: clear what the demo recording created, run the pipeline again from the
committed inputs in a git worktree, and prove every published figure reproduces.

Three parts:

1. Reset (``--reset``): delete the checks the demo recording, the persistence check, the separate
   client verification and the load test made in the live log, by their stated notes, with their
   scores. The demo queue and the audit log stay; the reset adds an audit row of its own. Needs
   DATABASE_URL (or TURNAROUND_RESET_DATABASE_URL) and TURNAROUND_DB_SCHEMA when the database is
   shared. On Windows, deploy/reset.ps1 does the same through Neon's HTTP endpoint.
2. Rederive: in a worktree of HEAD (the default) or in place, run every step in the order
   ``turnaround_pipeline.order.RUN_ORDER`` declares, with the committed manifest's as of date so
   the comparison is like for like. The worktree gets the raw files through a symbolic link to
   data/external; everything derived from them is rebuilt.
3. Compare: every value and every table of the new manifest against the committed one. Floats may
   differ by one part in a billion (parallel sums); wall clock timings and timestamps are reported,
   never judged; anything else is drift and the script exits non zero unless ``--allow-drift``.
   Then the gates run in the worktree.

    uv run python scripts/reset_and_rederive.py                            # worktree, every step
    uv run python scripts/reset_and_rederive.py --steps chapters --in-place
    uv run python scripts/reset_and_rederive.py --compare-only
    DATABASE_URL=... uv run python scripts/reset_and_rederive.py --reset --steps none

The summary goes to results/rederive.json and the log to logs/rederive.log.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""}:
    sys.path.insert(0, str(ROOT))

from turnaround_pipeline.order import RUN_ORDER

RELATIVE_TOLERANCE = 1e-9
COMMANDS: dict[str, list[str]] = {
    "data": ["uv", "run", "turnaround", "data"],
    "warehouse": ["uv", "run", "turnaround", "warehouse"],
    "metrics": ["uv", "run", "turnaround", "metrics"],
    "simulate": ["uv", "run", "turnaround", "simulate"],
    "recovery": ["uv", "run", "turnaround", "recovery"],
    "chapters": ["uv", "run", "turnaround", "chapters"],
    "metrics-chapters": ["uv", "run", "turnaround", "metrics", "--chapters"],
    "exports": ["uv", "run", "turnaround", "exports"],
    "manifest": ["uv", "run", "turnaround", "manifest"],
    "render": ["uv", "run", "python", "scripts/check_published_numbers.py", "--write"],
    "marts": ["uv", "run", "turnaround", "marts"],
}
GATES = (
    "scripts/check_no_em_dash.py",
    "scripts/check_vocabulary.py",
    "scripts/check_statement.py",
    "scripts/check_published_numbers.py",
    "scripts/scan_for_planted_identifiers.py",
)
# Values that record when or how fast something ran, not what it found.
TIMING_SUFFIXES = ("_seconds", ".seconds", "_at", "_ms", "checked_at", "written_at")
# Values that describe the repository (commit count, the checklist's own evidence), which moves on
# with every commit after the manifest was written; reported beside the drift, never judged as it.
REPOSITORY_PREFIXES = ("build.", "checklist.")
# Results the pipeline does not produce: they come from the live API, the browser and the release,
# so the worktree gets the committed copies rather than an empty folder.
CARRIED = (
    "results/deploy",
    "results/latency",
    "results/live_check.json",
    "results/web_tests.json",
    "results/quality.json",
    "results/release.json",
    "web/public/data/recorded_session.json",
)


def log(handle: Any, message: str) -> None:
    line = f"{datetime.now(UTC).strftime('%H:%M:%S')} {message}"
    print(line, flush=True)
    handle.write(line + "\n")
    handle.flush()


def reset_log(url: str, schema: str, handle: Any) -> dict[str, int]:
    from turnaround_api.db import RECORDING_NOTES, make_engine, reset_notes

    sync_url = (
        url.replace("postgresql://", "postgresql+psycopg://", 1) if url.startswith("postgresql://") else url
    )
    engine = make_engine(sync_url, schema)
    try:
        counts = reset_notes(engine, RECORDING_NOTES)
    finally:
        engine.dispose()
    log(handle, f"reset: removed {counts}; the demo queue and the audit log stay")
    return counts


def run(command: list[str], cwd: Path, env: dict[str, str], handle: Any) -> tuple[bool, float]:
    started = time.time()
    log(handle, "run " + " ".join(command) + f" in {cwd}")
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    handle.write(result.stdout)
    handle.write(result.stderr)
    seconds = time.time() - started
    if result.returncode != 0:
        log(handle, f"exit {result.returncode} after {seconds:,.0f} seconds")
        print(result.stdout[-3000:])
        print(result.stderr[-3000:])
        return False, seconds
    log(handle, f"finished in {seconds:,.0f} seconds")
    return True, seconds


def same_scalar(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a == b)
    if isinstance(a, int | float) and isinstance(b, int | float):
        if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
            return True
        return math.isclose(float(a), float(b), rel_tol=RELATIVE_TOLERANCE, abs_tol=1e-12)
    return bool(a == b)


def compare(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Every difference between two manifests, one line each, timings excepted."""
    drift: list[str] = []
    for bucket in ("values", "tables", "figures"):
        old = before.get(bucket, {})
        new = after.get(bucket, {})
        for key in sorted(set(old) | set(new)):
            if key not in new:
                drift.append(f"{bucket} {key}: missing after the rederive")
            elif key not in old:
                drift.append(f"{bucket} {key}: new since the committed manifest")
            elif bucket == "values":
                if key.endswith(TIMING_SUFFIXES) or key.startswith(REPOSITORY_PREFIXES):
                    continue
                if not same_scalar(old[key]["value"], new[key]["value"]):
                    drift.append(f"value {key}: {old[key]['value']!r} became {new[key]['value']!r}")
            elif bucket == "tables":
                rows_old, rows_new = old[key]["rows"], new[key]["rows"]
                if len(rows_old) != len(rows_new) or old[key]["columns"] != new[key]["columns"]:
                    drift.append(f"table {key}: shape changed")
                    continue
                for i, (ro, rn) in enumerate(zip(rows_old, rows_new, strict=True)):
                    for j, (a, b) in enumerate(zip(ro, rn, strict=True)):
                        if not same_scalar(a, b):
                            drift.append(f"table {key} row {i} column {j}: {a!r} became {b!r}")
            elif old[key] != new[key]:
                drift.append(f"figure {key}: changed")
    return drift


def timing_differences(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[Any]]:
    """Timings and repository facts that changed, for the record."""
    out: dict[str, list[Any]] = {}
    for key, entry in after.get("values", {}).items():
        reported = key.endswith(TIMING_SUFFIXES) or key.startswith(REPOSITORY_PREFIXES)
        if reported and key in before.get("values", {}) and before["values"][key]["value"] != entry["value"]:
            out[key] = [before["values"][key]["value"], entry["value"]]
    return out


def make_worktree(handle: Any) -> Path:
    """A worktree of HEAD beside the repository, with the raw files linked in."""
    target = ROOT.parent / f"{ROOT.name}-rederive"
    if target.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(target)], cwd=ROOT, check=False)
        shutil.rmtree(target, ignore_errors=True)
    subprocess.run(["git", "worktree", "prune"], cwd=ROOT, check=False)
    subprocess.run(["git", "worktree", "add", "--detach", str(target), "HEAD"], cwd=ROOT, check=True)
    external = ROOT / "data" / "external"
    if external.exists():
        link = target / "data" / "external"
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            shutil.rmtree(link)
        link.symlink_to(external.resolve(), target_is_directory=True)
    for rel in CARRIED:
        src, dst = ROOT / rel, target / rel
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    subprocess.run(["uv", "sync", "--frozen"], cwd=target, check=True, capture_output=True)
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=target, capture_output=True, text=True)
    log(handle, f"worktree at {target} ({head.stdout.strip()})")
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", default="all", help="comma separated steps, 'all' or 'none'")
    parser.add_argument(
        "--reset", action="store_true", help="delete the recording's rows from the live log first"
    )
    parser.add_argument("--compare-only", action="store_true", help="judge the last worktree run")
    parser.add_argument("--in-place", action="store_true", help="run in this checkout rather than a worktree")
    parser.add_argument("--allow-drift", action="store_true")
    parser.add_argument("--skip-gates", action="store_true")
    args = parser.parse_args()

    (ROOT / "logs").mkdir(exist_ok=True)
    committed = ROOT / "results" / "manifest.json"
    summary_path = ROOT / "results" / "rederive.json"
    with (ROOT / "logs" / "rederive.log").open("a", encoding="utf-8") as handle:
        log(handle, "reset and rederive started")
        summary: dict[str, Any] = {
            "started_at": datetime.now(UTC).isoformat(),
            "steps": {},
            "reset": None,
            "where": "in place",
        }
        if args.reset:
            url = os.environ.get("TURNAROUND_RESET_DATABASE_URL") or os.environ.get("DATABASE_URL")
            if not url:
                raise SystemExit("--reset needs DATABASE_URL or TURNAROUND_RESET_DATABASE_URL")
            summary["reset"] = reset_log(url, os.environ.get("TURNAROUND_DB_SCHEMA", ""), handle)

        if not committed.exists():
            raise SystemExit("results/manifest.json is missing; there is nothing to compare against")
        before = json.loads(committed.read_text(encoding="utf-8"))
        steps = (
            list(RUN_ORDER) if args.steps == "all" else [] if args.steps == "none" else args.steps.split(",")
        )
        unknown = [s for s in steps if s not in COMMANDS]
        if unknown:
            raise SystemExit(f"unknown steps: {unknown}; choose from {list(COMMANDS)}")
        cwd = ROOT
        worktree = ROOT.parent / f"{ROOT.name}-rederive"
        if args.compare_only:
            cwd = worktree if (worktree / "results" / "manifest.json").exists() else ROOT
        elif steps:
            if not args.in_place:
                cwd = make_worktree(handle)
                summary["where"] = str(cwd)
            summary["commit"] = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True
            ).stdout.strip()
            env = {**os.environ, "TURNAROUND_AS_OF": str(before["as_of"])}
            # Every derived step runs; manifest, render and marts close the run if a subset was asked for.
            tail = [s for s in ("manifest", "render", "marts") if s not in steps]
            for name in [*steps, *tail]:
                ok, seconds = run(COMMANDS[name], cwd, env, handle)
                summary["steps"][name] = round(seconds, 1)
                if not ok:
                    summary["failed_step"] = name
                    summary["reproduced"] = False
                    summary["status"] = f"failed at {name}"
                    summary_path.write_text(
                        json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8"
                    )
                    return 1

        after = json.loads((cwd / "results" / "manifest.json").read_text(encoding="utf-8"))
        drift = compare(before, after)
        summary["values_compared"] = len(after.get("values", {}))
        summary["tables_compared"] = len(after.get("tables", {}))
        summary["figures_compared"] = len(after.get("figures", {}))
        summary["drift"] = len(drift)
        summary["drift_lines"] = drift
        summary["timing_differences"] = timing_differences(before, after)
        for line in drift[:200]:
            log(handle, "drift: " + line)
        log(
            handle,
            f"compared {summary['values_compared']} values, {summary['tables_compared']} tables and "
            f"{summary['figures_compared']} figures; {len(drift)} drifted",
        )
        gates_ok = True
        if not args.skip_gates:
            for gate in GATES:
                ok, _ = run(["uv", "run", "python", gate], cwd, dict(os.environ), handle)
                gates_ok = gates_ok and ok
        summary["gates_passed"] = gates_ok
        summary["finished_at"] = datetime.now(UTC).isoformat()
        summary["reproduced"] = not drift and gates_ok
        summary["status"] = (
            "reproduced"
            if summary["reproduced"]
            else f"{len(drift)} figures drifted"
            if drift
            else "a gate failed"
        )
        summary_path.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        log(handle, f"summary written to {summary_path.relative_to(ROOT)}")
        if drift and not args.allow_drift:
            print(f"{len(drift)} published figures did not reproduce; see logs/rederive.log")
            return 1
        if not gates_ok:
            return 1
        print("every published figure reproduced and every gate passed" if not drift else "drift allowed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
