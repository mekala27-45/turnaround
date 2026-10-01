"""Open-Meteo hourly weather at the FAA Core 30, one JSON per airport and year, into one parquet.

The pulls are made by deploy/fetch-data.ps1 on a machine that can reach open-meteo.com, in UTC,
for temperature, precipitation, snowfall, wind speed and gusts, low cloud cover and the WMO
weather code. Open-Meteo's terms: CC BY 4.0, "Weather data by Open-Meteo.com".
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import polars as pl

VARIABLES = (
    "temperature_2m",
    "precipitation",
    "snowfall",
    "wind_speed_10m",
    "wind_gusts_10m",
    "cloud_cover_low",
    "weather_code",
)
FILE_PATTERN = re.compile(r"^(?P<airport>[A-Z0-9]{3})_(?P<year>\d{4})\.json$")
# WMO weather codes for the conditions that close or slow runways.
FOG_CODES = (45, 48)
THUNDER_CODES = (95, 96, 99)
FREEZING_CODES = (56, 57, 66, 67)


class WeatherError(ValueError):
    pass


def read_pull(path: Path) -> pl.DataFrame:
    match = FILE_PATTERN.match(path.name)
    if not match:
        raise WeatherError(f"{path.name} is not an airport_year weather pull")
    payload = json.loads(path.read_text(encoding="utf-8"))
    hourly = payload.get("hourly") or {}
    if payload.get("timezone") not in (None, "GMT", "UTC"):
        raise WeatherError(f"{path.name} was pulled in {payload.get('timezone')}, not UTC")
    missing = [v for v in ("time", *VARIABLES) if v not in hourly]
    if missing:
        raise WeatherError(f"{path.name} lacks {missing}")
    frame = pl.DataFrame({"time": hourly["time"], **{v: hourly[v] for v in VARIABLES}}, strict=False)
    return frame.select(
        pl.lit(match["airport"]).alias("airport"),
        pl.col("time").str.to_datetime("%Y-%m-%dT%H:%M", time_zone="UTC").alias("hour_utc"),
        *[pl.col(v).cast(pl.Float32) for v in VARIABLES if v != "weather_code"],
        pl.col("weather_code").cast(pl.Int16),
    )


def build_hourly(folder: Path) -> pl.DataFrame:
    files = sorted(p for p in folder.glob("*.json") if FILE_PATTERN.match(p.name))
    if not files:
        raise WeatherError(f"no weather pulls under {folder}")
    frame = pl.concat([read_pull(p) for p in files], how="vertical")
    frame = frame.unique(["airport", "hour_utc"], keep="first").sort(["airport", "hour_utc"])
    return frame.with_columns(
        pl.col("weather_code").is_in(list(FOG_CODES)).alias("fog"),
        pl.col("weather_code").is_in(list(THUNDER_CODES)).alias("thunder"),
        pl.col("weather_code").is_in(list(FREEZING_CODES)).alias("freezing"),
    )
