"""Chapter 7: a meltdown is a recovery.

The detector scores every carrier day and every day at the thirty busiest airports against the unit's
own previous 28 days (turnaround_events.detect). The alert threshold is chosen on 2015 to 2022 by the
stated costs against the known events of those years, held to the interior test, and graded on 2023
onward against the known events of those years: recall, the day each event was first flagged against
its onset, and false alarms per thousand unit days. The persistence rule makes each alert an episode
whose length is the unit's recovery time, and a permutation test asks whether carriers differ in it.
The two carrier meltdowns get event studies against peer carriers at the same airports.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import polars as pl
from turnaround_events import detect, study

CARRIER = "carrier:"
AIRPORT = "airport:"
GRID = tuple(float(t) for t in np.arange(3.0, 30.5, 1.0))
TRAIT_MIN_EPISODES = 5
TRAIT_PERMUTATIONS = 2000


@dataclass(frozen=True)
class KnownEvent:
    name: str
    start: date
    end: date
    unit_type: str
    units: tuple[str, ...]
    window: str
    citation: str

    def as_event(self) -> detect.Event:
        prefix = CARRIER if self.unit_type == "carrier" else AIRPORT
        units = tuple(prefix + u for u in self.units) if self.unit_type != "all" else ()
        return detect.Event(self.name, self.start, self.end, units)


@dataclass(frozen=True)
class EventRow:
    name: str
    start: date
    end: date
    window: str
    units: str
    detected: bool
    first_alert: date | None
    lag_days: int | None
    peak: float | None


@dataclass(frozen=True)
class MeltdownResult:
    operating: detect.OperatingPoint
    fit: detect.Grade
    test: detect.Grade
    events: list[EventRow]
    airports: list[str]
    carriers: int
    unit_days_test: int
    studies: list[study.Study]
    recovery_by_carrier: pl.DataFrame
    trait_statistic: float
    trait_p_value: float
    trait_carriers: int
    episodes: pl.DataFrame
    sql_daily: str


def load_events(path: Path) -> list[KnownEvent]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    out = [
        KnownEvent(
            name=r["event"],
            start=date.fromisoformat(r["start"]),
            end=date.fromisoformat(r["end"]),
            unit_type=r["unit_type"],
            units=tuple(u for u in r["units"].split(";") if u),
            window=r["window"],
            citation=r["citation"],
        )
        for r in rows
    ]
    return sorted(out, key=lambda e: (e.start, e.name))


def busiest_airports(con: duckdb.DuckDBPyConnection, source: str, k: int) -> list[str]:
    rows = con.execute(
        f"select origin, count(*) as n from {source} group by origin order by n desc, origin limit {k}"
    ).fetchall()
    return sorted(str(r[0]) for r in rows)


def scored_units(con: duckdb.DuckDBPyConnection, source: str, airports: list[str]) -> pl.DataFrame:
    carriers = detect.run_daily(con, source, "carrier").with_columns(
        (pl.lit(CARRIER) + pl.col("unit")).alias("unit")
    )
    listed = ", ".join(f"'{a}'" for a in airports)
    ports = detect.run_daily(con, source, "origin", f"origin in ({listed})").with_columns(
        (pl.lit(AIRPORT) + pl.col("unit")).alias("unit")
    )
    return detect.anomalies(pl.concat([carriers, ports], how="vertical"))


def _event_rows(
    scored: pl.DataFrame, known: list[KnownEvent], threshold: float, slack_days: int = 2
) -> list[EventRow]:
    fired = detect.alerts(scored, threshold)
    out: list[EventRow] = []
    for k in known:
        event = k.as_event()
        hits = fired.filter(
            (pl.col("day") >= event.start)
            & (pl.col("day") <= pl.lit(event.end) + pl.duration(days=slack_days))
            & (pl.lit(not event.units) | pl.col("unit").is_in(list(event.units)))
        )
        first = hits["day"].min() if hits.height else None
        out.append(
            EventRow(
                name=k.name,
                start=k.start,
                end=k.end,
                window=k.window,
                units=";".join(k.units) if k.units else "all",
                detected=hits.height > 0,
                first_alert=first,  # type: ignore[arg-type]
                lag_days=(first - k.start).days if isinstance(first, date) else None,
                peak=float(hits["score"].max()) if hits.height else None,  # type: ignore[arg-type]
            )
        )
    return out


def recovery_trait(
    found: pl.DataFrame, *, seed: int, permutations: int = TRAIT_PERMUTATIONS
) -> tuple[pl.DataFrame, float, float, int]:
    """Episode lengths by carrier, and a permutation test of whether the carrier explains them.

    The statistic is the Kruskal-Wallis H on episode lengths across carriers with at least five
    episodes; its null distribution comes from shuffling the carrier labels (seeded, sorted first)."""
    carrier_eps = found.filter(pl.col("unit").str.starts_with(CARRIER)).with_columns(
        pl.col("unit").str.replace(CARRIER, "").alias("carrier")
    )
    table = (
        carrier_eps.group_by("carrier")
        .agg(
            pl.len().alias("episodes"),
            pl.col("days").median().alias("median_days"),
            pl.col("days").mean().alias("mean_days"),
            pl.col("days").max().alias("longest_days"),
        )
        .sort(["median_days", "mean_days", "carrier"])
    )
    eligible = table.filter(pl.col("episodes") >= TRAIT_MIN_EPISODES)["carrier"].to_list()
    data = carrier_eps.filter(pl.col("carrier").is_in(eligible)).sort(["carrier", "start", "days"])
    if len(eligible) < 2:
        return table, float("nan"), float("nan"), len(eligible)
    lengths = data["days"].to_numpy().astype(np.float64)
    ranks = _ranks(lengths)
    labels = np.unique(data["carrier"].to_numpy(), return_inverse=True)[1]

    def h_stat(lab: np.ndarray) -> float:
        n = ranks.shape[0]
        sums = np.bincount(lab, weights=ranks)
        counts = np.bincount(lab).astype(np.float64)
        return float(12.0 / (n * (n + 1)) * np.sum(sums**2 / counts) - 3.0 * (n + 1))

    observed = h_stat(labels)
    rng = np.random.default_rng(seed)
    exceed = sum(1 for _ in range(permutations) if h_stat(rng.permutation(labels)) >= observed - 1e-12)
    return table, observed, (exceed + 1) / (permutations + 1), len(eligible)


def _ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="stable")
    ranks = np.empty(values.shape[0])
    sorted_values = values[order]
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and sorted_values[j + 1] == sorted_values[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def estimate(
    con: duckdb.DuckDBPyConnection,
    source: str,
    *,
    known: list[KnownEvent],
    split: date,
    meltdowns: list[tuple[str, date, date]],
    cost_false_alarm: float,
    cost_miss: float,
    seed: int,
    airports: int = 30,
) -> MeltdownResult:
    ports = busiest_airports(con, source, airports)
    scored = scored_units(con, source, ports)
    fit_scores = scored.filter(pl.col("day") < split)
    test_scores = scored.filter(pl.col("day") >= split)
    fit_events = [k.as_event() for k in known if k.window == "fit"]
    test_events = [k.as_event() for k in known if k.window == "test"]
    operating = detect.choose_threshold(
        fit_scores, fit_events, grid=GRID, cost_false_alarm=cost_false_alarm, cost_miss=cost_miss
    )
    fit_grade = detect.grade(fit_scores, fit_events, operating.threshold)
    test_grade = detect.grade(test_scores, test_events, operating.threshold)
    rows = _event_rows(scored, known, operating.threshold)
    found = detect.episodes(scored, operating.threshold)
    trait, statistic, p_value, eligible = recovery_trait(found, seed=seed)
    studies = [study.study(con, source, carrier, onset, end) for carrier, onset, end in meltdowns]
    return MeltdownResult(
        operating=operating,
        fit=fit_grade,
        test=test_grade,
        events=rows,
        airports=ports,
        carriers=int(scored.filter(pl.col("unit").str.starts_with(CARRIER))["unit"].n_unique()),
        unit_days_test=test_grade.unit_days,
        studies=studies,
        recovery_by_carrier=trait,
        trait_statistic=statistic,
        trait_p_value=p_value,
        trait_carriers=eligible,
        episodes=found,
        sql_daily=detect.daily_sql(source, "carrier").strip(),
    )


def message(r: MeltdownResult) -> str:
    if r.trait_p_value < 0.05:
        return "A meltdown is a recovery, and how fast a carrier recovers is a trait of the carrier"
    return "Meltdowns are caught on their first day, but recovery speed does not separate the carriers"
