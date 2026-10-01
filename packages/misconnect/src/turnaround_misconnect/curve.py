"""The misconnect curve at a hub, from the joint same day distribution of inbound and outbound delays.

A connection at a hub is missed when the inbound flight is cancelled or diverted, or when it arrives so
late that the time left before the outbound departure is under the minimum connection time:

    missed  <=>  inbound cancelled or diverted,  or  A - D > b - m

where A is the inbound arrival delay, D the outbound departure delay (an outbound that leaves late
gives the traveler time back), b the scheduled buffer between the inbound's scheduled arrival and the
outbound's scheduled departure, and m the minimum connection time the policy states.

Delays at one hub on one day move together (the same storm, the same ground stop), so the curve is
built day by day: within each day, every inbound arrival is paired with every outbound departure,
and the day's probability is weighted by its inbound flights. The interval resamples whole days. The
pooled curve, which treats inbound and outbound delays as independent across the whole window, is
computed beside it; their ratio is the same day correlation the calculator applies to its cells.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import duckdb
import numpy as np
import numpy.typing as npt
import polars as pl
from turnaround_core.seeds import rng

LO = -60
HI = 600
BUFFERS: tuple[int, ...] = tuple(range(0, 185, 5))
Array = npt.NDArray[np.float64]


@dataclass(frozen=True)
class HubCurve:
    hub: str
    days: int
    inbound: int
    outbound: int
    buffers: list[int]
    probability: list[float]
    low: list[float]
    high: list[float]
    pooled: list[float]
    crossing: int | None
    crossing_low: int | None
    crossing_high: int | None
    interior: bool
    design_effect: float
    replicates: int


def day_histograms_sql(source: str, hubs: Sequence[str], where: str) -> str:
    listed = ", ".join(f"'{h}'" for h in hubs)
    return f"""
    select dest as hub, flight_date as day, 'in' as kind,
           cast(least(greatest(arr_delay, {LO}), {HI}) as integer) as delay, count(*) as n
    from {source}
    where dest in ({listed}) and not cancelled and not diverted and arr_delay is not null and ({where})
    group by all
    union all
    select origin as hub, flight_date as day, 'out' as kind,
           cast(least(greatest(dep_delay, {LO}), {HI}) as integer) as delay, count(*) as n
    from {source}
    where origin in ({listed}) and not cancelled and dep_delay is not null and ({where})
    group by all
    union all
    select dest as hub, flight_date as day, 'lost' as kind, 0 as delay, count(*) as n
    from {source}
    where dest in ({listed}) and (cancelled or diverted) and ({where})
    group by all
    """


def survival_by_day(arr_hist: Array, dep_hist: Array, offsets: Sequence[int]) -> Array:
    """P(A - D > x) for each day (row) and each x in ``offsets``, A and D independent within the day.

    Rows of the two histograms are counts over LO..HI by minute. A - D > x holds when the arrival's bin
    index exceeds the departure's index plus x, so the answer is the departure histogram dotted with
    the arrival survival function shifted by x."""
    n_bins = HI - LO + 1
    n_in = arr_hist.sum(axis=1)
    n_out = dep_hist.sum(axis=1)
    safe_in = np.where(n_in > 0, n_in, 1.0)
    safe_out = np.where(n_out > 0, n_out, 1.0)
    surv = 1.0 - np.cumsum(arr_hist, axis=1) / safe_in[:, None]
    lowest = min(0, min(offsets))
    highest = max(0, max(offsets))
    pad_lo = -lowest
    extended = np.concatenate(
        [np.ones((surv.shape[0], pad_lo)), surv, np.zeros((surv.shape[0], highest + 1))], axis=1
    )
    dep_share = dep_hist / safe_out[:, None]
    out = np.empty((arr_hist.shape[0], len(offsets)))
    for k, x in enumerate(offsets):
        window = extended[:, pad_lo + x : pad_lo + x + n_bins]
        out[:, k] = np.einsum("dj,dj->d", dep_share, window)
    valid = (n_in > 0) & (n_out > 0)
    out[~valid] = np.nan
    return out


def _crossing(curve: Array, buffers: Sequence[int], line: float) -> int | None:
    below = np.nonzero(curve <= line)[0]
    return int(buffers[int(below[0])]) if below.size else None


def hub_curve(
    frame: pl.DataFrame,
    hub: str,
    *,
    min_connection: int,
    line: float,
    replicates: int,
    seed: int,
    buffers: Sequence[int] = BUFFERS,
) -> HubCurve:
    """One hub's curve from the day histograms ``frame`` (the rows of day_histograms_sql)."""
    sub = frame.filter(pl.col("hub") == hub)
    days = sorted(sub["day"].unique().to_list())
    index = {d: i for i, d in enumerate(days)}
    n_days = len(days)
    n_bins = HI - LO + 1
    arr = np.zeros((n_days, n_bins))
    dep = np.zeros((n_days, n_bins))
    lost = np.zeros(n_days)
    for kind, target in (("in", arr), ("out", dep)):
        part = sub.filter(pl.col("kind") == kind)
        rows = np.array([index[d] for d in part["day"].to_list()], dtype=np.int64)
        cols = part["delay"].to_numpy().astype(np.int64) - LO
        np.add.at(target, (rows, cols), part["n"].to_numpy().astype(np.float64))
    part = sub.filter(pl.col("kind") == "lost")
    if part.height:
        lost[np.array([index[d] for d in part["day"].to_list()], dtype=np.int64)] = part["n"].to_numpy()
    offsets = [b - min_connection for b in buffers]
    surv = survival_by_day(arr, dep, offsets)
    flown_in = arr.sum(axis=1)
    scheduled_in = flown_in + lost
    cancel_share = np.where(scheduled_in > 0, lost / np.where(scheduled_in > 0, scheduled_in, 1.0), 0.0)
    per_day = cancel_share[:, None] + (1.0 - cancel_share[:, None]) * surv
    ok = np.isfinite(per_day).all(axis=1)
    per_day = per_day[ok]
    weights = scheduled_in[ok]
    curve = weights @ per_day / weights.sum()

    # The pooled curve: the same arithmetic on the window's histograms summed, as if days did not matter.
    pooled_surv = survival_by_day(
        arr[ok].sum(axis=0, keepdims=True), dep[ok].sum(axis=0, keepdims=True), offsets
    )[0]
    pooled_cancel = float(lost[ok].sum() / scheduled_in[ok].sum())
    pooled = pooled_cancel + (1.0 - pooled_cancel) * pooled_surv

    generator = rng(seed, "misconnect", hub)
    n = per_day.shape[0]
    draws = np.empty((replicates, len(buffers)))
    crossings: list[int | None] = []
    for b in range(replicates):
        counts = np.bincount(generator.integers(0, n, n), minlength=n).astype(np.float64)
        w = counts * weights
        draws[b] = w @ per_day / w.sum()
        crossings.append(_crossing(draws[b], buffers, line))
    low, high = np.quantile(draws, [0.025, 0.975], axis=0)
    crossing = _crossing(curve, buffers, line)
    finite = sorted(c if c is not None else int(buffers[-1]) + 5 for c in crossings)
    c_low = int(np.quantile(finite, 0.025, method="lower"))
    c_high = int(np.quantile(finite, 0.975, method="higher"))
    interior = crossing is not None and buffers[0] < crossing < buffers[-1] and bool(curve[0] > line)
    if crossing is not None:
        k = list(buffers).index(crossing)
        p = float(curve[k])
        binomial = p * (1.0 - p) / max(float(weights.sum()), 1.0)
        effect = float(np.var(draws[:, k], ddof=1) / binomial) if binomial > 0 else float("nan")
    else:
        effect = float("nan")
    return HubCurve(
        hub=hub,
        days=n,
        inbound=int(flown_in[ok].sum()),
        outbound=int(dep[ok].sum()),
        buffers=list(buffers),
        probability=[float(v) for v in curve],
        low=[float(v) for v in low],
        high=[float(v) for v in high],
        pooled=[float(v) for v in pooled],
        crossing=crossing,
        crossing_low=c_low if c_low <= buffers[-1] else None,
        crossing_high=c_high if c_high <= buffers[-1] else None,
        interior=interior,
        design_effect=effect,
        replicates=replicates,
    )


def largest_hubs(con: duckdb.DuckDBPyConnection, source: str, where: str, k: int) -> list[str]:
    """The k airports with the most scheduled departures in the window, ties broken by code."""
    rows = con.execute(
        f"select origin, count(*) as n from {source} where ({where}) group by origin order by n desc, origin limit {k}"
    ).fetchall()
    return [str(r[0]) for r in rows]


def curves(
    con: duckdb.DuckDBPyConnection,
    source: str,
    *,
    hubs: Sequence[str],
    where: str,
    min_connection: int,
    line: float,
    replicates: int,
    seed: int,
) -> list[HubCurve]:
    frame = con.execute(day_histograms_sql(source, hubs, where)).pl()
    return [
        hub_curve(frame, h, min_connection=min_connection, line=line, replicates=replicates, seed=seed)
        for h in hubs
    ]
