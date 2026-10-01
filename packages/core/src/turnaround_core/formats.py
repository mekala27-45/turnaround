"""Number formats shared by the manifest, the renderer, the workbook and the site bundle.

A figure is stored raw in the manifest with a named format, and every surface formats it
through this module (the site through a generated copy of the same table), so the story,
the memo and the README cannot print the same number two different ways.
"""

from __future__ import annotations

import math
from collections.abc import Callable

FormatFn = Callable[[float | int | str | None], str]


def _num(value: float | int | str | None) -> float:
    if value is None or isinstance(value, str):
        raise TypeError(f"expected a number, got {value!r}")
    return float(value)


def _is_zero(text: str) -> bool:
    digits = text.replace(",", "").lstrip("+-")
    return float(digits) == 0


def _plain(value: float, decimals: int) -> str:
    text = f"{value:,.{decimals}f}"
    # A value that rounds to zero prints without a sign, whatever its sign before rounding.
    return text[1:] if text.startswith("-") and _is_zero(text) else text


def _signed(value: float, decimals: int) -> str:
    text = _plain(value, decimals)
    return f"+{text}" if value > 0 and not _is_zero(text) else text


def fmt_int(value: float | int | str | None) -> str:
    return f"{round(_num(value)):,}"


def _fixed(decimals: int) -> FormatFn:
    def inner(value: float | int | str | None) -> str:
        return _plain(_num(value), decimals)

    return inner


def _signed_fixed(decimals: int) -> FormatFn:
    def inner(value: float | int | str | None) -> str:
        return _signed(_num(value), decimals)

    return inner


def _pct(decimals: int) -> FormatFn:
    def inner(value: float | int | str | None) -> str:
        return f"{_plain(_num(value) * 100.0, decimals)}%"

    return inner


def _signed_pct(decimals: int) -> FormatFn:
    def inner(value: float | int | str | None) -> str:
        return f"{_signed(_num(value) * 100.0, decimals)}%"

    return inner


def _points(decimals: int) -> FormatFn:
    """A difference of two shares, stored as a fraction, printed in percentage points."""

    def inner(value: float | int | str | None) -> str:
        return f"{_signed(_num(value) * 100.0, decimals)} pts"

    return inner


def _minutes(decimals: int) -> FormatFn:
    def inner(value: float | int | str | None) -> str:
        return f"{_plain(_num(value), decimals)} min"

    return inner


def _signed_minutes(decimals: int) -> FormatFn:
    def inner(value: float | int | str | None) -> str:
        return f"{_signed(_num(value), decimals)} min"

    return inner


def fmt_millions1(value: float | int | str | None) -> str:
    return f"{_plain(_num(value) / 1_000_000.0, 1)} million"


def fmt_thousands0(value: float | int | str | None) -> str:
    return f"{round(_num(value) / 1_000.0):,} thousand"


def fmt_hours0(value: float | int | str | None) -> str:
    return f"{round(_num(value)):,} h"


def fmt_hours1(value: float | int | str | None) -> str:
    return f"{_plain(_num(value), 1)} h"


def fmt_days1(value: float | int | str | None) -> str:
    return f"{_plain(_num(value), 1)} days"


def fmt_ms0(value: float | int | str | None) -> str:
    return f"{round(_num(value)):,} ms"


def fmt_text(value: float | int | str | None) -> str:
    if value is None:
        return "not available"
    return str(value)


FORMATS: dict[str, FormatFn] = {
    "int": fmt_int,
    "float1": _fixed(1),
    "float2": _fixed(2),
    "float3": _fixed(3),
    "float4": _fixed(4),
    "sfloat2": _signed_fixed(2),
    "sfloat3": _signed_fixed(3),
    "pct0": _pct(0),
    "pct1": _pct(1),
    "pct2": _pct(2),
    "spct1": _signed_pct(1),
    "spct2": _signed_pct(2),
    "pts1": _points(1),
    "pts2": _points(2),
    "min0": _minutes(0),
    "min1": _minutes(1),
    "min2": _minutes(2),
    "smin1": _signed_minutes(1),
    "smin2": _signed_minutes(2),
    "millions1": fmt_millions1,
    "thousands0": fmt_thousands0,
    "hours0": fmt_hours0,
    "hours1": fmt_hours1,
    "days1": fmt_days1,
    "ms": fmt_ms0,
    "text": fmt_text,
}


def format_value(value: float | int | str | None, fmt: str) -> str:
    if fmt not in FORMATS:
        raise KeyError(f"unknown format {fmt!r}")
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "not available"
    if value is None and fmt != "text":
        return "not applicable"
    return FORMATS[fmt](value)
