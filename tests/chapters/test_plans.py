"""Pre-registration: the hash is stable, a changed plan is refused, an edited file is caught, and a
chapter that reports on its fitting years is rejected."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from turnaround_chapters.plan import PlanError, SplitViolation, register, registry_path, report_years, verify
from turnaround_chapters.plans import all_plans, padding


def test_eight_plans_with_stable_distinct_hashes() -> None:
    plans = all_plans()
    assert [p.chapter for p in plans] == list(range(1, 9))
    hashes = [p.digest() for p in plans]
    assert len(set(hashes)) == 8
    assert hashes == [p.digest() for p in all_plans()]
    assert all(len(h) == 16 for h in hashes)


def test_registering_twice_is_idempotent_and_a_changed_plan_is_refused(tmp_path: Path) -> None:
    plan = padding()
    first = register(tmp_path, plan)
    assert register(tmp_path, plan) == first
    changed = plan.model_copy(update={"claim": plan.claim + " Edited after the data was seen."})
    with pytest.raises(PlanError, match="cannot change"):
        register(tmp_path, changed)


def test_verify_catches_an_unregistered_plan_and_an_edited_file(tmp_path: Path) -> None:
    plans = all_plans()
    for plan in plans:
        register(tmp_path, plan)
    assert verify(tmp_path, plans) == []
    path = registry_path(tmp_path, plans[2])
    payload = json.loads(path.read_text())
    payload["plan"]["claim"] = "a quieter claim"
    path.write_text(json.dumps(payload))
    problems = verify(tmp_path, plans)
    assert any("edited after it was hashed" in p for p in problems)
    path.unlink()
    assert any("not registered" in p for p in verify(tmp_path, plans))
    with pytest.raises(PlanError):
        verify(tmp_path, [])


def test_reporting_on_the_fitting_years_is_rejected() -> None:
    assert report_years(2023, 2026) == "year between 2023 and 2026"
    with pytest.raises(SplitViolation):
        report_years(2022, 2026)
    with pytest.raises(SplitViolation):
        report_years(2024, 2023)
