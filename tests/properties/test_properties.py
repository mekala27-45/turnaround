"""Properties that hold for any input, checked with Hypothesis against the code that ships: the
padding reference, the misconnect probability, the reported cause shares and the reconcile."""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import polars as pl
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from turnaround_chapters import padding
from turnaround_misconnect.model import N_BINS, exceed_probability
from turnaround_pipeline.metric_layer import close, load

ROOT = Path(__file__).resolve().parents[2]
CAUSES = ("cause_late_aircraft", "cause_carrier", "cause_nas", "cause_weather", "cause_security")
SHARES = (
    "reported_late_aircraft_share",
    "reported_carrier_share",
    "reported_nas_share",
    "reported_weather_share",
    "reported_security_share",
)


@settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    actual=st.lists(st.integers(min_value=35, max_value=420), min_size=30, max_size=120),
    percentile=st.floats(min_value=0.10, max_value=0.99),
)
def test_padding_is_non_negative_for_a_schedule_at_or_above_the_reference(
    actual: list[int], percentile: float
) -> None:
    """Airlines write block times at a percentile of what the trip took. Any schedule written at or
    above the unimpeded percentile has non negative padding on this definition, whatever the times."""
    n = len(actual)
    scheduled = float(np.quantile(np.array(actual, dtype=np.float64), percentile))
    frame = pl.DataFrame(
        {
            "route": ["AAA-BBB"] * n,
            "dep_hour": [9] * n,
            "month": [7] * n,
            "year": [2016] * n,
            "cancelled": [False] * n,
            "diverted": [False] * n,
            "actual_elapsed": [float(a) for a in actual],
            "crs_elapsed": [scheduled] * n,
        }
    )
    con = duckdb.connect()
    con.register("flights", frame.to_arrow())
    assert (
        padding.build_unimpeded(con, "flights", where_fit="year = 2016", percentile=0.10, min_flights=30) == 1
    )
    worst = con.execute(f"select min(padding) from ({padding.padded_flights_sql('flights')})").fetchone()
    con.close()
    assert worst is not None and worst[0] >= -1e-9


def shares(draw: st.DrawFn) -> np.ndarray:
    weights = np.array(
        draw(st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=N_BINS, max_size=N_BINS))
    )
    if weights.sum() == 0:
        weights[draw(st.integers(min_value=0, max_value=N_BINS - 1))] = 1.0
    return weights / weights.sum()


@settings(max_examples=60, deadline=None)
@given(data=st.data(), shift=st.floats(min_value=-30.0, max_value=30.0))
def test_the_misconnect_probability_is_a_probability_and_never_rises_with_the_buffer(
    data: st.DataObject, shift: float
) -> None:
    arrival = shares(data.draw)
    departure = shares(data.draw)
    curve = [exceed_probability(arrival, departure, float(b), shift) for b in range(-30, 400, 5)]
    assert all(-1e-12 <= p <= 1 + 1e-12 for p in curve)
    assert all(later <= earlier + 1e-12 for earlier, later in zip(curve, curve[1:], strict=False))


@settings(max_examples=40, deadline=None)
@given(
    minutes=st.lists(
        st.tuples(*[st.integers(min_value=0, max_value=600) for _ in CAUSES]).filter(lambda t: sum(t) > 0),
        min_size=1,
        max_size=60,
    ),
    broken=st.lists(st.booleans(), min_size=60, max_size=60),
)
def test_the_reported_cause_shares_sum_to_one_where_a_breakdown_exists(
    minutes: list[tuple[int, ...]], broken: list[bool]
) -> None:
    flags = [not broken[i] for i in range(len(minutes))]
    if not any(flags):
        flags[0] = True
    frame = pl.DataFrame({name: [row[i] for row in minutes] for i, name in enumerate(CAUSES)}).with_columns(
        pl.Series("cause_ok", flags)
    )
    metrics = {m.name: m for m in load(ROOT / "metrics" / "metrics.yml")}
    con = duckdb.connect()
    con.register("f", frame.to_arrow())
    total = 0.0
    for name in SHARES:
        row = con.execute(f"select {metrics[name].flight} from f").fetchone()
        assert row is not None and row[0] is not None and 0.0 <= row[0] <= 1.0
        total += float(row[0])
    con.close()
    assert abs(total - 1.0) < 1e-9


@given(
    a=st.one_of(st.none(), st.floats(allow_nan=False, allow_infinity=False, width=64)),
    b=st.one_of(st.none(), st.floats(allow_nan=False, allow_infinity=False, width=64)),
)
def test_the_reconcile_is_symmetric(a: float | None, b: float | None) -> None:
    assert close(a, b) == close(b, a)
    if a is not None:
        assert close(a, a)
