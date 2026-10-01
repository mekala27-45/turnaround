"""The calculator's binned arithmetic, its interval and the scorer."""

from __future__ import annotations

from datetime import date

import duckdb
import numpy as np
import polars as pl
import pytest
from turnaround_misconnect import marts, model
from turnaround_misconnect.curve import curves
from turnaround_sim.network import SimSpec, simulate


def test_triangle_arithmetic_matches_monte_carlo() -> None:
    rng = np.random.default_rng(5)
    arr_share = rng.dirichlet(np.ones(model.N_BINS))
    dep_share = rng.dirichlet(np.ones(model.N_BINS))
    exact = model.exceed_probability(arr_share, dep_share, 17.0, shift=3.0)
    n = 400_000
    a_bin = rng.choice(model.N_BINS, n, p=arr_share)
    d_bin = rng.choice(model.N_BINS, n, p=dep_share)
    a = model.CELL_LO + model.BIN * (a_bin + rng.random(n)) + 3.0
    d = model.CELL_LO + model.BIN * (d_bin + rng.random(n))
    assert exact == pytest.approx(float(np.mean(a - d > 17.0)), abs=0.004)


def test_wilson_interval_contains_the_estimate() -> None:
    for p, n in ((0.0, 10.0), (0.1, 500.0), (0.9, 40.0), (1.0, 3.0)):
        low, high = model.wilson(p, n)
        assert 0.0 <= low <= p <= high <= 1.0
    assert model.wilson(0.5, 0) == (0.0, 1.0)


@pytest.fixture(scope="module")
def cells_and_outcomes(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Cells, pl.DataFrame]:
    sim = simulate(SimSpec(seed=8))
    con = duckdb.connect()
    con.register("f", sim.flights.to_arrow())
    found = curves(
        con, "f", hubs=["H0", "H1"], where="month < 12", min_connection=25, line=0.1, replicates=50, seed=2
    )
    out = tmp_path_factory.mktemp("marts")
    marts.build(
        con, "f", hubs=["H0", "H1"], where="month < 12", outcome=(2023, 12), curves=found, out_dir=out
    )
    frames = marts.load(out)
    cells = model.Cells.from_frames(
        frames["misconnect_cells"],
        frames["misconnect_lost"],
        frames["misconnect_routes"],
        frames["misconnect_hubs"],
    )
    return cells, frames["misconnect_outcomes"]


def _route(cells: model.Cells) -> tuple[str, str, str]:
    inbound = sorted(k for k in cells.routes if k[1] == "H0" and k[2] == "in" and k[3] == 11)
    outbound = sorted(k for k in cells.routes if k[0] == "H0" and k[2] == "out" and k[3] == 11)
    return inbound[0][0], "H0", outbound[0][1]


def test_estimate_is_a_probability_that_falls_with_the_buffer(
    cells_and_outcomes: tuple[model.Cells, pl.DataFrame],
) -> None:
    cells, _ = cells_and_outcomes
    origin, hub, dest = _route(cells)
    found = cells.curve(
        origin=origin,
        hub=hub,
        destination=dest,
        month=11,
        inbound_hour=12,
        outbound_hour=13,
        buffers=list(range(0, 185, 15)),
        min_connection=25,
    )
    probs = [e.probability for e in found]
    assert all(0.0 <= p <= 1.0 for p in probs)
    assert all(b <= a + 1e-9 for a, b in zip(probs, probs[1:], strict=False))
    assert all(e.low <= e.probability <= e.high for e in found)
    assert found[0].flights > 0


def test_unknown_hub_and_unflown_route_are_refused(
    cells_and_outcomes: tuple[model.Cells, pl.DataFrame],
) -> None:
    cells, _ = cells_and_outcomes
    with pytest.raises(model.UnknownConnection):
        cells.estimate(
            origin="S01",
            hub="ZZZ",
            destination="S02",
            month=3,
            inbound_hour=9,
            outbound_hour=10,
            buffer=60,
            min_connection=25,
        )
    with pytest.raises(model.UnknownConnection):
        cells.estimate(
            origin="NOPE",
            hub="H0",
            destination="S02",
            month=3,
            inbound_hour=9,
            outbound_hour=10,
            buffer=60,
            min_connection=25,
        )


def test_realized_counts_same_day_pairs(cells_and_outcomes: tuple[model.Cells, pl.DataFrame]) -> None:
    _, outcomes = cells_and_outcomes
    assert outcomes["flight_date"].min() >= date(2023, 12, 1)  # type: ignore[operator]
    inbound = outcomes.filter((pl.col("kind") == "in") & (pl.col("dest") == "H0"))
    origin = sorted(inbound["origin"].unique().to_list())[0]
    hour = int(inbound.filter(pl.col("origin") == origin)["hour"][0])
    outbound = outcomes.filter((pl.col("kind") == "out") & (pl.col("origin") == "H0"))
    dest = sorted(outbound["dest"].unique().to_list())[0]
    out_hour = int(outbound.filter(pl.col("dest") == dest)["hour"][0])
    result = model.realized(
        outcomes,
        origin=origin,
        hub="H0",
        destination=dest,
        inbound_hour=hour,
        outbound_hour=out_hour,
        buffer=60,
        min_connection=25,
    )
    assert result is not None
    rate, pairs = result
    assert 0.0 <= rate <= 1.0 and pairs > 0
    never = model.realized(
        outcomes,
        origin="NOPE",
        hub="H0",
        destination=dest,
        inbound_hour=hour,
        outbound_hour=out_hour,
        buffer=60,
        min_connection=25,
    )
    assert never is None
