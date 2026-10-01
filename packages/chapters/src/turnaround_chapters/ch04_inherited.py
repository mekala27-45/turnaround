"""Chapter 4: most delay is inherited.

The aircraft's day is rebuilt from tail numbers (turnaround_rotations.reconstruct, the warehouse's
int_legs). The minimum turn is chosen by profile on the last fitting year; the propagation
coefficient, the buffer curve and the inherited share are reported on the test years. Each leg's
inherited minutes are the model's carried minutes capped at the leg's own departure delay; they are
written back to the warehouse (legs_inherited) so the metric layer can reconcile the share against
the shipped monthly mart.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
import polars as pl
from turnaround_core.frames import num
from turnaround_rotations import propagation
from turnaround_rotations.reconstruct import RotationCounts, counts


@dataclass(frozen=True)
class InheritedResult:
    rotations: RotationCounts
    estimate: propagation.Propagation
    fit_year: int
    fit_links: int
    test_links: int
    inherited_minutes: float
    arrival_minutes: float
    share: float
    share_low: float
    share_high: float
    reported_late_aircraft_minutes: float
    reported_share: float
    halving_buffer: float
    sql_legs: str


def window(first: int, last: int, column: str = "year") -> str:
    return f"{column} between {first} and {last}"


def estimate(
    con: duckdb.DuckDBPyConnection,
    *,
    legs: str,
    flights: str,
    fit_year: int,
    test_first: int,
    test_last: int,
    bins: tuple[int, ...],
) -> InheritedResult:
    rotation_counts = counts(con, legs)
    test_where = window(test_first, test_last)
    legs_where = window(test_first, test_last, "year(flight_date)")
    fit_links = propagation.load_links(con, legs, f"year(flight_date) = {fit_year}")
    test_links = propagation.load_links(con, legs, legs_where)
    est = propagation.estimate(fit_links, test_links, bins=bins)
    arrival = con.execute(
        f"""
        select sum(greatest(arr_delay, 0)), sum(cause_late_aircraft) filter (where cause_ok)
        from {flights} where not cancelled and not diverted and arr_delay is not null and ({test_where})
        """
    ).fetchone()
    assert arrival is not None
    arrival_minutes = float(arrival[0] or 0.0)
    reported = float(arrival[1] or 0.0)
    inherited = propagation.inherited_minutes(test_links, est.rho, est.min_turn)
    low = propagation.inherited_minutes(test_links, est.low, est.min_turn)
    high = propagation.inherited_minutes(test_links, est.high, est.min_turn)
    return InheritedResult(
        rotations=rotation_counts,
        estimate=est,
        fit_year=fit_year,
        fit_links=fit_links.n,
        test_links=test_links.n,
        inherited_minutes=inherited,
        arrival_minutes=arrival_minutes,
        share=inherited / arrival_minutes,
        share_low=low / arrival_minutes,
        share_high=high / arrival_minutes,
        reported_late_aircraft_minutes=reported,
        reported_share=reported / arrival_minutes,
        halving_buffer=propagation.halving_buffer(test_links.prev_arr_delay),
        sql_legs=f"select * from {legs} where link_status = 'linked' and {legs_where}",
    )


def write_legs_inherited(
    con: duckdb.DuckDBPyConnection,
    *,
    legs: str,
    flights: str,
    rho: float,
    min_turn: int,
    test_first: int,
    test_last: int,
) -> None:
    """Per flown leg in the test years: the minutes the model attributes to the previous leg, and the
    leg's positive arrival delay. Legs with no link carry zero inherited minutes."""
    con.execute(
        f"""
        create or replace table legs_inherited as
        select f.flight_id, f.carrier, f.year, f.month,
               coalesce(least({rho} * greatest(0, l.prev_arr_delay - (l.sched_turn - {min_turn})),
                              greatest(f.dep_delay, 0)), 0) as inherited_minutes,
               greatest(f.arr_delay, 0) as arr_delay_pos
        from {flights} f
        left join {legs} l on l.flight_id = f.flight_id and l.link_status = 'linked'
        where not f.cancelled and not f.diverted and f.arr_delay is not null and ({window(test_first, test_last, "f.year")})
        """
    )


def inherited_month(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    return con.execute(
        """
        select carrier, year, month, sum(inherited_minutes) as inherited_minutes_sum,
               sum(arr_delay_pos) as arr_delay_pos_sum, count(*) as flown
        from legs_inherited group by all order by carrier, year, month
        """
    ).pl()


def worst_days(con: duckdb.DuckDBPyConnection, *, legs: str, test_first: int, test_last: int) -> pl.DataFrame:
    """For each month of the test years, the day whose linked legs carried the most inherited minutes per leg."""
    return con.execute(
        f"""
        with per_day as (
            select flight_date, year(flight_date) as year, month(flight_date) as month, count(*) as legs,
                   avg(greatest(0, prev_arr_delay - sched_turn)) as late_beyond_turn
            from {legs}
            where link_status = 'linked' and {window(test_first, test_last, "year(flight_date)")}
            group by 1, 2, 3
        )
        select year, month, arg_max(flight_date, late_beyond_turn) as worst_day, max(late_beyond_turn) as score
        from per_day group by year, month order by year, month
        """
    ).pl()


def rotations_on(con: duckdb.DuckDBPyConnection, *, legs: str, days: list[str]) -> pl.DataFrame:
    if not days:
        return pl.DataFrame()
    listed = ", ".join(f"date '{d}'" for d in days)
    return con.execute(
        f"""
        select l.flight_date, l.tail_number, l.carrier, l.rotation_id, l.leg_index, l.day_leg_index,
               l.origin, l.dest, l.sched_dep_utc, l.sched_arr_utc, l.dep_delay, l.arr_delay, l.sched_turn,
               l.link_status, l.prev_arr_delay
        from {legs} l
        where l.rotation_id in (select distinct rotation_id from {legs} where flight_date in ({listed}))
        order by l.rotation_id, l.leg_index
        """
    ).pl()


def message(r: InheritedResult) -> str:
    share = r.share
    if share >= 0.5:
        lead = "Most arrival delay was inherited from the aircraft's previous flight"
    elif share >= 0.3:
        lead = "About a third of arrival delay was inherited from the aircraft's previous flight"
    else:
        lead = "Less arrival delay was inherited than the airline's day suggests"
    return lead


def buffer_trade(links: propagation.Links, rho: float, min_turn: int) -> float:
    """Expected inherited minutes saved per leg by one more minute of scheduled turn, at today's turns."""
    slack = links.sched_turn - min_turn
    return float(rho * np.mean(links.prev_arr_delay > slack))


def describe(r: InheritedResult) -> dict[str, float]:
    return {
        "share": r.share,
        "reported_share": r.reported_share,
        "gap": r.share - r.reported_share,
        "linked_share": num(r.rotations.linked) / max(num(r.rotations.legs), 1.0),
    }
