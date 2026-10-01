"""Schedule padding: how much longer the schedule is than the flight needs, and when that changed.

Unimpeded block time is the 10th percentile of actual gate to gate time on the route, in its
three hour departure block and its season, over the fitting years: the time the trip takes when
nothing is in the way. Padding is the scheduled block time minus that. The reference is fixed on
the fitting years on purpose; recomputed every year it drifts with congestion and hides exactly
the growth the chapter is about (notebook 01 keeps that dead end).

Each carrier's padding series is adjusted for its route mix (each flight's padding minus its
route's own average for that carrier, plus the carrier's overall mean), so a carrier that moves
into long, padded routes does not look like it padded its schedule. PELT finds the dates the
series moved and stayed moved.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import numpy as np
import polars as pl
from turnaround_stats.pelt import bic_penalty, estimate_sigma, pelt

HOUR_BLOCK = "cast(dep_hour // 3 as integer)"
SEASON = "cast(case when month in (12, 1, 2) then 0 when month in (3, 4, 5) then 1 when month in (6, 7, 8) then 2 else 3 end as integer)"


def unimpeded_sql(source: str, where_fit: str, percentile: float, min_flights: int) -> str:
    return f"""
    select route, {HOUR_BLOCK} as hour_block, {SEASON} as season,
           quantile_cont(actual_elapsed, {percentile}) as unimpeded, count(*) as flights
    from {source}
    where not cancelled and not diverted and actual_elapsed is not null and ({where_fit})
    group by all
    having count(*) >= {min_flights}
    """


def build_unimpeded(
    con: duckdb.DuckDBPyConnection,
    source: str,
    *,
    where_fit: str,
    percentile: float,
    min_flights: int,
    target: str = "unimpeded",
) -> int:
    con.execute(
        f"create or replace table {target} as {unimpeded_sql(source, where_fit, percentile, min_flights)}"
    )
    row = con.execute(f"select count(*) from {target}").fetchone()
    return int(row[0]) if row else 0


def padded_flights_sql(source: str, unimpeded: str = "unimpeded") -> str:
    """Every scheduled flight with a reference, its padding in minutes and as a share of block time."""
    return f"""
    select f.*, u.unimpeded, f.crs_elapsed - u.unimpeded as padding,
           (f.crs_elapsed - u.unimpeded) / nullif(f.crs_elapsed, 0) as padding_share
    from {source} f
    join {unimpeded} u on u.route = f.route and u.hour_block = {HOUR_BLOCK.replace("dep_hour", "f.dep_hour")}
                      and u.season = {SEASON.replace("month", "f.month")}
    where f.crs_elapsed is not null
    """


def carrier_route_month(con: duckdb.DuckDBPyConnection, padded: str) -> pl.DataFrame:
    return con.execute(
        f"""
        select carrier, route, year, month, count(*) as flights, avg(padding) as padding
        from {padded} group by all order by carrier, route, year, month
        """
    ).pl()


def series(con: duckdb.DuckDBPyConnection, padded: str, period: str) -> pl.DataFrame:
    """Route mix adjusted padding per carrier and period (``period`` is a SQL expression giving a date)."""
    return con.execute(
        f"""
        with base as (
            select carrier, {period} as period, padding,
                   padding - avg(padding) over (partition by carrier, route) as within,
                   avg(padding) over (partition by carrier) as overall
            from {padded}
        )
        select carrier, period, count(*) as flights, avg(within) + any_value(overall) as padding
        from base group by carrier, period order by carrier, period
        """
    ).pl()


@dataclass(frozen=True)
class Changepoint:
    carrier: str
    when: date
    before: float
    after: float

    @property
    def step(self) -> float:
        return self.after - self.before


def changepoints(
    frame: pl.DataFrame, *, min_size: int, min_step: float, n_params: int = 2
) -> tuple[list[Changepoint], int]:
    """PELT on each carrier's series, keeping the moves of at least ``min_step`` minutes.

    The penalty alone lets a long, smooth series split on steps of a tenth of a minute, which nobody
    scheduling an airline would call a change; the floor is stated in the policy and applied after
    the search, so the search itself stays exact. Returns the changepoints and how many carriers
    were searched."""
    found: list[Changepoint] = []
    searched = 0
    for carrier in sorted(frame["carrier"].unique().to_list()):
        sub = frame.filter(pl.col("carrier") == carrier).sort("period")
        values = sub["padding"].to_numpy().astype(np.float64)
        searched += 1
        if values.shape[0] < 2 * min_size:
            continue
        sigma = estimate_sigma(values)
        if sigma <= 0:
            continue
        cuts = pelt(values, bic_penalty(values.shape[0], sigma, n_params=n_params), min_size=min_size)
        bounds = [0, *cuts, values.shape[0]]
        periods = sub["period"].to_list()
        for i, cut in enumerate(cuts):
            before = float(values[bounds[i] : cut].mean())
            after = float(values[cut : bounds[i + 2]].mean())
            if abs(after - before) >= min_step:
                found.append(Changepoint(carrier, periods[cut], before, after))
    return found, searched
