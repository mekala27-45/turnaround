"""The detector, its operating point and the event study, on small fixtures with planted answers."""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import numpy as np
import polars as pl
import pytest
from turnaround_events import detect, study


def _daily(spike_days: tuple[int, ...], seed: int = 1) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for unit in ("AA", "BB"):
        for d in range(120):
            scheduled = 500
            rate = 0.015 + rng.normal(0, 0.003)
            delay = 8 + rng.normal(0, 2)
            if unit == "AA" and d in spike_days:
                rate, delay = 0.30, 55.0
            rows.append({"unit": unit, "day": date(2024, 1, 1) + timedelta(days=d), "scheduled": scheduled,
                         "cancelled": int(round(rate * scheduled)), "mean_delay": delay})  # fmt: skip
    return pl.DataFrame(rows)


def test_planted_spike_is_found_on_its_first_day() -> None:
    scored = detect.anomalies(_daily((80, 81, 82)))
    fired = detect.alerts(scored, 4.0)
    assert date(2024, 1, 1) + timedelta(days=80) in fired.filter(pl.col("unit") == "AA")["day"].to_list()
    assert fired.filter(pl.col("unit") == "BB").height == 0


def test_no_score_before_the_baseline_has_history() -> None:
    scored = detect.anomalies(_daily(()))
    first_days = scored.filter(pl.col("day") < date(2024, 1, 1) + timedelta(days=detect.MIN_HISTORY))
    assert first_days["score"].null_count() == first_days.height


def test_grade_counts_recall_lag_and_false_alarms() -> None:
    scored = detect.anomalies(_daily((80, 81, 82, 100)))
    events = [detect.Event("planted", date(2024, 3, 21), date(2024, 3, 23), ("AA",))]
    graded = detect.grade(scored, events, 4.0)
    assert graded.recall == 1.0 and graded.lags == [0]
    assert graded.false_alarm_days >= 1  # day 100 is not in the table


def test_operating_point_is_chosen_by_cost_and_tested_for_the_interior() -> None:
    scored = detect.anomalies(_daily((80, 81, 82)))
    events = [detect.Event("planted", date(2024, 3, 21), date(2024, 3, 23), ("AA",))]
    point = detect.choose_threshold(
        scored, events, grid=[1.0, 2.0, 4.0, 8.0, 1000.0], cost_false_alarm=1.0, cost_miss=25.0
    )
    assert point.interior
    assert 1.0 < point.threshold < 1000.0
    edge = detect.choose_threshold(scored, events, grid=[1000.0, 2000.0], cost_false_alarm=1.0, cost_miss=0.0)
    assert not edge.interior


def test_event_study_excludes_the_treated_carrier_from_its_peers() -> None:
    rng = np.random.default_rng(3)
    rows = []
    for d in range(60):
        day = date(2024, 6, 1) + timedelta(days=d)
        for carrier in ("WN", "DL", "UA"):
            for i in range(40):
                melt = carrier == "WN" and 35 <= d < 39
                rows.append({"flight_date": day, "carrier": carrier, "origin": ["DEN", "LAS"][i % 2],
                             "cancelled": bool(rng.random() < (0.5 if melt else 0.02)), "diverted": False,
                             "arr_delay": float(rng.normal(60 if melt else 5, 5))})  # fmt: skip
    con = duckdb.connect()
    con.register("f", pl.DataFrame(rows).to_arrow())
    onset = date(2024, 6, 1) + timedelta(days=35)
    result = study.study(con, "f", "WN", onset, onset + timedelta(days=3), airports=2)
    series = result.series
    assert (series["peer_scheduled"] == 80).all() and (series["treated_scheduled"] == 40).all()
    assert result.excess_cancelled > 40
    assert result.recovery_days is not None and 3 <= result.recovery_days <= 8


@pytest.mark.parametrize("unit", ["carrier", "origin"])
def test_daily_sql_groups_by_the_stated_unit(unit: str) -> None:
    sql = detect.daily_sql("f", unit)
    assert f"select {unit} as unit" in sql
