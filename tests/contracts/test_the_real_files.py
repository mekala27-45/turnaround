"""The real public files, where this machine has them: the newest monthly file reads against the
contract, the derived months are contiguous and match the ingest ledger, and the weather covers the
Core 30 hour by hour with its attribution. Each test names the dependency it skips for."""

from __future__ import annotations

import csv
from pathlib import Path

import polars as pl
import pytest
from turnaround_contracts.bts import FIELDS, ingest_month, month_of
from turnaround_contracts.faa import read_registry
from turnaround_core.config import CORE30

from tests._deps import need

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL = ROOT / "data" / "external"
FLIGHTS = ROOT / "data" / "flights"
WEATHER = ROOT / "data" / "weather"


@pytest.mark.external
def test_the_newest_monthly_file_reads_against_the_contract(tmp_path: Path) -> None:
    zips = sorted((EXTERNAL / "bts").glob("*.zip"), key=month_of) if (EXTERNAL / "bts").exists() else []
    need("external", bool(zips), "no monthly files under data/external/bts")
    report = ingest_month(zips[-1], tmp_path)
    assert report.rows > 100_000 and report.layout_matches_readme
    written = pl.read_parquet(next(tmp_path.glob("*.parquet")))
    assert written.height == report.rows
    assert {f.name for f in FIELDS} <= set(written.columns)


@pytest.mark.external
def test_the_registry_reads_the_aircraft_and_never_the_registrant() -> None:
    zipped = EXTERNAL / "faa" / "ReleasableAircraft.zip"
    need("external", zipped.exists(), "the FAA registry zip is not under data/external/faa")
    aircraft, _ = read_registry(zipped)
    assert aircraft.height > 100_000
    assert not {c for c in aircraft.columns if "name" in c.lower() or "street" in c.lower()}


@pytest.mark.derived
def test_the_derived_months_are_contiguous_and_match_the_ledger() -> None:
    files = sorted(FLIGHTS.glob("flights_*.parquet")) if FLIGHTS.exists() else []
    need("derived", bool(files), "no derived flight parquet under data/flights (run `make data`)")
    months = [(int(f.stem.split("_")[1]), int(f.stem.split("_")[2])) for f in files]
    first, last = months[0], months[-1]
    expected = [(y, m) for y in range(first[0], last[0] + 1) for m in range(1, 13) if first <= (y, m) <= last]
    assert months == expected, "a month is missing from data/flights"
    with (ROOT / "data" / "ingest_ledger.csv").open(encoding="utf-8") as handle:
        ledger = {(int(r["year"]), int(r["month"])): int(r["rows"]) for r in csv.DictReader(handle)}
    for path, month in zip(files, months, strict=True):
        assert pl.scan_parquet(path).select(pl.len()).collect().item() == ledger[month], path.name


@pytest.mark.weather
def test_the_weather_covers_the_core_30_every_hour_with_attribution() -> None:
    hourly = WEATHER / "hourly.parquet"
    attribution = WEATHER / "ATTRIBUTION.md"
    # The data stage writes the two together; a parquet without its attribution was not written by it.
    need(
        "weather",
        hourly.exists() and attribution.exists(),
        "data/weather has no hourly.parquet with its ATTRIBUTION.md (run `make data` with the pulls in place)",
    )
    frame = pl.read_parquet(hourly)
    assert set(frame["airport"].unique().to_list()) == set(CORE30)
    per_airport = frame.group_by("airport").agg(
        pl.len().alias("hours"),
        pl.col("hour_utc").min().alias("first"),
        pl.col("hour_utc").max().alias("last"),
    )
    for row in per_airport.iter_rows(named=True):
        expected = int((row["last"] - row["first"]).total_seconds() // 3600) + 1
        assert row["hours"] == expected, f"{row['airport']} has gaps or repeats"
    assert "CC BY 4.0" in attribution.read_text(encoding="utf-8")
