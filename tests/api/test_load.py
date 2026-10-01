"""The load test, against a running server named by TURNAROUND_LOADTEST_BASE: a short run that must
finish without an error and report ordered percentiles. CI starts the API on the committed marts and
sets TURNAROUND_REQUIRE_LOADTEST so this cannot skip there; the published figures come from
deploy/load-test.ps1 against the live API."""

from __future__ import annotations

import asyncio
import os

import pytest

from scripts.load_test import run
from tests._deps import need

pytestmark = pytest.mark.loadtest


def test_a_short_load_test_runs_clean_with_ordered_percentiles() -> None:
    base = os.environ.get("TURNAROUND_LOADTEST_BASE", "")
    need("loadtest", bool(base), "TURNAROUND_LOADTEST_BASE names no running server")
    token = os.environ.get("TURNAROUND_WRITE_TOKEN", "check-token")
    result = asyncio.run(run(base.rstrip("/"), token, requests=12, concurrency=4))
    assert result["errors"] == 0 and result["hubs"] > 0
    for kind in ("check", "read"):
        assert 0 < result[kind]["p50_ms"] <= result[kind]["p99_ms"] <= result[kind]["max_ms"]
