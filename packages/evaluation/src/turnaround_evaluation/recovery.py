"""The recovery study: every estimator graded on simulated networks where the truth is known.

Conditions cross three things that break these estimators in practice: how strongly the better
carriers are steered onto the harder routes (none, moderate, strong confounding), how much of a late
arrival comes through to the next departure (propagation 0.8 or 1.0), and how noisy the operation is
(low noise with a quarter of flights flying unimpeded, high noise with one in sixteen). Twenty seeds
per condition. Each run simulates a year and runs the same estimator code the chapters run on the
real flights, then compares with the truth:

- padding: mean absolute error of padding by carrier, route and month; the changepoint date error
  for carriers whose padding stepped, and changepoints found where nothing stepped;
- propagation: the coefficient's bias and whether its interval covers the truth, the minimum turn
  found, and the inherited share against the true share;
- the fair ranking: rank correlation with the true carrier effects, adjusted against raw;
- the density test: false positive rate on clean carriers, power on carriers with planted bunching;
- the detector: whether it caught the planted meltdown, how late, and its precision.

Runs are cached under .cache/recovery keyed by a digest of the run's spec and the code version, so
an interrupted study resumes; the rederive passes no_cache and runs every seed again.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from turnaround_core.hashing import design_hash
from turnaround_sim.network import SimSpec

CODE_VERSION = "recovery-v2"
SPLIT = date(2023, 7, 1)
DETECTOR_THRESHOLD = 4.0
CHANGE_TOLERANCE_DAYS = 14


@dataclass(frozen=True)
class Condition:
    name: str
    confounding: float
    propagation: float
    noise: float
    zero_share: float


def conditions() -> list[Condition]:
    out: list[Condition] = []
    for conf_name, conf in (("none", 0.0), ("moderate", 0.5), ("strong", 0.9)):
        for prop_name, prop in (("weak", 0.8), ("strong", 1.0)):
            for noise_name, noise, zero in (("low", 8.0, 0.25), ("high", 16.0, 0.06)):
                out.append(
                    Condition(
                        f"confounding {conf_name}, propagation {prop_name}, noise {noise_name}",
                        conf,
                        prop,
                        noise,
                        zero,
                    )
                )
    return out


def spec_for(condition: Condition, seed: int) -> SimSpec:
    return SimSpec(
        seed=seed,
        confounding=condition.confounding,
        propagation=condition.propagation,
        noise=condition.noise,
        congestion_zero_share=condition.zero_share,
    )


def run_one(condition: Condition, seed: int) -> dict[str, object]:
    """One simulated year and every estimator on it. Pure: the same inputs give the same record."""
    import duckdb
    import numpy as np
    import polars as pl
    from turnaround_chapters import line, padding, ranking
    from turnaround_core.config import POLICY
    from turnaround_events import detect
    from turnaround_rotations import propagation, reconstruct
    from turnaround_sim.network import simulate

    sim = simulate(spec_for(condition, seed))
    truth = sim.truth
    con = duckdb.connect()
    con.execute("set enable_progress_bar = false")
    con.execute("set threads = 1")
    con.register("sim_flights", sim.flights.to_arrow())
    record: dict[str, object] = {"condition": condition.name, "seed": seed, "flights": sim.flights.height}

    # Padding and its changepoints.
    padding.build_unimpeded(
        con, "sim_flights", where_fit="true", percentile=POLICY.unimpeded_percentile, min_flights=20
    )
    con.execute(f"create table padded as {padding.padded_flights_sql('sim_flights')}")
    estimated = padding.carrier_route_month(con, "padded")
    joined = estimated.join(
        truth.padding_by_carrier_route_month, on=["carrier", "route", "month"], suffix="_true"
    )
    errors = (joined["padding"] - joined["padding_true"]).to_numpy()
    record["padding_mae"] = float(np.abs(errors).mean())
    record["padding_bias"] = float(errors.mean())
    weekly = padding.series(con, "padded", "cast(date_trunc('week', flight_date) as date)")
    found, searched = padding.changepoints(weekly, min_size=4, min_step=1.0)
    record["changepoint_carriers_searched"] = searched
    stepped = [c for c, step in truth.padding_change.items() if step != 0.0]
    date_errors: list[int] = []
    hits = 0
    for carrier in stepped:
        true_day = date.fromisoformat(truth.padding_change_date[carrier])
        mine = [cp for cp in found if cp.carrier == carrier]
        if mine:
            best = min(abs((cp.when - true_day).days) for cp in mine)
            if best <= CHANGE_TOLERANCE_DAYS:
                hits += 1
                date_errors.append(best)
    record["changepoints_true"] = len(stepped)
    record["changepoints_found"] = hits
    record["changepoint_date_error_days"] = float(np.mean(date_errors)) if date_errors else None
    record["changepoints_false"] = sum(
        1
        for cp in found
        if cp.carrier not in stepped
        or abs((cp.when - date.fromisoformat(truth.padding_change_date[cp.carrier])).days)
        > CHANGE_TOLERANCE_DAYS
    )

    # Rotations and propagation: the minimum turn chosen on the first half, rho reported on the second.
    counts = reconstruct.reconstruct(con, "sim_flights", "legs", POLICY.rotation_gap_hours)
    record["legs"] = counts.legs
    record["rotations"] = counts.rotations
    record["links_impossible"] = counts.impossible
    record["links_broken"] = counts.broken_chain
    fit_links = propagation.load_links(con, "legs", f"flight_date < date '{SPLIT}'")
    test_links = propagation.load_links(con, "legs", f"flight_date >= date '{SPLIT}'")
    est = propagation.estimate(fit_links, test_links, bins=POLICY.turn_bins)
    record["rho_true"] = truth.propagation
    record["rho_hat"] = est.rho
    record["rho_low"] = est.low
    record["rho_high"] = est.high
    record["rho_covered"] = int(est.low <= truth.propagation <= est.high)
    record["min_turn_true"] = truth.min_turn
    record["min_turn_hat"] = est.min_turn
    second = sim.flights.filter(~pl.col("cancelled") & (pl.col("flight_date") >= SPLIT))
    arrival_minutes = float(second["arr_delay"].clip(lower_bound=0).sum())
    true_inherited = float(
        second.select(pl.min_horizontal("true_inherited", pl.col("dep_delay").clip(lower_bound=0)))
        .sum()
        .item()
    )
    record["inherited_share_true"] = true_inherited / arrival_minutes
    record["inherited_share_hat"] = (
        propagation.inherited_minutes(test_links, est.rho, est.min_turn) / arrival_minutes
    )

    # The fair ranking.
    result = ranking.estimate(con, "sim_flights")
    record["rank_raw"] = ranking.spearman(result.order("raw"), truth.carrier_effect_ranking)
    record["rank_adjusted"] = ranking.spearman(result.order("adjusted"), truth.carrier_effect_ranking)
    effects = dict(zip(result.carriers, result.adjusted, strict=True))
    record["ranking_mae"] = float(
        np.mean([abs(effects[c] - truth.carrier_effect[c]) for c in result.carriers])
    )

    # The density test per carrier.
    lines = line.by_carrier(con, "sim_flights", q=POLICY.bh_q)
    planted = set(truth.bunching_carriers)
    record["bunching_planted"] = len(planted)
    record["bunching_detected"] = sum(1 for r in lines if r.carrier in planted and r.flagged)
    record["bunching_clean"] = sum(1 for r in lines if r.carrier not in planted)
    record["bunching_false_positive"] = sum(1 for r in lines if r.carrier not in planted and r.flagged)
    record["bunching_placebos_evaluated"] = min(r.test.placebos_evaluated for r in lines)

    # The detector on carrier days.
    scored = detect.anomalies(detect.run_daily(con, "sim_flights", "carrier"))
    days = [date.fromisoformat(d) for d in truth.meltdown_dates]
    event = detect.Event("planted meltdown", days[0], days[-1], (truth.meltdown_carrier,))
    graded = detect.grade(scored, [event], DETECTOR_THRESHOLD)
    fired = detect.alerts(scored, DETECTOR_THRESHOLD)
    in_window = fired.filter(
        (pl.col("unit") == truth.meltdown_carrier)
        & (pl.col("day") >= days[0])
        & (pl.col("day") <= days[-1] + timedelta(days=2))
    ).height
    # A carrier day is a true disruption when it is a meltdown day (or the two after) or when at least a
    # fifth of the carrier's flights left an airport under a planted storm.
    stormy = (
        sim.flights.group_by(["carrier", "flight_date"])
        .agg(pl.col("true_storm_origin").mean().alias("storm_share"))
        .filter(pl.col("storm_share") >= 0.2)
        .select(pl.col("carrier").alias("unit"), pl.col("flight_date").alias("day"))
    )
    true_alerts = fired.join(stormy, on=["unit", "day"], how="semi").height + in_window
    record["detector_recall"] = graded.recall
    record["detector_lag_days"] = graded.lags[0] if graded.lags else None
    record["detector_alert_days"] = fired.height
    record["detector_precision"] = min(true_alerts / fired.height, 1.0) if fired.height else None
    con.close()
    return record


def _key(condition: Condition, seed: int) -> str:
    return design_hash(
        {"code": CODE_VERSION, "spec": spec_for(condition, seed).model_dump(), "condition": condition.name}
    )


def _worker(args: tuple[Condition, int, str | None]) -> dict[str, object]:
    condition, seed, cache_dir = args
    if cache_dir is not None:
        path = Path(cache_dir) / f"{_key(condition, seed)}.json"
        if path.exists():
            cached: dict[str, object] = json.loads(path.read_text())
            return cached
    record = run_one(condition, seed)
    if cache_dir is not None:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, sort_keys=True))
    return record


def _init_worker() -> None:
    # One numerical thread per worker, set before any library loads its pool: two threads per
    # worker on two cores ran the Day 13 study twelve times slower.
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "POLARS_MAX_THREADS"):
        os.environ[name] = "1"


def run_study(
    seeds: int, *, workers: int, cache_dir: Path | None, only: Iterable[str] | None = None
) -> list[dict[str, object]]:
    chosen = [c for c in conditions() if only is None or c.name in set(only)]
    jobs = [(c, s, str(cache_dir) if cache_dir else None) for c in chosen for s in range(1, seeds + 1)]
    if workers <= 1:
        _init_worker()
        records = [_worker(job) for job in jobs]
    else:
        import multiprocessing

        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=workers, mp_context=context, initializer=_init_worker) as pool:
            records = list(pool.map(_worker, jobs, chunksize=1))
    return sorted(records, key=lambda r: (str(r["condition"]), int(str(r["seed"]))))
