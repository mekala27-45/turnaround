"""The misconnect arithmetic against brute force: every same day pair counted one by one."""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import numpy as np
import polars as pl
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from turnaround_misconnect.curve import (
    BUFFERS,
    HI,
    LO,
    curves,
    day_histograms_sql,
    hub_curve,
    survival_by_day,
)
from turnaround_sim.network import SimSpec, simulate


def _hist(values: np.ndarray) -> np.ndarray:
    h = np.zeros(HI - LO + 1)
    np.add.at(h, np.clip(values, LO, HI) - LO, 1.0)
    return h


@given(
    st.lists(st.integers(-40, 200), min_size=1, max_size=40),
    st.lists(st.integers(-20, 120), min_size=1, max_size=40),
    st.integers(-30, 160),
)
@settings(max_examples=60, deadline=None)
def test_survival_equals_pair_count(arrivals: list[int], departures: list[int], x: int) -> None:
    a = np.array(arrivals)
    d = np.array(departures)
    brute = float(np.mean((a[:, None] - d[None, :]) > x))
    fast = survival_by_day(_hist(a)[None, :], _hist(d)[None, :], [x])[0, 0]
    assert fast == pytest.approx(brute, abs=1e-12)


def _brute_force_curve(flights: pl.DataFrame, hub: str, buffers: list[int], mct: int) -> np.ndarray:
    """Every inbound flight paired with every outbound flight on the same day, counted directly."""
    totals = np.zeros(len(buffers))
    weight = 0.0
    for day in sorted(flights["flight_date"].unique().to_list()):
        today = flights.filter(pl.col("flight_date") == day)
        inbound = today.filter(pl.col("dest") == hub)
        outbound = today.filter(
            (pl.col("origin") == hub) & ~pl.col("cancelled") & pl.col("dep_delay").is_not_null()
        )
        flown = inbound.filter(~pl.col("cancelled") & ~pl.col("diverted"))
        if flown.height == 0 or outbound.height == 0:
            continue
        lost = inbound.height - flown.height
        a = np.clip(flown["arr_delay"].to_numpy(), LO, HI)
        d = np.clip(outbound["dep_delay"].to_numpy(), LO, HI)
        diff = a[:, None] - d[None, :]
        share_lost = lost / inbound.height
        per_day = np.array([share_lost + (1 - share_lost) * float(np.mean(diff > b - mct)) for b in buffers])
        totals += inbound.height * per_day
        weight += inbound.height
    return totals / weight


def test_hub_curve_equals_brute_force_on_a_simulated_hub() -> None:
    sim = simulate(SimSpec(seed=21, days=130, meltdown_day=100))
    con = duckdb.connect()
    con.register("f", sim.flights.to_arrow())
    frame = con.execute(day_histograms_sql("f", ["H0"], "true")).pl()
    curve = hub_curve(frame, "H0", min_connection=25, line=0.10, replicates=50, seed=1)
    brute = _brute_force_curve(sim.flights, "H0", list(BUFFERS), 25)
    assert np.allclose(curve.probability, brute, atol=1e-10)


def test_curve_is_a_probability_and_falls_with_the_buffer() -> None:
    sim = simulate(SimSpec(seed=22, days=130, meltdown_day=100))
    con = duckdb.connect()
    con.register("f", sim.flights.to_arrow())
    found = curves(
        con, "f", hubs=["H1", "H2"], where="true", min_connection=25, line=0.10, replicates=100, seed=3
    )
    for c in found:
        p = np.array(c.probability)
        assert np.all((p >= 0) & (p <= 1))
        assert np.all(np.diff(p) <= 1e-12)
        assert np.all(np.array(c.low) <= p + 1e-12) and np.all(p <= np.array(c.high) + 1e-12)
        assert c.replicates == 100


def test_interior_is_false_when_the_curve_starts_under_the_line() -> None:
    days = [date(2024, 1, 1) + timedelta(days=i) for i in range(20)]
    rows = []
    for d in days:
        rows += [("X", d, "in", -60, 50), ("X", d, "out", 0, 50)]
    frame = pl.DataFrame(rows, schema=["hub", "day", "kind", "delay", "n"], orient="row")
    c = hub_curve(frame, "X", min_connection=25, line=0.10, replicates=20, seed=1)
    assert c.crossing == 0
    assert not c.interior
