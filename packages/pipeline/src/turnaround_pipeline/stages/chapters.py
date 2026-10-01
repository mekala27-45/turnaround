"""The eight chapters on the flights: plans registered first, then each estimate, its numbers, its chart.

Every plan is registered (hashed and written to results/plans) before any estimate runs; a plan that
changed since it was registered stops the stage. Each chapter writes its values, tables and chart
message into the partial manifest, its chart specification into results/charts, and anything the site
or the API reads into results/marts. Chapter 4 also writes legs_inherited into the warehouse, which the
metric layer reconciles against the shipped mart_inherited_month.
"""

from __future__ import annotations

import csv
import json
import os
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import polars as pl
from turnaround_chapters import (
    ch01_definition,
    ch02_padding,
    ch03_line,
    ch04_inherited,
    ch05_ranking,
    ch06_causes,
    ch07_meltdowns,
    ch08_decision,
)
from turnaround_chapters.plan import register, report_years
from turnaround_chapters.plans import all_plans
from turnaround_core.config import POLICY
from turnaround_core.frames import num
from turnaround_core.log import get_logger
from turnaround_core.manifest import Manifest, Scribe
from turnaround_core.paths import Paths
from turnaround_misconnect import marts as misconnect_marts
from turnaround_stats.density import DEFAULT_PLACEBOS

from turnaround_pipeline.charts import Annotation, Chart, Panel, Series, State
from turnaround_pipeline.common import connect, new_partial, save_partial

log = get_logger(__name__)

# What each chapter is about, as a heading. The registered title states the plan's claim, which the
# estimate can contradict; the heading names the subject, and the method note quotes the claim.
HEADINGS: dict[int, str] = {
    1: "What on time measures",
    2: "Padding in the schedule",
    3: "The fifteen minute line",
    4: "Inherited delay",
    5: "The fair ranking",
    6: "Causes, reported and estimated",
    7: "Meltdowns and recovery",
    8: "The reader's decision",
}
MELTDOWNS: tuple[tuple[str, str, str], ...] = (
    ("WN", "2022-12-21", "2022-12-30"),
    ("DL", "2024-07-19", "2024-07-25"),
)
CHAPTER_SOURCES = {
    1: "real:bts",
    2: "real:bts",
    3: "real:bts",
    4: "real:bts",
    5: "real:bts+faa",
    6: "real:bts+open_meteo",
    7: "real:bts",
    8: "real:bts",
}


@dataclass(frozen=True)
class Window:
    first_year: int
    last_year: int
    last_full_year: int
    test_first: int
    latest: tuple[int, int]

    @property
    def test_where(self) -> str:
        return report_years(self.test_first, self.last_year)

    @property
    def test_legs_where(self) -> str:
        return f"year(flight_date) between {self.test_first} and {self.last_year}"


def carrier_names(p: Paths) -> dict[str, str]:
    path = p.data / "carriers.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        return {r["code"]: r["name"] for r in csv.DictReader(handle)}


def window(con: duckdb.DuckDBPyConnection, flights: str) -> Window:
    rows = con.execute(
        f"select year, count(distinct month), max(month) from {flights} group by year order by year"
    ).fetchall()
    years = [int(r[0]) for r in rows]
    full = [int(r[0]) for r in rows if int(r[1]) == 12]
    last = years[-1]
    latest_month = int([r for r in rows if int(r[0]) == last][0][2])
    return Window(years[0], last, full[-1], POLICY.test_first_year, (last, latest_month))


def _year(value: int) -> str:
    return str(value)


def _scribe(manifest: Manifest, chapter: int, population: str, model: str = "none") -> Scribe:
    return Scribe(
        manifest,
        source=CHAPTER_SOURCES[chapter],
        population=population,
        origin=f"stages/chapters.py, chapter {chapter}",
        model=model,
    )


def _interval(s: Scribe, key: str, interval: Any, fmt: str) -> None:
    s.put(key, interval.estimate, fmt)
    s.put(f"{key}.low", interval.low, fmt)
    s.put(f"{key}.high", interval.high, fmt)


def run(
    p: Paths,
    *,
    warehouse_db: Path | None = None,
    flights: str = "wh.fct_flights",
    legs: str = "wh.int_legs",
    replicates: int | None = None,
    hubs: int | None = None,
    events_path: Path | None = None,
    meltdowns: tuple[tuple[str, str, str], ...] = MELTDOWNS,
) -> Manifest:
    plans = all_plans()
    hashes = {plan.chapter: register(p.results, plan) for plan in plans}
    reps = replicates or POLICY.bootstrap_replicates
    seed = POLICY.seed
    names = carrier_names(p)
    charts_dir = p.results / "charts"
    chapters_dir = p.results / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    # DuckDB shares the machine with the estimators' arrays (twenty million linked legs and their
    # design in chapter 4), so its buffer is held well under the memory there is; it spills past it.
    con = connect(p, memory_limit=os.environ.get("TURNAROUND_CHAPTERS_DUCKDB_MEMORY", "2GB"))
    db = warehouse_db or p.warehouse_db
    con.execute(f"attach '{db.as_posix()}' as wh")
    w = window(con, flights)
    log.info("chapters.window", first=w.first_year, last=w.last_year, full=w.last_full_year)
    manifest = new_partial("chapters")
    window_label = f"every scheduled flight, {w.first_year} to {w.latest[0]}-{w.latest[1]:02d}"
    test_label = f"scheduled flights {w.test_first} to {w.latest[0]}-{w.latest[1]:02d}"

    for plan in plans:
        s = Scribe(manifest, source="static", population="the registered plan", origin="results/plans")
        s.put(f"plan.{plan.chapter}.hash", hashes[plan.chapter], "text")
        s.put(f"plan.{plan.chapter}.title", plan.title, "text")
        s.put(f"chapter.{plan.chapter}.heading", HEADINGS[plan.chapter], "text")
        s.put(f"plan.{plan.chapter}.claim", plan.claim, "text")
        s.put(f"plan.{plan.chapter}.estimator", plan.estimator, "text")
        s.put(f"plan.{plan.chapter}.test", plan.test, "text")
        s.put(f"plan.{plan.chapter}.split", plan.split, "text")
        s.put(f"plan.{plan.chapter}.family", plan.family, "text")
        s.put(f"plan.{plan.chapter}.interval", plan.interval, "text")
        s.put(f"plan.{plan.chapter}.simulator", plan.simulator, "text")
    s = Scribe(manifest, source="real:bts", population=window_label, origin="stages/chapters.py")
    s.put("window.first_year", _year(w.first_year), "text")
    s.put("window.last_year", _year(w.last_year), "text")
    s.put("window.last_full_year", _year(w.last_full_year), "text")
    s.put("window.test_first_year", _year(w.test_first), "text")
    s.put("window.latest_month", f"{w.latest[0]}-{w.latest[1]:02d}", "text")
    s.put("window.fit_years", f"{POLICY.fit_first_year} to {POLICY.fit_last_year}", "text")

    clock = time.perf_counter()

    def done(chapter: int) -> None:
        # One line per chapter, so a run over every flight can be followed while it works.
        nonlocal clock
        now = time.perf_counter()
        log.info("chapters.done", chapter=chapter, seconds=round(now - clock, 1))
        clock = now

    _chapter1(con, flights, manifest, w, reps, seed, charts_dir, window_label)
    done(1)
    _chapter2(con, flights, manifest, w, reps, seed, charts_dir, window_label, names)
    done(2)
    _chapter3(con, flights, manifest, w, charts_dir, test_label, names)
    done(3)
    inherited = _chapter4(con, flights, legs, manifest, w, charts_dir, test_label, p)
    done(4)
    _chapter5(con, flights, manifest, w, charts_dir, test_label, names)
    done(5)
    _chapter6(con, flights, legs, manifest, w, charts_dir, test_label, inherited.estimate.min_turn)
    done(6)
    _chapter7(
        con,
        flights,
        manifest,
        w,
        seed,
        charts_dir,
        window_label,
        names,
        events_path or p.data / "known_events.csv",
        meltdowns,
    )
    done(7)
    _chapter8(con, flights, legs, manifest, w, reps, seed, charts_dir, test_label, inherited, p, hubs)
    done(8)
    con.close()
    save_partial(p, "chapters", manifest)
    (chapters_dir / "hashes.json").write_text(
        json.dumps({str(k): v for k, v in sorted(hashes.items())}, indent=1) + "\n"
    )
    return manifest


# Chapter 1 ---------------------------------------------------------------------------------------


def _chapter1(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    manifest: Manifest,
    w: Window,
    reps: int,
    seed: int,
    charts_dir: Path,
    label: str,
) -> None:
    r = ch01_definition.estimate(con, flights, replicates=reps, seed=seed)
    s = _scribe(manifest, 1, label, "bootstrap")
    s.put("ch1.first_year", _year(r.first_year), "text")
    s.put("ch1.last_year", _year(r.last_year), "text")
    _interval(s, "ch1.on_time.first", r.on_time_first, "pct1")
    _interval(s, "ch1.on_time.last", r.on_time_last, "pct1")
    _interval(s, "ch1.on_time.change", r.on_time_change, "pts1")
    _interval(s, "ch1.sched.change", r.sched_block_change, "smin1")
    _interval(s, "ch1.actual.change", r.actual_block_change, "smin1")
    _interval(s, "ch1.gap.change", r.gap_change, "smin1")
    s.put("ch1.panel_routes", r.panel_routes, "int")
    s.put("ch1.panel_share", r.panel_share, "pct1")
    s.put("ch1.flights_total", int(num(r.by_year["flown"].sum())), "int")
    rows = r.by_year.sort("year").to_dicts()
    s.table(
        "ch1.by_year",
        ["Year", "Flights flown", "On time", "Scheduled block, route panel", "Actual block, route panel"],
        ["text", "int", "pct1", "min1", "min1"],
        [
            [
                _year(x["year"]),
                x["flown"],
                x["on_time_rate"],
                x["panel_scheduled_block"],
                x["panel_actual_block"],
            ]
            for x in rows
        ],
    )
    message = ch01_definition.message(r)
    callout = (
        f"From {r.first_year} to {r.last_year} the on time rate moved {r.on_time_change.estimate * 100:+.1f} points; "
        f"on the same {r.panel_routes:,} routes the schedule moved {r.sched_block_change.estimate:+.1f} minutes and the "
        f"flying {r.actual_block_change.estimate:+.1f}."
    )
    s.figure(
        "chart.definition",
        message,
        callout,
        data="results/charts/definition.json",
        subtitle="On time rate, and scheduled and actual gate to gate minutes on a fixed panel of routes, by year",
        sql=r.sql_on_time + "\n\n-- the route panel\n" + r.sql_panel,
    )
    full = [x for x in rows if x["full_year"]]
    Chart(
        id="definition",
        kind="multiples",
        message=message,
        subtitle="On time rate, and scheduled and actual gate to gate minutes on a fixed panel of routes, by year",
        source=manifest.label("chart.definition"),
        sql=r.sql_on_time,
        x_label="Year",
        x_format="year",
        y_label="",
        y_format="",
        panels=[
            Panel(
                title="Share of flown flights arriving less than 15 minutes late",
                y_label="On time",
                y_format="pct0",
                series=[Series("On time rate", "ink", [(x["year"], x["on_time_rate"]) for x in full])],
                annotations=[
                    Annotation(
                        full[0]["year"],
                        full[0]["on_time_rate"],
                        f"{full[0]['on_time_rate'] * 100:.1f}%",
                        "base",
                    ),
                    Annotation(
                        full[-1]["year"],
                        full[-1]["on_time_rate"],
                        f"{full[-1]['on_time_rate'] * 100:.1f}%",
                        "base",
                    ),
                ],
            ),
            Panel(
                title="Gate to gate minutes on the same routes",
                y_label="Minutes",
                y_format="min0",
                series=[
                    Series("Actual", "ink", [(x["year"], x["panel_actual_block"]) for x in full]),
                    Series(
                        "Scheduled",
                        "delay",
                        [(x["year"], x["panel_scheduled_block"]) for x in full],
                        label="the schedule",
                    ),
                ],
            ),
        ],
        states=[
            State("rate", "The on time rate by year.", highlight=["On time rate"]),
            State(
                "actual",
                "The minutes flights actually spent gate to gate on the same routes.",
                highlight=["Actual"],
            ),
            State("scheduled", "The minutes the schedule allowed on those routes.", highlight=["Scheduled"]),
        ],
        table_columns=["Year", "On time", "Scheduled block", "Actual block"],
        table_rows=[
            [x["year"], x["on_time_rate"], x["panel_scheduled_block"], x["panel_actual_block"]] for x in rows
        ],
    ).write(charts_dir)


# Chapter 2 ---------------------------------------------------------------------------------------


def _chapter2(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    manifest: Manifest,
    w: Window,
    reps: int,
    seed: int,
    charts_dir: Path,
    label: str,
    names: dict[str, str],
) -> None:
    r = ch02_padding.estimate(
        con, flights, first=w.first_year, last=w.last_full_year, replicates=reps, seed=seed
    )
    s = _scribe(manifest, 2, label, "pelt")
    s.put("ch2.first_year", _year(r.first_year), "text")
    s.put("ch2.last_year", _year(r.last_year), "text")
    _interval(s, "ch2.padding.change", r.padding_change, "smin2")
    _interval(s, "ch2.actual.change", r.actual_change, "smin2")
    _interval(s, "ch2.scheduled.change", r.scheduled_change, "smin2")
    _interval(s, "ch2.gap.change", r.gap_change, "smin2")
    s.put("ch2.padding.first", r.padding_first, "min1")
    s.put("ch2.padding.last", r.padding_last, "min1")
    s.put("ch2.share_last", r.share_last, "pct1")
    s.put("ch2.hours_last", r.hours_last, "hours0")
    s.put("ch2.matched_flights_last", r.matched_flights_last, "int")
    s.put("ch2.carriers_searched", r.carriers_searched, "int")
    s.put("ch2.changepoints", len(r.changepoints), "int")
    up = [c for c in r.changepoints if c.step > 0]
    down = [c for c in r.changepoints if c.step < 0]
    s.put("ch2.changepoints_up", len(up), "int")
    s.put("ch2.changepoints_down", len(down), "int")
    biggest = max(r.changepoints, key=lambda c: (abs(c.step), c.carrier)) if r.changepoints else None
    if biggest is not None:
        s.put("ch2.biggest.carrier", names.get(biggest.carrier, biggest.carrier), "text")
        s.put("ch2.biggest.date", biggest.when.strftime("%B %Y"), "text")
        s.put("ch2.biggest.step", biggest.step, "smin1")
    s.table(
        "ch2.changepoints",
        ["Carrier", "Month", "Padding before", "Padding after", "Step"],
        ["text", "text", "min1", "min1", "smin1"],
        [
            [names.get(c.carrier, c.carrier), c.when.strftime("%Y-%m"), c.before, c.after, c.step]
            for c in r.changepoints
        ]
        or [["none", "", None, None, None]],
    )
    by_carrier = r.by_carrier_year.filter(pl.col("year").is_in([r.first_year, r.last_year]))
    wide = by_carrier.pivot(on="year", index="carrier", values="padding").sort("carrier")
    s.table(
        "ch2.by_carrier",
        ["Carrier", f"Padding {r.first_year}", f"Padding {r.last_year}"],
        ["text", "min1", "min1"],
        [
            [names.get(x["carrier"], x["carrier"]), x.get(str(r.first_year)), x.get(str(r.last_year))]
            for x in wide.to_dicts()
        ],
    )
    message = ch02_padding.message(r)
    callout = (
        f"On the same routes, carriers, hours and months, padding moved {r.padding_change.estimate:+.2f} minutes from "
        f"{r.first_year} to {r.last_year} while the flying moved {r.actual_change.estimate:+.2f}; PELT found "
        f"{len(r.changepoints)} steps of a minute or more across {r.carriers_searched} carriers."
    )
    s.figure(
        "chart.padding",
        message,
        callout,
        data="results/charts/padding.json",
        subtitle="Mean padding per flight by month, minutes over the unimpeded block time, with each carrier's steps",
        sql=r.sql_series,
    )
    monthly = r.monthly.sort("period").to_dicts()
    Chart(
        id="padding",
        kind="line",
        message=message,
        subtitle="Mean padding per flight by month, minutes over the unimpeded block time, with each carrier's steps",
        source=manifest.label("chart.padding"),
        sql=r.sql_series,
        x_label="Month",
        x_format="month",
        y_label="Padding, minutes",
        y_format="min0",
        panels=[
            Panel(
                title="All reporting carriers",
                series=[
                    Series("Padding", "delay", [(x["period"].isoformat(), x["padding"]) for x in monthly])
                ],
                annotations=[
                    Annotation(c.when.isoformat(), None, f"{c.carrier} {c.step:+.1f} min", "steps")
                    for c in sorted(r.changepoints, key=lambda c: (-abs(c.step), c.carrier))[:6]
                ],
            )
        ],
        states=[
            State("series", "Padding per flight, every month of the window."),
            State("steps", "The largest steps PELT found, carrier by carrier.", show=["steps"]),
        ],
        table_columns=["Month", "Flights", "Padding", "Padding share"],
        table_rows=[
            [x["period"].isoformat(), x["flights"], x["padding"], x["padding_share"]] for x in monthly
        ],
    ).write(charts_dir)


# Chapter 3 ---------------------------------------------------------------------------------------


def _chapter3(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    manifest: Manifest,
    w: Window,
    charts_dir: Path,
    label: str,
    names: dict[str, str],
) -> None:
    r = ch03_line.estimate(con, flights, where=w.test_where, q=POLICY.bh_q)
    s = _scribe(manifest, 3, label, "density")
    flagged = [c for c in r.carriers if c.flagged]
    s.put("ch3.carriers", len(r.carriers), "int")
    s.put("ch3.flagged", len(flagged), "int")
    s.put("ch3.flagged_names", ", ".join(names.get(c.carrier, c.carrier) for c in flagged) or "none", "text")
    s.put("ch3.pooled.z", r.pooled.z, "float2")
    s.put("ch3.pooled.p", r.pooled.p_value, "float3")
    s.put("ch3.pooled.excess", r.pooled.excess_below, "pct2")
    s.put("ch3.pooled.flights", r.pooled_flights, "int")
    s.put("ch3.placebos", r.pooled.placebos_evaluated, "int")
    s.put("ch3.placebos_planned", len(DEFAULT_PLACEBOS), "int")
    s.put("ch3.q", POLICY.bh_q, "float2")
    ordered = sorted(r.carriers, key=lambda c: (c.q_value, c.carrier))
    s.table(
        "ch3.by_carrier",
        ["Carrier", "Flights", "Excess below the line", "z against placebos", "p", "q (BH)", "Verdict"],
        ["text", "int", "pct2", "float2", "float3", "float3", "text"],
        [
            [
                names.get(c.carrier, c.carrier),
                c.flights,
                c.test.excess_below,
                c.test.z,
                c.test.p_value,
                c.q_value,
                "bunches" if c.flagged else "no evidence",
            ]
            for c in ordered
        ],
    )
    message = ch03_line.message(r)
    callout = (
        f"{len(flagged)} of {len(r.carriers)} carriers pass Benjamini-Hochberg at q = {POLICY.bh_q}; pooled, the line's "
        f"statistic sits {r.pooled.z:.2f} placebo standard deviations from the placebo mean."
    )
    s.figure(
        "chart.line",
        message,
        callout,
        data="results/charts/line.json",
        subtitle="Flights by whole minute of arrival delay, all carriers, with the fifteen minute line and the placebo lines",
        sql=r.sql,
    )
    hist = r.histogram.sort("minute").to_dicts()
    Chart(
        id="line",
        kind="histogram",
        message=message,
        subtitle="Flights by whole minute of arrival delay, all carriers, with the fifteen minute line and the placebo lines",
        source=manifest.label("chart.line"),
        sql=r.sql,
        x_label="Arrival delay, minutes",
        x_format="min0",
        y_label="Flights",
        y_format="int",
        panels=[
            Panel(
                title="All carriers",
                series=[
                    Series(
                        "Flights",
                        "ink",
                        [(x["minute"], x["flights"]) for x in hist if -30 <= x["minute"] <= 60],
                    )
                ],
                rules=[{"x": 15, "label": "15 minutes", "role": "delay", "state": "line"}]
                + [{"x": t, "faint": True, "state": "placebos"} for t in DEFAULT_PLACEBOS if t <= 60],
            )
        ],
        states=[
            State("shape", "Every flown flight in the reporting years by minute of arrival delay."),
            State("line", "The fifteen minute line.", show=["line"]),
            State("placebos", "The same test at placebo thresholds.", show=["line", "placebos"]),
        ],
        table_columns=["Minute", "Flights"],
        table_rows=[[x["minute"], x["flights"]] for x in hist],
    ).write(charts_dir)


# Chapter 4 ---------------------------------------------------------------------------------------


def _chapter4(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    legs: str,
    manifest: Manifest,
    w: Window,
    charts_dir: Path,
    label: str,
    p: Paths,
) -> ch04_inherited.InheritedResult:
    r = ch04_inherited.estimate(
        con,
        legs=legs,
        flights=flights,
        fit_year=POLICY.fit_last_year,
        test_first=w.test_first,
        test_last=w.last_year,
        bins=POLICY.turn_bins,
    )
    s = _scribe(manifest, 4, label, "propagation")
    rc = r.rotations
    s.put("ch4.legs", rc.legs, "int")
    s.put("ch4.linked", rc.linked, "int")
    s.put("ch4.rotations", rc.rotations, "int")
    s.put("ch4.tails", rc.tails, "int")
    s.put("ch4.first", rc.first, "int")
    s.put("ch4.gap", rc.gap, "int")
    s.put("ch4.broken_chain", rc.broken_chain, "int")
    s.put("ch4.impossible", rc.impossible, "int")
    s.put("ch4.linked_share", rc.linked / max(rc.legs, 1), "pct1")
    s.put("ch4.rho", r.estimate.rho, "float3")
    s.put("ch4.rho.low", r.estimate.low, "float3")
    s.put("ch4.rho.high", r.estimate.high, "float3")
    s.put("ch4.min_turn", r.estimate.min_turn, "min0")
    s.put("ch4.fit_year", _year(r.fit_year), "text")
    s.put("ch4.test_links", r.test_links, "int")
    s.put("ch4.clusters", r.estimate.clusters, "int")
    s.put("ch4.share", r.share, "pct1")
    s.put("ch4.share.low", r.share_low, "pct1")
    s.put("ch4.share.high", r.share_high, "pct1")
    s.put("ch4.reported_share", r.reported_share, "pct1")
    s.put("ch4.gap_to_reported", r.share - r.reported_share, "pts1")
    s.put("ch4.halving_buffer", r.halving_buffer, "min0")
    s.put("ch4.inherited_hours", r.inherited_minutes / 60.0, "hours0")
    crossing, crossing_minutes = ch04_inherited.across_dates(
        con,
        legs=legs,
        legs_where=ch04_inherited.window(w.test_first, w.last_year, "year(flight_date)"),
        rho=r.estimate.rho,
        min_turn=r.estimate.min_turn,
    )
    s.put("ch4.across_dates", crossing, "int")
    s.put(
        "ch4.across_dates_share",
        crossing_minutes / r.inherited_minutes if r.inherited_minutes else 0.0,
        "pct1",
    )
    s.table(
        "ch4.buffer_curve",
        ["Scheduled turn", "Legs", "Minutes passed on per late minute", "Low", "High"],
        ["text", "int", "float2", "float2", "float2"],
        [
            [f"{c.low} to {c.high} min", c.legs, c.slope, c.slope - 1.96 * c.se, c.slope + 1.96 * c.se]
            for c in r.estimate.curve
        ],
    )
    s.table(
        "ch4.profile",
        ["Minimum turn", "Residual sum of squares"],
        ["min0", "float1"],
        [[m, v] for m, v in r.estimate.profile],
    )
    ch04_inherited.write_legs_inherited(
        con,
        legs=legs,
        flights=flights,
        rho=r.estimate.rho,
        min_turn=r.estimate.min_turn,
        test_first=w.test_first,
        test_last=w.last_year,
    )
    con.execute("create or replace table wh.legs_inherited as select * from legs_inherited")
    monthly = ch04_inherited.inherited_month(con)
    p.marts.mkdir(parents=True, exist_ok=True)
    monthly.write_parquet(p.marts / "mart_inherited_month.parquet", compression="zstd", statistics=False)
    worst = ch04_inherited.worst_days(con, legs=legs, test_first=w.test_first, test_last=w.last_year)
    worst.write_parquet(p.marts / "rotation_worst_days.parquet", compression="zstd", statistics=False)
    sample_days = [d.isoformat() for d in worst["worst_day"].to_list()]
    timelines = ch04_inherited.sample_rotations(con, legs=legs, days=sample_days, per_day=20)
    timelines.write_parquet(p.marts / "rotation_samples.parquet", compression="zstd", statistics=False)
    s.put("ch4.sample_days", len(sample_days), "int")
    message = ch04_inherited.message(r)
    callout = (
        f"rho = {r.estimate.rho:.3f} on {r.test_links:,} linked legs: {r.share * 100:.1f}% of arrival delay minutes were "
        f"inherited (interval {r.share_low * 100:.1f}% to {r.share_high * 100:.1f}%), against {r.reported_share * 100:.1f}% "
        f"in the reported late aircraft field."
    )
    s.figure(
        "chart.inherited",
        message,
        callout,
        data="results/charts/inherited.json",
        subtitle="Departure delay minutes passed on per minute of late inbound arrival, by scheduled turnaround",
        sql=r.sql_legs,
    )
    curve = r.estimate.curve
    Chart(
        id="inherited",
        kind="line",
        message=message,
        subtitle="Departure delay minutes passed on per minute of late inbound arrival, by scheduled turnaround",
        source=manifest.label("chart.inherited"),
        sql=r.sql_legs,
        x_label="Scheduled turnaround, minutes",
        x_format="min0",
        y_label="Minutes passed on per late minute",
        y_format="float2",
        panels=[
            Panel(
                title="The buffer curve",
                series=[
                    Series(
                        "Passed on",
                        "delay",
                        [((c.low + c.high) / 2, c.slope) for c in curve],
                        low=[c.slope - 1.96 * c.se for c in curve],
                        high=[c.slope + 1.96 * c.se for c in curve],
                    )
                ],
                annotations=[
                    Annotation(
                        r.estimate.min_turn + r.halving_buffer,
                        None,
                        f"half passed on at {r.estimate.min_turn + r.halving_buffer:.0f} min",
                        "halving",
                    )
                ],
            )
        ],
        states=[
            State(
                "curve", "How much of a late inbound arrival the next departure inherits, by scheduled turn."
            ),
            State("halving", "The buffer at which the minutes passed on halve.", show=["halving"]),
        ],
        table_columns=["Turn from", "Turn to", "Legs", "Slope", "Standard error"],
        table_rows=[[c.low, c.high, c.legs, c.slope, c.se] for c in curve],
    ).write(charts_dir)
    return r


# Chapter 5 ---------------------------------------------------------------------------------------


def _chapter5(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    manifest: Manifest,
    w: Window,
    charts_dir: Path,
    label: str,
    names: dict[str, str],
) -> None:
    r = ch05_ranking.estimate(con, flights, where=w.test_where)
    s = _scribe(manifest, 5, label, "fixed_effects")
    s.put("ch5.carriers", len(r.rows), "int")
    s.put("ch5.cells", r.cells, "int")
    s.put("ch5.days", r.days, "int")
    s.put("ch5.moved", sum(1 for x in r.rows if x.change != 0), "int")
    up, down = ch05_ranking.biggest_movers(r)
    s.put("ch5.up.carrier", names.get(up.carrier, up.carrier), "text")
    s.put("ch5.up.raw_rank", up.raw_rank, "int")
    s.put("ch5.up.adjusted_rank", up.adjusted_rank, "int")
    s.put("ch5.down.carrier", names.get(down.carrier, down.carrier), "text")
    s.put("ch5.down.raw_rank", down.raw_rank, "int")
    s.put("ch5.down.adjusted_rank", down.adjusted_rank, "int")
    by_raw = sorted(r.rows, key=lambda x: x.raw_rank)
    by_adj = sorted(r.rows, key=lambda x: x.adjusted_rank)
    for tag, ordered in (("raw", by_raw), ("adjusted", by_adj)):
        s.put(f"ch5.{tag}.top3", ", ".join(names.get(x.carrier, x.carrier) for x in ordered[:3]), "text")
        s.put(f"ch5.{tag}.bottom3", ", ".join(names.get(x.carrier, x.carrier) for x in ordered[-3:]), "text")
    for x in r.rows:
        s.put(f"ch5.effect.{x.carrier}", x.adjusted, "smin2")
        s.put(f"ch5.raw.{x.carrier}", x.raw, "smin2")
    s.table(
        "ch5.ranking",
        [
            "Carrier",
            "Flights",
            "Raw rank",
            "Raw effect",
            "Adjusted rank",
            "Adjusted effect",
            "Interval",
            "Moved",
        ],
        ["text", "int", "int", "smin2", "int", "smin2", "text", "text"],
        [
            [
                names.get(x.carrier, x.carrier),
                x.flights,
                x.raw_rank,
                x.raw,
                x.adjusted_rank,
                x.adjusted,
                f"{x.adjusted - 1.96 * x.adjusted_se:+.2f} to {x.adjusted + 1.96 * x.adjusted_se:+.2f} min",
                "up " + str(x.change)
                if x.change > 0
                else ("down " + str(-x.change) if x.change < 0 else "same"),
            ]
            for x in r.rows
        ],
    )
    message = ch05_ranking.message(r, names)
    callout = (
        f"{names.get(up.carrier, up.carrier)} moves from {up.raw_rank} to {up.adjusted_rank} once the routes, months, hours "
        f"and aircraft are held constant; {names.get(down.carrier, down.carrier)} moves from {down.raw_rank} to "
        f"{down.adjusted_rank}."
    )
    s.figure(
        "chart.ranking",
        message,
        callout,
        data="results/charts/ranking.json",
        subtitle="Carrier rank on mean arrival delay, raw and adjusted for route, month, hour and aircraft type",
        sql=r.sql,
    )
    Chart(
        id="ranking",
        kind="slope",
        message=message,
        subtitle="Carrier rank on mean arrival delay, raw and adjusted for route, month, hour and aircraft type",
        source=manifest.label("chart.ranking"),
        sql=r.sql,
        x_label="",
        x_format="text",
        y_label="Rank, 1 is the least delay",
        y_format="int",
        panels=[
            Panel(
                title="Raw against adjusted",
                series=[
                    Series(
                        x.carrier,
                        "early" if x.change > 0 else ("delay" if x.change < 0 else "control"),
                        [("Raw", float(x.raw_rank)), ("Adjusted", float(x.adjusted_rank))],
                        label=names.get(x.carrier, x.carrier),
                    )
                    for x in by_adj
                ],
            )
        ],
        states=[
            State("raw", "The raw ranking: mean arrival delay against the average carrier."),
            State("adjusted", "Held constant what each carrier flies.", show=["adjusted"]),
            State("movers", "The largest moves.", highlight=[up.carrier, down.carrier]),
        ],
        table_columns=[
            "Carrier",
            "Raw rank",
            "Raw effect",
            "Adjusted rank",
            "Adjusted effect",
            "Adjusted se",
        ],
        table_rows=[
            [x.carrier, x.raw_rank, x.raw, x.adjusted_rank, x.adjusted, x.adjusted_se] for x in r.rows
        ],
    ).write(charts_dir)


# Chapter 6 ---------------------------------------------------------------------------------------


def _chapter6(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    legs: str,
    manifest: Manifest,
    w: Window,
    charts_dir: Path,
    label: str,
    min_turn: int,
) -> None:
    r = ch06_causes.estimate(con, flights, where=w.test_where, legs=legs, min_turn=min_turn)
    s = _scribe(
        manifest, 6, label + ", flights between two Core 30 airports for the weather model", "weather_fe"
    )
    s.put("ch6.flights_modelled", r.flights_modelled, "int")
    s.put("ch6.days", r.days, "int")
    s.put("ch6.weather_share", r.weather_share, "pct1")
    s.put("ch6.weather_share.low", r.weather_share_low, "pct1")
    s.put("ch6.weather_share.high", r.weather_share_high, "pct1")
    s.put("ch6.reported_weather_share", r.reported_weather_share, "pct1")
    s.put("ch6.reported_nas_share", r.reported_nas_share, "pct1")
    s.put("ch6.reported_weather_cause_share", r.reported_weather_cause_share, "pct1")
    ratio = r.weather_share / r.reported_weather_share if r.reported_weather_share else None
    s.put("ch6.ratio", ratio, "float1")
    s.put("ch6.carried", r.carried_coefficient, "float3")
    latest = r.by_year.sort("year").to_dicts()
    s.table(
        "ch6.reported_by_year",
        ["Year", "Late aircraft", "Carrier", "Air traffic system", "Weather", "Security"],
        ["text", "pct1", "pct1", "pct1", "pct1", "pct2"],
        [
            [
                _year(x["year"]),
                x["late_aircraft_share"],
                x["carrier_share"],
                x["nas_share"],
                x["weather_share"],
                x["security_share"],
            ]
            for x in latest
        ],
    )
    s.table(
        "ch6.nas_by_airport",
        ["Airport", "Flights", "Air traffic system share of cause minutes", "Air traffic minutes per flight"],
        ["text", "int", "pct1", "min2"],
        [
            [x["airport"], x["flights"], x["nas_share"], x["nas_minutes_per_flight"]]
            for x in r.nas_by_airport.head(10).to_dicts()
        ],
    )
    s.table(
        "ch6.coefficients",
        ["Weather term", "Minutes", "Standard error"],
        ["text", "smin2", "float2"],
        [[n.replace("_", " "), b, se] for n, b, se in r.coefficients],
    )
    top = r.nas_by_airport.head(3)["airport"].to_list()
    s.put("ch6.nas_top3", ", ".join(top), "text")
    message = ch06_causes.message(r)
    callout = (
        f"Weather at the two ends of the flight explains {r.weather_share * 100:.1f}% of arrival delay minutes "
        f"(interval {r.weather_share_low * 100:.1f}% to {r.weather_share_high * 100:.1f}%); the weather field records "
        f"{r.reported_weather_share * 100:.1f}% and the air traffic system field {r.reported_nas_share * 100:.1f}%."
    )
    s.figure(
        "chart.causes",
        message,
        callout,
        data="results/charts/causes.json",
        subtitle="Share of arrival delay minutes: the reported cause fields beside the weather model's estimate",
        sql=r.sql_model,
    )
    Chart(
        id="causes",
        kind="bars",
        message=message,
        subtitle="Share of arrival delay minutes: the reported cause fields beside the weather model's estimate",
        source=manifest.label("chart.causes"),
        sql=r.sql_model,
        x_label="Share of arrival delay minutes",
        x_format="pct0",
        y_label="",
        y_format="text",
        panels=[
            Panel(
                title="Flights between two Core 30 airports, reporting years",
                series=[
                    Series(
                        "Reported weather field",
                        "control",
                        [("Reported weather field", r.reported_weather_share)],
                    ),
                    Series(
                        "Reported air traffic system field",
                        "control",
                        [("Reported air traffic system field", r.reported_nas_share)],
                    ),
                    Series(
                        "Estimated from the weather",
                        "delay",
                        [("Estimated from the weather", r.weather_share)],
                        low=[r.weather_share_low],
                        high=[r.weather_share_high],
                    ),
                ],
            )
        ],
        states=[
            State("reported", "What the carriers reported.", highlight=["Reported weather field"]),
            State(
                "nas",
                "Where most weather goes in the reporting: the air traffic system field.",
                highlight=["Reported air traffic system field"],
            ),
            State("estimated", "What the weather itself explains.", highlight=["Estimated from the weather"]),
        ],
        table_columns=["Measure", "Share", "Low", "High"],
        table_rows=[
            ["Reported weather field", r.reported_weather_share, None, None],
            ["Reported air traffic system field", r.reported_nas_share, None, None],
            ["Estimated from the weather", r.weather_share, r.weather_share_low, r.weather_share_high],
        ],
    ).write(charts_dir)


# Chapter 7 ---------------------------------------------------------------------------------------


def _chapter7(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    manifest: Manifest,
    w: Window,
    seed: int,
    charts_dir: Path,
    label: str,
    names: dict[str, str],
    events_path: Path,
    meltdowns: tuple[tuple[str, str, str], ...],
) -> None:
    known = ch07_meltdowns.load_events(events_path)
    plan = next(x for x in all_plans() if x.chapter == 7)
    r = ch07_meltdowns.estimate(
        con,
        flights,
        known=known,
        split=date(POLICY.test_first_year, 1, 1),
        meltdowns=[(c, date.fromisoformat(a), date.fromisoformat(b)) for c, a, b in meltdowns],
        cost_false_alarm=float(plan.policy["cost_false_alarm"]),
        cost_miss=float(plan.policy["cost_miss"]),
        seed=seed,
    )
    s = _scribe(manifest, 7, label, "detector")
    op = r.operating
    s.put("ch7.threshold", op.threshold, "float1")
    s.put("ch7.interior", "inside the grid" if op.interior else "at the edge of the grid", "text")
    s.put("ch7.grid_low", op.grid[0], "float1")
    s.put("ch7.grid_high", op.grid[-1], "float1")
    s.put("ch7.cost_false_alarm", op.cost_false_alarm, "float1")
    s.put("ch7.cost_miss", op.cost_miss, "float1")
    s.put("ch7.fit.events", r.fit.events, "int")
    s.put("ch7.fit.detected", r.fit.detected, "int")
    s.put("ch7.fit.false_alarms", r.fit.false_alarm_episodes, "int")
    s.put("ch7.test.events", r.test.events, "int")
    s.put("ch7.test.detected", r.test.detected, "int")
    s.put("ch7.test.recall", r.test.recall, "pct0")
    s.put("ch7.test.false_alarms", r.test.false_alarm_episodes, "int")
    s.put("ch7.test.episodes", r.test.episodes, "int")
    s.put("ch7.test.unit_days", r.test.unit_days, "int")
    s.put("ch7.test.false_per_thousand", r.test.false_alarms_per_thousand_unit_days, "float2")
    lags = [e.lag_days for e in r.events if e.window == "test" and e.lag_days is not None]
    s.put("ch7.test.median_lag", sorted(lags)[len(lags) // 2] if lags else None, "days1")
    s.put("ch7.airports", len(r.airports), "int")
    s.put("ch7.carriers", r.carriers, "int")
    s.put("ch7.trait.statistic", r.trait_statistic, "float2")
    s.put("ch7.trait.p", r.trait_p_value, "float3")
    s.put("ch7.trait.carriers", r.trait_carriers, "int")
    s.table(
        "ch7.events",
        ["Event", "Onset", "Window", "Units", "Flagged", "First alert", "Days after onset"],
        ["text", "text", "text", "text", "text", "text", "int"],
        [
            [
                e.name,
                e.start.isoformat(),
                "fitting" if e.window == "fit" else "reporting",
                e.units,
                "yes" if e.detected else "no",
                e.first_alert.isoformat() if e.first_alert else "none",
                e.lag_days,
            ]
            for e in r.events
        ],
    )
    s.table(
        "ch7.operating",
        ["Threshold", "Cost"],
        ["float1", "float1"],
        [[t, c] for t, c in zip(op.grid, op.costs, strict=True)],
    )
    test_episodes = detect_episodes(r, POLICY.test_first_year)
    s.table(
        "ch7.top_episodes",
        ["Unit", "First day", "Days", "Peak score"],
        ["text", "text", "int", "float1"],
        test_episodes or [["none", "", 0, None]],
    )
    s.table(
        "ch7.recovery_by_carrier",
        ["Carrier", "Alert episodes", "Median days", "Mean days", "Longest"],
        ["text", "int", "days1", "days1", "int"],
        [
            [
                names.get(x["carrier"], x["carrier"]),
                x["episodes"],
                x["median_days"],
                x["mean_days"],
                x["longest_days"],
            ]
            for x in r.recovery_by_carrier.to_dicts()
        ]
        or [["no carrier alert episodes", 0, None, None, None]],
    )
    panels: list[Panel] = []
    for st in r.studies:
        tag = st.carrier
        s.put(f"ch7.study.{tag}.carrier", names.get(tag, tag), "text")
        s.put(f"ch7.study.{tag}.onset", st.onset.isoformat(), "text")
        s.put(f"ch7.study.{tag}.end", st.window_end.isoformat(), "text")
        s.put(f"ch7.study.{tag}.excess_cancelled", st.excess_cancelled, "int")
        s.put(f"ch7.study.{tag}.excess_delay_hours", st.excess_delay_minutes / 60.0, "hours0")
        s.put(f"ch7.study.{tag}.recovery_days", st.recovery_days, "int")
        s.put(f"ch7.study.{tag}.peak_gap", st.peak_gap, "pts1")
        s.put(f"ch7.study.{tag}.airports", ", ".join(st.airports), "text")
        series = st.series.sort("day").to_dicts()
        panels.append(
            Panel(
                title=f"{names.get(tag, tag)}, {st.onset.strftime('%B %Y')}",
                y_label="Share of scheduled flights cancelled",
                y_format="pct0",
                series=[
                    Series(
                        names.get(tag, tag),
                        "delay",
                        [(x["day"].isoformat(), x["treated_rate"]) for x in series],
                    ),
                    Series(
                        "Other carriers at the same airports",
                        "control",
                        [(x["day"].isoformat(), x["peer_rate"]) for x in series],
                    ),
                ],
                bands=[
                    {"from": st.onset.isoformat(), "to": st.window_end.isoformat(), "label": "the disruption"}
                ],
                annotations=(
                    [
                        Annotation(
                            st.onset.isoformat(),
                            None,
                            f"back to its peers after {st.recovery_days} days"
                            if st.recovery_days is not None
                            else "not back within three weeks",
                            "recovery",
                        )
                    ]
                ),
            )
        )
    message = ch07_meltdowns.message(r, names)
    s.figure(
        "chart.meltdowns",
        message,
        f"Threshold {op.threshold:.1f} chosen on {POLICY.fit_first_year} to {POLICY.fit_last_year} "
        f"({'inside' if op.interior else 'at the edge of'} the grid); {r.test.detected} of {r.test.events} reporting year events flagged.",
        data="results/charts/meltdowns.json",
        subtitle="Daily cancellation rate of the carrier against other carriers at its ten busiest airports",
        sql=r.sql_daily,
    )
    Chart(
        id="meltdowns",
        kind="event",
        message=message,
        subtitle="Daily cancellation rate of the carrier against other carriers at its ten busiest airports",
        source=manifest.label("chart.meltdowns"),
        sql=r.sql_daily,
        x_label="Day",
        x_format="date",
        y_label="Cancelled",
        y_format="pct0",
        panels=panels,
        states=[
            State(
                "first",
                "The first meltdown against its peers.",
                highlight=[panels[0].series[0].name] if panels else [],
            ),
            State("second", "The second.", highlight=[panels[-1].series[0].name] if panels else []),
            State("recovery", "How long each took to get back to its peers.", show=["recovery"]),
        ],
        table_columns=["Event", "First alert", "Days after onset"],
        table_rows=[
            [e.name, e.first_alert.isoformat() if e.first_alert else None, e.lag_days] for e in r.events
        ],
    ).write(charts_dir)


def detect_episodes(r: ch07_meltdowns.MeltdownResult, first_year: int, top: int = 25) -> list[list[Any]]:
    """The reporting years' alert episodes with the highest peak scores, ties broken by unit and day."""
    found = r.episodes.filter(pl.col("start") >= date(first_year, 1, 1))
    found = found.sort(["peak", "unit", "start"], descending=[True, False, False]).head(top)
    return [
        [
            str(x["unit"]).replace("carrier:", "carrier ").replace("airport:", "airport "),
            x["start"].isoformat(),
            x["days"],
            x["peak"],
        ]
        for x in found.to_dicts()
    ]


# Chapter 8 ---------------------------------------------------------------------------------------


def _chapter8(
    con: duckdb.DuckDBPyConnection,
    flights: str,
    legs: str,
    manifest: Manifest,
    w: Window,
    reps: int,
    seed: int,
    charts_dir: Path,
    label: str,
    inherited: ch04_inherited.InheritedResult,
    p: Paths,
    hubs: int | None,
) -> None:
    k = hubs or POLICY.hub_count
    r = ch08_decision.estimate(
        con,
        flights,
        legs=legs,
        where=w.test_where,
        legs_where=w.test_legs_where,
        rho=inherited.estimate.rho,
        min_turn=inherited.estimate.min_turn,
        hubs=k,
        min_connection=POLICY.min_connection_minutes,
        line=POLICY.misconnect_line,
        replicates=reps,
        seed=seed,
    )
    s = _scribe(manifest, 8, label, "misconnect")
    s.put("ch8.first_on_time", r.first_on_time, "pct1")
    s.put("ch8.later_on_time", r.later_on_time, "pct1")
    _interval(s, "ch8.first_advantage", r.first_advantage, "pts1")
    hours = r.by_hour.filter(pl.col("flights") >= 10000).sort(
        ["on_time_rate", "key"], descending=[True, False]
    )
    s.put("ch8.best_hour", f"{int(hours['key'][0]):02d}:00", "text")
    s.put("ch8.best_hour_rate", float(hours["on_time_rate"][0]), "pct1")
    s.put("ch8.worst_hour", f"{int(hours['key'][-1]):02d}:00", "text")
    s.put("ch8.worst_hour_rate", float(hours["on_time_rate"][-1]), "pct1")
    months = r.by_month.sort(["on_time_rate", "key"], descending=[True, False])
    s.put("ch8.best_month", date(2000, int(months["key"][0]), 1).strftime("%B"), "text")
    s.put("ch8.worst_month", date(2000, int(months["key"][-1]), 1).strftime("%B"), "text")
    s.put("ch8.line", POLICY.misconnect_line, "pct0")
    s.put("ch8.min_connection", POLICY.min_connection_minutes, "min0")
    s.put("ch8.hubs", len(r.hubs), "int")
    s.put("ch8.hubs_interior", sum(1 for h in r.hubs if h.interior), "int")
    for i, h in enumerate(r.hubs[:3], start=1):
        s.put(f"ch8.hub{i}.code", h.hub, "text")
        s.put(f"ch8.hub{i}.buffer", h.crossing, "min0")
        s.put(f"ch8.hub{i}.low", h.crossing_low, "min0")
        s.put(f"ch8.hub{i}.high", h.crossing_high, "min0")
    crossings = [h.crossing for h in r.hubs if h.crossing is not None]
    s.put("ch8.buffer_min", min(crossings) if crossings else None, "min0")
    s.put("ch8.buffer_max", max(crossings) if crossings else None, "min0")
    s.put("ch8.binding_share", r.binding_share, "pct1")
    s.put("ch8.binding_after_binding", r.binding_after_binding, "pct1")
    s.put("ch8.trade_overall", r.trade_overall, "float2")
    pays = r.trade_airports.filter(pl.col("pays"))
    s.put("ch8.trade_pays_airports", pays.height, "int")
    s.put(
        "ch8.trade_best_airport", r.trade_airports["airport"][0] if r.trade_airports.height else None, "text"
    )
    s.put(
        "ch8.trade_best_saved",
        float(r.trade_airports["saved_per_minute"][0]) if r.trade_airports.height else None,
        "float2",
    )
    s.table(
        "ch8.by_hour",
        ["Scheduled departure hour", "Flights", "On time", "Mean arrival delay"],
        ["text", "int", "pct1", "smin1"],
        [
            [f"{int(x['key']):02d}:00", x["flights"], x["on_time_rate"], x["mean_delay"]]
            for x in r.by_hour.to_dicts()
        ],
    )
    s.table(
        "ch8.by_dow",
        ["Day", "Flights", "On time", "Mean arrival delay"],
        ["text", "int", "pct1", "smin1"],
        [
            [
                ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[
                    int(x["key"]) - 1
                ],
                x["flights"],
                x["on_time_rate"],
                x["mean_delay"],
            ]
            for x in r.by_dow.to_dicts()
            if 1 <= int(x["key"]) <= 7
        ],
    )
    s.table(
        "ch8.by_month",
        ["Month", "Flights", "On time", "Mean arrival delay"],
        ["text", "int", "pct1", "smin1"],
        [
            [date(2000, int(x["key"]), 1).strftime("%B"), x["flights"], x["on_time_rate"], x["mean_delay"]]
            for x in r.by_month.to_dicts()
        ],
    )
    s.table(
        "ch8.by_position",
        ["Leg of the aircraft's day", "Flights", "On time", "Mean arrival delay"],
        ["text", "int", "pct1", "smin1"],
        [
            [
                "first"
                if int(x["position"]) == 1
                else ("sixth or later" if int(x["position"]) >= 6 else str(int(x["position"]))),
                x["flights"],
                x["on_time_rate"],
                x["mean_delay"],
            ]
            for x in r.by_position.to_dicts()
        ],
    )
    s.table(
        "ch8.hubs",
        ["Hub", "Days", "Inbound flights", "Buffer for under the line", "Interval", "Interior"],
        ["text", "int", "int", "min0", "text", "text"],
        [
            [
                h.hub,
                h.days,
                h.inbound,
                h.crossing,
                f"{h.crossing_low} to {h.crossing_high} min"
                if h.crossing_low is not None and h.crossing_high is not None
                else "beyond the grid",
                "yes" if h.interior else "no",
            ]
            for h in r.hubs
        ],
    )
    s.table(
        "ch8.trade_airports",
        [
            "Airport",
            "Turns",
            "Turns reached by a late inbound",
            "Arrival minutes saved per buffer minute",
            "Pays",
        ],
        ["text", "int", "pct1", "float2", "text"],
        [
            [
                x["airport"],
                x["turns"],
                x["binding_share"],
                x["saved_per_minute"],
                "yes" if x["pays"] else "no",
            ]
            for x in r.trade_airports.to_dicts()
        ]
        or [["none", 0, None, None, "no"]],
    )
    routes = r.trade_routes.head(10).to_dicts()
    s.table(
        "ch8.trade_routes",
        [
            "Route",
            "Turns",
            "Turns reached by a late inbound",
            "Arrival minutes saved per buffer minute",
            "Pays",
        ],
        ["text", "int", "pct1", "float2", "text"],
        [
            [x["route"], x["turns"], x["binding_share"], x["saved_per_minute"], "yes" if x["pays"] else "no"]
            for x in routes
        ]
        or [["none with enough turns", 0, None, None, "no"]],
    )
    top = r.hubs[0]
    message = ch08_decision.message(r)
    s.figure(
        "chart.decision",
        message,
        f"At {top.hub}, the busiest airport, the chance of missing a connection falls under {POLICY.misconnect_line:.0%} "
        f"at a {top.crossing} minute buffer; the first leg of the aircraft's day is on time {r.first_on_time * 100:.1f}% of "
        f"the time against {r.later_on_time * 100:.1f}% for the rest.",
        data="results/charts/decision.json",
        subtitle="Chance of missing a connection by scheduled buffer at the three busiest hubs, with the line",
        sql=r.sql_hour,
    )
    roles = ("delay", "early", "adjusted")
    Chart(
        id="decision",
        kind="curves",
        message=message,
        subtitle="Chance of missing a connection by scheduled buffer at the three busiest hubs, with the line",
        source=manifest.label("chart.decision"),
        sql=r.sql_hour,
        x_label="Scheduled buffer, minutes",
        x_format="min0",
        y_label="Chance of missing the connection",
        y_format="pct0",
        panels=[
            Panel(
                title="Misconnect curves",
                series=[
                    Series(
                        h.hub,
                        roles[i],
                        list(zip(h.buffers, h.probability, strict=True)),
                        low=h.low,
                        high=h.high,
                        label=h.hub,
                    )
                    for i, h in enumerate(r.hubs[:3])
                ],
                rules=[
                    {
                        "y": POLICY.misconnect_line,
                        "label": f"{POLICY.misconnect_line:.0%} line",
                        "role": "control",
                    }
                ],
                annotations=[
                    Annotation(h.crossing, POLICY.misconnect_line, f"{h.hub} {h.crossing} min", "buffers")
                    for h in r.hubs[:3]
                    if h.crossing is not None
                ],
            )
        ],
        states=[
            State(
                "curve",
                "The chance of missing a connection at the busiest hub, by buffer.",
                highlight=[r.hubs[0].hub],
            ),
            State("hubs", "The next two hubs.", highlight=[h.hub for h in r.hubs[:3]]),
            State("buffers", "The buffer where each curve crosses the line.", show=["buffers"]),
        ],
        table_columns=["Hub", "Buffer", "Probability", "Low", "High"],
        table_rows=[
            [h.hub, b, pr, lo, hi]
            for h in r.hubs
            for b, pr, lo, hi in zip(h.buffers, h.probability, h.low, h.high, strict=True)
        ],
    ).write(charts_dir)

    # The calculator's marts: cells from the reporting years up to the month before the latest one.
    year, month = w.latest
    predict_where = f"({w.test_where}) and (year * 100 + month) < {year * 100 + month}"
    counts = misconnect_marts.build(
        con,
        flights,
        hubs=[h.hub for h in r.hubs],
        where=predict_where,
        outcome=(year, month),
        curves=r.hubs,
        out_dir=p.marts,
    )
    s.put("ch8.calculator_cells", counts["misconnect_cells"], "int")
    s.put("ch8.calculator_outcome_month", f"{year}-{month:02d}", "text")
    s.put("ch8.calculator_outcome_flights", counts["misconnect_outcomes"], "int")
    hub_curves = [
        {
            "hub": h.hub,
            "buffers": h.buffers,
            "probability": h.probability,
            "low": h.low,
            "high": h.high,
            "crossing": h.crossing,
            "crossing_low": h.crossing_low,
            "crossing_high": h.crossing_high,
            "interior": h.interior,
            "days": h.days,
            "inbound": h.inbound,
        }
        for h in r.hubs
    ]
    (p.results / "chapters").mkdir(parents=True, exist_ok=True)
    (p.results / "chapters" / "hub_curves.json").write_text(json.dumps(hub_curves, indent=1) + "\n")
