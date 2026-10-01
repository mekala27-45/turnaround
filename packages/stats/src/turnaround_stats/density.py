"""The density test at a threshold: is there too much mass just under the line and too little just over it?

On time means arriving less than fifteen minutes late. If a carrier could move flights from sixteen
minutes late to fourteen (by padding the schedule on the flights most likely to miss, by holding
the door, or by how it reports), the arrival delay distribution would show a step at the line:
excess mass just below, missing mass just above. The test fits the distribution's shape on either
side of a window around the threshold, predicts the counts inside the window, and measures the
excess below plus the shortfall above, both as shares of the predicted mass.

A smooth distribution can still bend near any threshold, so the statistic at fifteen minutes is
judged against the same statistic at placebo thresholds where nobody has a reason to bunch: the p
value is the share of placebos whose statistic is at least as large. A family of carriers is
corrected by Benjamini-Hochberg. A null is a finding and is published as one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

WINDOW = 5
SPAN = 25
DEGREE = 3
DEFAULT_PLACEBOS: tuple[int, ...] = tuple(t for t in range(10, 66) if abs(t - 15) > 3)


@dataclass(frozen=True)
class Bunching:
    threshold: int
    excess_below: float
    missing_above: float
    statistic: float
    observed_below: float
    predicted_below: float


@dataclass(frozen=True)
class DensityTest:
    threshold: int
    statistic: float
    excess_below: float
    missing_above: float
    placebo_statistics: list[float]
    p_value: float
    placebos_evaluated: int


def bunching(minutes: npt.NDArray[np.int64], counts: npt.NDArray[np.float64], threshold: int) -> Bunching:
    """The statistic at one threshold from counts of flights by whole minute of arrival delay."""
    m = np.asarray(minutes)
    c = np.asarray(counts, dtype=np.float64)
    lo, hi = threshold - SPAN, threshold + SPAN
    in_span = (m >= lo) & (m < hi)
    window = (m >= threshold - WINDOW) & (m < threshold + WINDOW)
    fit_mask = in_span & ~window
    if fit_mask.sum() < DEGREE + 3:
        raise ValueError(f"too few minutes around {threshold} to fit the shape")
    x = (m[fit_mask] - threshold) / SPAN
    y = np.log(c[fit_mask] + 1.0)
    coef = np.polyfit(x, y, DEGREE)
    below = (m >= threshold - WINDOW) & (m < threshold)
    above = (m >= threshold) & (m < threshold + WINDOW)
    predicted_below = float(np.sum(np.exp(np.polyval(coef, (m[below] - threshold) / SPAN)) - 1.0))
    predicted_above = float(np.sum(np.exp(np.polyval(coef, (m[above] - threshold) / SPAN)) - 1.0))
    observed_below = float(c[below].sum())
    observed_above = float(c[above].sum())
    if predicted_below <= 0 or predicted_above <= 0:
        raise ValueError(f"no predicted mass around {threshold}")
    excess = (observed_below - predicted_below) / predicted_below
    missing = (predicted_above - observed_above) / predicted_above
    return Bunching(threshold, excess, missing, excess + missing, observed_below, predicted_below)


def density_test(
    minutes: npt.NDArray[np.int64],
    counts: npt.NDArray[np.float64],
    threshold: int = 15,
    placebos: Sequence[int] = DEFAULT_PLACEBOS,
) -> DensityTest:
    if threshold in placebos:
        raise ValueError("the threshold cannot be its own placebo")
    if len(placebos) < 10:
        raise ValueError("at least ten placebo thresholds")
    real = bunching(minutes, counts, threshold)
    stats = [bunching(minutes, counts, t).statistic for t in placebos]
    exceed = sum(1 for s in stats if s >= real.statistic)
    p = (1 + exceed) / (1 + len(stats))
    return DensityTest(threshold, real.statistic, real.excess_below, real.missing_above, stats, p, len(stats))


def counts_by_minute(
    delays: npt.ArrayLike, lo: int = -60, hi: int = 180
) -> tuple[npt.NDArray[np.int64], npt.NDArray[np.float64]]:
    d = np.asarray(delays)
    d = d[(d >= lo) & (d < hi)].astype(np.int64)
    minutes = np.arange(lo, hi)
    return minutes, np.bincount(d - lo, minlength=hi - lo).astype(np.float64)
