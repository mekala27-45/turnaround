"""Named skips for what a machine may not have, and a way for CI to forbid them.

A test that needs Postgres, LibreOffice, the raw files, the derived flights, the weather cache or a
live server calls ``need``. Where the dependency is missing the test is skipped with the dependency
named, so a skip reads as "not run here" and never as a pass; where CI sets
TURNAROUND_REQUIRE_<NAME>=1 the same absence fails the test, so CI cannot pass by skipping.
"""

from __future__ import annotations

import os

import pytest

NAMES = ("postgres", "libreoffice", "external", "derived", "weather", "loadtest")


def need(name: str, available: bool, why: str) -> None:
    if name not in NAMES:
        raise ValueError(f"unknown dependency {name!r}; add it to tests/_deps.py and the pytest markers")
    if available:
        return
    flag = f"TURNAROUND_REQUIRE_{name.upper()}"
    if os.environ.get(flag):
        pytest.fail(f"{flag} is set but {why}")
    pytest.skip(f"{name} not available: {why}")
