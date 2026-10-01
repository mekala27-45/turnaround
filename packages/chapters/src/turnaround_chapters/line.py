"""The fifteen minute line, per carrier: the density test with placebos and Benjamini-Hochberg."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
from turnaround_stats.density import DEFAULT_PLACEBOS, DensityTest, density_test
from turnaround_stats.multiple import bh_adjust

LO, HI = -60, 180


@dataclass(frozen=True)
class CarrierLine:
    carrier: str
    flights: int
    test: DensityTest
    q_value: float
    flagged: bool


def counts_sql(source: str, where: str) -> str:
    return f"""
    select carrier, cast(arr_delay as integer) as minute, count(*) as flights
    from {source}
    where not cancelled and not diverted and arr_delay is not null
      and arr_delay >= {LO} and arr_delay < {HI} and ({where})
    group by all order by carrier, minute
    """


def by_carrier(
    con: duckdb.DuckDBPyConnection, source: str, *, where: str = "true", q: float = 0.05, threshold: int = 15
) -> list[CarrierLine]:
    frame = con.execute(counts_sql(source, where)).pl()
    minutes = np.arange(LO, HI)
    tests: list[tuple[str, int, DensityTest]] = []
    for carrier in sorted(frame["carrier"].unique().to_list()):
        sub = frame.filter(frame["carrier"] == carrier)
        counts = np.zeros(HI - LO)
        counts[sub["minute"].to_numpy() - LO] = sub["flights"].to_numpy()
        tests.append((carrier, int(counts.sum()), density_test(minutes, counts, threshold, DEFAULT_PLACEBOS)))
    adjusted = bh_adjust([t.p_value for _, _, t in tests])
    return [
        CarrierLine(carrier, n, test, q_value, q_value <= q)
        for (carrier, n, test), q_value in zip(tests, adjusted, strict=True)
    ]
