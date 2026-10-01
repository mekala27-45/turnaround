"""Rotations from tail numbers: the integrity rules, the planted impossible sequence, the swapped aircraft."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import duckdb
import numpy as np
import polars as pl
import pytest
from turnaround_rotations import propagation, reconstruct


def _legs(rows: list[tuple[str, str, str, str, int, int, int]]) -> pl.DataFrame:
    """(tail, origin, dest, scheduled departure HH:MM on 2024-05-01, block minutes, dep delay, arr delay)."""
    out = []
    for i, (tail, origin, dest, hhmm, block, dep, arr) in enumerate(rows):
        h, m = map(int, hhmm.split(":"))
        sdep = datetime(2024, 5, 1, h, m)
        out.append(
            {
                "flight_id": i + 1,
                "flight_date": date(2024, 5, 1),
                "carrier": "XX",
                "tail_number": tail,
                "origin": origin,
                "dest": dest,
                "dep_hour": h,
                "sched_dep_utc": sdep,
                "sched_arr_utc": sdep + timedelta(minutes=block),
                "dep_delay": dep,
                "arr_delay": arr,
                "cancelled": False,
                "diverted": False,
            }
        )
    return pl.DataFrame(out)


def _run(frame: pl.DataFrame) -> tuple[duckdb.DuckDBPyConnection, reconstruct.RotationCounts]:
    con = duckdb.connect()
    con.register("f", frame.to_arrow())
    return con, reconstruct.reconstruct(con, "f", "legs", 6.0)


def test_clean_day_links_every_leg_and_satisfies_the_rules() -> None:
    con, counts = _run(
        _legs(
            [
                ("N1", "AAA", "BBB", "06:00", 90, 0, 5),
                ("N1", "BBB", "CCC", "08:15", 80, 10, 12),
                ("N1", "CCC", "AAA", "10:30", 100, 0, -3),
            ]
        )
    )
    assert counts.linked == 2 and counts.first == 1 and counts.rotations == 1
    bad = con.execute(
        "select count(*) from legs where link_status = 'linked' and (prev_dest <> origin or sched_dep_utc < prev_sched_arr_utc)"
    ).fetchone()
    assert bad == (0,)
    assert con.execute("select list(leg_index order by sched_dep_utc) from legs").fetchone() == ([1, 2, 3],)


def test_planted_impossible_sequence_is_quarantined() -> None:
    # The second leg left before the first had landed: one airframe cannot do that.
    con, counts = _run(
        _legs([("N2", "AAA", "BBB", "06:00", 90, 0, 60), ("N2", "BBB", "CCC", "08:00", 80, 0, 0)])
    )
    assert counts.impossible == 1 and counts.linked == 0
    assert counts.rotations == 2


def test_swapped_aircraft_is_split_not_joined() -> None:
    # The tail number says the airframe jumped from BBB to DDD between legs: an unrecorded swap.
    con, counts = _run(
        _legs([("N3", "AAA", "BBB", "06:00", 90, 0, 0), ("N3", "DDD", "EEE", "09:00", 60, 0, 0)])
    )
    assert counts.broken_chain == 1 and counts.linked == 0 and counts.rotations == 2


def test_a_long_sit_starts_a_new_rotation() -> None:
    con, counts = _run(
        _legs([("N4", "AAA", "BBB", "06:00", 60, 0, 0), ("N4", "BBB", "AAA", "14:00", 60, 0, 0)])
    )
    assert counts.gap == 1 and counts.rotations == 2


def test_every_leg_gets_exactly_one_rotation_and_the_counts_add_up() -> None:
    rows = [
        ("N5", "AAA", "BBB", "06:00", 60, 0, 0),
        ("N5", "BBB", "AAA", "07:30", 60, 0, 0),
        ("N6", "CCC", "DDD", "06:00", 60, 0, 0),
    ]
    con, counts = _run(_legs(rows))
    assert counts.legs == len(rows)
    assert counts.linked + counts.starts == counts.legs
    assert counts.rotations == counts.starts


def test_halving_buffer_and_inherited_share_bounds() -> None:
    rng = np.random.default_rng(1)
    late = rng.exponential(20.0, 5000)
    b = propagation.halving_buffer(late)
    assert 0 < b < 60
    assert np.maximum(late - b, 0).mean() <= 0.5 * late.mean()
    links = propagation.Links(
        dep_delay=rng.normal(5, 10, 300),
        prev_arr_delay=rng.normal(5, 20, 300),
        sched_turn=rng.uniform(30, 90, 300),
        carrier_day=np.zeros(300, dtype=np.int64),
        origin_day=np.zeros(300, dtype=np.int64),
        dep_hour=np.zeros(300, dtype=np.int64),
        cluster=np.arange(300, dtype=np.int64) // 3,
    )
    inherited = propagation.inherited_minutes(links, 1.0, 35)
    assert 0.0 <= inherited <= float(np.maximum(links.dep_delay, 0).sum())


@pytest.mark.parametrize("rho", [0.5, 1.0])
def test_rho_recovered_on_a_linear_fixture(rho: float) -> None:
    rng = np.random.default_rng(2)
    n = 20000
    prev = rng.exponential(25.0, n) - 10
    turn = rng.uniform(30, 120, n)
    carrier = rng.integers(0, 3, n)
    x = np.maximum(0.0, prev - (turn - 40))
    dep = rho * x + np.array([0.0, 2.0, -1.0])[carrier] + rng.normal(0, 5, n)
    links = propagation.Links(
        dep, prev, turn, carrier.astype(np.int64), rng.integers(0, 50, n).astype(np.int64),
        rng.integers(0, 24, n).astype(np.int64), np.arange(n, dtype=np.int64) // 4,
    )  # fmt: skip
    m, _ = propagation.profile_min_turn(links)
    estimate, se, clusters, converged = propagation.fit_rho(links, m)
    assert m == 40 and converged
    assert abs(estimate - rho) < 4 * se + 0.01
    assert clusters == n // 4


def test_buckets_of_tails_together_equal_one_statement() -> None:
    # The warehouse builds int_legs one bucket of tails at a time; the union must be the same table.
    rng = np.random.default_rng(14)
    rows = []
    airports = ["AAA", "BBB", "CCC", "DDD"]
    for t in range(40):
        place = "AAA"
        clock = 5 * 60 + int(rng.integers(0, 120))
        for _ in range(int(rng.integers(2, 7))):
            dest = airports[int(rng.integers(0, 4))]
            if rng.random() < 0.1:
                place = airports[int(rng.integers(0, 4))]  # a swap the tail number does not show
            rows.append(
                (
                    f"N{t + 1}",
                    place,
                    dest,
                    f"{clock // 60:02d}:{clock % 60:02d}",
                    75,
                    int(rng.integers(-5, 60)),
                    int(rng.integers(-10, 70)),
                )
            )
            place = dest
            clock += 75 + int(rng.integers(20, 200))
            if clock > 22 * 60:
                break
    con = duckdb.connect()
    con.register("f", _legs(rows).to_arrow())
    whole = con.execute(f"select * from ({reconstruct.full_sql('f', 6.0)}) order by flight_id").fetchall()
    parts = " union all ".join(f"({reconstruct.full_sql('f', 6.0, bucket=(b, 5))})" for b in range(5))
    pieces = con.execute(f"select * from ({parts}) order by flight_id").fetchall()
    assert len(whole) == len(rows) and pieces == whole
