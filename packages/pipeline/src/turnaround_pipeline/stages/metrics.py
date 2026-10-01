"""The metric layer's reconcile over the warehouse, and the headline values of every metric.

Run after the warehouse for the data metrics and again after the chapters for the ones a model
produces (stage: chapters in metrics/metrics.yml). Any disagreement fails the stage; the counts and
each metric's overall value go into the manifest.
"""

from __future__ import annotations

import json

import duckdb
from turnaround_core.manifest import Manifest, Scribe
from turnaround_core.paths import Paths

from turnaround_pipeline.common import new_partial, save_partial
from turnaround_pipeline.metric_layer import Metric, MetricError, load, reconcile


def shipped_connection(p: Paths, metrics: list[Metric]) -> duckdb.DuckDBPyConnection:
    """The flight grain from the warehouse; every mart from the parquet actually shipped in results/marts,
    which is what the site, the workbook and the BI extracts read."""
    con = duckdb.connect()
    con.execute("set enable_progress_bar = false")
    con.execute(f"attach '{p.warehouse_db.as_posix()}' as wh (read_only)")
    for source in sorted({m.flight_source for m in metrics}):
        con.execute(f"create view {source} as select * from wh.{source}")
    for source in sorted({m.mart_source for m in metrics}):
        shipped = p.marts / f"{source}.parquet"
        if not shipped.exists():
            raise MetricError(f"{shipped} is missing: run the warehouse stage before reconciling")
        con.execute(f"create view {source} as select * from read_parquet('{shipped.as_posix()}')")
    return con


def run(p: Paths, *, stages: tuple[str, ...] = ("warehouse", "chapters")) -> Manifest:
    metrics = [m for m in load(p.root / "metrics" / "metrics.yml") if m.stage in stages]
    con = shipped_connection(p, metrics)
    report = reconcile(con, metrics)
    if not report.ok:
        lines = [
            f"{d.metric} [{d.grain}] {d.key}: flight {d.flight} against mart {d.mart}"
            for d in report.disagreements[:20]
        ]
        raise MetricError("the metric layer does not reconcile:\n" + "\n".join(lines))
    values = {}
    for metric in metrics:
        sql = f"select {metric.flight} from {metric.flight_source}"
        row = con.execute(sql).fetchone()
        values[metric.name] = None if not row or row[0] is None else float(row[0])
    con.close()
    out = p.results / "metrics"
    out.mkdir(parents=True, exist_ok=True)
    (out / "reconcile.json").write_text(
        json.dumps(
            {
                "metrics": report.metrics,
                "grains": report.grains,
                "cells": report.cells,
                "disagreements": 0,
                "values": values,
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = new_partial("metrics")
    s = Scribe(
        manifest,
        source="real:bts",
        population="every flight in the window, through the metric layer",
        origin="stages/metrics.py",
    )
    s.put("metrics.count", report.metrics, "int")
    s.put("metrics.grains", report.grains, "int")
    s.put("metrics.cells", report.cells, "int")
    s.put("metrics.disagreements", len(report.disagreements), "int")
    for metric in metrics:
        s.put(f"metric.{metric.name}", values[metric.name], metric.fmt)
    s.table(
        "metrics.definitions",
        ["Metric", "Over the flights", "Over the mart"],
        ["text", "text", "text"],
        [[m.name.replace("_", " "), m.flight, m.mart] for m in metrics],
    )
    save_partial(p, "metrics", manifest)
    return manifest
