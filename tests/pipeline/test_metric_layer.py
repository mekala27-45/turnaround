"""The metric layer: a correct mart reconciles at every grain, a broken mart fails, an empty one refuses."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from turnaround_pipeline.metric_layer import Metric, MetricError, close, load, reconcile

ROOT = Path(__file__).resolve().parents[2]
MART_SQL = """
create table mart_carrier_month as
select carrier, year, month, count(*) as scheduled, count(*) filter (where cancelled) as cancelled,
       count(*) filter (where diverted) as diverted,
       count(*) filter (where not cancelled and not diverted) as flown,
       count(*) filter (where not cancelled and not diverted and arr_delay < 15) as on_time,
       sum(arr_delay) filter (where not cancelled and not diverted) as arr_delay_sum
from fct_flights group by all
"""
HIST_SQL = """
create table mart_delay_histogram as
select carrier, year, month, cast(least(greatest(arr_delay, -60), 300) as integer) as minute, count(*) as flights
from fct_flights where not cancelled and not diverted and arr_delay is not null group by all
"""


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    c.execute(
        """
        create table fct_flights as
        select
            case when i % 3 = 0 then 'AA' when i % 3 = 1 then 'DL' else 'WN' end as carrier,
            2023 + (i % 2) as year,
            1 + (i % 12) as month,
            (i % 37 = 0) as cancelled,
            (i % 101 = 0) as diverted,
            cast(((i * 7919) % 97) - 20 as integer) as arr_delay
        from range(5000) t(i)
        """
    )
    c.execute(MART_SQL)
    c.execute(HIST_SQL)
    return c


def _metrics() -> list[Metric]:
    keep = {
        "scheduled_flights",
        "cancellation_rate",
        "on_time_rate",
        "mean_arrival_delay",
        "median_arrival_delay",
        "completion_factor",
    }
    return [m for m in load(ROOT / "metrics" / "metrics.yml") if m.name in keep]


def test_every_metric_reconciles_at_every_grain(con: duckdb.DuckDBPyConnection) -> None:
    report = reconcile(con, _metrics())
    assert report.ok, report.disagreements[:3]
    assert report.metrics == 6 and report.grains == 4
    assert report.cells > report.metrics * 4


def test_a_mart_that_dropped_rows_fails(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("delete from mart_carrier_month where carrier = 'WN' and month = 3")
    report = reconcile(con, _metrics())
    assert not report.ok
    assert {d.grain for d in report.disagreements} >= {"overall", "by carrier"}


def test_the_reconcile_refuses_an_empty_mart(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("delete from mart_carrier_month")
    with pytest.raises(MetricError, match="empty"):
        reconcile(con, _metrics())
    with pytest.raises(MetricError):
        reconcile(con, [])


def test_closeness_is_symmetric() -> None:
    for a, b in [(1.0, 1.0 + 1e-12), (0.0, 1e-10), (None, None), (2.0, 3.0), (None, 1.0)]:
        assert close(a, b) == close(b, a)


def test_the_layer_file_defines_each_metric_once_with_both_expressions() -> None:
    metrics = load(ROOT / "metrics" / "metrics.yml")
    assert len({m.name for m in metrics}) == len(metrics) >= 15
    assert all(m.flight and m.mart and m.fmt for m in metrics)
    assert (
        next(m for m in metrics if m.name == "on_time_rate").dax()
        == "DIVIDE(SUM('carrier_month'[on_time]), SUM('carrier_month'[flown]))"
    )
