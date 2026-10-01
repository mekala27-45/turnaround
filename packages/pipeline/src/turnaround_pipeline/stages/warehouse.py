"""Stage two: dbt builds and tests the warehouse over the derived parquet, then the shipped marts are exported.

dbt runs from warehouse/ so the sources' relative paths resolve to the repository's data folder. Its
run results are read back for the counts the README prints (models, tests, failures), and a failing
test fails the stage. The marts the site, the workbook and the BI extracts read are copied to
results/marts as parquet, sorted by their keys so the files are byte for byte the same on a rerun.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from turnaround_core.manifest import Manifest, Scribe
from turnaround_core.paths import Paths

from turnaround_pipeline.common import new_partial, save_partial

SHIPPED: dict[str, tuple[str, ...]] = {
    "mart_carrier_month": ("carrier", "year", "month"),
    "mart_route_month": ("route", "carrier", "year", "month"),
    "mart_hour_profile": ("year", "month", "day_of_week", "dep_hour"),
    "mart_delay_histogram": ("carrier", "year", "month", "minute"),
    "mart_quarantine": ("carrier", "year", "month"),
    "mart_leg_position": ("carrier", "year", "leg_position"),
    "mart_carrier_day": ("carrier", "flight_date"),
    "mart_airport_day": ("airport", "flight_date"),
}


class WarehouseError(RuntimeError):
    pass


def dbt_executable() -> str:
    candidate = Path(sys.executable).with_name("dbt")
    return str(candidate) if candidate.exists() else "dbt"


def run_dbt(p: Paths, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.setdefault("TURNAROUND_WAREHOUSE_PATH", str(p.warehouse_db))
    env.setdefault("TURNAROUND_DUCKDB_TMP", str(p.scratch / "duckdb_tmp"))
    p.scratch.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [dbt_executable(), *args, "--profiles-dir", "."],
        cwd=p.warehouse,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def summarise_results(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    counts = {"models": 0, "tests": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0, "warned": 0}
    for result in payload.get("results", []):
        unique_id = str(result.get("unique_id", ""))
        status = str(result.get("status", ""))
        if unique_id.startswith("model."):
            counts["models"] += 1
            if status == "error":
                counts["errors"] += 1
        elif unique_id.startswith("test."):
            counts["tests"] += 1
            counts["passed"] += status == "pass"
            counts["failed"] += status == "fail"
            counts["errors"] += status == "error"
            counts["warned"] += status == "warn"
        counts["skipped"] += status == "skipped"
    return counts


def export_marts(p: Paths) -> dict[str, int]:
    import duckdb

    p.marts.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(p.warehouse_db), read_only=True)
    con.execute("set enable_progress_bar = false")
    rows: dict[str, int] = {}
    for name, keys in SHIPPED.items():
        out = p.marts / f"{name}.parquet"
        con.execute(
            f"copy (select * from {name} order by {', '.join(keys)}) to '{out.as_posix()}' "
            "(format parquet, compression zstd, row_group_size 100000)"
        )
        count = con.execute(f"select count(*) from {name}").fetchone()
        rows[name] = int(count[0]) if count else 0
    con.close()
    return rows


def run(p: Paths) -> Manifest:
    from turnaround_pipeline.generated_sql import stale

    problems = stale()
    if problems:
        raise WarehouseError(
            f"generated warehouse models are stale, run scripts/build_warehouse_sql.py --write: {problems}"
        )
    built = run_dbt(p, "build")
    results_file = p.warehouse / "target" / "run_results.json"
    counts = summarise_results(results_file) if results_file.exists() else {}
    if built.returncode != 0:
        raise WarehouseError("dbt build failed:\n" + built.stdout[-4000:] + built.stderr[-2000:])
    rows = export_marts(p)
    out = p.results / "warehouse"
    out.mkdir(parents=True, exist_ok=True)
    (out / "build_summary.json").write_text(
        json.dumps({"counts": counts, "mart_rows": rows}, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest = new_partial("warehouse")
    s = Scribe(
        manifest,
        source="real:bts",
        population="the dbt warehouse over every flight in the window",
        origin="stages/warehouse.py",
    )
    s.put("warehouse.models", counts.get("models", 0), "int")
    s.put("warehouse.tests", counts.get("tests", 0), "int")
    s.put("warehouse.tests_passed", counts.get("passed", 0), "int")
    s.put("warehouse.tests_failed", counts.get("failed", 0) + counts.get("errors", 0), "int")
    for name, n in rows.items():
        s.put(f"warehouse.rows.{name}", n, "int")
    save_partial(p, "warehouse", manifest)
    return manifest
