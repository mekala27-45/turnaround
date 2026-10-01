"""Run the chapters stage on a small simulated warehouse and write its manifest as JSON to the path
given. The determinism test runs this twice, under two PYTHONHASHSEED values, and compares them."""

from __future__ import annotations

import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "pipeline"))

from test_chapters_stage import build_sim_warehouse  # noqa: E402
from turnaround_core.paths import Paths  # noqa: E402
from turnaround_pipeline.stages import chapters  # noqa: E402
from turnaround_sim.network import SimSpec  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "packages" / "core").mkdir(parents=True)
        (root / "pyproject.toml").write_text("[project]\nname = 'fixture'\n")
        (root / "data").mkdir()
        shutil.copy(ROOT / "data" / "carriers.csv", root / "data" / "carriers.csv")
        db = root / "sim.duckdb"
        truth = build_sim_warehouse(db, SimSpec(seed=7, days=730, start="2022-01-01", meltdown_day=600))
        events = root / "data" / "known_events.csv"
        with events.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["event", "start", "end", "unit_type", "units", "window", "citation"])
            writer.writerow(
                ["planted", truth["start"], truth["end"], "carrier", truth["meltdown_carrier"], "test", "sim"]
            )
        manifest = chapters.run(
            Paths(root),
            warehouse_db=db,
            replicates=40,
            hubs=4,
            events_path=events,
            meltdowns=((truth["meltdown_carrier"], truth["start"], truth["end"]),),
        )
        out = root / "m.json"
        manifest.save(out)
        payload = json.loads(out.read_text(encoding="utf-8"))
        Path(sys.argv[1]).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
