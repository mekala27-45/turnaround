"""The chapters stage end to end on a two year simulated warehouse: every chapter runs, every plan is
registered first, every chart has a message and its SQL, and the calculator's marts are written."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import duckdb
import pytest
from turnaround_chapters import padding
from turnaround_chapters.plan import registry_path
from turnaround_chapters.plans import all_plans
from turnaround_core.manifest import Manifest
from turnaround_core.paths import Paths
from turnaround_rotations import reconstruct
from turnaround_sim.network import SimSpec, simulate

pytestmark = pytest.mark.slow
ROOT = Path(__file__).resolve().parents[2]


def build_sim_warehouse(db: Path, spec: SimSpec) -> dict[str, str]:
    """A warehouse file shaped like the real one: fct_flights with padding, and int_legs."""
    sim = simulate(spec)
    con = duckdb.connect(str(db))
    con.register("sim", sim.flights.to_arrow())
    con.execute("create table raw as select * from sim")
    padding.build_unimpeded(con, "raw", where_fit="year = 2022", percentile=0.10, min_flights=20)
    con.execute(f"create table fct_flights as {padding.padded_flights_sql('raw')}")
    con.execute(f"create table int_legs as {reconstruct.full_sql('fct_flights', 6.0)}")
    con.close()
    return {
        "meltdown_carrier": sim.truth.meltdown_carrier,
        "start": sim.truth.meltdown_dates[0],
        "end": sim.truth.meltdown_dates[-1],
    }


@pytest.fixture(scope="module")
def staged(tmp_path_factory: pytest.TempPathFactory) -> tuple[Paths, Manifest]:
    root = tmp_path_factory.mktemp("repo")
    (root / "packages" / "core").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname = 'fixture'\n")
    (root / "data").mkdir()
    shutil.copy(ROOT / "data" / "carriers.csv", root / "data" / "carriers.csv")
    p = Paths(root)
    db = root / "sim_warehouse.duckdb"
    truth = build_sim_warehouse(db, SimSpec(seed=31, days=730, start="2022-01-01", meltdown_day=600))
    events = root / "data" / "known_events.csv"
    with events.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["event", "start", "end", "unit_type", "units", "window", "citation"])
        writer.writerow(
            [
                "planted meltdown",
                truth["start"],
                truth["end"],
                "carrier",
                truth["meltdown_carrier"],
                "test",
                "simulator",
            ]
        )
        writer.writerow(
            ["a fitting year disruption", "2022-06-01", "2022-06-02", "all", "", "fit", "simulator"]
        )
    from turnaround_pipeline.stages import chapters

    manifest = chapters.run(
        p,
        warehouse_db=db,
        replicates=60,
        hubs=6,
        events_path=events,
        meltdowns=((truth["meltdown_carrier"], truth["start"], truth["end"]),),
    )
    return p, manifest


def test_every_plan_is_registered_before_the_results(staged: tuple[Paths, Manifest]) -> None:
    p, manifest = staged
    for plan in all_plans():
        path = registry_path(p.results, plan)
        assert path.exists()
        assert json.loads(path.read_text())["hash"] == manifest.raw(f"plan.{plan.chapter}.hash")


def test_every_chart_has_a_message_its_sql_and_a_file(staged: tuple[Paths, Manifest]) -> None:
    p, manifest = staged
    ids = ["definition", "padding", "line", "inherited", "ranking", "causes", "meltdowns", "decision"]
    for chart_id in ids:
        figure = manifest.figures[f"chart.{chart_id}"]
        assert figure.title and figure.sql and figure.subtitle
        spec = json.loads((p.results / "charts" / f"{chart_id}.json").read_text())
        assert spec["message"] == figure.title
        assert spec["panels"] and spec["states"] and spec["sql"]


def test_intervals_bracket_their_estimates(staged: tuple[Paths, Manifest]) -> None:
    _, m = staged
    for key in (
        "ch1.on_time.change",
        "ch2.padding.change",
        "ch4.share",
        "ch6.weather_share",
        "ch8.first_advantage",
    ):
        assert m.raw(f"{key}.low") <= m.raw(key) <= m.raw(f"{key}.high")  # type: ignore[operator]


def test_calculator_marts_and_inherited_mart_are_written(staged: tuple[Paths, Manifest]) -> None:
    p, _ = staged
    for name in (
        "misconnect_cells",
        "misconnect_lost",
        "misconnect_routes",
        "misconnect_hubs",
        "misconnect_outcomes",
        "mart_inherited_month",
    ):
        assert (p.marts / f"{name}.parquet").exists()


def test_the_planted_meltdown_is_flagged(staged: tuple[Paths, Manifest]) -> None:
    _, m = staged
    assert m.raw("ch7.test.detected") == 1
