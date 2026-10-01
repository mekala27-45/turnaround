"""Stage: the workbook, the BI extracts and specifications, and the CSV bundle, under exports/.

Reads the chapter tables from the chapters stage's manifest and the metric values from the metrics
stage's, so it runs after both and before the manifest is assembled; its own counts go into the
exports partial manifest, which the documents quote.
"""

from __future__ import annotations

import polars as pl
from turnaround_core.manifest import Manifest, Scribe
from turnaround_core.paths import Paths
from turnaround_exports import bi, workbook

from turnaround_pipeline.common import new_partial, save_partial
from turnaround_pipeline.metric_layer import load

CHAPTER_TABLES: tuple[tuple[str, str], ...] = (
    ("ch1.by_year", "Ch1 on time by year"),
    ("ch2.changepoints", "Ch2 padding steps"),
    ("ch2.by_carrier", "Ch2 padding by carrier"),
    ("ch3.by_carrier", "Ch3 the line by carrier"),
    ("ch4.buffer_curve", "Ch4 buffer curve"),
    ("ch5.ranking", "Ch5 fair ranking"),
    ("ch6.reported_by_year", "Ch6 reported causes"),
    ("ch6.nas_by_airport", "Ch6 air traffic by airport"),
    ("ch7.events", "Ch7 known events"),
    ("ch7.recovery_by_carrier", "Ch7 recovery by carrier"),
    ("ch8.by_hour", "Ch8 by hour"),
    ("ch8.by_dow", "Ch8 by day"),
    ("ch8.by_month", "Ch8 by month"),
    ("ch8.by_position", "Ch8 leg of the day"),
    ("ch8.hubs", "Ch8 connection buffers"),
    ("ch8.trade_airports", "Ch8 buffer trade"),
    ("recovery.by_condition", "Recovery study"),
    ("metrics.definitions", "Metric definitions"),
)


def _partials(p: Paths) -> Manifest:
    merged = Manifest(as_of="", seed=0)
    for stage in ("recovery", "metrics", "chapters"):
        path = p.results / stage / "manifest.json"
        if path.exists():
            loaded = Manifest.load(path)
            merged.as_of, merged.seed = loaded.as_of, loaded.seed
            merged.merge(loaded)
    return merged


def run(p: Paths) -> Manifest:
    source = _partials(p)
    out = p.root / "exports"
    carrier_month = pl.read_parquet(p.marts / "mart_carrier_month.parquet")
    inherited_month = pl.read_parquet(p.marts / "mart_inherited_month.parquet")
    year_text = str(source.values["metrics.summary_year"].value)
    default_year = int(year_text) if year_text.isdigit() else int(carrier_month["year"].max())  # type: ignore[arg-type]
    built = workbook.build(
        out / "workbook.xlsx",
        source,
        carrier_month,
        inherited_month,
        default_year=default_year,
        chapter_tables=CHAPTER_TABLES,
    )
    extracts = bi.tableau(p.marts, out / "tableau")
    metrics = load(p.root / "metrics" / "metrics.yml")
    measures = bi.powerbi(metrics, out / "powerbi", len(source.tables["ch5.ranking"].rows))
    bundle = bi.csv_bundle(
        source,
        [k for k, _ in CHAPTER_TABLES],
        out / "csv",
        {"mart_inherited_month": inherited_month.sort(["carrier", "year", "month"])},
    )
    manifest = new_partial("exports")
    s = Scribe(
        manifest,
        source="mixed",
        population="the exports, from the marts and the chapter tables",
        origin="stages/exports.py",
    )
    s.put("exports.workbook.sheets", built["sheets"], "int")
    s.put("exports.workbook.chapter_sheets", built["chapter_sheets"], "int")
    s.put("exports.workbook.formulas", built["formulas"], "int")
    s.put("exports.workbook.named_ranges", built["named_ranges"], "int")
    s.put("exports.workbook.default_year", str(built["default_year"]), "text")
    for name, rows in extracts.items():
        s.put(f"exports.tableau.{name}.rows", rows, "int")
    s.put("exports.powerbi.measures", measures, "int")
    s.put("exports.csv.files", len(bundle), "int")
    s.put("exports.csv.rows", sum(bundle.values()), "int")
    save_partial(p, "exports", manifest)
    return manifest
