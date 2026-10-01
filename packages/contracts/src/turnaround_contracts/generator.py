"""A seeded generator of monthly on time files in the real schema, with defects planted at stated counts.

The real files are four gigabytes and cannot be fetched by CI, so the tests run the identical ingest
code path on files this module writes: the same zip layout, the same 109 fields with the trailing
comma, the same readme record layout, the same HHMM clock text and two decimal minutes. It
reproduces the defects, not the values: each quarantine rule gets a planted count, and the test
asserts the ingest finds exactly that many. A second version of a month can be written with some
rows changed, which is what the revision rule exists to count.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np

_BASE = [
    "Year",
    "Quarter",
    "Month",
    "DayofMonth",
    "DayOfWeek",
    "FlightDate",
    "Reporting_Airline",
    "DOT_ID_Reporting_Airline",
    "IATA_CODE_Reporting_Airline",
    "Tail_Number",
    "Flight_Number_Reporting_Airline",
    "OriginAirportID",
    "OriginAirportSeqID",
    "OriginCityMarketID",
    "Origin",
    "OriginCityName",
    "OriginState",
    "OriginStateFips",
    "OriginStateName",
    "OriginWac",
    "DestAirportID",
    "DestAirportSeqID",
    "DestCityMarketID",
    "Dest",
    "DestCityName",
    "DestState",
    "DestStateFips",
    "DestStateName",
    "DestWac",
    "CRSDepTime",
    "DepTime",
    "DepDelay",
    "DepDelayMinutes",
    "DepDel15",
    "DepartureDelayGroups",
    "DepTimeBlk",
    "TaxiOut",
    "WheelsOff",
    "WheelsOn",
    "TaxiIn",
    "CRSArrTime",
    "ArrTime",
    "ArrDelay",
    "ArrDelayMinutes",
    "ArrDel15",
    "ArrivalDelayGroups",
    "ArrTimeBlk",
    "Cancelled",
    "CancellationCode",
    "Diverted",
    "CRSElapsedTime",
    "ActualElapsedTime",
    "AirTime",
    "Flights",
    "Distance",
    "DistanceGroup",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "SecurityDelay",
    "LateAircraftDelay",
    "FirstDepTime",
    "TotalAddGTime",
    "LongestAddGTime",
    "DivAirportLandings",
    "DivReachedDest",
    "DivActualElapsedTime",
    "DivArrDelay",
    "DivDistance",
]
_DIVERSION = (
    "Airport",
    "AirportID",
    "AirportSeqID",
    "WheelsOn",
    "TotalGTime",
    "LongestGTime",
    "WheelsOff",
    "TailNum",
)
LAYOUT: tuple[str, ...] = tuple(_BASE + [f"Div{i}{part}" for i in range(1, 6) for part in _DIVERSION])
assert len(LAYOUT) == 109

AIRPORTS = (("ATL", 10397, "Atlanta, GA", "GA"), ("ORD", 13930, "Chicago, IL", "IL"), ("DFW", 11298, "Dallas/Fort Worth, TX", "TX"), ("DEN", 11292, "Denver, CO", "CO"), ("LAX", 12892, "Los Angeles, CA", "CA"))  # fmt: skip
CARRIERS = (("DL", 19790), ("AA", 19805), ("WN", 19393))


@dataclass
class Planted:
    duplicate_key: int = 3
    actual_without_scheduled: int = 2
    impossible_time: int = 4
    elapsed_mismatch: int = 5
    status_conflict: int = 2
    missing_actual: int = 3
    cause_mismatch: int = 6
    tail_missing: int = 3
    tail_format: int = 7
    counts: dict[str, int] = field(default_factory=dict)

    @classmethod
    def none(cls) -> Planted:
        """A month with no defect planted."""
        return cls(
            duplicate_key=0,
            actual_without_scheduled=0,
            impossible_time=0,
            elapsed_mismatch=0,
            status_conflict=0,
            missing_actual=0,
            cause_mismatch=0,
            tail_missing=0,
            tail_format=0,
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "duplicate_key": self.duplicate_key,
            "actual_without_scheduled": self.actual_without_scheduled,
            "impossible_time": self.impossible_time,
            "elapsed_mismatch": self.elapsed_mismatch,
            "status_conflict": self.status_conflict,
            "missing_actual": self.missing_actual,
            "cause_mismatch": self.cause_mismatch,
            "tail_missing": self.tail_missing,
            "tail_format": self.tail_format,
        }


def _hhmm(minutes: int) -> str:
    minutes %= 1440
    return f"{minutes // 60:02d}{minutes % 60:02d}"


def _blank_row() -> dict[str, str]:
    return dict.fromkeys(LAYOUT, "")


def generate_rows(year: int, month: int, n: int, seed: int, planted: Planted) -> list[dict[str, str]]:
    """Clean flights, then the planted defects applied to distinct rows."""
    rng = np.random.default_rng([seed, year, month])
    first = date(year, month, 1)
    days = ((first.replace(day=28) + timedelta(days=4)).replace(day=1) - first).days
    rows: list[dict[str, str]] = []
    for i in range(n):
        o, d = rng.choice(len(AIRPORTS), size=2, replace=False)
        carrier, dot = CARRIERS[i % len(CARRIERS)]
        day = first + timedelta(days=int(rng.integers(0, days)))
        crs_dep = int(rng.integers(300, 1320))
        block = int(rng.integers(70, 280))
        dep_delay = int(rng.choice([-5, -2, 0, 3, 12, 25, 48]))
        taxi_out, taxi_in = int(rng.integers(8, 30)), int(rng.integers(3, 15))
        air = block - taxi_out - taxi_in + int(rng.integers(-10, 10))
        elapsed = taxi_out + air + taxi_in
        arr_delay = dep_delay + (elapsed - block)
        row = _blank_row()
        row.update(
            {
                "Year": str(year), "Quarter": str((month - 1) // 3 + 1), "Month": str(month),
                "DayofMonth": str(day.day), "DayOfWeek": str(day.isoweekday()), "FlightDate": day.isoformat(),
                "Reporting_Airline": carrier, "DOT_ID_Reporting_Airline": str(dot), "IATA_CODE_Reporting_Airline": carrier,
                "Tail_Number": f"N{100 + i % 400}{carrier[0]}", "Flight_Number_Reporting_Airline": str(1000 + i),
                "OriginAirportID": str(AIRPORTS[o][1]), "Origin": AIRPORTS[o][0], "OriginCityName": AIRPORTS[o][2],
                "OriginState": AIRPORTS[o][3], "DestAirportID": str(AIRPORTS[d][1]), "Dest": AIRPORTS[d][0],
                "DestCityName": AIRPORTS[d][2], "DestState": AIRPORTS[d][3],
                "CRSDepTime": _hhmm(crs_dep), "DepTime": _hhmm(crs_dep + dep_delay), "DepDelay": f"{dep_delay:.2f}",
                "TaxiOut": f"{taxi_out:.2f}", "WheelsOff": _hhmm(crs_dep + dep_delay + taxi_out),
                "WheelsOn": _hhmm(crs_dep + dep_delay + taxi_out + air), "TaxiIn": f"{taxi_in:.2f}",
                "CRSArrTime": _hhmm(crs_dep + block), "ArrTime": _hhmm(crs_dep + dep_delay + elapsed),
                "ArrDelay": f"{arr_delay:.2f}", "Cancelled": "0.00", "Diverted": "0.00",
                "CRSElapsedTime": f"{block:.2f}", "ActualElapsedTime": f"{elapsed:.2f}", "AirTime": f"{air:.2f}",
                "Flights": "1.00", "Distance": f"{block * 7:.2f}", "DivAirportLandings": "0",
            }
        )  # fmt: skip
        if arr_delay >= 15:
            late = max(arr_delay - 10, 0)
            row.update(
                {
                    "CarrierDelay": "10.00", "WeatherDelay": "0.00", "NASDelay": f"{arr_delay - 10 - late:.2f}",
                    "SecurityDelay": "0.00", "LateAircraftDelay": f"{late:.2f}",
                }
            )  # fmt: skip
        rows.append(row)
    cursor = 0

    def take(k: int) -> list[int]:
        nonlocal cursor
        picked = list(range(cursor, cursor + k))
        cursor += k
        return picked

    for i in take(planted.actual_without_scheduled):
        rows[i]["CRSDepTime"] = ""
    for n, i in enumerate(take(planted.impossible_time)):
        # Four ways a time cannot be, each with the elapsed time kept consistent so only this rule fires:
        # a negative taxi in, a negative scheduled elapsed time, a day in the air, a day on the schedule.
        kind = n % 4
        if kind == 0:
            rows[i]["TaxiIn"] = "-4.00"
        elif kind == 1:
            rows[i]["CRSElapsedTime"] = "-60.00"
        elif kind == 2:
            rows[i]["AirTime"] = "1557.00"
        else:
            rows[i]["CRSElapsedTime"] = "1510.00"
        if kind in (0, 2):
            consistent = float(rows[i]["TaxiOut"]) + float(rows[i]["AirTime"]) + float(rows[i]["TaxiIn"])
            rows[i]["ActualElapsedTime"] = f"{consistent:.2f}"
    for i in take(planted.elapsed_mismatch):
        rows[i]["ActualElapsedTime"] = f"{float(rows[i]['ActualElapsedTime']) + 30:.2f}"
    for i in take(planted.status_conflict):
        rows[i]["Cancelled"] = "1.00"
        rows[i]["Diverted"] = "1.00"
    for n, i in enumerate(take(planted.missing_actual)):
        # An arrival time with no arrival delay, as some months of the real files carry, or a flight
        # with no elapsed or air time.
        if n % 2 == 0:
            rows[i]["ArrDelay"] = ""
        else:
            rows[i]["ActualElapsedTime"] = ""
            rows[i]["AirTime"] = ""
    for i in take(planted.cause_mismatch):
        rows[i].update({"ArrDelay": "40.00", "CarrierDelay": "5.00", "WeatherDelay": "0.00", "NASDelay": "0.00", "SecurityDelay": "0.00", "LateAircraftDelay": "0.00"})  # fmt: skip
    for i in take(planted.tail_missing):
        rows[i]["Tail_Number"] = ""
    for i in take(planted.tail_format):
        rows[i]["Tail_Number"] = ["UNKNOW", "N0000", "NA", "N12IO", "N1ABC", "N123456", "XA-ABC"][i % 7]
    for i in take(planted.duplicate_key):
        rows.append(dict(rows[i]))
    return rows


def readme_html() -> str:
    cells = "\n".join(f"\t<TR><TD>{name}</TD><TD>{name}</TD></TR>" for name in LAYOUT)
    return (
        "<HTML><BODY><TABLE>\n\t<TR><TD COLSPAN=2><H4>RECORD LAYOUT</H4></TD></TR>\n"
        "\t<TR><TD COLSPAN=2>Below are fields in the order that they appear on the records:</TD></TR>\n"
        f"{cells}\n</TABLE></BODY></HTML>\n"
    )


def _csv(rows: list[dict[str, str]]) -> str:
    def quote(name: str, value: str) -> str:
        numeric = name in {"Year", "Quarter", "Month", "DayofMonth", "DayOfWeek", "DOT_ID_Reporting_Airline"}
        return value if numeric or value.replace(".", "", 1).lstrip("-").isdigit() else f'"{value}"'

    out = io.StringIO()
    out.write(",".join(f'"{name}"' for name in LAYOUT) + ",\n")
    for row in rows:
        out.write(",".join(quote(name, row[name]) for name in LAYOUT) + ",\n")
    return out.getvalue()


def write_month(folder: Path, year: int, month: int, rows: list[dict[str, str]]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}"
    path = folder / f"{stem}.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            f"On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_{year}_{month}.csv", _csv(rows)
        )
        archive.writestr("readme.html", readme_html())
    return path


def revise(rows: list[dict[str, str]], count: int, seed: int) -> list[dict[str, str]]:
    """A later download of the same month with ``count`` clean rows' arrival delays changed."""
    rng = np.random.default_rng([seed, 7])
    revised = [dict(r) for r in rows]
    clean = [i for i, r in enumerate(revised) if r["Tail_Number"].startswith("N1") and r["CRSDepTime"]]
    for i in sorted(rng.choice(clean, size=count, replace=False).tolist()):
        revised[i]["ArrDelay"] = f"{float(revised[i]['ArrDelay'] or 0) + 1:.2f}"
    return revised
