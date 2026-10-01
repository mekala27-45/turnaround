"""Chapters 6, 7 and 8 on simulated networks: the weather estimator against planted storms, the
recovery trait test, and the reader's tables. The chapters stage test runs every chapter end to end."""

from __future__ import annotations

from datetime import date

import duckdb
import numpy as np
import polars as pl
import pytest
from turnaround_chapters import ch06_causes, ch07_meltdowns, ch08_decision
from turnaround_rotations import reconstruct
from turnaround_sim.network import SimSpec, Simulation, simulate


@pytest.fixture(scope="module")
def sim() -> Simulation:
    return simulate(SimSpec(seed=41, confounding=0.0, noise=4.0, weather_storm_rate=0.05))


@pytest.fixture(scope="module")
def con(sim: Simulation) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    connection.execute("set enable_progress_bar = false")
    connection.register("f", sim.flights.to_arrow())
    reconstruct.reconstruct(connection, "f", "legs", 6.0)
    return connection


def test_weather_share_is_recovered_and_the_reported_field_understates_it(
    sim: Simulation, con: duckdb.DuckDBPyConnection
) -> None:
    r = ch06_causes.estimate(con, "f", where="true", legs="legs", min_turn=sim.spec.min_turn, top_airports=10)
    assert r.weather_share_low <= sim.truth.weather_share <= r.weather_share_high
    assert abs(r.weather_share - sim.truth.weather_share) < 0.02
    coefficients = {name: b for name, b, _ in r.coefficients}
    assert coefficients["origin_thunder"] == pytest.approx(sim.spec.weather_storm_minutes, abs=2.0)
    assert coefficients["dest_thunder"] == pytest.approx(
        sim.spec.weather_storm_minutes * sim.spec.weather_dest_fraction, abs=2.0
    )
    assert r.reported_weather_share == pytest.approx(sim.truth.reported_weather_share, abs=1e-9)
    assert r.reported_weather_share < r.weather_share
    assert ch06_causes.message(r) == "Weather explains more delay than the weather field records"


def test_cause_fields_sum_to_the_arrival_delay(sim: Simulation) -> None:
    late = sim.flights.filter(pl.col("cause_carrier").is_not_null())
    total = late.select(
        pl.sum_horizontal(
            "cause_carrier", "cause_weather", "cause_nas", "cause_security", "cause_late_aircraft"
        )
    ).to_series()
    assert (total == late["arr_delay"]).all()
    assert (late["arr_delay"] >= 15).all()


def test_recovery_trait_test_finds_planted_differences_and_not_planted_sameness() -> None:
    rng = np.random.default_rng(3)
    rows = []
    for carrier, mean in (("AA", 1.5), ("BB", 1.5), ("CC", 6.0)):
        for i in range(30):
            days = max(1, int(rng.poisson(mean)))
            rows.append(
                ("carrier:" + carrier, date(2020, 1, 1 + i % 28), date(2020, 1, 1 + i % 28), days, 9.0)
            )
    found = pl.DataFrame(rows, schema=["unit", "start", "end", "days", "peak"], orient="row")
    table, statistic, p_value, carriers = ch07_meltdowns.recovery_trait(found, seed=1, permutations=500)
    assert carriers == 3 and p_value < 0.01 and statistic > 0
    assert table["carrier"][-1] == "CC"
    same = found.with_columns(pl.lit(2).alias("days"))
    _, _, p_same, _ = ch07_meltdowns.recovery_trait(same, seed=1, permutations=200)
    assert p_same > 0.5


def test_known_events_load_with_citations() -> None:
    from pathlib import Path

    events = ch07_meltdowns.load_events(Path(__file__).resolve().parents[2] / "data" / "known_events.csv")
    assert len(events) >= 10
    assert all(e.citation.startswith("https://") for e in events)
    assert all(e.start <= e.end for e in events)
    assert {e.window for e in events} == {"fit", "test"}
    assert all((e.window == "fit") == (e.start.year <= 2022) for e in events)


def test_reader_tables_and_buffer_trade(sim: Simulation, con: duckdb.DuckDBPyConnection) -> None:
    r = ch08_decision.estimate(
        con,
        "f",
        legs="legs",
        where="true",
        legs_where="true",
        rho=sim.spec.propagation,
        min_turn=sim.spec.min_turn,
        hubs=4,
        min_connection=25,
        line=0.10,
        replicates=50,
        seed=2,
    )
    assert r.by_hour["flights"].sum() == sim.flights.filter(~pl.col("cancelled")).height
    assert r.first_on_time > r.later_on_time, "the simulator carries delay down the day"
    assert r.first_advantage.low > 0
    assert 0 < r.binding_share < 1 and 0 < r.binding_after_binding < 1
    assert r.trade_overall >= 0
    assert all(h.replicates == 50 for h in r.hubs)
