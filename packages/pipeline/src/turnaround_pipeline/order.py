"""The order the pipeline runs in, and what each step reads from the steps before it.

The Makefile's `pipeline` target, docs/runbook.md and this module must agree; tests/core/
test_make_order.py reads all three. A step may only read what an earlier step wrote, so the
order is checked against the inputs below as well as against the Makefile.
"""

from __future__ import annotations

RUN_ORDER: tuple[str, ...] = (
    "data",
    "warehouse",
    "metrics",
    "simulate",
    "recovery",
    "chapters",
    "metrics-chapters",
    "exports",
    "manifest",
    "render",
    "marts",
)

# Which earlier steps each step reads. Empty means it reads only committed inputs.
READS: dict[str, tuple[str, ...]] = {
    "data": (),
    "warehouse": ("data",),
    "metrics": ("warehouse",),
    "simulate": (),
    "recovery": ("simulate",),
    "chapters": ("warehouse", "recovery"),
    "metrics-chapters": ("chapters",),
    "exports": ("warehouse", "metrics", "chapters"),
    "manifest": ("data", "warehouse", "metrics", "simulate", "recovery", "chapters", "exports"),
    "render": ("manifest",),
    "marts": ("manifest", "render"),
}


def violations(order: tuple[str, ...] = RUN_ORDER) -> list[str]:
    """Every step that reads a step which has not run yet, or that is unknown."""
    seen: set[str] = set()
    problems: list[str] = []
    for step in order:
        if step not in READS:
            problems.append(f"{step} is not a known step")
            continue
        for needed in READS[step]:
            if needed not in seen:
                problems.append(f"{step} reads {needed}, which runs later or not at all")
        seen.add(step)
    return problems
