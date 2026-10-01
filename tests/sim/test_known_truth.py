"""Known truth tests: with the noise turned down and no confounding, each estimator recovers what the
simulator planted. These are the tests the chapters' method notes point to."""

from __future__ import annotations

from datetime import date

import duckdb
import polars as pl
import pytest
from turnaround_chapters import line, padding, ranking
from turnaround_core.config import POLICY
from turnaround_events import detect
from turnaround_rotations import propagation, reconstruct
from turnaround_sim.network import SimSpec, Simulation, simulate


@pytest.fixture(scope="module")
def quiet() -> Simulation:
    return simulate(
        SimSpec(
            seed=11,
            confounding=0.0,
            propagation=1.0,
            noise=2.0,
            congestion_zero_share=0.5,
            congestion_scale=4.0,
            weather_storm_rate=0.0,
            swap_rate=0.0,
        )
    )


@pytest.fixture(scope="module")
def con(quiet: Simulation) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    connection.execute("set enable_progress_bar = false")
    connection.register("sim_flights", quiet.flights.to_arrow())
    return connection


def test_padding_is_recovered_and_changepoints_land_on_their_dates(
    quiet: Simulation, con: duckdb.DuckDBPyConnection
) -> None:
    padding.build_unimpeded(
        con, "sim_flights", where_fit="true", percentile=POLICY.unimpeded_percentile, min_flights=20
    )
    con.execute(f"create or replace table padded as {padding.padded_flights_sql('sim_flights')}")
    estimated = padding.carrier_route_month(con, "padded")
    joined = estimated.join(
        quiet.truth.padding_by_carrier_route_month, on=["carrier", "route", "month"], suffix="_true"
    )
    assert float((joined["padding"] - joined["padding_true"]).abs().mean()) < 0.6
    weekly = padding.series(con, "padded", "cast(date_trunc('week', flight_date) as date)")
    found, searched = padding.changepoints(weekly, min_size=4, min_step=1.0)
    assert searched == len(quiet.truth.padding_change)
    for carrier, step in quiet.truth.padding_change.items():
        mine = [cp for cp in found if cp.carrier == carrier]
        if step == 0.0:
            assert mine == []
        else:
            true_day = date.fromisoformat(quiet.truth.padding_change_date[carrier])
            assert min(abs((cp.when - true_day).days) for cp in mine) <= 7


def test_propagation_coefficient_and_minimum_turn_are_recovered(
    quiet: Simulation, con: duckdb.DuckDBPyConnection
) -> None:
    reconstruct.reconstruct(con, "sim_flights", "legs", POLICY.rotation_gap_hours)
    fit_links = propagation.load_links(con, "legs", "flight_date < date '2023-07-01'")
    test_links = propagation.load_links(con, "legs", "flight_date >= date '2023-07-01'")
    est = propagation.estimate(fit_links, test_links, bins=POLICY.turn_bins)
    assert est.min_turn == quiet.truth.min_turn
    # A small downward bias remains (an early departure is capped, so the slope flattens at the
    # smallest excesses); the recovery study reports it by condition.
    assert abs(est.rho - quiet.truth.propagation) < 0.03
    assert est.converged


def test_adjusted_ranking_equals_the_true_ranking(quiet: Simulation, con: duckdb.DuckDBPyConnection) -> None:
    result = ranking.estimate(con, "sim_flights")
    assert result.order("adjusted") == quiet.truth.carrier_effect_ranking


def test_density_test_fires_on_planted_carriers_only(
    quiet: Simulation, con: duckdb.DuckDBPyConnection
) -> None:
    lines = line.by_carrier(con, "sim_flights", q=POLICY.bh_q)
    flagged = {r.carrier for r in lines if r.flagged}
    assert flagged == set(quiet.truth.bunching_carriers)
    assert all(r.test.placebos_evaluated == len(lines[0].test.placebo_statistics) for r in lines)


def test_detector_finds_the_meltdown_on_its_first_day(
    quiet: Simulation, con: duckdb.DuckDBPyConnection
) -> None:
    scored = detect.anomalies(detect.run_daily(con, "sim_flights", "carrier"))
    days = [date.fromisoformat(d) for d in quiet.truth.meltdown_dates]
    fired = detect.alerts(scored, 4.0).filter(pl.col("unit") == quiet.truth.meltdown_carrier)
    assert days[0] in set(fired["day"].to_list())


def test_simulation_is_deterministic_for_a_seed() -> None:
    a = simulate(SimSpec(seed=3, days=40))
    b = simulate(SimSpec(seed=3, days=40))
    assert a.flights.equals(b.flights)
    assert a.truth.carrier_effect == b.truth.carrier_effect
