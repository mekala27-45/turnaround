"""The recovery study over every condition and seed, summarised for the data page and the method notes."""

from __future__ import annotations

import polars as pl
from turnaround_core.frames import num
from turnaround_core.manifest import Manifest, Scribe
from turnaround_core.paths import Paths
from turnaround_evaluation.recovery import conditions, run_study

from turnaround_pipeline.common import new_partial, save_partial

SEEDS = 20


def summarise(records: pl.DataFrame) -> pl.DataFrame:
    return (
        records.group_by("condition")
        .agg(
            pl.len().alias("seeds"),
            pl.col("padding_mae").mean(),
            pl.col("padding_bias").mean(),
            (pl.col("changepoints_found").sum() / pl.col("changepoints_true").sum()).alias(
                "changepoint_recall"
            ),
            pl.col("changepoint_date_error_days").mean().alias("changepoint_date_error"),
            pl.col("changepoints_false").mean().alias("changepoints_false"),
            (pl.col("rho_hat") - pl.col("rho_true")).mean().alias("rho_bias"),
            pl.col("rho_covered").mean().alias("rho_coverage"),
            (pl.col("min_turn_hat") == pl.col("min_turn_true")).mean().alias("min_turn_exact"),
            (pl.col("inherited_share_hat") - pl.col("inherited_share_true")).mean().alias("inherited_error"),
            pl.col("rank_raw").mean(),
            pl.col("rank_adjusted").mean(),
            pl.col("ranking_mae").mean(),
            (pl.col("bunching_false_positive").sum() / pl.col("bunching_clean").sum()).alias("bunching_fpr"),
            (pl.col("bunching_detected").sum() / pl.col("bunching_planted").sum()).alias("bunching_power"),
            pl.col("detector_recall").mean(),
            pl.col("detector_precision").mean(),
            pl.col("detector_lag_days").mean().alias("detector_lag"),
        )
        .sort("condition")
    )


def run(p: Paths, *, seeds: int = SEEDS, workers: int = 2, use_cache: bool = True) -> Manifest:
    cache = p.scratch / "recovery" if use_cache else None
    records = pl.DataFrame(run_study(seeds, workers=workers, cache_dir=cache), infer_schema_length=None)
    out = p.results / "recovery"
    out.mkdir(parents=True, exist_ok=True)
    records.write_parquet(out / "records.parquet", compression="zstd")
    summary = summarise(records)
    summary.write_parquet(out / "summary.parquet", compression="zstd")

    manifest = new_partial("recovery")
    s = Scribe(
        manifest,
        source="simulated",
        population="the recovery study, every condition and seed",
        origin="stages/recovery.py",
        seeds=seeds,
    )
    s.put("recovery.seeds", seeds, "int")
    s.put("recovery.conditions", len(conditions()), "int")
    s.put("recovery.runs", records.height, "int")
    s.put("recovery.flights_per_run", int(num(records["flights"].median())), "int")
    s.put("recovery.padding_mae", num(records["padding_mae"].mean()), "min2")
    s.put("recovery.changepoint_recall", num(summary["changepoint_recall"].mean()), "pct0")
    s.put(
        "recovery.changepoint_date_error",
        num(records["changepoint_date_error_days"].mean()),
        "days1",
    )
    s.put("recovery.changepoints_false", num(records["changepoints_false"].mean()), "float2")
    for level in (0.8, 1.0):
        sub = records.filter(pl.col("rho_true") == level)
        tag = "weak" if level < 1 else "strong"
        s.put(f"recovery.rho_bias.{tag}", num((sub["rho_hat"] - sub["rho_true"]).mean()), "sfloat3")
        s.put(f"recovery.rho_coverage.{tag}", num(sub["rho_covered"].mean()), "pct0")
    s.put(
        "recovery.min_turn_exact",
        num((records["min_turn_hat"] == records["min_turn_true"]).mean()),
        "pct0",
    )
    s.put(
        "recovery.inherited_error",
        num((records["inherited_share_hat"] - records["inherited_share_true"]).abs().mean()),
        "pts1",
    )
    for strength in ("none", "moderate", "strong"):
        sub = records.filter(pl.col("condition").str.starts_with(f"confounding {strength}"))
        s.put(f"recovery.rank_raw.{strength}", num(sub["rank_raw"].mean()), "float2")
        s.put(f"recovery.rank_adjusted.{strength}", num(sub["rank_adjusted"].mean()), "float2")
    s.put(
        "recovery.bunching_fpr",
        num(records["bunching_false_positive"].sum()) / num(records["bunching_clean"].sum()),
        "pct1",
    )
    s.put(
        "recovery.bunching_power",
        num(records["bunching_detected"].sum()) / num(records["bunching_planted"].sum()),
        "pct0",
    )
    s.put("recovery.detector_recall", num(records["detector_recall"].mean()), "pct0")
    s.put("recovery.detector_precision", num(records["detector_precision"].mean()), "pct0")
    s.put("recovery.detector_lag", num(records["detector_lag_days"].mean()), "days1")

    worst = {
        "padding": summary.sort("padding_mae", descending=True)["condition"][0],
        "propagation": summary.sort("rho_coverage")["condition"][0],
        "ranking": summary.sort("rank_adjusted")["condition"][0],
        "raw_ranking": summary.sort("rank_raw")["condition"][0],
        "bunching": summary.sort("bunching_power")["condition"][0],
        "detector": summary.sort("detector_precision")["condition"][0],
    }
    for name, condition in worst.items():
        s.put(f"recovery.worst.{name}", condition, "text")
    s.table(
        "recovery.by_condition",
        [
            "Condition",
            "Padding error",
            "Changepoint date error",
            "Rho bias",
            "Rho coverage",
            "Inherited share error",
            "Raw rank correlation",
            "Adjusted rank correlation",
            "Bunching false positives",
            "Bunching power",
            "Detector precision",
        ],
        ["text", "min2", "days1", "sfloat3", "pct0", "pts1", "float2", "float2", "pct1", "pct0", "pct0"],
        [
            [
                r["condition"],
                r["padding_mae"],
                r["changepoint_date_error"],
                r["rho_bias"],
                r["rho_coverage"],
                r["inherited_error"],
                r["rank_raw"],
                r["rank_adjusted"],
                r["bunching_fpr"],
                r["bunching_power"],
                r["detector_precision"],
            ]
            for r in summary.iter_rows(named=True)
        ],
    )
    save_partial(p, "recovery", manifest)
    return manifest
