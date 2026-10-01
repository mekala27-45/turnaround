"""The calculator's estimate for one connection, from committed cells small enough to ship with the API.

The chapter's curve pairs every inbound and outbound flight at a hub day by day. The calculator answers
for one connection (an origin, a hub, a destination, a month, an inbound arrival hour, an outbound
departure hour and a buffer), so it works from cells:

- the hub's inbound arrival delays and outbound departure delays by month and scheduled hour, in five
  minute bins, from the reporting window (the hour asked for and the hours either side, widened to the
  whole month when that holds fewer than MIN_CELL flights);
- each route's mean delay by month against its hub's, which shifts the hub's distribution to the route
  (a location shift: the route keeps the hub's shape and moves by its own average);
- the inbound route's cancelled and diverted share by month (the hub's when the route is thin);
- the hub's same day correlation ratio at each buffer from chapter 8 (the joint curve over the pooled
  one), which the independent cell arithmetic would otherwise miss.

Within a pair of five minute bins the two delays are taken as uniform, so the difference is triangular
and the arithmetic is exact for binned data. The interval is a Wilson interval on the smaller side's
flights, widened by the hub's design effect from chapter 8's day bootstrap.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import polars as pl

BIN = 5
CELL_LO = -60
CELL_HI = 360
N_BINS = (CELL_HI - CELL_LO) // BIN
MIN_CELL = 150
MIN_ROUTE = 30
Z95 = 1.959963984540054
Array = npt.NDArray[np.float64]


class UnknownConnection(LookupError):
    pass


@dataclass(frozen=True)
class Estimate:
    probability: float
    low: float
    high: float
    flights: int
    inbound_flights: int
    outbound_flights: int
    level: str
    correlation_ratio: float
    lost_share: float


def bin_of(delay_sql: str) -> str:
    return f"cast(floor((least(greatest({delay_sql}, {CELL_LO}), {CELL_HI - 1}) - ({CELL_LO})) / {BIN}) as integer)"


def _triangle_survival(z: Array) -> Array:
    """P(U1 - U2 > z) for U1, U2 independent uniform on a bin of width BIN."""
    w = float(BIN)
    out = np.where(z <= -w, 1.0, 0.0)
    left = (z > -w) & (z <= 0)
    right = (z > 0) & (z < w)
    out = np.where(left, 1.0 - (z + w) ** 2 / (2 * w * w), out)
    out = np.where(right, (w - z) ** 2 / (2 * w * w), out)
    return out


def exceed_probability(arr_share: Array, dep_share: Array, threshold: float, shift: float = 0.0) -> float:
    """P(A + shift - D > threshold) for binned A and D (shares over the N_BINS bins)."""
    starts = CELL_LO + BIN * np.arange(N_BINS, dtype=np.float64)
    gap = starts[:, None] + shift - starts[None, :]
    return float(arr_share @ _triangle_survival(threshold - gap) @ dep_share)


def wilson(p: float, n: float) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 1.0
    denom = 1.0 + Z95 * Z95 / n
    centre = (p + Z95 * Z95 / (2 * n)) / denom
    half = Z95 * math.sqrt(max(p * (1 - p) / n + Z95 * Z95 / (4 * n * n), 0.0)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


@dataclass(frozen=True)
class Cells:
    """The committed marts, indexed for lookups."""

    hist: dict[tuple[str, str, int, int], Array]  # (hub, direction, month, hour) -> counts by bin
    lost: dict[tuple[str, int, int], tuple[float, float]]  # (hub, month, hour) -> (scheduled, lost)
    routes: dict[
        tuple[str, str, str, int], tuple[float, float, float, float]
    ]  # (o, d, dir, month) -> sched, flown, lost, mean
    hub_means: dict[tuple[str, str, int], float]  # (hub, direction, month) -> mean delay
    ratio: dict[str, tuple[list[int], list[float]]]  # hub -> buffers, joint over pooled
    design_effect: dict[str, float]
    hubs: list[str]

    @classmethod
    def from_frames(
        cls, cells: pl.DataFrame, lost: pl.DataFrame, routes: pl.DataFrame, hubs: pl.DataFrame
    ) -> Cells:
        hist: dict[tuple[str, str, int, int], Array] = {}
        for (hub, direction, month, hour), sub in cells.group_by(
            ["hub", "direction", "month", "hour"], maintain_order=True
        ):
            counts = np.zeros(N_BINS)
            np.add.at(
                counts, sub["bin"].to_numpy().astype(np.int64), sub["flights"].to_numpy().astype(np.float64)
            )
            hist[(str(hub), str(direction), int(month), int(hour))] = counts
        lost_map = {
            (str(r["hub"]), int(r["month"]), int(r["hour"])): (float(r["scheduled"]), float(r["lost"]))
            for r in lost.iter_rows(named=True)
        }
        route_map = {
            (str(r["origin"]), str(r["dest"]), str(r["direction"]), int(r["month"])): (
                float(r["scheduled"]),
                float(r["flown"]),
                float(r["lost"]),
                float(r["mean_delay"]) if r["mean_delay"] is not None else 0.0,
            )
            for r in routes.iter_rows(named=True)
        }
        means: dict[tuple[str, str, int], float] = {}
        weighted = (
            cells.with_columns(
                (pl.lit(CELL_LO + BIN / 2) + pl.col("bin") * BIN).alias("centre"),
            )
            .group_by(["hub", "direction", "month"])
            .agg(((pl.col("centre") * pl.col("flights")).sum() / pl.col("flights").sum()).alias("mean"))
        )
        for r in weighted.iter_rows(named=True):
            means[(str(r["hub"]), str(r["direction"]), int(r["month"]))] = float(r["mean"])
        # The route means are taken on the same clipped, binned scale as the hub's, so the shift compares like with like.
        ratio: dict[str, tuple[list[int], list[float]]] = {}
        effects: dict[str, float] = {}
        for hub, sub in hubs.sort(["hub", "buffer"]).group_by("hub", maintain_order=True):
            ratio[str(hub[0])] = (sub["buffer"].to_list(), sub["ratio"].to_list())
            effect = sub["design_effect"].drop_nulls()
            effects[str(hub[0])] = float(effect[0]) if effect.len() else 1.0
        return cls(hist, lost_map, route_map, means, ratio, effects, sorted(ratio))

    def _pooled(self, hub: str, direction: str, month: int, hour: int) -> tuple[Array, str]:
        hours = [(hour + k) % 24 for k in (-1, 0, 1)]
        counts = sum(
            (self.hist.get((hub, direction, month, h), np.zeros(N_BINS)) for h in hours),
            start=np.zeros(N_BINS),
        )
        if counts.sum() >= MIN_CELL:
            return counts, "hour"
        counts = sum(
            (self.hist.get((hub, direction, month, h), np.zeros(N_BINS)) for h in range(24)),
            start=np.zeros(N_BINS),
        )
        return counts, "month"

    def estimate(
        self,
        *,
        origin: str,
        hub: str,
        destination: str,
        month: int,
        inbound_hour: int,
        outbound_hour: int,
        buffer: int,
        min_connection: int,
    ) -> Estimate:
        if hub not in self.ratio:
            raise UnknownConnection(f"{hub} is not one of the hubs the calculator covers")
        inbound, in_level = self._pooled(hub, "in", month, inbound_hour)
        outbound, out_level = self._pooled(hub, "out", month, outbound_hour)
        if inbound.sum() == 0 or outbound.sum() == 0:
            raise UnknownConnection(f"no flights at {hub} in month {month}")
        in_route = self.routes.get((origin, hub, "in", month))
        out_route = self.routes.get((hub, destination, "out", month))
        if in_route is None or out_route is None:
            raise UnknownConnection(
                f"{origin} to {hub} or {hub} to {destination} was not flown in month {month}"
            )
        shift = 0.0
        level = "route"
        if in_route[1] >= MIN_ROUTE:
            shift += in_route[3] - self.hub_means.get((hub, "in", month), in_route[3])
        else:
            level = "hub"
        if out_route[1] >= MIN_ROUTE:
            shift -= out_route[3] - self.hub_means.get((hub, "out", month), out_route[3])
        else:
            level = "hub"
        if in_route[0] >= MIN_ROUTE:
            lost_share = in_route[2] / in_route[0]
        else:
            scheduled, lost = (0.0, 0.0)
            for h in ((inbound_hour + k) % 24 for k in (-1, 0, 1)):
                s, lo = self.lost.get((hub, month, h), (0.0, 0.0))
                scheduled, lost = scheduled + s, lost + lo
            lost_share = lost / scheduled if scheduled else 0.0
        late = exceed_probability(
            inbound / inbound.sum(), outbound / outbound.sum(), buffer - min_connection, shift
        )
        independent = lost_share + (1.0 - lost_share) * late
        buffers, ratios = self.ratio[hub]
        r = float(np.interp(buffer, buffers, ratios))
        p = float(min(max(independent * r, 0.0), 1.0))
        n_eff = min(inbound.sum(), outbound.sum()) / max(self.design_effect.get(hub, 1.0), 1.0)
        low, high = wilson(p, n_eff)
        tag = (
            f"{level}, {in_level} cells"
            if in_level == out_level
            else f"{level}, {in_level} and {out_level} cells"
        )
        return Estimate(
            probability=p,
            low=low,
            high=high,
            flights=int(inbound.sum() + outbound.sum()),
            inbound_flights=int(inbound.sum()),
            outbound_flights=int(outbound.sum()),
            level=tag,
            correlation_ratio=r,
            lost_share=lost_share,
        )

    def curve(
        self,
        *,
        origin: str,
        hub: str,
        destination: str,
        month: int,
        inbound_hour: int,
        outbound_hour: int,
        buffers: Sequence[int],
        min_connection: int,
    ) -> list[Estimate]:
        return [
            self.estimate(
                origin=origin,
                hub=hub,
                destination=destination,
                month=month,
                inbound_hour=inbound_hour,
                outbound_hour=outbound_hour,
                buffer=b,
                min_connection=min_connection,
            )
            for b in buffers
        ]


def realized(
    outcomes: pl.DataFrame,
    *,
    origin: str,
    hub: str,
    destination: str,
    inbound_hour: int,
    outbound_hour: int,
    buffer: int,
    min_connection: int,
) -> tuple[float, int] | None:
    """What happened on that connection in the outcome month: every same day pair of an inbound flight on
    the route arriving in the hour (or either side) and an outbound flight on the route departing in the
    hour (or either side), missed by the same rule. None when no pair existed."""
    hours_in = [(inbound_hour + k) % 24 for k in (-1, 0, 1)]
    hours_out = [(outbound_hour + k) % 24 for k in (-1, 0, 1)]
    inbound = outcomes.filter(
        (pl.col("kind") == "in")
        & (pl.col("origin") == origin)
        & (pl.col("dest") == hub)
        & pl.col("hour").is_in(hours_in)
    )
    outbound = outcomes.filter(
        (pl.col("kind") == "out")
        & (pl.col("origin") == hub)
        & (pl.col("dest") == destination)
        & pl.col("hour").is_in(hours_out)
        & ~pl.col("lost")
    )
    pairs = inbound.join(outbound, on="flight_date", suffix="_out")
    if pairs.height == 0:
        return None
    missed = pairs.select(
        (pl.col("lost") | ((pl.col("delay") - pl.col("delay_out")) > (buffer - min_connection))).alias("m")
    )["m"]
    return float(missed.mean()), pairs.height  # type: ignore[arg-type]
