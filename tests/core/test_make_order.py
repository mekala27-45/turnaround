"""The Makefile, the runbook and the pipeline package agree on the order the steps run in."""

from __future__ import annotations

import re
from pathlib import Path

from turnaround_pipeline.order import READS, RUN_ORDER, violations

ROOT = Path(__file__).resolve().parents[2]


def makefile_pipeline() -> tuple[str, ...]:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    found = re.search(r"^pipeline:\s*(.+)$", text, re.M)
    assert found, "the Makefile has no pipeline target"
    return tuple(found.group(1).split())


def makefile_targets() -> set[str]:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    return set(re.findall(r"^([a-z][a-z-]*):", text, re.M))


def runbook_sections() -> tuple[str, ...]:
    text = (ROOT / "docs" / "runbook.md").read_text(encoding="utf-8")
    pipeline = text.split("## The pipeline", 1)[1].split("\n## ", 1)[0]
    return tuple(re.findall(r"^### ([a-z-]+)\s*$", pipeline, re.M))


def test_the_makefile_runs_the_steps_in_the_package_order() -> None:
    assert makefile_pipeline() == RUN_ORDER


def test_every_step_has_its_own_target() -> None:
    missing = [step for step in RUN_ORDER if step not in makefile_targets()]
    assert missing == []


def test_the_runbook_describes_every_step_in_order() -> None:
    assert runbook_sections() == RUN_ORDER


def test_no_step_reads_a_step_that_runs_after_it() -> None:
    assert violations() == []
    assert set(READS) == set(RUN_ORDER)


def test_a_reordered_pipeline_is_caught() -> None:
    swapped = ("warehouse", "data", *RUN_ORDER[2:])
    assert violations(swapped) == ["warehouse reads data, which runs later or not at all"]
    assert violations(("data", "nonsense")) == ["nonsense is not a known step"]
