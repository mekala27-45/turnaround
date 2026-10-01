"""Benjamini-Hochberg: the false discovery rate across a family of comparisons."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def bh_adjust(pvalues: Sequence[float]) -> list[float]:
    """Adjusted p values (step up), in the input order. Reject where the adjusted value is at most q."""
    p = np.asarray(pvalues, dtype=np.float64)
    if p.size == 0:
        raise ValueError("Benjamini-Hochberg needs at least one p value")
    if np.any((p < 0) | (p > 1) | ~np.isfinite(p)):
        raise ValueError("p values must lie in [0, 1]")
    n = p.size
    order = np.argsort(p, kind="stable")
    ranked = p[order] * n / np.arange(1, n + 1)
    adjusted_sorted = np.minimum.accumulate(ranked[::-1])[::-1]
    adjusted = np.empty(n)
    adjusted[order] = np.minimum(adjusted_sorted, 1.0)
    return [float(x) for x in adjusted]


def bh_reject(pvalues: Sequence[float], q: float) -> list[bool]:
    return [a <= q for a in bh_adjust(pvalues)]
