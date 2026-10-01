"""The FAA releasable aircraft registry, joined on the tail number for type and year built.

The registry's MASTER file holds every aircraft registered today; DEREG holds the ones whose
registration was cancelled, which is where the airliners retired since 2015 are. Both carry the
registrant's name and street address. Only the aircraft columns are read here; the registrant
columns never leave the zip, and the identifier scan fails on any of their names in a committed
table.

MFR MDL CODE is seven characters: three for the manufacturer, two for the model, two for the
series. The first five identify a type (a Boeing 737-800 of any series), which is the aircraft
type the fair ranking and the propagation chapter control for. ACFTREF.txt names the codes when
the registry ships it.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

import polars as pl

AIRCRAFT_COLUMNS = {
    "N-NUMBER": "n_number",
    "SERIAL NUMBER": "serial_number",
    "SERIAL-NUMBER": "serial_number",
    "MFR MDL CODE": "mfr_mdl_code",
    "MFR-MDL-CODE": "mfr_mdl_code",
    "YEAR MFR": "year_built",
    "YEAR-MFR": "year_built",
    "TYPE AIRCRAFT": "type_aircraft",
    "TYPE ENGINE": "type_engine",
    "CANCEL-DATE": "cancel_date",
    "CERT ISSUE DATE": "cert_issue_date",
    "CERT-ISSUE-DATE": "cert_issue_date",
    "AIR WORTH DATE": "airworthiness_date",
    "AIR-WORTH-DATE": "airworthiness_date",
}
OLDEST_AIRLINER = 1975
# TYPE ENGINE codes: 2 turbo-prop, 4 turbo-jet, 5 turbo-fan.
TURBINE_ENGINES = ("2", "4", "5")
REFERENCE_COLUMNS = {
    "CODE": "mfr_mdl_code",
    "MFR": "manufacturer",
    "MODEL": "model",
    "TYPE-ACFT": "type_aircraft",
    "NO-SEATS": "seats",
}


def _rows(archive: zipfile.ZipFile, member: str, keep: dict[str, str]) -> Iterator[dict[str, str]]:
    with archive.open(member) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
        reader = csv.reader(text)
        header = [h.strip() for h in next(reader)]
        index = {keep[h]: i for i, h in enumerate(header) if h in keep}
        for values in reader:
            if not values:
                continue
            yield {name: values[i].strip() if i < len(values) else "" for name, i in index.items()}


def read_registry(zip_path: Path) -> tuple[pl.DataFrame, pl.DataFrame | None]:
    """Aircraft rows from MASTER and DEREG (registrant columns never read), and ACFTREF if present."""
    with zipfile.ZipFile(zip_path) as archive:
        names = {n.upper(): n for n in archive.namelist()}
        frames: list[pl.DataFrame] = []
        for member, source in (("MASTER.TXT", "master"), ("DEREG.TXT", "dereg")):
            if member not in names:
                continue
            rows = list(_rows(archive, names[member], AIRCRAFT_COLUMNS))
            frame = pl.DataFrame(rows).with_columns(pl.lit(source).alias("registry_file"))
            for column in (
                "cancel_date",
                "airworthiness_date",
                "serial_number",
                "type_aircraft",
                "type_engine",
                "cert_issue_date",
            ):
                if column not in frame.columns:
                    frame = frame.with_columns(pl.lit("").alias(column))
            frames.append(frame)
        reference = None
        if "ACFTREF.TXT" in names:
            reference = pl.DataFrame(list(_rows(archive, names["ACFTREF.TXT"], REFERENCE_COLUMNS)))
    if not frames:
        raise ValueError(f"{zip_path.name} has neither MASTER.txt nor DEREG.txt")
    columns = [
        "n_number",
        "mfr_mdl_code",
        "year_built",
        "type_aircraft",
        "type_engine",
        "cancel_date",
        "cert_issue_date",
        "registry_file",
    ]
    aircraft = pl.concat([f.select(columns) for f in frames], how="vertical")
    aircraft = aircraft.with_columns(
        ("N" + pl.col("n_number").str.strip_chars()).alias("tail_number"),
        pl.col("year_built").str.strip_chars().cast(pl.Int32, strict=False),
        pl.col("mfr_mdl_code").str.strip_chars(),
        pl.col("cancel_date").str.strip_chars(),
        pl.col("cert_issue_date").str.strip_chars(),
    ).drop("n_number")
    return aircraft, reference


def match_tails(tails: pl.DataFrame, aircraft: pl.DataFrame) -> pl.DataFrame:
    """One registry row per tail number in the flights, or unmatched when no registration fits.

    An N-number is reassigned when an aircraft leaves the register, so the number on a 2015 flight
    can belong today to a 1959 aircraft registered in 2019, and DEREG can hold a 1934 biplane under
    the number a regional jet flew. A registration fits the flights when the airframe existed by
    their last date (year built), its certificate was issued by their last date, and, for a cancelled
    registration, it was cancelled after their first date, and it is an airliner: built in or after
    1975 (the DC-9s that were older left the reporting fleets before the window) and, where the
    registry says, turbine powered. MASTER is taken when it fits; otherwise the
    fitting DEREG registration cancelled earliest; otherwise the tail is unmatched rather than
    joined to the wrong aircraft. A year built of zero is the registry's blank and becomes null.
    ``tails`` has tail_number, first_seen, last_seen and flights.
    """
    clean = aircraft.with_columns(
        pl.when(pl.col("year_built") > 0).then(pl.col("year_built")).otherwise(None).alias("year_built"),
        pl.col("cancel_date").str.to_date("%Y%m%d", strict=False).alias("cancelled_on"),
        pl.col("cert_issue_date").str.to_date("%Y%m%d", strict=False).alias("issued_on"),
    )
    candidates = tails.join(clean, on="tail_number", how="inner")
    fits = (
        (
            pl.col("year_built").is_null()
            | (pl.col("year_built").is_between(OLDEST_AIRLINER, pl.col("last_seen").dt.year()))
        )
        & (
            pl.col("type_engine").is_null()
            | (pl.col("type_engine") == "")
            | pl.col("type_engine").is_in(TURBINE_ENGINES)
        )
        & (pl.col("issued_on").is_null() | (pl.col("issued_on") <= pl.col("last_seen")))
        & ((pl.col("registry_file") == "master") | (pl.col("cancelled_on") >= pl.col("first_seen")))
    )
    chosen = (
        candidates.filter(fits)
        .with_columns(pl.when(pl.col("registry_file") == "master").then(0).otherwise(1).alias("_order"))
        .sort(["tail_number", "_order", "cancelled_on"], nulls_last=True)
        .unique("tail_number", keep="first", maintain_order=True)
        .drop("_order")
    )
    unmatched = tails.join(chosen.select("tail_number"), on="tail_number", how="anti").with_columns(
        pl.lit(None, dtype=pl.Utf8).alias("mfr_mdl_code"),
        pl.lit(None, dtype=pl.Int32).alias("year_built"),
        pl.lit(None, dtype=pl.Utf8).alias("type_aircraft"),
        pl.lit(None, dtype=pl.Utf8).alias("type_engine"),
        pl.lit(None, dtype=pl.Utf8).alias("cancel_date"),
        pl.lit(None, dtype=pl.Utf8).alias("cert_issue_date"),
        pl.lit("unmatched").alias("registry_file"),
        pl.lit(None, dtype=pl.Date).alias("cancelled_on"),
        pl.lit(None, dtype=pl.Date).alias("issued_on"),
    )
    columns = chosen.columns
    out = pl.concat([chosen, unmatched.select(columns)], how="vertical_relaxed").drop(
        "cancelled_on", "issued_on"
    )
    return out.with_columns(pl.col("mfr_mdl_code").str.slice(0, 5).alias("type_code")).sort("tail_number")
