"""The BI extracts and their specifications, and the CSV bundle with its dictionary.

Tableau: the route by month and carrier by month marts as CSV extracts (Tableau Public reads CSV; a
.hyper file needs Tableau's own library, which the free tier does not ship for Linux), with a
committed workbook specification listing the views the companion workbook shows and the calculated
fields behind them. Power BI: a model specification with the tables, the relationships and the DAX
measures, every measure generated from the metric layer's mart expression so the BI numbers are the
metric layer's numbers. The CSV bundle carries every chapter's table with a dictionary that names
every column.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import polars as pl
from turnaround_core.manifest import Manifest
from turnaround_core.statements import STATEMENT

TABLEAU_EXTRACTS = ("mart_route_month", "mart_carrier_month")
# GitHub refuses a file over 100 MB and warns past 50; the route by month extract is about 110 MB as
# one CSV over the whole window, so it is written one CSV per year in a folder of its own, which
# Tableau reads as one table through a wildcard union and Power BI through its folder connector.
BY_YEAR = ("mart_route_month",)
TABLEAU_VIEWS: tuple[dict[str, str], ...] = (
    {
        "view": "On time rate by month",
        "source": "mart_carrier_month",
        "rows": "SUM([on_time]) / SUM([flown])",
        "columns": "MAKEDATE([year], [month], 1)",
        "filters": "carrier",
        "message": "the explorer's first chart",
    },
    {
        "view": "Arrival delay by hour",
        "source": "mart_route_month joined to the hour profile on the site; here by month",
        "rows": "SUM([arr_delay_sum]) / SUM([flown])",
        "columns": "[month]",
        "filters": "carrier, origin, dest, year",
        "message": "the explorer's second chart",
    },
    {
        "view": "Padding by month",
        "source": "mart_route_month",
        "rows": "SUM([padding_sum]) / SUM([flown])",
        "columns": "MAKEDATE([year], [month], 1)",
        "filters": "carrier, route",
        "message": "the explorer's padding series",
    },
    {
        "view": "Reported cause shares",
        "source": "mart_carrier_month",
        "rows": "SUM([cause_<field>_sum]) / (sum of the five cause sums)",
        "columns": "the five cause fields, pivoted",
        "filters": "carrier, year",
        "message": "the explorer's cause chart",
    },
    {
        "view": "The fair ranking slope chart",
        "source": "exports/csv/ch5_ranking.csv",
        "rows": "[Raw rank] and [Adjusted rank] as two columns, a line per carrier",
        "columns": "Measure Names (raw, adjusted)",
        "filters": "none",
        "message": "chapter 5's chart",
    },
)


def _csv(frame: pl.DataFrame, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_csv(path)
    return frame.height


def tableau(marts: Path, out: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in TABLEAU_EXTRACTS:
        frame = pl.read_parquet(marts / f"{name}.parquet")
        sort_keys = [c for c in ("route", "carrier", "year", "month") if c in frame.columns]
        frame = frame.sort(sort_keys)
        if name in BY_YEAR:
            folder = out / name
            if folder.exists():
                for stale in folder.glob("*.csv"):
                    stale.unlink()
            (out / f"{name}.csv").unlink(missing_ok=True)
            for year in sorted(frame["year"].unique().to_list()):
                _csv(frame.filter(pl.col("year") == year), folder / f"{name}_{year}.csv")
            counts[name] = frame.height
        else:
            counts[name] = _csv(frame, out / f"{name}.csv")
    lines = [
        "# The Tableau companion workbook",
        "",
        STATEMENT,
        "",
        "The extracts are CSV files of the shipped marts, with exactly the marts' rows (a test holds them to it).",
        "The route by month extract is one CSV per year under `mart_route_month/`; open it with a wildcard union",
        "of `mart_route_month_*.csv` so the years read as one table.",
        "Open them in Tableau Public, relate them on carrier, year and month, and build the views below.",
        "The companion reads the same numbers as the site; the site is the reference.",
        "",
        "| View | Source | Rows | Columns | Filters | On the site |",
        "|---|---|---|---|---|---|",
    ]
    for v in TABLEAU_VIEWS:
        lines.append(
            f"| {v['view']} | {v['source']} | `{v['rows']}` | `{v['columns']}` | {v['filters']} | {v['message']} |"
        )
    (out / "workbook_spec.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return counts


def powerbi(metrics: Sequence[Any], out: Path, ranking_rows: int) -> int:
    """The model specification; ``metrics`` are turnaround_pipeline.metric_layer.Metric objects."""
    measures = []
    for m in metrics:
        source = "inherited_month" if m.mart_source == "mart_inherited_month" else "carrier_month"
        measures.append(
            {
                "name": m.name,
                "table": source,
                "dax": m.dax(source),
                "format": m.fmt,
                "description": m.description.strip(),
            }
        )
    measures.append(
        {
            "name": "fair_ranking_effect",
            "table": "ranking",
            "dax": "AVERAGE('ranking'[adjusted_effect])",
            "format": "smin2",
            "description": "Chapter 5's adjusted carrier effect on arrival delay, minutes against the flight weighted average carrier.",
        }
    )
    relationships = [
        {"from": "carrier_month[carrier]", "to": "carrier[code]", "cardinality": "many to one"},
        {"from": "route_month[carrier]", "to": "carrier[code]", "cardinality": "many to one"},
        {"from": "inherited_month[carrier]", "to": "carrier[code]", "cardinality": "many to one"},
    ]
    model = {
        "statement": STATEMENT,
        "tables": [
            {"name": "carrier_month", "source": "exports/tableau/mart_carrier_month.csv"},
            {
                "name": "route_month",
                "source": "exports/tableau/mart_route_month/ (a folder, one CSV per year)",
            },
            {"name": "inherited_month", "source": "exports/csv/mart_inherited_month.csv"},
            {"name": "ranking", "source": "exports/csv/ch5_ranking.csv", "rows": ranking_rows},
            {"name": "carrier", "source": "data/carriers.csv"},
        ],
        "relationships": relationships,
        "measures": measures,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "model.json").write_text(json.dumps(model, indent=1) + "\n", encoding="utf-8")
    lines = [
        "# The Power BI model",
        "",
        STATEMENT,
        "",
        "Tables, relationships and measures; build it on Windows from this file.",
        "",
    ]
    lines += ["## Measures", "", "| Measure | Table | DAX |", "|---|---|---|"]
    lines += [f"| {m['name']} | {m['table']} | `{m['dax']}` |" for m in measures]
    lines += ["", "## Relationships", ""] + [
        f"- {r['from']} to {r['to']}, {r['cardinality']}" for r in relationships
    ]
    (out / "model.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(measures)


def csv_bundle(
    manifest: Manifest, keys: Sequence[str], out: Path, extra: dict[str, pl.DataFrame]
) -> dict[str, int]:
    """Every chapter table as CSV with the manifest's columns, and a dictionary naming every column."""
    out.mkdir(parents=True, exist_ok=True)
    dictionary: list[tuple[str, str, str, str]] = []
    counts: dict[str, int] = {}
    for key in keys:
        entry = manifest.tables.get(key)
        if entry is None:
            continue
        name = key.replace(".", "_")
        with (out / f"{name}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(entry.columns)
            writer.writerows(entry.rows)
        counts[name] = len(entry.rows)
        for column, fmt in zip(entry.columns, entry.formats, strict=True):
            dictionary.append((f"{name}.csv", column, fmt, manifest.label(key)))
    for name, frame in extra.items():
        frame.write_csv(out / f"{name}.csv")
        counts[name] = frame.height
        for column, dtype in zip(frame.columns, frame.dtypes, strict=True):
            dictionary.append((f"{name}.csv", column, str(dtype), "a shipped mart, as the site reads it"))
    with (out / "dictionary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["file", "column", "format", "source"])
        writer.writerows(dictionary)
    return counts
