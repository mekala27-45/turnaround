"""Chapter 5: the fair ranking.

The raw ranking is each carrier's mean arrival delay against the average; the adjusted ranking holds
the routes, months, scheduled hours and aircraft types each carrier flies constant. Both are fit on
the test years with intervals clustered by day. The rank changes are named.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
from turnaround_stats.fe import contrasts_to_mean, dummies, fit

from turnaround_chapters.ranking import Ranking
from turnaround_chapters.ranking import estimate as adjusted_estimate


@dataclass(frozen=True)
class RankRow:
    carrier: str
    flights: int
    raw: float
    raw_se: float
    adjusted: float
    adjusted_se: float
    raw_rank: int
    adjusted_rank: int

    @property
    def change(self) -> int:
        """Places moved; positive means better (a lower, earlier rank) once adjusted."""
        return self.raw_rank - self.adjusted_rank


@dataclass(frozen=True)
class RankingResult:
    rows: list[RankRow]
    cells: int
    days: int
    converged: bool
    iterations: int
    sql: str


def raw_with_intervals(
    con: duckdb.DuckDBPyConnection, source: str, where: str
) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Carrier means against the flight weighted average, with day clustered errors, from day by carrier sums."""
    frame = con.execute(
        f"""
        select carrier, flight_date, count(*) as n, sum(arr_delay) as s
        from {source}
        where not cancelled and not diverted and arr_delay is not null and ({where})
        group by all order by carrier, flight_date
        """
    ).pl()
    carriers = sorted(frame["carrier"].unique().to_list())
    code = {c: i for i, c in enumerate(carriers)}
    idx = np.array([code[c] for c in frame["carrier"].to_list()], dtype=np.int64)
    n = frame["n"].to_numpy().astype(np.float64)
    y = frame["s"].to_numpy().astype(np.float64) / n
    days = frame["flight_date"].to_numpy()
    # A carrier by day cell lies inside one day, so the in memory cluster scores are exact here.
    result = fit(
        y,
        dummies(idx, len(carriers)),
        n,
        [np.zeros(idx.shape[0], dtype=np.int64)],
        carriers[1:],
        cluster=days,
    )
    shares = np.bincount(idx, weights=n, minlength=len(carriers))
    effects, vcov = contrasts_to_mean(result.coef, result.vcov, shares)
    assert vcov is not None
    return carriers, effects, np.sqrt(np.clip(np.diag(vcov), 0, None))


def estimate(con: duckdb.DuckDBPyConnection, source: str, *, where: str) -> RankingResult:
    adjusted: Ranking = adjusted_estimate(con, source, where=where, cluster_by_day=True)
    carriers, raw, raw_se = raw_with_intervals(con, source, where)
    if carriers != adjusted.carriers:
        raise ValueError("the raw and adjusted rankings list different carriers")
    assert adjusted.adjusted_se is not None and adjusted.days is not None
    raw_order = adjusted.order("raw")
    adj_order = adjusted.order("adjusted")
    rows = [
        RankRow(
            carrier=c,
            flights=adjusted.flights[i],
            raw=float(raw[i]),
            raw_se=float(raw_se[i]),
            adjusted=adjusted.adjusted[i],
            adjusted_se=adjusted.adjusted_se[i],
            raw_rank=raw_order.index(c) + 1,
            adjusted_rank=adj_order.index(c) + 1,
        )
        for i, c in enumerate(carriers)
    ]
    rows.sort(key=lambda r: (r.adjusted_rank, r.carrier))
    sql = (
        "select carrier, route, year * 100 + month as period, dep_hour, coalesce(type_code, 'unknown') as type_code,\n"
        "       count(*) as flights, avg(arr_delay) as arr_delay\n"
        f"from {source}\nwhere not cancelled and not diverted and arr_delay is not null and ({where})\ngroup by all"
    )
    return RankingResult(rows, adjusted.cells, adjusted.days, adjusted.converged, adjusted.iterations, sql)


def biggest_movers(r: RankingResult) -> tuple[RankRow, RankRow]:
    """The carrier that rises most once adjusted, and the one that falls most (ties broken by code)."""
    up = max(r.rows, key=lambda x: (x.change, -ord(x.carrier[0]), x.carrier))
    down = min(r.rows, key=lambda x: (x.change, x.carrier))
    return up, down


def message(r: RankingResult, names: dict[str, str] | None = None) -> str:
    """The chart's one message, by rule: whether the ranking moves once the routes, months, hours and
    aircraft are held constant, and the carriers it moves most for (ties broken by code)."""
    moved = [x for x in r.rows if x.change != 0]
    if not moved:
        return "Holding constant what each carrier flies leaves the ranking unchanged"

    def name(code: str) -> str:
        return (names or {}).get(code, code)

    # The same movers the chart's callout names, with the same tie break.
    up, down = biggest_movers(r)
    return (
        f"The ranking changes once you hold constant what each carrier flies: {name(up.carrier)} rises "
        f"{up.change} {'place' if up.change == 1 else 'places'} and {name(down.carrier)} falls {-down.change}"
    )
