"""Stage one: the monthly files into typed, flagged parquet; airports, aircraft and weather beside them.

Every month present under data/external/bts is read whole. A month already ingested from a file
with the same SHA-256 is skipped; a month whose file changed is ingested again and compared row by
row with the earlier version, the changes counted under the revision rule. The ledger of files,
their checksums and row counts is committed as data/ingest_ledger.csv.
"""

from __future__ import annotations

import csv
import json
import shutil
from dataclasses import asdict
from datetime import date
from pathlib import Path

import polars as pl
from turnaround_contracts import airports as airport_contract
from turnaround_contracts import faa, weather
from turnaround_contracts.bts import FILE_PATTERN, RULES, MonthReport, ingest_month, mark_revisions, month_of
from turnaround_core.log import get_logger
from turnaround_core.manifest import Manifest, Scribe
from turnaround_core.paths import Paths

from turnaround_pipeline.common import connect, flights_glob, new_partial, save_partial

log = get_logger("turnaround.data")
LEDGER = Path("data/ingest_ledger.csv")
MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def month_label(year: int, month: int) -> str:
    return f"{MONTH_NAMES[month - 1]} {year}"


def _read_ledger(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["file"]: row for row in csv.DictReader(handle)}


def _write_ledger(path: Path, reports: list[MonthReport]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["file", "year", "month", "rows", "bytes", "sha256", "layout_matches_readme"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for report in sorted(reports, key=lambda r: (r.year, r.month)):
            row = asdict(report)
            row["layout_matches_readme"] = int(report.layout_matches_readme)
            writer.writerow({k: row[k] for k in fields})


def ingest_flights(p: Paths) -> list[MonthReport]:
    raw = sorted(p.external_bts.glob("*.zip"), key=lambda z: month_of(z))
    raw = [z for z in raw if FILE_PATTERN.search(z.name)]
    if not raw:
        raise FileNotFoundError(
            f"no monthly files under {p.external_bts}; run deploy/fetch-data.ps1 flights on a machine that "
            "can reach transtats.bts.gov and place the zips there"
        )
    ledger = _read_ledger(p.root / LEDGER)
    con = connect(p)
    reports: list[MonthReport] = []
    for zip_path in raw:
        year, month = month_of(zip_path)
        out = p.flights / f"flights_{year:04d}_{month:02d}.parquet"
        known = ledger.get(zip_path.name)
        from turnaround_core.hashing import file_sha256

        digest = file_sha256(zip_path)
        if known and out.exists() and known["sha256"] == digest:
            reports.append(
                MonthReport(
                    file=known["file"],
                    year=int(known["year"]),
                    month=int(known["month"]),
                    rows=int(known["rows"]),
                    sha256=known["sha256"],
                    bytes=int(known["bytes"]),
                    layout_matches_readme=known["layout_matches_readme"] == "1",
                )
            )
            continue
        if out.exists():
            # A changed file for a month already ingested: ingest it beside the old one and count revisions.
            staging = p.scratch / "revision"
            report = ingest_month(zip_path, staging, con=con)
            revised = mark_revisions(out, staging / out.name)
            shutil.move(str(staging / out.name), out)
            log.info("month revised", file=zip_path.name, revised_rows=revised)
        else:
            report = ingest_month(zip_path, p.flights, con=con)
        log.info("month ingested", file=zip_path.name, rows=report.rows)
        reports.append(report)
    con.close()
    _write_ledger(p.root / LEDGER, reports)
    return reports


def build_airports(p: Paths) -> tuple[pl.DataFrame, list[str]]:
    con = connect(p)
    codes = [
        r[0]
        for r in con.execute(
            f"select distinct code from (select origin as code from read_parquet('{flights_glob(p)}') "
            f"union select dest from read_parquet('{flights_glob(p)}')) order by code"
        ).fetchall()
    ]
    con.close()
    source = p.external / "ourairports" / "airports.csv"
    if not source.exists():
        raise FileNotFoundError(f"OurAirports airports.csv is not at {source}")
    found, missing = airport_contract.locate(codes, airport_contract.load_ourairports(source))
    frame = airport_contract.airports_frame(found)
    frame.write_csv(p.data / "airports.csv")
    return frame, missing


def build_offsets(p: Paths, airports: pl.DataFrame, first: date, last: date) -> Path:
    out = p.scratch / "tz_offsets.parquet"
    airport_contract.offsets_frame(airports["tz"].unique().to_list(), first, last).write_parquet(out)
    return out


def build_aircraft(p: Paths) -> pl.DataFrame:
    zips = sorted(p.external_faa.glob("*.zip"))
    if not zips:
        raise FileNotFoundError(f"no registry zip under {p.external_faa}")
    con = connect(p)
    tails = con.execute(
        f"""
        select tail_number, min(flight_date) as first_seen, max(flight_date) as last_seen, count(*) as flights
        from read_parquet('{flights_glob(p)}')
        where not q_tail_missing and not q_tail_format
        group by 1 order by 1
        """
    ).pl()
    con.close()
    frames = [faa.read_registry(z) for z in zips]
    aircraft = pl.concat([f[0] for f in frames], how="vertical_relaxed")
    references = [f[1] for f in frames if f[1] is not None]
    matched = faa.match_tails(tails, aircraft)
    if references:
        reference = pl.concat(references, how="vertical_relaxed").unique("mfr_mdl_code", keep="first")
        matched = matched.join(
            reference.select("mfr_mdl_code", "manufacturer", "model", "seats"), on="mfr_mdl_code", how="left"
        )
    p.aircraft.mkdir(parents=True, exist_ok=True)
    matched.write_parquet(p.aircraft / "aircraft.parquet", compression="zstd")
    return matched


def build_weather(p: Paths) -> pl.DataFrame:
    frame = weather.build_hourly(p.external_weather)
    p.weather.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(p.weather / "hourly.parquet", compression="zstd")
    (p.weather / "ATTRIBUTION.md").write_text(
        "# Weather attribution\n\n"
        "Hourly weather at the FAA Core 30 airports from the Open-Meteo historical weather API,\n"
        "https://open-meteo.com/, pulled once per airport and year in UTC.\n\n"
        "Weather data by Open-Meteo.com, licensed under CC BY 4.0\n"
        "(https://creativecommons.org/licenses/by/4.0/). The values are ERA5 based reanalysis at the\n"
        "airport's coordinates, not the airport's own observations.\n",
        encoding="utf-8",
    )
    return frame


def latest_check(p: Paths, last: tuple[int, int]) -> tuple[str, bool]:
    """When the fetch ran, and whether it asked BTS for the month after the last one and got nothing.

    deploy/fetch-data.ps1 writes fetch-status-flights.json; a copy beside the zips as
    fetch-status.json is the evidence that the window ends at the latest published month.
    """
    status_file = p.external_bts / "fetch-status.json"
    if not status_file.exists():
        return "not recorded", False
    status = json.loads(status_file.read_text(encoding="utf-8-sig"))
    following = (last[0] + 1, 1) if last[1] == 12 else (last[0], last[1] + 1)
    asked = f"{following[0]}_{following[1]}" in (status.get("bts_missing") or [])
    return str(status.get("fetched_at", ""))[:10] or "not recorded", asked


def tails_restored(p: Paths) -> tuple[int, str]:
    """Rows whose tail number had its leading N restored at ingest, and the carriers that sent them."""
    con = connect(p)
    row = con.execute(
        f"""
        select count(*), coalesce(string_agg(distinct carrier, ', ' order by carrier), '')
        from read_parquet('{flights_glob(p)}')
        where tail_reported is distinct from tail_number
        """
    ).fetchone()
    con.close()
    assert row is not None
    return int(row[0]), str(row[1])


def quarantine_report(p: Paths) -> pl.DataFrame:
    con = connect(p)
    sums = ", ".join(f"sum(q_{r.name}::int) as {r.name}" for r in RULES)
    frame = con.execute(
        f"""
        select carrier, year, month, count(*) as rows, {sums}
        from read_parquet('{flights_glob(p)}')
        group by all order by carrier, year, month
        """
    ).pl()
    con.close()
    out = p.results / "quarantine"
    out.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(out / "by_carrier_month.parquet", compression="zstd")
    return frame


def run(p: Paths) -> Manifest:
    reports = ingest_flights(p)
    first = min((r.year, r.month) for r in reports)
    last = max((r.year, r.month) for r in reports)
    airports, missing_airports = build_airports(p)
    build_offsets(
        p, airports, date(first[0], first[1], 1), date(last[0] + (last[1] == 12), last[1] % 12 + 1, 1)
    )
    aircraft = build_aircraft(p)
    hourly = build_weather(p)
    quarantine = quarantine_report(p)

    manifest = new_partial("data")
    bts = Scribe(
        manifest,
        source="real:bts",
        population="every row of every monthly file in the window",
        origin="stages/data.py",
    )
    rows = sum(r.rows for r in reports)
    bts.put("data.months", len(reports), "int")
    bts.put("data.first_month", month_label(*first), "text")
    bts.put("data.last_month", month_label(*last), "text")
    bts.put("data.rows", rows, "int")
    bts.put("data.rows_millions", rows, "millions1")
    bts.put("data.files_bytes", sum(r.bytes for r in reports), "int")
    bts.put("data.layout_matches", sum(r.layout_matches_readme for r in reports), "int")
    present = {(r.year, r.month) for r in reports}
    expected: list[tuple[int, int]] = []
    y, mo = first
    while (y, mo) <= last:
        expected.append((y, mo))
        y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
    gaps = [f"{a}-{b:02d}" for a, b in expected if (a, b) not in present]
    bts.put("data.months_expected", len(expected), "int")
    bts.put("data.gaps", ", ".join(gaps) if gaps else "none", "text")
    # "The latest month BTS has published" rests on the fetch having asked for the month after it.
    fetched_on, next_unpublished = latest_check(p, last)
    following = (last[0] + 1, 1) if last[1] == 12 else (last[0], last[1] + 1)
    bts.put("data.fetched_on", fetched_on, "text")
    bts.put("data.next_month", month_label(*following), "text")
    bts.put("data.next_month_unpublished", int(next_unpublished), "int")
    bts.table(
        "data.files",
        ["File", "Rows", "Bytes", "SHA-256 (first 16)"],
        ["text", "int", "int", "text"],
        [[r.file, r.rows, r.bytes, r.sha256[:16]] for r in sorted(reports, key=lambda r: (r.year, r.month))],
    )
    totals = quarantine.select(pl.exclude(["carrier", "year", "month"])).sum()
    flagged_any = 0
    rule_rows: list[list[str | int | float | None]] = []
    for rule in RULES:
        n = int(totals[rule.name][0])
        bts.put(f"quarantine.{rule.name}.rows", n, "int")
        bts.put(f"quarantine.{rule.name}.share", n / rows, "pct2")
        rule_rows.append([rule.name.replace("_", " "), rule.description, n, n / rows, rule.excludes_from])
        flagged_any += n
    bts.table(
        "quarantine.by_rule",
        ["Rule", "What it catches", "Rows", "Share", "Excluded from"],
        ["text", "text", "int", "pct2", "text"],
        rule_rows,
    )
    by_year = (
        quarantine.group_by("year")
        .agg(pl.col("rows").sum(), pl.col("carrier").n_unique().alias("carriers"))
        .sort("year")
    )
    bts.table(
        "data.by_year",
        ["Year", "Flights", "Carriers"],
        ["text", "int", "int"],
        [[str(y), int(n), int(c)] for y, n, c in by_year.iter_rows()],
    )
    bts.put("data.carriers", int(quarantine["carrier"].n_unique()), "int")
    restored, restored_carriers = tails_restored(p)
    bts.put("data.tails_restored", restored, "int")
    bts.put("data.tails_restored_share", restored / rows, "pct2")
    bts.put("data.tails_restored_carriers", restored_carriers or "none", "text")

    ap = Scribe(
        manifest,
        source="real:ourairports",
        population="every airport code in the flights",
        origin="stages/data.py",
    )
    ap.put("airports.count", airports.height, "int")
    ap.put("airports.missing", len(missing_airports), "int")
    ap.put("airports.missing_codes", ", ".join(missing_airports) or "none", "text")
    ap.put("airports.zones", int(airports["tz"].n_unique()), "int")

    reg = Scribe(
        manifest,
        source="real:bts+faa",
        population="tail numbers in the flights that pass the format rule",
        origin="stages/data.py",
    )
    total_tails = aircraft.height
    by_file = {k: int(v) for k, v in aircraft.group_by("registry_file").len().iter_rows()}
    flights_total = int(aircraft["flights"].sum())
    flights_matched = int(aircraft.filter(pl.col("registry_file") != "unmatched")["flights"].sum())
    reg.put("registry.tails", total_tails, "int")
    reg.put("registry.tails_master", by_file.get("master", 0), "int")
    reg.put("registry.tails_dereg", by_file.get("dereg", 0), "int")
    reg.put("registry.tails_unmatched", by_file.get("unmatched", 0), "int")
    reg.put("registry.tail_join_rate", (total_tails - by_file.get("unmatched", 0)) / total_tails, "pct1")
    reg.put("registry.flight_join_rate", flights_matched / flights_total, "pct1")
    reg.put("registry.has_reference", int("model" in aircraft.columns), "int")

    wx = Scribe(
        manifest,
        source="real:open_meteo",
        population="hourly weather at the FAA Core 30",
        origin="stages/data.py",
    )
    wx.put("weather.rows", hourly.height, "int")
    wx.put("weather.airports", int(hourly["airport"].n_unique()), "int")
    wx.put("weather.first_hour", str(hourly["hour_utc"].min())[:16], "text")
    wx.put("weather.last_hour", str(hourly["hour_utc"].max())[:16], "text")
    wx.put("weather.null_temperature", int(hourly["temperature_2m"].null_count()), "int")
    save_partial(p, "data", manifest)
    (p.results / "data").mkdir(parents=True, exist_ok=True)
    (p.results / "data" / "missing_airports.json").write_text(json.dumps(missing_airports, indent=1) + "\n")
    return manifest
