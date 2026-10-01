"""Chapter 1: on time is a decision.

On time means arriving less than fifteen minutes after a schedule the airline writes itself. This
chapter puts the on time rate by year beside the time flights actually spend gate to gate, and the
time the schedule allows, on a fixed panel of routes flown in every full year of the window, so the
reader sees whether the metric and the flying moved together.

The panel holds the route mix constant: each route's yearly mean is weighted by its flights over the
whole window, so a year that adds long routes does not look like a year of slower flying. Intervals
are a block bootstrap over days; for the panel means the weights and route counts are held fixed, so
the estimator is linear in the flights and the day sums carry it.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
import polars as pl
from turnaround_core.frames import num
from turnaround_stats.bootstrap import Interval, day_bootstrap, difference_of_ratios, ratio

FLOWN = "not cancelled and not diverted and arr_delay is not null"


@dataclass(frozen=True)
class DefinitionResult:
    years: list[int]
    by_year: pl.DataFrame
    first_year: int
    last_year: int
    on_time_first: Interval
    on_time_last: Interval
    on_time_change: Interval
    sched_block_change: Interval
    actual_block_change: Interval
    panel_routes: int
    panel_share: float
    sql_on_time: str
    sql_panel: str


def full_years(con: duckdb.DuckDBPyConnection, source: str) -> list[int]:
    rows = con.execute(
        f"select year from {source} group by year having count(distinct month) = 12 order by year"
    ).fetchall()
    return [int(r[0]) for r in rows]


def on_time_sql(source: str) -> str:
    return f"""
    select year, flight_date,
           count(*) filter (where arr_delay < 15) as on_time,
           count(*) as flown
    from {source}
    where {FLOWN}
    group by year, flight_date
    order by flight_date
    """


def panel_sql(source: str, years: list[int]) -> str:
    """Per flight weight for the fixed route panel: the route's flights over the window over its flights that year."""
    span = ", ".join(str(y) for y in years)
    n = len(years)
    return f"""
    with flown as (
        select route, year, flight_date, crs_elapsed, actual_elapsed
        from {source}
        where {FLOWN} and actual_elapsed is not null and crs_elapsed is not null and year in ({span})
    ),
    route_year as (select route, year, count(*) as n from flown group by route, year),
    panel as (
        select route, sum(n) as weight from route_year group by route having count(distinct year) = {n}
    )
    select f.year, f.flight_date,
           sum(p.weight / ry.n * f.crs_elapsed) as sched_weighted,
           sum(p.weight / ry.n * f.actual_elapsed) as actual_weighted,
           sum(p.weight / ry.n) as weight
    from flown f
    join panel p using (route)
    join route_year ry on ry.route = f.route and ry.year = f.year
    group by f.year, f.flight_date
    order by f.flight_date
    """


def estimate(con: duckdb.DuckDBPyConnection, source: str, *, replicates: int, seed: int) -> DefinitionResult:
    years = full_years(con, source)
    if len(years) < 2:
        raise ValueError("chapter 1 needs at least two full years")
    first, last = years[0], years[-1]
    sql_on_time = on_time_sql(source)
    days = con.execute(sql_on_time).pl()
    sql_panel = panel_sql(source, years)
    panel = con.execute(sql_panel).pl()
    counts = con.execute(
        f"""
        with flown as (select route, year from {source} where {FLOWN} and year in ({", ".join(map(str, years))})),
        ry as (select route, count(distinct year) as y, count(*) as n from flown group by route)
        select count(*) filter (where y = {len(years)}), sum(n) filter (where y = {len(years)}) / sum(n) from ry
        """
    ).fetchone()
    assert counts is not None
    by_year_rows = []
    for year in sorted(days["year"].unique().to_list()):
        d = days.filter(pl.col("year") == year)
        pa = panel.filter(pl.col("year") == year)
        on_time = num(d["on_time"].sum()) / num(d["flown"].sum())
        sched = num(pa["sched_weighted"].sum()) / num(pa["weight"].sum()) if pa.height else None
        actual = num(pa["actual_weighted"].sum()) / num(pa["weight"].sum()) if pa.height else None
        by_year_rows.append(
            {
                "year": int(year),
                "full_year": year in years,
                "flown": int(num(d["flown"].sum())),
                "on_time_rate": float(on_time),
                "panel_scheduled_block": None if sched is None else float(sched),
                "panel_actual_block": None if actual is None else float(actual),
            }
        )
    by_year = pl.DataFrame(by_year_rows)

    def year_interval(year: int) -> Interval:
        d = days.filter(pl.col("year") == year)
        return day_bootstrap(
            d["flight_date"].to_numpy(),
            np.column_stack([d["on_time"].to_numpy(), d["flown"].to_numpy()]).astype(np.float64),
            ratio(0, 1),
            replicates=replicates,
            seed=seed,
            label=f"ch1.on_time.{year}",
        )

    def change(frame: pl.DataFrame, num: str, den: str, label: str) -> Interval:
        a = frame.filter(pl.col("year") == last)
        b = frame.filter(pl.col("year") == first)
        keys = np.concatenate([a["flight_date"].to_numpy(), b["flight_date"].to_numpy()])
        sums = np.zeros((a.height + b.height, 4))
        sums[: a.height, 0] = a[num].to_numpy()
        sums[: a.height, 1] = a[den].to_numpy()
        sums[a.height :, 2] = b[num].to_numpy()
        sums[a.height :, 3] = b[den].to_numpy()
        return day_bootstrap(
            keys, sums, difference_of_ratios((0, 1), (2, 3)), replicates=replicates, seed=seed, label=label
        )

    return DefinitionResult(
        years=years,
        by_year=by_year,
        first_year=first,
        last_year=last,
        on_time_first=year_interval(first),
        on_time_last=year_interval(last),
        on_time_change=change(days, "on_time", "flown", "ch1.on_time.change"),
        sched_block_change=change(panel, "sched_weighted", "weight", "ch1.sched.change"),
        actual_block_change=change(panel, "actual_weighted", "weight", "ch1.actual.change"),
        panel_routes=int(counts[0] or 0),
        panel_share=float(counts[1] or 0.0),
        sql_on_time=sql_on_time.strip(),
        sql_panel=sql_panel.strip(),
    )


def message(r: DefinitionResult) -> str:
    """The chart's one message, chosen by rule from the signs and sizes of the three changes."""
    pts = r.on_time_change.estimate * 100
    sched = r.sched_block_change.estimate
    actual = r.actual_block_change.estimate
    rate = "rose" if pts >= 1 else "fell" if pts <= -1 else "barely moved"
    if sched > 0.5 and actual > 0.5:
        flying = "flights took longer gate to gate and the schedule grew to cover it"
    elif sched > 0.5:
        flying = "the schedule grew while the flying did not"
    elif actual > 0.5:
        flying = "flights took longer while the schedule did not"
    else:
        flying = "neither the schedule nor the flying changed much"
    return f"The on time rate {rate} while {flying}"
