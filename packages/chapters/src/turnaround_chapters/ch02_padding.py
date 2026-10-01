"""Chapter 2: the schedule absorbed the delay.

Padding is the scheduled block time minus the unimpeded block time (the 10th percentile of actual
gate to gate time on the route, three hour block and season over the fitting years). The change
from the first to the latest full year is measured on matched cells (route, carrier, block and
month present in both years), so a carrier that moved into long, padded routes does not count as
padding; actual block time on the same cells sits beside it. PELT finds the dates each carrier's
route mix adjusted monthly series moved by a minute or more and stayed moved.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
import polars as pl
from turnaround_core.frames import num
from turnaround_stats.bootstrap import Interval, day_bootstrap, difference_of_ratios

from turnaround_chapters.padding import Changepoint, changepoints, deseasonalize, series

PERIOD_MONTH = "make_date(cast(year as integer), cast(month as integer), 1)"


@dataclass(frozen=True)
class PaddingResult:
    first_year: int
    last_year: int
    padding_change: Interval
    actual_change: Interval
    scheduled_change: Interval
    padding_first: float
    padding_last: float
    share_last: float
    hours_last: float
    matched_flights_last: int
    monthly: pl.DataFrame
    by_carrier_year: pl.DataFrame
    changepoints: list[Changepoint]
    carriers_searched: int
    sql_series: str
    sql_matched: str


def matched_sql(source: str, first: int, last: int) -> str:
    """Per day weighted sums for a fixed weight change on matched cells.

    A cell is a route, carrier, three hour block and month flown in both years. Its weight is the mean
    of its two years' flights, and each flight carries its cell's weight over its cell's flights that
    year, so a year's weighted mean is a fixed weight index over the same cells. The change is last
    year's weighted mean minus the first year's: a difference of two ratios of day sums, which the
    day bootstrap resamples within each year.
    """
    return f"""
    with flown as (
        select route, carrier, cast(dep_hour // 3 as integer) as block, month, year, flight_date,
               padding, actual_elapsed, crs_elapsed
        from {source}
        where year in ({first}, {last}) and padding is not null and not cancelled and not diverted
              and actual_elapsed is not null
    ),
    cells as (
        select route, carrier, block, month,
               count(*) filter (where year = {first}) as n_first,
               count(*) filter (where year = {last}) as n_last
        from flown group by all
        having count(*) filter (where year = {first}) > 0 and count(*) filter (where year = {last}) > 0
    ),
    weighted as (select *, (n_first + n_last) / 2.0 as w from cells)
    select f.flight_date, f.year,
           sum(c.w / (case when f.year = {last} then c.n_last else c.n_first end) * f.padding) as padding,
           sum(c.w / (case when f.year = {last} then c.n_last else c.n_first end) * f.actual_elapsed) as actual,
           sum(c.w / (case when f.year = {last} then c.n_last else c.n_first end) * f.crs_elapsed) as scheduled,
           sum(c.w / (case when f.year = {last} then c.n_last else c.n_first end)) as weight,
           count(*) as n
    from flown f
    join weighted c using (route, carrier, block, month)
    group by f.flight_date, f.year
    order by f.flight_date
    """


def estimate(
    con: duckdb.DuckDBPyConnection,
    source: str,
    *,
    first: int,
    last: int,
    replicates: int,
    seed: int,
    min_segment: int = 3,
    min_step: float = 1.0,
) -> PaddingResult:
    sql_matched = matched_sql(source, first, last)
    days = con.execute(sql_matched).pl()

    last_mask = (days["year"] == last).to_numpy()

    def change(column: str, label: str) -> Interval:
        sums = np.zeros((days.height, 4))
        sums[last_mask, 0] = days[column].to_numpy()[last_mask]
        sums[last_mask, 1] = days["weight"].to_numpy()[last_mask]
        sums[~last_mask, 2] = days[column].to_numpy()[~last_mask]
        sums[~last_mask, 3] = days["weight"].to_numpy()[~last_mask]
        return day_bootstrap(
            days["flight_date"].to_numpy(),
            sums,
            difference_of_ratios((0, 1), (2, 3)),
            replicates=replicates,
            seed=seed,
            label=label,
            strata=days["year"].to_numpy(),
        )

    def level(year_mask: np.ndarray) -> float:
        return float(days["padding"].to_numpy()[year_mask].sum() / days["weight"].to_numpy()[year_mask].sum())

    padded = f"(select * from {source} where padding is not null)"
    monthly_all = con.execute(
        f"""
        select {PERIOD_MONTH} as period, count(*) as flights, avg(padding) as padding,
               avg(padding / crs_elapsed) as padding_share
        from {padded} group by 1 order by 1
        """
    ).pl()
    sql_series = f"""
    with base as (
        select carrier, {PERIOD_MONTH} as period, padding,
               padding - avg(padding) over (partition by carrier, route) as within,
               avg(padding) over (partition by carrier) as overall
        from {source} where padding is not null
    )
    select carrier, period, count(*) as flights, avg(within) + any_value(overall) as padding
    from base group by carrier, period order by carrier, period
    """.strip()
    by_carrier = deseasonalize(series(con, padded, PERIOD_MONTH))
    found, searched = changepoints(by_carrier, min_size=min_segment, min_step=min_step)
    totals = con.execute(
        f"""
        select sum(padding) / 60.0, sum(padding) / sum(crs_elapsed), count(*)
        from {source} where year = {last} and padding is not null
        """
    ).fetchone()
    assert totals is not None
    by_carrier_year = con.execute(
        f"""
        select carrier, year, count(*) as flights, avg(padding) as padding
        from {padded} group by all order by carrier, year
        """
    ).pl()
    return PaddingResult(
        first_year=first,
        last_year=last,
        padding_change=change("padding", "ch2.padding.change"),
        actual_change=change("actual", "ch2.actual.change"),
        scheduled_change=change("scheduled", "ch2.scheduled.change"),
        padding_first=level(~last_mask),
        padding_last=level(last_mask),
        share_last=float(totals[1] or 0.0),
        hours_last=float(totals[0] or 0.0),
        matched_flights_last=int(num(days.filter(pl.col("year") == last)["n"].sum())),
        monthly=monthly_all,
        by_carrier_year=by_carrier_year,
        changepoints=sorted(found, key=lambda c: (c.carrier, c.when)),
        carriers_searched=searched,
        sql_series=sql_series,
        sql_matched=sql_matched.strip(),
    )


def message(r: PaddingResult) -> str:
    pad = r.padding_change.estimate
    act = r.actual_change.estimate
    if pad > 0.5 and pad > act:
        return "The schedule grew faster than the flying, so it absorbed the delay"
    if pad < -0.5:
        return "Schedules lost padding, so delay reached the arrival board"
    if act > pad + 0.5:
        return "The flying slowed faster than the schedule grew"
    return "Padding barely moved on the same routes, hours and months"
