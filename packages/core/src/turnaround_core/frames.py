"""Small typed helpers for reading scalars out of data frames."""

from __future__ import annotations

from typing import Any


def num(value: Any, default: float = 0.0) -> float:
    """A frame scalar as a float; None (an empty column's mean) becomes the default."""
    if value is None:
        return default
    return float(value)
