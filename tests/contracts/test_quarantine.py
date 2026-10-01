"""Every quarantine rule finds exactly what the seeded generator planted, in the real schema.

Three tests per rule as for every gate: the clean month passes every rule, the planted month
fails each rule exactly as often as it was planted, and the ingest refuses a file it cannot read.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import duckdb
import pytest
from turnaround_contracts.bts import (
    RULES,
    ContractError,
    ingest_month,
    mark_revisions,
    month_of,
    readme_fields,
)
from turnaround_contracts.generator import LAYOUT, Planted, generate_rows, readme_html, revise, write_month


def _counts(path: Path) -> dict[str, int]:
    con = duckdb.connect()
    cols = ", ".join(f"sum(q_{r.name}::int) as {r.name}" for r in RULES)
    row = con.execute(f"select {cols} from read_parquet('{path.as_posix()}')").fetchone()
    assert row is not None
    return {r.name: int(v) for r, v in zip(RULES, row, strict=True)}


def test_clean_month_passes_every_rule(tmp_path: Path) -> None:
    zero = Planted(0, 0, 0, 0, 0, 0, 0)
    raw = write_month(tmp_path / "raw", 2023, 3, generate_rows(2023, 3, 400, 11, zero))
    report = ingest_month(raw, tmp_path / "flights")
    assert report.rows == 400
    assert report.layout_matches_readme
    assert all(v == 0 for v in _counts(tmp_path / "flights" / "flights_2023_03.parquet").values())


def test_each_rule_finds_exactly_what_was_planted(tmp_path: Path) -> None:
    planted = Planted()
    raw = write_month(tmp_path / "raw", 2023, 3, generate_rows(2023, 3, 500, 11, planted))
    report = ingest_month(raw, tmp_path / "flights")
    assert report.rows == 500 + planted.duplicate_key
    found = _counts(tmp_path / "flights" / "flights_2023_03.parquet")
    expected = planted.as_dict() | {"revision": 0}
    assert found == expected


def test_revision_rule_counts_rows_a_later_download_changed(tmp_path: Path) -> None:
    rows = generate_rows(2023, 4, 300, 5, Planted(0, 0, 0, 0, 0, 0, 0))
    first = ingest_month(write_month(tmp_path / "v1", 2023, 4, rows), tmp_path / "f1")
    second = ingest_month(write_month(tmp_path / "v2", 2023, 4, revise(rows, 9, 5)), tmp_path / "f2")
    assert first.sha256 != second.sha256
    revised = mark_revisions(
        tmp_path / "f1" / "flights_2023_04.parquet", tmp_path / "f2" / "flights_2023_04.parquet"
    )
    assert revised == 9
    assert _counts(tmp_path / "f2" / "flights_2023_04.parquet")["revision"] == 9


def test_identical_download_has_no_revisions(tmp_path: Path) -> None:
    rows = generate_rows(2023, 4, 200, 5, Planted(0, 0, 0, 0, 0, 0, 0))
    ingest_month(write_month(tmp_path / "v1", 2023, 4, rows), tmp_path / "f1")
    ingest_month(write_month(tmp_path / "v2", 2023, 4, rows), tmp_path / "f2")
    assert (
        mark_revisions(
            tmp_path / "f1" / "flights_2023_04.parquet", tmp_path / "f2" / "flights_2023_04.parquet"
        )
        == 0
    )


def test_ingest_refuses_a_zip_without_one_csv(tmp_path: Path) -> None:
    path = tmp_path / "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_5.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("readme.html", readme_html())
    with pytest.raises(ContractError, match="CSV"):
        ingest_month(path, tmp_path / "out")


def test_ingest_refuses_a_file_missing_a_field(tmp_path: Path) -> None:
    path = tmp_path / "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2023_5.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("x.csv", '"Year","Month"\n2023,5\n')
    with pytest.raises(ContractError, match="lacks fields"):
        ingest_month(path, tmp_path / "out")


def test_ingest_refuses_rows_from_another_month(tmp_path: Path) -> None:
    rows = generate_rows(2023, 6, 50, 2, Planted(0, 0, 0, 0, 0, 0, 0))
    rows[3]["Month"] = "7"
    raw = write_month(tmp_path / "raw", 2023, 6, rows)
    with pytest.raises(ContractError, match="months"):
        ingest_month(raw, tmp_path / "out")


def test_month_is_read_from_the_file_name() -> None:
    assert month_of(Path("On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_7.zip")) == (
        2026,
        7,
    )
    with pytest.raises(ContractError):
        month_of(Path("something_else.zip"))


def test_readme_layout_is_read_in_order() -> None:
    assert readme_fields(readme_html()) == list(LAYOUT)
    with pytest.raises(ContractError):
        readme_fields("<html>no layout</html>")
