"""Determinism: the same inputs give the same manifest whatever Python's hash seed, and the caches
are keyed by a digest of their inputs, so a changed input misses rather than serving a stale run."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from turnaround_evaluation import recovery

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).with_name("_run_chapters.py")


@pytest.mark.slow
def test_the_chapters_manifest_is_identical_under_two_hash_seeds(tmp_path: Path) -> None:
    outputs = [tmp_path / "a.json", tmp_path / "b.json"]
    runs = [
        subprocess.Popen(
            [sys.executable, str(RUNNER), str(out)],
            cwd=ROOT,
            env={**os.environ, "PYTHONHASHSEED": seed, "TURNAROUND_AS_OF": "2026-10-01"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        for seed, out in zip(("0", "4242"), outputs, strict=True)
    ]
    for run in runs:
        _, err = run.communicate(timeout=600)
        assert run.returncode == 0, err[-2000:]
    first, second = (json.loads(p.read_text(encoding="utf-8")) for p in outputs)
    assert first["values"], "the run wrote no values"
    differing = [
        f"{bucket} {key}"
        for bucket in ("values", "tables", "figures")
        for key in sorted(set(first[bucket]) | set(second[bucket]))
        if first[bucket].get(key) != second[bucket].get(key)
    ]
    assert differing == []


def test_the_recovery_cache_hits_on_the_same_input_and_misses_when_it_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, int]] = []

    def fake_run(condition: recovery.Condition, seed: int) -> dict[str, object]:
        calls.append((condition.name, seed))
        return {"condition": condition.name, "seed": seed}

    monkeypatch.setattr(recovery, "run_one", fake_run)
    condition = recovery.conditions()[0]
    cache = str(tmp_path)
    first = recovery._worker((condition, 1, cache))
    again = recovery._worker((condition, 1, cache))
    assert again == first
    assert calls == [(condition.name, 1)], "the second run should have read the cache"
    recovery._worker((condition, 2, cache))
    assert calls[-1] == (condition.name, 2), "a different seed is a different input"
    other = recovery.conditions()[1]
    recovery._worker((other, 1, cache))
    assert calls[-1] == (other.name, 1), "a different condition is a different input"
    monkeypatch.setattr(recovery, "CODE_VERSION", "changed for the test")
    recovery._worker((condition, 1, cache))
    assert len(calls) == 4, "a change to the estimator code invalidates every cached run"


def test_the_cache_key_is_a_digest_of_the_whole_spec() -> None:
    condition = recovery.conditions()[0]
    assert recovery._key(condition, 1) == recovery._key(condition, 1)
    keys = {recovery._key(c, s) for c in recovery.conditions() for s in (1, 2)}
    assert len(keys) == 2 * len(recovery.conditions())
