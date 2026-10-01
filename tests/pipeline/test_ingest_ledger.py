"""The ingest ledger: a month whose file and contract are unchanged is not read again, and a run the
machine stops partway resumes at the month it had reached."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from turnaround_contracts.generator import Planted, generate_rows, write_month
from turnaround_core.paths import Paths
from turnaround_pipeline.stages import data


def _root(tmp_path: Path) -> Paths:
    p = Paths(tmp_path)
    for year, month in ((2023, 1), (2023, 2), (2023, 3)):
        write_month(p.external_bts, year, month, generate_rows(year, month, 40, 7, Planted.none()))
    return p


def _ledger(p: Paths) -> list[dict[str, str]]:
    with (p.root / data.LEDGER).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_unchanged_months_are_not_read_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = _root(tmp_path)
    first = data.ingest_flights(p)
    assert [r.month for r in first] == [1, 2, 3]
    assert {row["contract"] for row in _ledger(p)} == {data.contract_digest()}
    calls: list[str] = []
    monkeypatch.setattr(data, "ingest_month", lambda *a, **k: calls.append(str(a[0])))
    again = data.ingest_flights(p)
    assert calls == [] and [r.rows for r in again] == [r.rows for r in first]


def test_a_stopped_run_resumes_at_the_month_it_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = _root(tmp_path)
    real = data.ingest_month
    seen: list[str] = []

    def stop_at_march(zip_path: Path, *args: object, **kwargs: object) -> object:
        if zip_path.name.endswith("2023_3.zip"):
            raise RuntimeError("the machine stopped")
        seen.append(zip_path.name)
        return real(zip_path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(data, "ingest_month", stop_at_march)
    with pytest.raises(RuntimeError):
        data.ingest_flights(p)
    assert [row["month"] for row in _ledger(p)] == ["1", "2"]
    resumed: list[str] = []

    def count(zip_path: Path, *args: object, **kwargs: object) -> object:
        resumed.append(zip_path.name)
        return real(zip_path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(data, "ingest_month", count)
    reports = data.ingest_flights(p)
    assert [Path(n).name.split("_")[-1] for n in resumed] == ["3.zip"]
    assert [r.month for r in reports] == [1, 2, 3]
