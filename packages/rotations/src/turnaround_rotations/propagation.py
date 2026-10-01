"""How much of a late arrival the next departure inherits, and what a turnaround buffer is worth.

The model, for leg n of an aircraft's day:

    departure delay(n) = rho * max(0, arrival delay(n-1) - (scheduled turn(n) - m))
                         + carrier x date + origin x date + departure hour + e

The scheduled turnaround is the moderator: the minutes beyond a minimum turn m are slack that soaks
up a late arrival before any of it reaches the next departure, and rho is the share of what is left
that comes through. Carrier by date fixed effects take out each carrier's own punctuality on the
day, including the days a whole airline falls over (a crew system, an outage), which would
otherwise make consecutive legs look linked when both were late for the same reason; origin by date
fixed effects take out the day's weather and air traffic at the airport where the turn happens,
which would otherwise make a late inbound and a late outbound look causally linked when both were
late for the same storm; departure hour fixed effects take out the way delay builds through the
day, which consecutive legs share and which the simulator showed biases rho upward when it is left
in. Errors are clustered by tail number and day.

m is chosen on the fitting years by profiling (the value with the least residual sum of squares
over a stated grid), then fixed, and rho is estimated on the test years. Beside the structural fit,
the buffer curve is reduced form: the slope of departure delay on a late inbound's minutes within
each scheduled turnaround bin, same fixed effects, which is the chart.

The inherited share is the minutes of departure delay the fit attributes to the previous leg,
capped at the departure delay itself, over all arrival delay minutes of flown legs.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt
from turnaround_stats.fe import cluster_scores, demean, vcov_from_scores

Array = npt.NDArray[np.float64]
DEFAULT_GRID: tuple[int, ...] = tuple(range(10, 75, 5))


@dataclass(frozen=True)
class Links:
    """One row per linked leg: its departure delay, the previous leg's arrival delay and the turn."""

    dep_delay: Array
    prev_arr_delay: Array
    sched_turn: Array
    carrier_day: npt.NDArray[np.int64]
    origin_day: npt.NDArray[np.int64]
    dep_hour: npt.NDArray[np.int64]
    cluster: npt.NDArray[np.int64]

    @property
    def n(self) -> int:
        return int(self.dep_delay.shape[0])


@dataclass(frozen=True)
class CurvePoint:
    low: int
    high: int
    slope: float
    se: float
    legs: int


@dataclass(frozen=True)
class Propagation:
    rho: float
    se: float
    low: float
    high: float
    min_turn: int
    profile: list[tuple[int, float]]
    curve: list[CurvePoint]
    legs: int
    clusters: int
    converged: bool
    extra: dict[str, float] = field(default_factory=dict)


def excess(links: Links, m: float) -> Array:
    return np.maximum(0.0, links.prev_arr_delay - (links.sched_turn - m))


def _groups(links: Links) -> list[npt.NDArray[np.int64]]:
    return [links.carrier_day, links.origin_day, links.dep_hour]


def profile_min_turn(links: Links, grid: Sequence[int] = DEFAULT_GRID) -> tuple[int, list[tuple[int, float]]]:
    """The minimum turn with the least residual sum of squares, and the profile over the grid."""
    w = np.ones(links.n)
    yt, _, _ = demean(links.dep_delay, w, _groups(links))
    y0 = yt[:, 0]
    profile: list[tuple[int, float]] = []
    for m in grid:
        xt, _, _ = demean(excess(links, m), w, _groups(links))
        x0 = xt[:, 0]
        denom = float(x0 @ x0)
        if denom <= 0:
            profile.append((int(m), float("inf")))
            continue
        beta = float(x0 @ y0) / denom
        resid = y0 - beta * x0
        profile.append((int(m), float(resid @ resid)))
    best = min(profile, key=lambda item: (item[1], item[0]))[0]
    return best, profile


def fit_rho(links: Links, m: int, *, level_z: float = 1.959963984540054) -> tuple[float, float, int, bool]:
    w = np.ones(links.n)
    stacked, _, converged = demean(np.column_stack([links.dep_delay, excess(links, m)]), w, _groups(links))
    y, x = stacked[:, 0], stacked[:, 1:]
    bread_inverse = np.linalg.inv(x.T @ x)
    beta = bread_inverse @ (x.T @ y)
    resid = y - x @ beta
    scores = cluster_scores(x, resid, w, links.cluster)
    vcov = vcov_from_scores(bread_inverse, scores)
    clusters = int(np.count_nonzero(np.any(scores != 0.0, axis=1)))
    return float(beta[0]), float(np.sqrt(vcov[0, 0])), clusters, converged


def buffer_curve(links: Links, bins: Sequence[int]) -> list[CurvePoint]:
    """Reduced form: slope of departure delay on a late inbound's minutes, by scheduled turnaround bin.

    Built for the size of the real reporting years (tens of millions of links). Only the links whose
    scheduled turn falls in the bins enter, which is the same fit as weighting the others zero, and
    the outcome and the bins' columns are one float64 block swept in place."""
    edges = list(bins)
    keep = np.flatnonzero((links.sched_turn >= edges[0]) & (links.sched_turn < edges[-1]))
    turn = links.sched_turn[keep]
    which = np.searchsorted(np.asarray(edges[1:-1], dtype=np.float64), turn, side="right")
    del turn
    counts = [int(np.count_nonzero(which == j)) for j in range(len(edges) - 1)]
    present = [j for j, n in enumerate(counts) if n > 0]
    stacked = np.zeros((keep.shape[0], 1 + len(present)))
    stacked[:, 0] = links.dep_delay[keep]
    late = np.maximum(links.prev_arr_delay[keep], 0.0)
    for column, j in enumerate(present, start=1):
        inside = which == j
        stacked[inside, column] = late[inside]
    del late, which
    groups = [g[keep] for g in _groups(links)]
    demean(stacked, np.ones(keep.shape[0]), groups, copy=False)
    del groups
    y, x = stacked[:, 0], stacked[:, 1:]
    bread_inverse = np.linalg.inv(x.T @ x)
    beta = bread_inverse @ (x.T @ y)
    resid = y - x @ beta
    vcov = vcov_from_scores(bread_inverse, cluster_scores(x, resid, np.ones(x.shape[0]), links.cluster[keep]))
    return [
        CurvePoint(int(edges[j]), int(edges[j + 1]), float(beta[i]), float(np.sqrt(vcov[i, i])), counts[j])
        for i, j in enumerate(present)
    ]


def inherited_minutes(links: Links, rho: float, m: int) -> float:
    carried = rho * excess(links, m)
    return float(np.minimum(carried, np.maximum(links.dep_delay, 0.0)).sum())


def halving_buffer(prev_arr_delay: Array, step: float = 1.0, limit: float = 600.0) -> float:
    """Minutes of buffer beyond the minimum turn at which the expected minutes passed on halve."""
    late = np.sort(np.maximum(np.asarray(prev_arr_delay, dtype=np.float64), 0.0))
    if late.sum() <= 0:
        return 0.0
    target = 0.5 * float(late.mean())
    b = 0.0
    while b <= limit:
        if float(np.maximum(late - b, 0.0).mean()) <= target:
            return b
        b += step
    return limit


def estimate(
    fit_links: Links,
    test_links: Links,
    *,
    grid: Sequence[int] = DEFAULT_GRID,
    bins: Sequence[int],
) -> Propagation:
    m, profile = profile_min_turn(fit_links, grid)
    rho, se, clusters, converged = fit_rho(test_links, m)
    curve = buffer_curve(test_links, bins)
    return Propagation(
        rho=rho,
        se=se,
        low=rho - 1.959963984540054 * se,
        high=rho + 1.959963984540054 * se,
        min_turn=m,
        profile=profile,
        curve=curve,
        legs=test_links.n,
        clusters=clusters,
        converged=converged,
    )


def encode(values: npt.ArrayLike) -> npt.NDArray[np.int64]:
    _, inverse = np.unique(np.asarray(values), return_inverse=True)
    return inverse.astype(np.int64)


def load_links(con: object, legs_table: str, where: str = "true") -> Links:
    """Linked legs from a reconstructed legs table, as arrays for the estimator."""
    import duckdb

    assert isinstance(con, duckdb.DuckDBPyConnection)
    # The groupings arrive as dense integer codes ranked in DuckDB, not as strings: twenty million
    # Python strings per grouping would not fit beside the arrays. Codes are labels only; the fit is
    # the same whatever numbers name the groups.
    arrays = con.execute(
        f"""
        select dep_delay::double as dep_delay, prev_arr_delay::double as prev_arr_delay,
               sched_turn::double as sched_turn,
               (dense_rank() over (order by carrier, flight_date) - 1)::bigint as carrier_day,
               (dense_rank() over (order by origin, flight_date) - 1)::bigint as origin_day,
               (dense_rank() over (order by dep_hour) - 1)::bigint as dep_hour_local,
               (dense_rank() over (order by tail_number, cast(sched_dep_utc as date)) - 1)::bigint as tail_day
        from {legs_table}
        where link_status = 'linked' and ({where})
        order by flight_id
        """
    ).fetchnumpy()
    return Links(
        dep_delay=np.asarray(arrays["dep_delay"], dtype=np.float64),
        prev_arr_delay=np.asarray(arrays["prev_arr_delay"], dtype=np.float64),
        sched_turn=np.asarray(arrays["sched_turn"], dtype=np.float64),
        carrier_day=np.asarray(arrays["carrier_day"], dtype=np.int64),
        origin_day=np.asarray(arrays["origin_day"], dtype=np.int64),
        dep_hour=np.asarray(arrays["dep_hour_local"], dtype=np.int64),
        cluster=np.asarray(arrays["tail_day"], dtype=np.int64),
    )
