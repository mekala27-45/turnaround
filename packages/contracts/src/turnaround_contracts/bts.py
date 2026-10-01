"""The BTS Reporting Carrier On-Time Performance monthly files: the contract, the reader, the quarantine.

One zip per month, ``On_Time_Reporting_Carrier_On_Time_Performance_1987_present_<year>_<month>.zip``,
holding one CSV of 109 fields (and a trailing comma) and ``readme.html``, whose record layout lists
the fields in order. The contract here is that layout: the fields this project reads, what they are
called downstream, their types, and the rules a row must pass to enter the analysis. Nothing is
deleted. A row that breaks a rule keeps its place in the derived month file with the rule's flag
set, the quarantine report counts it by carrier and month, and each analysis states which flags it
excludes (docs/definitions.md).

Times in the files are local clock times as HHMM text at the airport they happened at; delays are
whole minutes. The derived files carry the local fields as minutes after midnight and leave the
conversion to UTC to the warehouse, which knows each airport's time zone.
"""

from __future__ import annotations

import html
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import duckdb

FILE_PATTERN = re.compile(
    r"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_(\d{4})_(\d{1,2})\.zip$"
)


@dataclass(frozen=True)
class Field:
    raw: str
    name: str
    kind: str  # text, int, minutes, clock, flag, date


# The fields read, in the order the record layout lists them. Everything else in the file
# (the city market ids, the state FIPS codes, the second to fifth diversion airports) is left out.
FIELDS: tuple[Field, ...] = (
    Field("Year", "year", "int"),
    Field("Month", "month", "int"),
    Field("DayofMonth", "day_of_month", "int"),
    Field("DayOfWeek", "day_of_week", "int"),
    Field("FlightDate", "flight_date", "date"),
    Field("Reporting_Airline", "carrier", "text"),
    Field("Tail_Number", "tail_number", "text"),
    Field("Flight_Number_Reporting_Airline", "flight_number", "int"),
    Field("OriginAirportID", "origin_airport_id", "int"),
    Field("Origin", "origin", "text"),
    Field("OriginCityName", "origin_city", "text"),
    Field("OriginState", "origin_state", "text"),
    Field("DestAirportID", "dest_airport_id", "int"),
    Field("Dest", "dest", "text"),
    Field("DestCityName", "dest_city", "text"),
    Field("DestState", "dest_state", "text"),
    Field("CRSDepTime", "crs_dep_local", "clock"),
    Field("DepTime", "dep_local", "clock"),
    Field("DepDelay", "dep_delay", "minutes"),
    Field("TaxiOut", "taxi_out", "minutes"),
    Field("WheelsOff", "wheels_off_local", "clock"),
    Field("WheelsOn", "wheels_on_local", "clock"),
    Field("TaxiIn", "taxi_in", "minutes"),
    Field("CRSArrTime", "crs_arr_local", "clock"),
    Field("ArrTime", "arr_local", "clock"),
    Field("ArrDelay", "arr_delay", "minutes"),
    Field("Cancelled", "cancelled", "flag"),
    Field("CancellationCode", "cancellation_code", "text"),
    Field("Diverted", "diverted", "flag"),
    Field("CRSElapsedTime", "crs_elapsed", "minutes"),
    Field("ActualElapsedTime", "actual_elapsed", "minutes"),
    Field("AirTime", "air_time", "minutes"),
    Field("Distance", "distance", "minutes"),
    Field("CarrierDelay", "cause_carrier", "minutes"),
    Field("WeatherDelay", "cause_weather", "minutes"),
    Field("NASDelay", "cause_nas", "minutes"),
    Field("SecurityDelay", "cause_security", "minutes"),
    Field("LateAircraftDelay", "cause_late_aircraft", "minutes"),
    Field("FirstDepTime", "first_dep_local", "clock"),
    Field("TotalAddGTime", "total_add_gtime", "minutes"),
    Field("LongestAddGTime", "longest_add_gtime", "minutes"),
    Field("DivAirportLandings", "div_airport_landings", "int"),
    Field("DivReachedDest", "div_reached_dest", "flag"),
    Field("DivActualElapsedTime", "div_actual_elapsed", "minutes"),
    Field("DivArrDelay", "div_arr_delay", "minutes"),
    Field("Div1Airport", "div1_airport", "text"),
)
CAUSE_COLUMNS = ("cause_carrier", "cause_weather", "cause_nas", "cause_security", "cause_late_aircraft")

# An FAA registration: N, a first digit 1 to 9, then up to four more characters, with at most two
# trailing letters, never I or O. N1 to N99999, N1A to N9999Z, N1AA to N999ZZ.
N_NUMBER = r"^N[1-9]([0-9]{0,4}|[0-9]{0,3}[A-HJ-NP-Z]|[0-9]{0,2}[A-HJ-NP-Z]{2})$"


@dataclass(frozen=True)
class Rule:
    name: str
    description: str
    excludes_from: str


# The quarantine rules, in the order the report lists them. A rule's flag is a boolean column
# q_<name> on every derived row. excludes_from names the analyses that drop a flagged row.
RULES: tuple[Rule, ...] = (
    Rule(
        "duplicate_key",
        "a second row with the same carrier, date, flight number, origin, destination and scheduled departure",
        "everything",
    ),
    Rule(
        "actual_without_scheduled",
        "an actual departure, arrival or elapsed time with no scheduled time to measure it against",
        "everything",
    ),
    Rule(
        "negative_time",
        "a negative taxi time, or an air time or elapsed time at or below zero",
        "everything",
    ),
    Rule(
        "elapsed_mismatch",
        "actual elapsed time that differs from taxi out plus air time plus taxi in by more than the tolerance",
        "everything",
    ),
    Rule(
        "cause_mismatch",
        "reported delay causes that do not sum to the arrival delay within the tolerance",
        "the cause shares in chapter 6",
    ),
    Rule("tail_missing", "no tail number on the row", "the rotations of chapter 4"),
    Rule(
        "tail_format",
        "a tail number that is not a valid FAA registration (N, a digit 1 to 9, at most two trailing letters)",
        "the rotations of chapter 4 and the registry join",
    ),
    Rule(
        "revision",
        "a row that a later download of the same month changed (the later kept, the change counted)",
        "nothing; the earlier version is the one that is replaced",
    ),
)
EXCLUDE_EVERYTHING = tuple(r.name for r in RULES if r.excludes_from == "everything")


class ContractError(ValueError):
    pass


def month_of(path: Path) -> tuple[int, int]:
    match = FILE_PATTERN.search(path.name)
    if not match:
        raise ContractError(f"{path.name} is not a monthly on time file")
    return int(match[1]), int(match[2])


def readme_fields(readme_html: str) -> list[str]:
    """The field names the readme's record layout lists, in order: the first cell of each two cell row."""
    start = readme_html.upper().find("RECORD LAYOUT")
    if start < 0:
        raise ContractError("the readme has no record layout")
    rows = re.findall(r"<TR>\s*<TD>(.*?)</TD>\s*<TD>", readme_html[start:], flags=re.I | re.S)
    names = [html.unescape(re.sub(r"<[^>]+>", "", cell)).strip() for cell in rows]
    return [n for n in names if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", n)]


def _typed(field: Field) -> str:
    col = f'"{field.raw}"'
    blank = f"nullif(trim({col}), '')"
    if field.kind == "text":
        return f"{blank} as {field.name}"
    if field.kind == "int":
        return f"try_cast({blank} as integer) as {field.name}"
    if field.kind == "date":
        return f"try_cast({blank} as date) as {field.name}"
    if field.kind == "flag":
        return f"(try_cast({blank} as double) > 0.5) as {field.name}"
    if field.kind == "minutes":
        return f"cast(round(try_cast({blank} as double)) as integer) as {field.name}"
    if field.kind == "clock":
        # HHMM as text, 2400 meaning midnight at the end of the day; minutes after midnight.
        value = f"try_cast({blank} as integer)"
        return f"(({value} // 100) * 60 + ({value} % 100)) as {field.name}"
    raise ContractError(f"unknown field kind {field.kind}")


def _parse_failures(field: Field) -> str:
    col = f'"{field.raw}"'
    blank = f"nullif(trim({col}), '')"
    if field.kind == "text":
        return "0"
    target = {"int": "integer", "date": "date", "flag": "double", "minutes": "double", "clock": "integer"}[
        field.kind
    ]
    return f"count(*) filter (where {blank} is not null and try_cast({blank} as {target}) is null)"


def _rules_sql(tolerance_elapsed: int, tolerance_cause: int) -> str:
    causes = " + ".join(f"coalesce({c}, 0)" for c in CAUSE_COLUMNS)
    any_cause = " or ".join(f"{c} is not null" for c in CAUSE_COLUMNS)
    return f"""
        row_number() over (
            partition by carrier, flight_date, flight_number, origin, dest, crs_dep_local order by source_row
        ) > 1 as q_duplicate_key,
        coalesce((dep_local is not null and crs_dep_local is null)
            or (arr_local is not null and crs_arr_local is null)
            or (actual_elapsed is not null and crs_elapsed is null), false) as q_actual_without_scheduled,
        coalesce(taxi_out < 0 or taxi_in < 0 or air_time <= 0 or actual_elapsed <= 0, false) as q_negative_time,
        coalesce(not cancelled and not diverted
            and abs(actual_elapsed - (taxi_out + air_time + taxi_in)) > {tolerance_elapsed}, false)
            as q_elapsed_mismatch,
        coalesce(({any_cause}) and abs(({causes}) - arr_delay) > {tolerance_cause}, false) as q_cause_mismatch,
        tail_number is null as q_tail_missing,
        coalesce(tail_number is not null and not regexp_full_match(tail_number, '{N_NUMBER}'), false)
            as q_tail_format,
        false as q_revision
    """


@dataclass(frozen=True)
class MonthReport:
    file: str
    year: int
    month: int
    rows: int
    sha256: str
    bytes: int
    layout_matches_readme: bool


def ingest_month(
    zip_path: Path,
    out_dir: Path,
    *,
    tolerance_elapsed: int = 5,
    tolerance_cause: int = 1,
    con: duckdb.DuckDBPyConnection | None = None,
) -> MonthReport:
    """Read one monthly zip, type it against the contract, flag it by the rules and write parquet."""
    from turnaround_core.hashing import file_sha256

    year, month = month_of(zip_path)
    connection = con or duckdb.connect()
    connection.execute("set enable_progress_bar = false")
    workdir = Path(tempfile.mkdtemp(prefix="bts_"))
    try:
        with zipfile.ZipFile(zip_path) as archive:
            members = archive.namelist()
            csv_names = [m for m in members if m.lower().endswith(".csv")]
            readme_names = [m for m in members if m.lower().endswith("readme.html")]
            if len(csv_names) != 1:
                raise ContractError(f"{zip_path.name} holds {len(csv_names)} CSV files, expected one")
            archive.extract(csv_names[0], workdir)
            readme = archive.read(readme_names[0]).decode("latin-1") if readme_names else ""
        csv_path = workdir / csv_names[0]
        header = csv_path.open(encoding="latin-1").readline().strip().rstrip(",")
        columns = [c.strip('"') for c in header.split(",")]
        missing = [f.raw for f in FIELDS if f.raw not in columns]
        if missing:
            raise ContractError(f"{zip_path.name} lacks fields {missing}")
        layout = readme_fields(readme) if readme else []
        layout_matches = bool(layout) and layout[: len(columns)] == columns
        source = f"read_csv('{csv_path.as_posix()}', header = true, all_varchar = true, quote = '\"', escape = '\"')"
        failures = connection.execute(
            "select " + ", ".join(f"{_parse_failures(f)} as {f.name}" for f in FIELDS) + f" from {source}"
        ).fetchone()
        assert failures is not None
        bad = {f.name: int(n) for f, n in zip(FIELDS, failures, strict=True) if int(n) > 0}
        if bad:
            raise ContractError(f"{zip_path.name}: values that do not parse as their type: {bad}")
        typed = ",\n            ".join(_typed(f) for f in FIELDS)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"flights_{year:04d}_{month:02d}.parquet"
        tmp = out.with_suffix(".parquet.tmp")
        # Staged through a temporary table: one statement with both windows and the sort was an
        # order of magnitude slower than the three steps on their own.
        connection.execute(
            f"""
            create or replace temp table _typed as
            select
                cast({year * 100 + month} as bigint) * 10000000 + source_row as flight_id,
                '{zip_path.name}' as source_file,
                cast(source_row as integer) as source_row,
            {typed}
            from (select *, row_number() over () as source_row from {source})
            """
        )
        connection.execute(
            f"""
            copy (
                select *, {_rules_sql(tolerance_elapsed, tolerance_cause)}
                from _typed
                order by flight_id
            ) to '{tmp.as_posix()}' (format parquet, compression zstd, row_group_size 122880)
            """
        )
        connection.execute("drop table _typed")
        rows, years, months = connection.execute(
            f"select count(*), list(distinct year), list(distinct month) from read_parquet('{tmp.as_posix()}')"
        ).fetchone() or (0, [], [])
        if sorted(years) != [year] or sorted(months) != [month]:
            raise ContractError(f"{zip_path.name} holds rows for years {years} and months {months}")
        line_count = sum(1 for _ in csv_path.open(encoding="latin-1")) - 1
        if int(rows) != line_count:
            raise ContractError(f"{zip_path.name}: {rows} rows parsed from {line_count} lines")
        tmp.replace(out)
        return MonthReport(
            file=zip_path.name,
            year=year,
            month=month,
            rows=int(rows),
            sha256=file_sha256(zip_path),
            bytes=zip_path.stat().st_size,
            layout_matches_readme=layout_matches,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        if con is None:
            connection.close()


def mark_revisions(previous: Path, current: Path) -> int:
    """Compare a month's earlier derived file with a new one; flag and count the rows that changed.

    Rows are matched on the flight key. A row present in both whose reported fields differ is a
    revision: the new file keeps it with q_revision set. Returns the number of revised rows.
    """
    key = "carrier, flight_date, flight_number, origin, dest, crs_dep_local"
    compared = [f.name for f in FIELDS]
    differs = " or ".join(f"p.{c} is distinct from c.{c}" for c in compared)
    con = duckdb.connect()
    try:
        tmp = current.with_suffix(".parquet.rev")
        con.execute(
            f"""
            copy (
                select c.* replace (
                    coalesce(c.q_revision, false) or coalesce(r.changed, false) as q_revision
                )
                from read_parquet('{current.as_posix()}') c
                left join (
                    select distinct c.flight_id, true as changed
                    from read_parquet('{current.as_posix()}') c
                    join read_parquet('{previous.as_posix()}') p using ({key})
                    where not c.q_duplicate_key and not p.q_duplicate_key and ({differs})
                ) r using (flight_id)
                order by flight_id
            ) to '{tmp.as_posix()}' (format parquet, compression zstd, row_group_size 122880)
            """
        )
        revised = con.execute(
            f"select count(*) from read_parquet('{tmp.as_posix()}') where q_revision"
        ).fetchone()
        tmp.replace(current)
        return int(revised[0]) if revised else 0
    finally:
        con.close()
