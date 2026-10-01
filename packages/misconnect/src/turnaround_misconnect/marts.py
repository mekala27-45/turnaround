"""The calculator's committed marts, built from the flights by the chapters stage.

misconnect_cells     hub, direction, month, hour, bin, flights     the binned delays at each hub
misconnect_lost      hub, month, hour, scheduled, lost             inbound cancelled or diverted
misconnect_routes    origin, dest, direction, month, scheduled,    each route's mean on the binned scale
                     flown, lost, mean_delay
misconnect_hubs      hub, buffer, joint, pooled, ratio,            chapter 8's same day correlation
                     design_effect
misconnect_outcomes  origin, dest, kind, flight_date, hour,        the outcome month's flights at the hubs,
                     delay, lost                                   which the scorer reads

The cells cover the reporting window up to the month before the outcome month, so a check made for the
outcome month is scored against flights its estimate never saw.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import duckdb
import polars as pl

from turnaround_misconnect.curve import HubCurve
from turnaround_misconnect.model import BIN, CELL_LO, bin_of

FILES = ("misconnect_cells", "misconnect_lost", "misconnect_routes", "misconnect_hubs", "misconnect_outcomes")


def _listed(hubs: Sequence[str]) -> str:
    return ", ".join(f"'{h}'" for h in hubs)


def cells_sql(source: str, hubs: Sequence[str], where: str) -> str:
    listed = _listed(hubs)
    return f"""
    select dest as hub, 'in' as direction, month, cast(crs_arr_local // 60 as integer) % 24 as hour,
           {bin_of("arr_delay")} as bin, count(*) as flights
    from {source}
    where dest in ({listed}) and not cancelled and not diverted and arr_delay is not null and ({where})
    group by all
    union all
    select origin as hub, 'out' as direction, month, dep_hour as hour, {bin_of("dep_delay")} as bin, count(*) as flights
    from {source}
    where origin in ({listed}) and not cancelled and dep_delay is not null and ({where})
    group by all
    order by hub, direction, month, hour, bin
    """


def lost_sql(source: str, hubs: Sequence[str], where: str) -> str:
    return f"""
    select dest as hub, month, cast(crs_arr_local // 60 as integer) % 24 as hour, count(*) as scheduled,
           count(*) filter (where cancelled or diverted) as lost
    from {source}
    where dest in ({_listed(hubs)}) and ({where})
    group by all order by hub, month, hour
    """


def routes_sql(source: str, hubs: Sequence[str], where: str) -> str:
    listed = _listed(hubs)
    centre = f"({CELL_LO} + {BIN / 2} + {BIN} * "
    return f"""
    select origin, dest, 'in' as direction, month, count(*) as scheduled,
           count(*) filter (where not cancelled and not diverted and arr_delay is not null) as flown,
           count(*) filter (where cancelled or diverted) as lost,
           avg({centre}{bin_of("arr_delay")})) filter (where not cancelled and not diverted and arr_delay is not null)
               as mean_delay
    from {source}
    where dest in ({listed}) and ({where})
    group by all
    union all
    select origin, dest, 'out' as direction, month, count(*) as scheduled,
           count(*) filter (where not cancelled and dep_delay is not null) as flown,
           count(*) filter (where cancelled) as lost,
           avg({centre}{bin_of("dep_delay")})) filter (where not cancelled and dep_delay is not null) as mean_delay
    from {source}
    where origin in ({listed}) and ({where})
    group by all
    order by origin, dest, direction, month
    """


def outcomes_sql(source: str, hubs: Sequence[str], year: int, month: int) -> str:
    listed = _listed(hubs)
    return f"""
    select origin, dest, 'in' as kind, flight_date, cast(crs_arr_local // 60 as integer) % 24 as hour,
           arr_delay as delay, (cancelled or diverted) as lost
    from {source}
    where dest in ({listed}) and year = {year} and month = {month}
    union all
    select origin, dest, 'out' as kind, flight_date, dep_hour as hour, dep_delay as delay, cancelled as lost
    from {source}
    where origin in ({listed}) and year = {year} and month = {month}
    order by kind, origin, dest, flight_date, hour, delay
    """


def hubs_frame(curves: Sequence[HubCurve]) -> pl.DataFrame:
    rows = []
    for c in curves:
        for b, joint, pooled in zip(c.buffers, c.probability, c.pooled, strict=True):
            rows.append(
                {
                    "hub": c.hub,
                    "buffer": b,
                    "joint": joint,
                    "pooled": pooled,
                    "ratio": joint / pooled if pooled > 0 else 1.0,
                    "design_effect": c.design_effect if c.design_effect == c.design_effect else None,
                }
            )
    return pl.DataFrame(rows).sort(["hub", "buffer"])


def build(
    con: duckdb.DuckDBPyConnection,
    source: str,
    *,
    hubs: Sequence[str],
    where: str,
    outcome: tuple[int, int],
    curves: Sequence[HubCurve],
    out_dir: Path,
) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = {
        "misconnect_cells": con.execute(cells_sql(source, hubs, where)).pl(),
        "misconnect_lost": con.execute(lost_sql(source, hubs, where)).pl(),
        "misconnect_routes": con.execute(routes_sql(source, hubs, where)).pl(),
        "misconnect_hubs": hubs_frame(curves),
        "misconnect_outcomes": con.execute(outcomes_sql(source, hubs, *outcome)).pl(),
    }
    counts: dict[str, int] = {}
    for name, frame in frames.items():
        frame.write_parquet(out_dir / f"{name}.parquet", compression="zstd", statistics=False)
        counts[name] = frame.height
    return counts


def load(directory: Path) -> dict[str, pl.DataFrame]:
    return {name: pl.read_parquet(directory / f"{name}.parquet") for name in FILES}
