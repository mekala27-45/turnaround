"""Benjamini-Hochberg, the day bootstrap and the density test at the line."""

from __future__ import annotations

import numpy as np
import pytest
from turnaround_stats.bootstrap import day_bootstrap, difference_of_ratios, ratio
from turnaround_stats.density import DEFAULT_PLACEBOS, bunching, counts_by_minute, density_test
from turnaround_stats.multiple import bh_adjust, bh_reject


def test_bh_matches_a_worked_example() -> None:
    p = [0.01, 0.04, 0.03, 0.005, 0.20]
    adjusted = bh_adjust(p)
    np.testing.assert_allclose(adjusted, [0.025, 0.05, 0.05, 0.025, 0.20])
    assert bh_reject(p, 0.05) == [True, True, True, True, False]
    with pytest.raises(ValueError):
        bh_adjust([])


def test_day_bootstrap_runs_the_stated_replicates_and_ignores_input_order() -> None:
    rng = np.random.default_rng(1)
    days = np.arange(200)
    flights = rng.integers(500, 800, 200).astype(float)
    on_time = flights * rng.uniform(0.7, 0.9, 200)
    sums = np.column_stack([on_time, flights])
    first = day_bootstrap(days, sums, ratio(0, 1), replicates=300, seed=7, label="t")
    order = rng.permutation(200)
    second = day_bootstrap(days[order], sums[order], ratio(0, 1), replicates=300, seed=7, label="t")
    assert first.replicates == 300 and first.days == 200
    assert first == second
    assert first.low < first.estimate < first.high
    assert first.covers(float(on_time.sum() / flights.sum()))


def test_difference_of_ratios() -> None:
    stat = difference_of_ratios((0, 1), (2, 3))
    assert stat(np.array([8.0, 10.0, 6.0, 10.0])) == pytest.approx(0.2)


def _smooth_delays(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.round(rng.gamma(1.6, 18.0, n) - 22.0)


def test_density_test_is_quiet_on_a_smooth_distribution() -> None:
    minutes, counts = counts_by_minute(_smooth_delays(400_000, 3))
    result = density_test(minutes, counts)
    assert result.placebos_evaluated == len(DEFAULT_PLACEBOS)
    assert result.p_value > 0.05


def test_density_test_fires_on_planted_bunching() -> None:
    delays = _smooth_delays(400_000, 3)
    rng = np.random.default_rng(5)
    just_late = np.nonzero((delays >= 15) & (delays < 20))[0]
    moved = rng.choice(just_late, size=len(just_late) * 3 // 10, replace=False)
    delays[moved] = rng.integers(10, 15, size=moved.size)
    minutes, counts = counts_by_minute(delays)
    result = density_test(minutes, counts)
    assert result.excess_below > 0 and result.missing_above > 0
    assert result.p_value < 0.05


def test_density_test_refuses_its_own_threshold_as_placebo() -> None:
    minutes, counts = counts_by_minute(_smooth_delays(10_000, 1))
    with pytest.raises(ValueError):
        density_test(minutes, counts, 15, placebos=[15, *range(30, 45)])
    with pytest.raises(ValueError):
        bunching(minutes[:5], counts[:5], 15)
