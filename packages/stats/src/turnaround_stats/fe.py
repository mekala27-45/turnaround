"""Fixed effects regression on weighted cells, by alternating projections, with cluster robust errors.

Chapter 5 regresses arrival delay on carrier with fixed effects for route, month, departure hour and
aircraft type. Seventy million flights do not fit in memory as a design matrix, but every regressor
and every fixed effect is constant within a cell of carrier, route, month, hour and type, so the
flight level least squares fit equals a weighted fit on cell means with the flight counts as weights
(the Frisch-Waugh-Lovell theorem, applied to grouped data). The test holds the cell fit to a row
level fit on a fixture to floating tolerance.

The fixed effects are swept out by alternating projections (demean by each grouping in turn until
nothing moves), which needs one pass of bincounts per grouping per iteration and no matrix the size
of the levels. Cluster robust variances are the sandwich with the CR1 small sample factor; when a
cluster cuts across cells (a day inside a month cell) the scores are summed at the flight level by
the caller and passed in.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

Array = npt.NDArray[np.float64]


class FixedEffectsError(ValueError):
    pass


def _codes(group: npt.ArrayLike) -> npt.NDArray[np.int64]:
    values = np.asarray(group)
    if values.dtype.kind in "iu" and values.min(initial=0) >= 0:
        return values.astype(np.int64, copy=False)
    _, inverse = np.unique(values, return_inverse=True)
    return inverse.astype(np.int64)


def demean(
    values: Array,
    weights: Array,
    groups: Sequence[npt.ArrayLike],
    *,
    tol: float = 1e-10,
    max_iter: int = 5000,
    copy: bool = True,
) -> tuple[Array, int, bool]:
    """Sweep every grouping out of every column of ``values``; returns the residuals, the iterations
    used and whether the sweep converged. With ``copy=False`` a float64 array is swept in place, which
    is how twenty million linked legs fit in memory with their design."""
    out = np.array(values, dtype=np.float64, copy=True) if copy else np.asarray(values, dtype=np.float64)
    if out.ndim == 1:
        out = out[:, None]
    w = np.asarray(weights, dtype=np.float64)
    codes = [_codes(g) for g in groups]
    sizes = [int(c.max()) + 1 if c.size else 0 for c in codes]
    totals = [np.bincount(c, weights=w, minlength=s) for c, s in zip(codes, sizes, strict=True)]
    for t in totals:
        t[t == 0] = 1.0
    scale = max(float(np.abs(out).max(initial=0.0)), 1.0)
    for iteration in range(1, max_iter + 1):
        largest = 0.0
        for code, size, total in zip(codes, sizes, totals, strict=True):
            for j in range(out.shape[1]):
                means = np.bincount(code, weights=w * out[:, j], minlength=size) / total
                step = means[code]
                largest = max(largest, float(np.abs(step).max(initial=0.0)))
                out[:, j] -= step
        if largest <= tol * scale:
            return out, iteration, True
    return out, max_iter, False


def demean_exact(
    values: Array, weights: Array, groups: Sequence[npt.ArrayLike], *, max_levels: int = 6000
) -> Array:
    """The same residuals as ``demean``, solved directly: one weighted least squares on the stacked
    indicators. For groupings with a few thousand levels in all (airport by hour, month), where
    alternating projections crawl because the groupings are nearly nested, this is one dense solve of
    the levels' cross products. The minimum norm solution is used, so the redundant level in each
    extra grouping costs nothing, and the fitted part is unique whichever solution is taken."""
    out = np.array(values, dtype=np.float64, copy=True)
    if out.ndim == 1:
        out = out[:, None]
    w = np.asarray(weights, dtype=np.float64)
    codes = [_codes(g) for g in groups]
    sizes = [int(c.max()) + 1 if c.size else 0 for c in codes]
    offsets = np.concatenate([[0], np.cumsum(sizes)]).astype(np.int64)
    levels = int(offsets[-1])
    if levels > max_levels:
        raise FixedEffectsError(f"{levels} levels is too many for the direct solve; use demean")
    cross = np.zeros((levels, levels))
    for a, (ca, sa) in enumerate(zip(codes, sizes, strict=True)):
        for b, (cb, sb) in enumerate(zip(codes, sizes, strict=True)):
            if b < a:
                continue
            block = np.bincount(ca * sb + cb, weights=w, minlength=sa * sb).reshape(sa, sb)
            cross[offsets[a] : offsets[a + 1], offsets[b] : offsets[b + 1]] = block
            if b != a:
                cross[offsets[b] : offsets[b + 1], offsets[a] : offsets[a + 1]] = block.T
    rhs = np.zeros((levels, out.shape[1]))
    for a, (ca, sa) in enumerate(zip(codes, sizes, strict=True)):
        for j in range(out.shape[1]):
            rhs[offsets[a] : offsets[a + 1], j] = np.bincount(ca, weights=w * out[:, j], minlength=sa)
    solution = np.linalg.lstsq(cross, rhs, rcond=None)[0]
    for a, ca in enumerate(codes):
        out -= solution[offsets[a] : offsets[a + 1]][ca]
    return out


@dataclass(frozen=True)
class FitResult:
    names: list[str]
    coef: Array
    bread_inverse: Array
    x_tilde: Array
    resid: Array
    weights: Array
    iterations: int
    converged: bool
    vcov: Array | None = None

    @property
    def se(self) -> Array:
        if self.vcov is None:
            raise FixedEffectsError("no variance was computed")
        return np.sqrt(np.clip(np.diag(self.vcov), 0.0, None))


def fit(
    y: npt.ArrayLike,
    x: npt.ArrayLike,
    weights: npt.ArrayLike,
    groups: Sequence[npt.ArrayLike],
    names: Sequence[str],
    *,
    cluster: npt.ArrayLike | None = None,
) -> FitResult:
    """Weighted least squares of y on x with the groupings absorbed."""
    yv = np.asarray(y, dtype=np.float64)
    xv = np.asarray(x, dtype=np.float64)
    if xv.ndim == 1:
        xv = xv[:, None]
    w = np.asarray(weights, dtype=np.float64)
    if not (yv.shape[0] == xv.shape[0] == w.shape[0]):
        raise FixedEffectsError("y, x and weights differ in length")
    if xv.shape[1] != len(names):
        raise FixedEffectsError("one name per regressor")
    if np.any(w < 0):
        raise FixedEffectsError("weights must be non negative")
    stacked, iterations, converged = demean(np.column_stack([yv, xv]), w, groups)
    yt, xt = stacked[:, 0], stacked[:, 1:]
    bread = xt.T @ (w[:, None] * xt)
    if np.linalg.matrix_rank(bread) < bread.shape[0]:
        raise FixedEffectsError("a regressor is collinear with the fixed effects")
    bread_inverse = np.linalg.inv(bread)
    coef = bread_inverse @ (xt.T @ (w * yt))
    resid = yt - xt @ coef
    result = FitResult(list(names), coef, bread_inverse, xt, resid, w, iterations, converged)
    if cluster is not None:
        scores = cluster_scores(xt, resid, w, cluster)
        result = FitResult(
            result.names,
            coef,
            bread_inverse,
            xt,
            resid,
            w,
            iterations,
            converged,
            vcov_from_scores(bread_inverse, scores),
        )
    return result


def cluster_scores(x_tilde: Array, resid: Array, weights: Array, cluster: npt.ArrayLike) -> Array:
    """Per cluster sums of w * e * x, one row per cluster. Exact when every cell lies in one cluster."""
    code = _codes(cluster)
    size = int(code.max()) + 1
    # Column by column: the full rows by regressors product would double the memory of the design.
    weighted = weights * resid
    return np.column_stack(
        [np.bincount(code, weights=weighted * x_tilde[:, j], minlength=size) for j in range(x_tilde.shape[1])]
    )


def vcov_from_scores(bread_inverse: Array, scores: Array) -> Array:
    """The CR1 sandwich: G / (G - 1) times bread inverse, meat, bread inverse."""
    scores = scores[np.any(scores != 0.0, axis=1)]
    g = scores.shape[0]
    if g < 2:
        raise FixedEffectsError("cluster robust errors need at least two clusters")
    meat = scores.T @ scores
    return float(g / (g - 1)) * (bread_inverse @ meat @ bread_inverse)


def contrasts_to_mean(coef: Array, vcov: Array | None, shares: Array) -> tuple[Array, Array | None]:
    """Effects of k categories (k - 1 dummies, the first category the reference at zero) restated
    relative to their share weighted mean, with the variance carried through the linear map."""
    full = np.concatenate([[0.0], coef])
    shares = np.asarray(shares, dtype=np.float64)
    shares = shares / shares.sum()
    k = full.shape[0]
    transform = np.eye(k) - np.tile(shares, (k, 1))
    effects = transform @ full
    if vcov is None:
        return effects, None
    padded = np.zeros((k, k))
    padded[1:, 1:] = vcov
    return effects, transform @ padded @ transform.T


def dummies(codes: npt.ArrayLike, levels: int) -> Array:
    """Indicator columns for levels 1..levels-1; level 0 is the reference."""
    c = _codes(codes)
    out = np.zeros((c.shape[0], levels - 1))
    rows = np.nonzero(c > 0)[0]
    out[rows, c[rows] - 1] = 1.0
    return out
