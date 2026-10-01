"""The block bootstrap by day.

Flights on the same day share weather, air traffic programs and the same aircraft running late
all day, so they are not independent; a flight level bootstrap would print intervals far too
narrow. Every interval in the story resamples whole days: the statistic is computed from per day
sufficient statistics (sums and counts), days are drawn with replacement, and the interval is the
percentile interval of the replicates. Days are sorted before the draw, so the same seed gives the
same interval whatever order a query returned the days in.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

Statistic = Callable[[npt.NDArray[np.float64]], float]


@dataclass(frozen=True)
class Interval:
    estimate: float
    low: float
    high: float
    replicates: int
    days: int

    def covers(self, value: float) -> bool:
        return self.low <= value <= self.high


def _rng(seed: int, label: str) -> np.random.Generator:
    stream = int.from_bytes(label.encode("utf-8")[:8].ljust(8, b"\0"), "little") % (2**31)
    return np.random.default_rng(np.random.SeedSequence([seed, stream]))


def day_bootstrap(
    day_keys: npt.ArrayLike,
    sums: npt.NDArray[np.float64],
    statistic: Statistic,
    *,
    replicates: int,
    seed: int,
    label: str,
    level: float = 0.95,
) -> Interval:
    """Resample days. ``sums`` holds one row of sufficient statistics per day; ``statistic`` maps the
    column sums of a resampled set of days to the number being estimated."""
    keys = np.asarray(day_keys)
    values = np.asarray(sums, dtype=np.float64)
    if values.ndim == 1:
        values = values[:, None]
    if keys.shape[0] != values.shape[0]:
        raise ValueError("one row of sums per day")
    if keys.shape[0] < 2:
        raise ValueError("the day bootstrap needs at least two days")
    if replicates < 1:
        raise ValueError("at least one replicate")
    order = np.argsort(keys, kind="stable")
    values = values[order]
    n = values.shape[0]
    estimate = statistic(values.sum(axis=0))
    rng = _rng(seed, label)
    draws = np.empty(replicates)
    for b in range(replicates):
        counts = np.bincount(rng.integers(0, n, n), minlength=n).astype(np.float64)
        draws[b] = statistic(counts @ values)
    alpha = (1.0 - level) / 2.0
    low, high = np.quantile(draws[np.isfinite(draws)], [alpha, 1.0 - alpha])
    return Interval(float(estimate), float(low), float(high), replicates, n)


def ratio(numerator: int = 0, denominator: int = 1) -> Statistic:
    def inner(total: npt.NDArray[np.float64]) -> float:
        return float(total[numerator] / total[denominator]) if total[denominator] else float("nan")

    return inner


def difference_of_ratios(a: tuple[int, int], b: tuple[int, int]) -> Statistic:
    def inner(total: npt.NDArray[np.float64]) -> float:
        return float(total[a[0]] / total[a[1]] - total[b[0]] / total[b[1]])

    return inner
