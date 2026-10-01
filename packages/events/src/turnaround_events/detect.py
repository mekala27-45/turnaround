"""Disruptions found in the daily numbers: a carrier's (or an airport's) day against its own recent normal.

For each carrier and day: the share of scheduled flights cancelled and the mean arrival delay of the
flights that flew. The baseline is the median of the previous 28 days for the same carrier, and the
spread their median absolute deviation, with a floor so that a carrier with a very steady record is
not flagged for one bad afternoon. A day's score is the larger of its two standardized anomalies.

An alert is a day whose score passes the threshold. The threshold is the operating point: chosen on
the fitting years by the cost of a false alarm day against the cost of a missed disruption, graded
on the test years, and held to the interior test (a threshold at the edge of the grid means the cost
curve had no minimum inside it, and the page says so).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

import duckdb
import numpy as np
import polars as pl

WINDOW_DAYS = 28
MIN_HISTORY = 14
CANCEL_FLOOR = 0.006
DELAY_FLOOR = 2.5


def daily_sql(source: str, unit: str, where: str = "true") -> str:
    """Per unit (carrier or origin) and day: scheduled flights, cancellations, mean arrival delay flown."""
    return f"""
    select {unit} as unit, flight_date as day, count(*) as scheduled,
           count(*) filter (where cancelled) as cancelled,
           avg(arr_delay) filter (where not cancelled and not diverted) as mean_delay
    from {source}
    where ({where})
    group by all order by unit, day
    """


def anomalies(daily: pl.DataFrame) -> pl.DataFrame:
    """Baseline, spread and standardized anomalies against each unit's previous 28 days."""
    frames: list[pl.DataFrame] = []
    for unit in sorted(daily["unit"].unique().to_list()):
        sub = daily.filter(pl.col("unit") == unit).sort("day")
        rate = (sub["cancelled"] / sub["scheduled"]).to_numpy().astype(np.float64)
        delay = sub["mean_delay"].fill_null(np.nan).to_numpy().astype(np.float64)
        n = rate.shape[0]
        z_cancel = np.full(n, np.nan)
        z_delay = np.full(n, np.nan)
        base_cancel = np.full(n, np.nan)
        base_delay = np.full(n, np.nan)
        for i in range(n):
            lo = max(0, i - WINDOW_DAYS)
            if i - lo < MIN_HISTORY:
                continue
            past_rate = rate[lo:i]
            past_delay = delay[lo:i][np.isfinite(delay[lo:i])]
            med_r = float(np.median(past_rate))
            mad_r = float(np.median(np.abs(past_rate - med_r))) * 1.4826
            base_cancel[i] = med_r
            z_cancel[i] = (rate[i] - med_r) / max(mad_r, CANCEL_FLOOR)
            if past_delay.size >= MIN_HISTORY // 2 and np.isfinite(delay[i]):
                med_d = float(np.median(past_delay))
                mad_d = float(np.median(np.abs(past_delay - med_d))) * 1.4826
                base_delay[i] = med_d
                z_delay[i] = (delay[i] - med_d) / max(mad_d, DELAY_FLOOR)
        frames.append(
            sub.with_columns(
                pl.Series("cancel_rate", rate),
                pl.Series("baseline_cancel", base_cancel),
                pl.Series("baseline_delay", base_delay),
                pl.Series("z_cancel", z_cancel),
                pl.Series("z_delay", z_delay),
            )
        )
    out = pl.concat(frames, how="vertical")
    return out.with_columns(
        pl.max_horizontal(pl.col("z_cancel").fill_nan(None), pl.col("z_delay").fill_nan(None)).alias("score")
    )


@dataclass(frozen=True)
class Event:
    name: str
    start: date
    end: date
    units: tuple[str, ...]  # carriers or airports affected; empty means every unit


@dataclass(frozen=True)
class Grade:
    threshold: float
    events: int
    detected: int
    lags: list[int]
    false_alarm_days: int
    unit_days: int

    @property
    def recall(self) -> float:
        return self.detected / self.events if self.events else float("nan")

    @property
    def false_alarm_rate(self) -> float:
        return self.false_alarm_days / self.unit_days if self.unit_days else float("nan")


def alerts(scored: pl.DataFrame, threshold: float) -> pl.DataFrame:
    return scored.filter(pl.col("score") > threshold).select("unit", "day", "score")


def _covered(unit: str, day: date, events: Sequence[Event], slack_days: int) -> bool:
    for event in events:
        if (not event.units or unit in event.units) and event.start <= day <= event.end + timedelta(
            days=slack_days
        ):
            return True
    return False


def grade(scored: pl.DataFrame, events: Sequence[Event], threshold: float, *, slack_days: int = 2) -> Grade:
    fired = alerts(scored, threshold)
    pairs = list(zip(fired["unit"].to_list(), fired["day"].to_list(), strict=True))
    detected = 0
    lags: list[int] = []
    for event in events:
        hits = [
            d
            for u, d in pairs
            if (not event.units or u in event.units)
            and event.start <= d <= event.end + timedelta(days=slack_days)
        ]
        if hits:
            detected += 1
            lags.append((min(hits) - event.start).days)
    false_days = sum(1 for u, d in pairs if not _covered(u, d, events, slack_days))
    eligible = scored.filter(pl.col("score").is_not_null())
    return Grade(threshold, len(events), detected, lags, false_days, eligible.height)


@dataclass(frozen=True)
class OperatingPoint:
    threshold: float
    grid: list[float]
    costs: list[float]
    interior: bool
    cost_false_alarm: float
    cost_miss: float


def choose_threshold(
    scored: pl.DataFrame,
    events: Sequence[Event],
    *,
    grid: Sequence[float],
    cost_false_alarm: float,
    cost_miss: float,
) -> OperatingPoint:
    costs: list[float] = []
    for t in grid:
        g = grade(scored, events, t)
        costs.append(cost_false_alarm * g.false_alarm_days + cost_miss * (g.events - g.detected))
    best = int(np.argmin(np.asarray(costs)))
    interior = 0 < best < len(grid) - 1
    return OperatingPoint(
        float(grid[best]), [float(g) for g in grid], costs, interior, cost_false_alarm, cost_miss
    )


def run_daily(con: duckdb.DuckDBPyConnection, source: str, unit: str, where: str = "true") -> pl.DataFrame:
    return con.execute(daily_sql(source, unit, where)).pl()
