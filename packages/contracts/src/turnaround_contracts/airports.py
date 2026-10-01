"""Airports: OurAirports for names and coordinates, a time zone for each from its coordinates.

The on time files give every time as a local clock time at the airport where it happened. The
warehouse converts them to UTC with the airport's IANA time zone, found here from OurAirports'
coordinates with timezonefinder (no fifth source), and a table of UTC offsets by zone, date and
local hour, so the conversion is a join rather than a per row time zone computation.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
OURAIRPORTS_MIRROR = "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv"
# U.S. states, territories and freely associated states served by reporting carriers.
COUNTRIES = ("US", "PR", "VI", "GU", "AS", "MP", "UM")


@dataclass(frozen=True)
class Airport:
    code: str
    name: str
    municipality: str
    region: str
    latitude: float
    longitude: float
    elevation_ft: int | None
    kind: str
    tz: str


class AirportError(ValueError):
    pass


def load_ourairports(path: Path) -> dict[str, dict[str, str]]:
    """Code to row, for airports in the U.S. and its territories.

    The on time files use the IATA code the airport had at the time of the flight, which is not always
    the code OurAirports lists today: an airport renamed and recoded keeps its old code in OurAirports'
    ident (K plus the code) or its keywords, and a closed airport keeps it only in the keywords. So the
    index is built in three passes, each filling only codes the earlier passes left empty: the current
    IATA code (larger airports win a shared code), then the ident and GPS code with the K dropped, then
    any three letter keyword.
    """
    rank = {
        "large_airport": 0,
        "medium_airport": 1,
        "small_airport": 2,
        "seaplane_base": 3,
        "heliport": 4,
        "closed": 5,
    }
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("iso_country") in COUNTRIES:
                rows.append(row)
    out: dict[str, dict[str, str]] = {}

    def offer(code: str, row: dict[str, str]) -> None:
        current = out.get(code)
        if current is None or rank.get(row["type"], 9) < rank.get(current["type"], 9):
            out[code] = row

    for row in rows:
        code = (row.get("iata_code") or "").strip()
        if code:
            offer(code, row)
    second: dict[str, dict[str, str]] = {}
    for row in rows:
        for field in ("ident", "gps_code", "icao_code"):
            value = (row.get(field) or "").strip()
            if len(value) == 4 and value.startswith("K") and value[1:] not in out:
                code = value[1:]
                if code not in second or rank.get(row["type"], 9) < rank.get(second[code]["type"], 9):
                    second[code] = row
    out.update(second)
    third: dict[str, dict[str, str]] = {}
    for row in rows:
        for token in (row.get("keywords") or "").replace(";", ",").split(","):
            code = token.strip()
            if len(code) == 3 and code.isalpha() and code.isupper() and code not in out and code not in third:
                third[code] = row
    out.update(third)
    return out


def locate(codes: Iterable[str], ourairports: dict[str, dict[str, str]]) -> tuple[list[Airport], list[str]]:
    """The airports for the codes seen in the flights, and the codes OurAirports does not know."""
    from timezonefinder import TimezoneFinder

    finder = TimezoneFinder()
    found: list[Airport] = []
    missing: list[str] = []
    for code in sorted(set(codes)):
        row = ourairports.get(code)
        if row is None:
            missing.append(code)
            continue
        lat, lon = float(row["latitude_deg"]), float(row["longitude_deg"])
        tz = finder.timezone_at(lng=lon, lat=lat)
        if tz is None:
            raise AirportError(f"no time zone for {code} at {lat}, {lon}")
        elevation = row.get("elevation_ft") or ""
        found.append(
            Airport(
                code=code,
                name=row["name"],
                municipality=row.get("municipality") or "",
                region=row.get("iso_region") or "",
                latitude=round(lat, 5),
                longitude=round(lon, 5),
                elevation_ft=int(float(elevation)) if elevation else None,
                kind=row["type"],
                tz=tz,
            )
        )
    return found, missing


def airports_frame(airports: list[Airport]) -> pl.DataFrame:
    return pl.DataFrame([a.__dict__ for a in airports]).sort("code")


def offsets_frame(zones: Iterable[str], first: date, last: date) -> pl.DataFrame:
    """UTC offset in minutes for every zone, local date and local hour in the window.

    The offset is that of the local wall clock time at the top of the hour. In the hour that does
    not exist at the spring change it is the offset after the change, and in the hour that occurs
    twice at the autumn change it is the first occurrence, the same convention zoneinfo uses.
    """
    rows: list[tuple[str, date, int, int]] = []
    days = (last - first).days + 1
    for zone in sorted(set(zones)):
        info = ZoneInfo(zone)
        for d in range(days):
            day = first + timedelta(days=d)
            for hour in range(24):
                local = datetime(day.year, day.month, day.day, hour, tzinfo=info)
                offset = local.utcoffset()
                assert offset is not None
                rows.append((zone, day, hour, int(offset.total_seconds() // 60)))
    return pl.DataFrame(
        rows,
        schema={"tz": pl.Utf8, "local_date": pl.Date, "local_hour": pl.Int8, "offset_minutes": pl.Int16},
        orient="row",
    )


def to_utc(local: datetime, zone: str) -> datetime:
    return local.replace(tzinfo=ZoneInfo(zone)).astimezone(UTC)
