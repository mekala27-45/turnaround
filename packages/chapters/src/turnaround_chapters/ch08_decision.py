"""Chapter 8: the reader's decision.

For the traveler: the on time rate and mean arrival delay by scheduled departure hour, day of week and
month in the reporting years, and by the leg's position in the aircraft's day, with the first
departure against the rest as a difference with a day bootstrap interval; then the misconnect curve
at each of the twenty busiest airports (turnaround_misconnect.curve) and the buffer at which it
crosses the stated line, with its interval and the interior test.

For the airline: chapter 4's propagation term priced. A minute added to a turn where the inbound's
lateness reaches into the turn takes rho minutes off this departure and arrival; the rest of the
aircraft's day keeps a share of that, rho times the chance the next turn is reached too, leg after leg.
The trade pays where the arrival minutes saved over the rest of the day exceed the minute added.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
import polars as pl
from turnaround_misconnect.curve import HubCurve, curves, largest_hubs
from turnaround_stats.bootstrap import Interval, day_bootstrap, difference_of_ratios

FLOWN = "not cancelled and not diverted and arr_delay is not null"


@dataclass(frozen=True)
class DecisionResult:
    by_hour: pl.DataFrame
    by_dow: pl.DataFrame
    by_month: pl.DataFrame
    by_position: pl.DataFrame
    first_on_time: float
    later_on_time: float
    first_advantage: Interval
    hubs: list[HubCurve]
    binding_share: float
    binding_after_binding: float
    trade_overall: float
    trade_airports: pl.DataFrame
    trade_routes: pl.DataFrame
    sql_hour: str
    sql_curve: str


def table_sql(source: str, column: str, where: str) -> str:
    return f"""
    select {column} as key, count(*) as flights,
           avg(case when arr_delay < 15 then 1.0 else 0.0 end) as on_time_rate,
           avg(arr_delay) as mean_delay
    from {source}
    where {FLOWN} and ({where})
    group by 1 order by 1
    """


def position_sql(legs: str, where: str) -> str:
    return f"""
    select least(day_leg_index, 6) as position, count(*) as flights,
           avg(case when arr_delay < 15 then 1.0 else 0.0 end) as on_time_rate,
           avg(arr_delay) as mean_delay, avg(dep_delay) as mean_departure_delay
    from {legs}
    where ({where})
    group by 1 order by 1
    """


def trade_sql(legs: str, where: str, rho: float, min_turn: int) -> str:
    """Per linked leg: whether the turn was reached, the legs left in the rotation, and whether the next
    leg's turn was reached as well."""
    return f"""
    with linked as (
        select rotation_id, leg_index, rotation_legs, origin, dest, origin || '-' || dest as route,
               flight_date, (prev_arr_delay > sched_turn - {min_turn}) as binding
        from {legs}
        where link_status = 'linked' and ({where})
    )
    select *, lead(binding) over (partition by rotation_id order by leg_index) as next_binding
    from linked
    """


def estimate(
    con: duckdb.DuckDBPyConnection,
    source: str,
    *,
    legs: str,
    where: str,
    legs_where: str,
    rho: float,
    min_turn: int,
    hubs: int,
    min_connection: int,
    line: float,
    replicates: int,
    seed: int,
    min_route_turns: int = 1000,
) -> DecisionResult:
    sql_hour = table_sql(source, "dep_hour", where)
    by_hour = con.execute(sql_hour).pl()
    by_dow = con.execute(table_sql(source, "day_of_week", where)).pl()
    by_month = con.execute(table_sql(source, "month", where)).pl()
    by_position = con.execute(position_sql(legs, legs_where)).pl()

    days = con.execute(
        f"""
        select flight_date,
               count(*) filter (where day_leg_index = 1 and arr_delay < 15) as first_on,
               count(*) filter (where day_leg_index = 1) as first_n,
               count(*) filter (where day_leg_index > 1 and arr_delay < 15) as later_on,
               count(*) filter (where day_leg_index > 1) as later_n
        from {legs} where ({legs_where}) group by 1 order by 1
        """
    ).pl()
    sums = days.select("first_on", "first_n", "later_on", "later_n").to_numpy().astype(np.float64)
    advantage = day_bootstrap(
        days["flight_date"].to_numpy(),
        sums,
        difference_of_ratios((0, 1), (2, 3)),
        replicates=replicates,
        seed=seed,
        label="ch8.first.advantage",
    )
    totals = sums.sum(axis=0)

    chosen = largest_hubs(con, source, where, hubs)
    hub_curves = curves(
        con,
        source,
        hubs=chosen,
        where=where,
        min_connection=min_connection,
        line=line,
        replicates=replicates,
        seed=seed,
    )

    turns = con.execute(trade_sql(legs, legs_where, rho, min_turn)).pl()
    q_all = float(turns["binding"].mean())  # type: ignore[arg-type]
    after = turns.filter(pl.col("binding") & pl.col("next_binding").is_not_null())
    q_next = float(after["next_binding"].mean()) if after.height else q_all  # type: ignore[arg-type]
    carry = rho * q_next
    remaining = (turns["rotation_legs"] - turns["leg_index"]).to_numpy().astype(np.float64)
    downstream = np.where(np.abs(1 - carry) > 1e-12, carry * (1 - carry**remaining) / (1 - carry), remaining)
    saved = rho * turns["binding"].cast(pl.Float64).to_numpy() * (1.0 + downstream)
    turns = turns.with_columns(pl.Series("saved", saved))
    by_airport = (
        turns.group_by("origin")
        .agg(pl.len().alias("turns"), pl.col("binding").mean().alias("binding_share"), pl.col("saved").mean())
        .filter(pl.col("origin").is_in(chosen))
        .with_columns((pl.col("saved") >= 1.0).alias("pays"))
        .sort(["saved", "origin"], descending=[True, False])
        .rename({"origin": "airport", "saved": "saved_per_minute"})
    )
    by_route = (
        turns.group_by("route")
        .agg(pl.len().alias("turns"), pl.col("binding").mean().alias("binding_share"), pl.col("saved").mean())
        .filter(pl.col("turns") >= min_route_turns)
        .with_columns((pl.col("saved") >= 1.0).alias("pays"))
        .sort(["saved", "route"], descending=[True, False])
        .rename({"saved": "saved_per_minute"})
    )
    return DecisionResult(
        by_hour=by_hour,
        by_dow=by_dow,
        by_month=by_month,
        by_position=by_position,
        first_on_time=float(totals[0] / totals[1]),
        later_on_time=float(totals[2] / totals[3]),
        first_advantage=advantage,
        hubs=hub_curves,
        binding_share=q_all,
        binding_after_binding=q_next,
        trade_overall=float(saved.mean()),
        trade_airports=by_airport,
        trade_routes=by_route,
        sql_hour=sql_hour.strip(),
        sql_curve="see turnaround_misconnect.curve.day_histograms_sql",
    )


def message(r: DecisionResult) -> str:
    """One message for the curve chart, from the largest hub's crossing buffer."""
    top = r.hubs[0]
    if top.crossing is None:
        return (
            f"No buffer on the grid brings the misconnect chance under the line at {top.hub}, the busiest hub"
        )
    if r.first_advantage.low > 0:
        return f"Book the first flight of the aircraft's day, and leave {top.crossing} minutes to connect at {top.hub}"
    return f"Leave {top.crossing} minutes to connect at {top.hub}; the first flight of the day is not reliably safer"
