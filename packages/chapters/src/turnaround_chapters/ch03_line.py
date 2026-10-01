"""Chapter 3: the fifteen minute line.

If the line were gamed, the arrival delay distribution would have too much mass at eleven to fourteen
minutes late and too little at fifteen to nineteen. Each carrier's distribution in the test years is
tested at the line against fifty placebo thresholds, the carriers corrected together by
Benjamini-Hochberg; all carriers pooled are tested the same way. A null is published as a finding.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
import polars as pl
from turnaround_stats.density import DEFAULT_PLACEBOS, DensityTest, density_test

from turnaround_chapters.line import HI, LO, CarrierLine, by_carrier


@dataclass(frozen=True)
class LineResult:
    carriers: list[CarrierLine]
    pooled: DensityTest
    pooled_flights: int
    histogram: pl.DataFrame
    sql: str


def histogram_sql(source: str, where: str) -> str:
    return f"""
    select cast(arr_delay as integer) as minute, count(*) as flights
    from {source}
    where not cancelled and not diverted and arr_delay is not null
      and arr_delay >= {LO} and arr_delay < {HI} and ({where})
    group by 1 order by 1
    """


def estimate(con: duckdb.DuckDBPyConnection, source: str, *, where: str, q: float) -> LineResult:
    sql = histogram_sql(source, where)
    hist = con.execute(sql).pl()
    minutes = np.arange(LO, HI)
    counts = np.zeros(HI - LO)
    counts[hist["minute"].to_numpy() - LO] = hist["flights"].to_numpy()
    pooled = density_test(minutes, counts, 15, DEFAULT_PLACEBOS)
    carriers = by_carrier(con, source, where=where, q=q)
    return LineResult(carriers, pooled, int(counts.sum()), hist, sql.strip())


def message(r: LineResult) -> str:
    flagged = [c for c in r.carriers if c.flagged]
    if not flagged:
        return "No carrier's arrivals bunch under the fifteen minute line beyond what the placebos show"
    if len(flagged) == 1:
        return "One carrier's arrivals bunch under the fifteen minute line; the rest do not"
    return f"{len(flagged)} of {len(r.carriers)} carriers' arrivals bunch under the fifteen minute line"
