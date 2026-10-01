"""Scan everything published for an identity or a raw row that should not be there.

What counts here: a Luhn valid card number, a Social Security number pattern, an email
address, a raw row of the BTS monthly files (recognised by their header, because the raw
files are never committed, only derived tables), the raw FAA registry header (the registry
carries registrant names and street addresses, and only the aircraft columns are kept), any
registrant column name in a committed table, or any token on the planted list in
data/planted_identifiers.txt. The planted list is what the test plants and then expects the
scan to find, including a traveler name and a booking reference in a check log row.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SSN = re.compile(r"(?<!\d)(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}(?!\d)")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# A run of 13 to 19 digits with optional separators, not inside a longer token: a UUID's last
# groups are hexadecimal and can pass Luhn by chance, so a run preceded or followed by a word
# character, a dot or a hyphen is part of an identifier or a number, not a card.
PAN = re.compile(r"(?<![\w.-])(?:\d[ -]?){13,19}(?![\w-])")
RAW_HEADERS = {
    "bts raw header": '"Year","Quarter","Month","DayofMonth","DayOfWeek","FlightDate"',
    "bts raw header (unquoted)": "Year,Quarter,Month,DayofMonth,DayOfWeek,FlightDate,Reporting_Airline",
    "faa registry raw header": "N-NUMBER,SERIAL NUMBER,MFR MDL CODE",
}
# Registrant columns of the FAA registry. A committed table that carries one of these names
# carries a person's name or address.
REGISTRANT_COLUMNS = ("street", "street2", "registrant_name", "zip_code", "other_names", "name_other")
SCAN_GLOBS = (
    "results/**/*.json",
    "results/**/*.csv",
    "results/**/*.parquet",
    "results/**/*.md",
    "data/**/*.csv",
    "data/**/*.parquet",
    "data/**/*.json",
    "data/**/*.md",
    "report/**/*.md",
    "report/**/*.html",
    "story/**/*.md",
    "exports/**/*.csv",
    "exports/**/*.json",
    "exports/**/*.md",
    "docs/**/*.md",
    "README.md",
    "RESULTS.md",
    "web/public/data/**/*",
    "web/out/**/*.html",
    "web/out/**/*.json",
    "logs/**/*.log",
)
PLANTED_FILE = Path("data/planted_identifiers.txt")
ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "turnaround.example", "anthropic.com")


def luhn_valid(digits: str) -> bool:
    total = 0
    for position, char in enumerate(reversed(digits)):
        number = int(char)
        if position % 2 == 1:
            number *= 2
            if number > 9:
                number -= 9
        total += number
    return total % 10 == 0


def find_card_numbers(text: str) -> list[str]:
    found: list[str] = []
    for match in PAN.finditer(text):
        digits = re.sub(r"[ -]", "", match.group(0))
        if 13 <= len(digits) <= 19 and len(set(digits)) > 1 and luhn_valid(digits):
            found.append(digits)
    return found


def load_planted(root: Path) -> set[str]:
    path = root / PLANTED_FILE
    if not path.exists():
        return set()
    return {
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def text_of(path: Path) -> str:
    if path.suffix == ".parquet":
        import polars as pl

        frame = pl.read_parquet(path)
        parts: list[str] = [",".join(frame.columns)]
        for column, dtype in zip(frame.columns, frame.dtypes, strict=True):
            if dtype == pl.Utf8:
                parts.extend(str(v) for v in frame[column].drop_nulls().unique().to_list())
            elif dtype.is_integer():
                values = frame[column].drop_nulls()
                big = values.filter(values.abs() >= 10**12)
                parts.extend(str(v) for v in big.to_list())
        return "\n".join(parts)
    if path.suffix == ".json":
        try:
            return json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def columns_of(path: Path) -> list[str]:
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq

        return [c.lower() for c in pq.read_schema(path).names]
    if path.suffix == ".csv":
        try:
            with path.open(encoding="utf-8") as handle:
                return [c.strip().strip('"').lower() for c in handle.readline().split(",")]
        except UnicodeDecodeError:
            return []
    return []


def findings(text: str, planted: set[str], columns: list[str] | None = None) -> list[str]:
    out = [f"card number ending {pan[-4:]}" for pan in find_card_numbers(text)]
    out += [f"SSN pattern {m.group(0)[:3]}-XX-XXXX" for m in SSN.finditer(text)]
    for match in EMAIL.finditer(text):
        address = match.group(0)
        if not address.lower().endswith(ALLOWED_EMAIL_DOMAINS):
            out.append(f"email address at {address.split('@')[1]}")
    for name, header in RAW_HEADERS.items():
        if header in text:
            out.append(name)
    for column in columns or []:
        if column in REGISTRANT_COLUMNS:
            out.append(f"registrant column '{column}'")
    if planted:
        lowered = text.lower()
        out.extend(f"planted identifier '{token}'" for token in sorted(planted) if token in lowered)
    return out


def targets(root: Path) -> list[Path]:
    found: list[Path] = []
    for pattern in SCAN_GLOBS:
        found.extend(
            p
            for p in root.glob(pattern)
            if p.is_file()
            and "node_modules" not in p.parts
            and "external" not in p.parts
            and "flights" not in p.parts
        )
    return sorted(set(found))


def check(root: Path, files: Iterable[Path] | None = None, planted: set[str] | None = None) -> int:
    scan = list(files) if files is not None else targets(root)
    if not scan:
        raise ValueError("the identifier scan found no files to scan")
    tokens = planted if planted is not None else load_planted(root)
    problems: list[str] = []
    for path in scan:
        if path.name == PLANTED_FILE.name:
            continue
        for finding in findings(text_of(path), tokens, columns_of(path)):
            problems.append(f"{path.relative_to(root)}: {finding}")
    if problems:
        raise ValueError("identifier scan failed:\n" + "\n".join(problems[:50]))
    return len(scan)


if __name__ == "__main__":
    count = check(Path(__file__).resolve().parents[1])
    print(
        f"identifier scan: {count} files, no card numbers, SSN patterns, addresses, raw rows, "
        "registrant columns or planted tokens"
    )
