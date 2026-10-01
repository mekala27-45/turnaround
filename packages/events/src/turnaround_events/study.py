"""The event study: a carrier's meltdown against the other carriers at the same airports on the same days.

The treated carrier's daily cancellation rate and mean arrival delay are compared with a peer
control built from every other carrier's flights at the treated carrier's busiest airports, so a
storm that hit everyone is differenced out and what is left is the carrier's own collapse. The
excess is summed over the event window in flights cancelled and in delay minutes. Recovery time is
the number of days from onset until the treated carrier's gap to its peers is back inside its own
pre-event band (the 95th percentile of the gap over the 28 days before onset) for three days running.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import duckdb
import numpy as np
import polars as pl
from turnaround_core.frames import num

PRE_DAYS = 28
POST_DAYS = 21
STABLE_DAYS = 3


@dataclass(frozen=True)
class Study:
    carrier: str
    onset: date
    window_end: date
    airports: list[str]
    excess_cancelled: float
    excess_delay_minutes: float
    recovery_days: int | None
    peak_gap: float
    series: pl.DataFrame


def peer_series(
    con: duckdb.DuckDBPyConnection, source: str, carrier: str, onset: date, airports: list[str]
) -> pl.DataFrame:
    first = onset - timedelta(days=PRE_DAYS)
    last = onset + timedelta(days=POST_DAYS)
    codes = ", ".join(f"'{a}'" for a in airports)
    return con.execute(
        f"""
        select flight_date as day,
               count(*) filter (where carrier = '{carrier}') as treated_scheduled,
               count(*) filter (where carrier = '{carrier}' and cancelled) as treated_cancelled,
               avg(arr_delay) filter (where carrier = '{carrier}' and not cancelled and not diverted) as treated_delay,
               sum(greatest(arr_delay, 0)) filter (where carrier = '{carrier}' and not cancelled and not diverted)
                   as treated_delay_minutes,
               count(*) filter (where carrier <> '{carrier}') as peer_scheduled,
               count(*) filter (where carrier <> '{carrier}' and cancelled) as peer_cancelled,
               avg(arr_delay) filter (where carrier <> '{carrier}' and not cancelled and not diverted) as peer_delay
        from {source}
        where origin in ({codes}) and flight_date between date '{first}' and date '{last}'
        group by 1 order by 1
        """
    ).pl()


def busiest_airports(
    con: duckdb.DuckDBPyConnection, source: str, carrier: str, onset: date, k: int
) -> list[str]:
    first = onset - timedelta(days=PRE_DAYS)
    rows = con.execute(
        f"""
        select origin, count(*) n from {source}
        where carrier = '{carrier}' and flight_date between date '{first}' and date '{onset}'
        group by 1 order by n desc, origin limit {k}
        """
    ).fetchall()
    return [r[0] for r in rows]


def study(
    con: duckdb.DuckDBPyConnection,
    source: str,
    carrier: str,
    onset: date,
    window_end: date,
    *,
    airports: int = 10,
) -> Study:
    chosen = busiest_airports(con, source, carrier, onset, airports)
    s = (
        peer_series(con, source, carrier, onset, chosen)
        .with_columns(
            (pl.col("treated_cancelled") / pl.col("treated_scheduled")).alias("treated_rate"),
            (pl.col("peer_cancelled") / pl.col("peer_scheduled")).alias("peer_rate"),
        )
        .with_columns(
            (pl.col("treated_rate") - pl.col("peer_rate")).alias("gap"),
            (pl.col("treated_delay") - pl.col("peer_delay")).alias("delay_gap"),
        )
    )
    pre = s.filter(pl.col("day") < onset)
    band = float(np.quantile(pre["gap"].to_numpy(), 0.95)) if pre.height else 0.0
    base_gap = num(pre["gap"].median()) if pre.height else 0.0
    base_delay_gap = num(pre["delay_gap"].median()) if pre.height else 0.0
    window = s.filter((pl.col("day") >= onset) & (pl.col("day") <= window_end))
    excess_cancelled = float(((window["gap"] - base_gap) * window["treated_scheduled"]).sum())
    flown = window["treated_scheduled"] - window["treated_cancelled"]
    excess_delay = float(((window["delay_gap"].fill_null(0.0) - base_delay_gap) * flown).sum())
    post = s.filter(pl.col("day") >= onset).sort("day")
    recovery: int | None = None
    run = 0
    for i, (day, gap) in enumerate(zip(post["day"].to_list(), post["gap"].to_list(), strict=True)):
        run = run + 1 if gap is not None and gap <= band else 0
        if run >= STABLE_DAYS and day > onset:
            recovery = (post["day"][i - STABLE_DAYS + 1] - onset).days
            break
    return Study(
        carrier=carrier,
        onset=onset,
        window_end=window_end,
        airports=chosen,
        excess_cancelled=excess_cancelled,
        excess_delay_minutes=excess_delay,
        recovery_days=recovery,
        peak_gap=num(window["gap"].max()),
        series=s,
    )
