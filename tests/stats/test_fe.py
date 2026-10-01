"""The weighted cell fit equals the row level fit; the cluster robust variance equals the sandwich."""

from __future__ import annotations

import numpy as np
import pytest
from turnaround_stats.fe import FixedEffectsError, contrasts_to_mean, demean, dummies, fit


def _rows(seed: int = 4) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    n = 4000
    carrier = rng.integers(0, 4, n)
    route = rng.integers(0, 30, n)
    month = rng.integers(0, 12, n)
    day = month * 31 + rng.integers(0, 28, n)
    y = np.array([0.0, 3.0, -2.0, 5.0])[carrier] + rng.normal(0, 4, 30)[route] + rng.normal(0, 2, 12)[month]
    y = y + rng.normal(0, 10, n) + 2.0 * rng.normal(0, 1, 400)[day]
    return {"carrier": carrier, "route": route, "month": month, "day": day, "y": y}


def _row_level_ols(data: dict[str, np.ndarray]) -> np.ndarray:
    n = data["y"].shape[0]
    design = np.column_stack(
        [
            dummies(data["carrier"], 4),
            np.eye(30)[data["route"]],
            np.eye(12)[data["month"]][:, 1:],
            np.ones(n)[:, None] * 0,
        ]
    )
    design = design[:, :-1]
    coef, *_ = np.linalg.lstsq(design, data["y"], rcond=None)
    return coef[:3]


def test_cell_fit_reproduces_the_row_level_fit() -> None:
    data = _rows()
    reference = _row_level_ols(data)
    # Collapse to cells of carrier, route and month: every regressor and fixed effect is constant within one.
    key = data["carrier"] * 10000 + data["route"] * 100 + data["month"]
    cells, inverse = np.unique(key, return_inverse=True)
    counts = np.bincount(inverse).astype(float)
    means = np.bincount(inverse, weights=data["y"]) / counts
    carrier = cells // 10000
    route = (cells // 100) % 100
    month = cells % 100
    result = fit(means, dummies(carrier, 4), counts, [route, month], ["c1", "c2", "c3"])
    assert result.converged
    np.testing.assert_allclose(result.coef, reference, atol=1e-7)


def test_cluster_robust_variance_matches_the_direct_sandwich() -> None:
    data = _rows(9)
    x = dummies(data["carrier"], 4)
    result = fit(
        data["y"],
        x,
        np.ones_like(data["y"]),
        [data["route"], data["month"]],
        ["c1", "c2", "c3"],
        cluster=data["day"],
    )
    xt, e = result.x_tilde, result.resid
    groups = np.unique(data["day"])
    meat = np.zeros((3, 3))
    for g in groups:
        s = (xt[data["day"] == g] * e[data["day"] == g, None]).sum(axis=0)
        meat += np.outer(s, s)
    bread = np.linalg.inv(xt.T @ xt)
    direct = len(groups) / (len(groups) - 1) * bread @ meat @ bread
    assert result.vcov is not None
    np.testing.assert_allclose(result.vcov, direct, rtol=1e-8)
    assert np.all(result.se > 0)


def test_contrasts_restate_effects_around_the_weighted_mean() -> None:
    effects, vcov = contrasts_to_mean(
        np.array([3.0, -2.0, 5.0]), np.eye(3) * 0.01, np.array([1.0, 1.0, 1.0, 1.0])
    )
    np.testing.assert_allclose(effects, [-1.5, 1.5, -3.5, 3.5])
    assert abs(float(effects.sum())) < 1e-12
    assert vcov is not None and vcov.shape == (4, 4)


def test_collinear_regressor_is_refused() -> None:
    data = _rows()
    with pytest.raises(FixedEffectsError, match="collinear"):
        fit(data["y"], data["route"] * 1.0, np.ones_like(data["y"]), [data["route"]], ["route"])


def test_demean_reports_convergence_and_iterations() -> None:
    data = _rows()
    out, iterations, converged = demean(data["y"], np.ones_like(data["y"]), [data["route"], data["month"]])
    assert converged and iterations >= 1
    for code in (data["route"], data["month"]):
        means = np.bincount(code, weights=out[:, 0]) / np.bincount(code)
        np.testing.assert_allclose(means, 0.0, atol=1e-8)


def test_direct_solve_matches_alternating_projections() -> None:
    """demean_exact is the same projection as demean, for nearly nested groupings where the sweep crawls."""
    from turnaround_stats.fe import demean_exact

    rng = np.random.default_rng(12)
    n = 5000
    origin_hour = rng.integers(0, 60, n)
    dest_hour = (origin_hour + rng.integers(0, 3, n)) % 60
    period = rng.integers(0, 12, n)
    values = np.column_stack([rng.normal(0, 1, n) + origin_hour * 0.1, rng.normal(0, 1, n), rng.random(n)])
    w = rng.uniform(0.5, 2.0, n)
    slow, _, converged = demean(values, w, [origin_hour, dest_hour, period], tol=1e-12, max_iter=20000)
    fast = demean_exact(values, w, [origin_hour, dest_hour, period])
    assert converged
    assert np.allclose(slow, fast, atol=1e-7)


def test_direct_solve_refuses_too_many_levels() -> None:
    from turnaround_stats.fe import demean_exact

    with pytest.raises(FixedEffectsError):
        demean_exact(np.ones((10, 1)), np.ones(10), [np.arange(10)], max_levels=5)
