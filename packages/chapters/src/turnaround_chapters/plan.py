"""Pre-registration: each chapter's analysis plan, hashed and committed before its estimate runs on real flights.

The plan states the claim (phrased so it could come out either way), the estimator, the test, the
split, the family of comparisons and its correction, the interval method, and the policy values it
depends on. Its hash is readout's design hash: SHA-256 of the canonical JSON, sixteen characters.
Registering writes results/plans/<chapter>.json. Registering a different plan under a slug that is
already registered refuses, so a plan cannot be edited after the data was seen without a recorded
reversal; the gate recomputes every plan from code and fails if any differs from its registered hash.

The split is enforced, not described: a chapter that fits anything chooses on the fitting years and
reports on the test years, and report_years() refuses a reporting window that reaches back into the
fitting years.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from turnaround_core.config import POLICY, Policy
from turnaround_core.hashing import design_hash
from turnaround_core.model import StrictModel


class Plan(StrictModel):
    chapter: int
    slug: str
    title: str
    claim: str
    estimator: str
    test: str
    split: str
    family: str
    interval: str
    simulator: str
    policy: dict[str, Any]

    def digest(self) -> str:
        return design_hash(self.model_dump(mode="json"))


class PlanError(ValueError):
    pass


class SplitViolation(PlanError):
    pass


def registry_path(results: Path, plan: Plan) -> Path:
    return results / "plans" / f"{plan.chapter:02d}_{plan.slug}.json"


def register(results: Path, plan: Plan) -> str:
    """Write the plan with its hash, or confirm the registered one is identical. Returns the hash."""
    path = registry_path(results, plan)
    digest = plan.digest()
    payload = {"hash": digest, "plan": plan.model_dump(mode="json")}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("hash") != digest:
            raise PlanError(
                f"chapter {plan.chapter} is registered under hash {existing.get('hash')} and the plan in code "
                f"hashes to {digest}: a registered plan cannot change without a recorded reversal"
            )
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return digest


def verify(results: Path, plans: list[Plan]) -> list[str]:
    """Problems with the registry: a plan never registered, or registered under another hash."""
    if not plans:
        raise PlanError("no plans to verify")
    problems: list[str] = []
    for plan in plans:
        path = registry_path(results, plan)
        if not path.exists():
            problems.append(f"chapter {plan.chapter} ({plan.slug}) is not registered")
            continue
        existing = json.loads(path.read_text(encoding="utf-8"))
        recomputed = design_hash(existing["plan"])
        if recomputed != existing["hash"]:
            problems.append(f"chapter {plan.chapter}: the registered file was edited after it was hashed")
        if existing["hash"] != plan.digest():
            problems.append(f"chapter {plan.chapter}: the plan in code differs from the registered plan")
    return problems


def fit_years(policy: Policy = POLICY) -> tuple[int, int]:
    return policy.fit_first_year, policy.fit_last_year


def report_years(first: int, last: int, policy: Policy = POLICY) -> str:
    """The SQL predicate for a reporting window, refused when it overlaps the fitting years."""
    if first <= policy.fit_last_year:
        raise SplitViolation(
            f"a chapter that fits on {policy.fit_first_year} to {policy.fit_last_year} cannot report on {first}"
        )
    if last < first:
        raise SplitViolation("the reporting window is empty")
    return f"year between {first} and {last}"


def fit_predicate(policy: Policy = POLICY) -> str:
    return f"year between {policy.fit_first_year} and {policy.fit_last_year}"
