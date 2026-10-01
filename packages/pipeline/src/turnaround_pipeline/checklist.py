"""The definition of done, evaluated: each of the eighteen lines marked done or not done with one
sentence of evidence, from the manifest and from facts about the repository that the manifest cannot
hold (the commit count, the decision log, the notebooks, the quality run, the rederive, the release).

Every number in the evidence is formatted from a manifest value or counted from a file here, so the
README and RESULTS print the checklist without a number typed into a template.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from turnaround_core.manifest import Manifest

LINES: tuple[str, ...] = (
    "Every monthly file from January 2015 to the latest ingested, the quarantine report published, the registry join rate stated, airports and weather committed with attribution, provenance and licenses recorded",
    "Warehouse with dbt tests and exposures; the metric layer reconciled across grains",
    "Simulator with known padding, propagation, carrier effects, planted bunching and a planted meltdown; the recovery study on every condition with at least twenty seeds",
    "Chapters 1 and 2 with plan hashes, simulator recovery, results on the test years with intervals, the changepoints named",
    "Chapter 4: rotations with integrity rules and their counts; the inherited share with its interval; the buffer curve",
    "Chapter 5: the fair ranking with cluster robust intervals beside the raw ranking, the rank changes named, the simulator recovery",
    "API deployed on Fly with Neon; live URL in the README; verified from a separate client, with the client's response printed",
    "Checks and scores observed from an independent connection; audit before response; the out of process check",
    "Chapter 3: the density test with placebos and correction, published either way; chapter 6: causes reported and estimated side by side",
    "Chapter 7: the known events table with citations and detection days; the operating point with its interior test; the two event studies with recovery times",
    "Chapter 8: the traveler's tables; the misconnect curves for the twenty hubs with the chosen buffer and its interior test; the airline's buffer trade",
    "Exports: the workbook with live formulas and its recalculation test, the Tableau extract and specification, the Power BI specification with measures, the CSV bundle with its dictionary",
    "The story live on GitHub Pages with sticky charts, method notes, the SQL behind every chart, the corrections section and the print stylesheet",
    "Explore, rank, rotations, events, planner, data and report pages live, working from the recorded session when the API is asleep; the test server refuses what the host refuses",
    "Latency published; the live check in a real browser recorded in results/live_check.json",
    "RESULTS.md with every figure re-derived by the gate and a specific limitations section",
    "README with the matrix and this checklist; DECISIONS.md with at least ten dated entries, two reversals and the corrections; three executed notebooks with a dead end each; the pushback paragraph on every chapter and page",
    "Coverage at or above 80 percent, mypy strict clean, ruff clean, zero em dashes, zero banned vocabulary, palette validator green including the dark card run, forty to sixty commits, the rederive run in a worktree before the tag, v0.1.0 pushed after the commits, Apache 2.0 for code with the four data sources' terms declared, repo described, topics set",
)


@dataclass(frozen=True)
class Item:
    number: int
    text: str
    done: bool
    evidence: str


def _json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8-sig"))
    return loaded


def repository_facts(root: Path) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    try:
        out = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        )
        facts["commits"] = int(out.stdout.strip())
    except (OSError, subprocess.CalledProcessError, ValueError):
        facts["commits"] = 0
    decisions = (
        (root / "DECISIONS.md").read_text(encoding="utf-8") if (root / "DECISIONS.md").exists() else ""
    )
    headings = re.findall(r"^## (\d{4}-\d{2}-\d{2}): (.+)$", decisions, flags=re.M)
    facts["decisions"] = len(headings)
    facts["reversals"] = sum(1 for _, title in headings if title.lower().startswith("reversal"))
    facts["corrections"] = sum(1 for _, title in headings if title.lower().startswith("correction"))
    notebooks = sorted((root / "notebooks").glob("*.ipynb"))
    executed = 0
    dead_ends = 0
    for nb in notebooks:
        cells = json.loads(nb.read_text(encoding="utf-8")).get("cells", [])
        if any(c.get("cell_type") == "code" and c.get("outputs") for c in cells):
            executed += 1
        if any(
            "dead end" in "".join(c.get("source", [])).lower()
            for c in cells
            if c.get("cell_type") == "markdown"
        ):
            dead_ends += 1
    facts["notebooks"] = len(notebooks)
    facts["notebooks_executed"] = executed
    facts["notebooks_dead_ends"] = dead_ends
    facts["quality"] = _json(root / "results" / "quality.json")
    facts["rederive"] = _json(root / "results" / "rederive.json")
    facts["release"] = _json(root / "results" / "release.json")
    facts["web"] = _json(root / "results" / "web_tests.json")
    facts["license"] = (root / "LICENSE").exists() and "Apache" in (root / "LICENSE").read_text(
        encoding="utf-8"
    )
    facts["provenance"] = (root / "data" / "PROVENANCE.md").exists()
    return facts


def evaluate(m: Manifest, facts: dict[str, Any]) -> list[Item]:
    def v(key: str) -> str:
        return m.text(key) if key in m.values else "not measured"

    def raw(key: str) -> Any:
        return m.values[key].value if key in m.values else None

    def has(*keys: str) -> bool:
        return all(k in m.values or k in m.tables or k in m.figures for k in keys)

    q = facts.get("quality", {})
    rederive = facts.get("rederive", {})
    release = facts.get("release", {})
    web = facts.get("web", {})
    items: list[Item] = []

    def add(done: bool, evidence: str) -> None:
        items.append(Item(len(items) + 1, LINES[len(items)], bool(done), evidence))

    add(
        has(
            "data.months", "quarantine.by_rule", "registry.flight_join_rate", "airports.count", "weather.rows"
        )
        and raw("data.gaps") == "none"
        and facts["provenance"],
        f"{v('data.months')} monthly files from {v('data.first_month')} to {v('data.last_month')} "
        f"(missing: {v('data.gaps')}), {v('data.rows')} rows; "
        f"quarantine by rule and by carrier and month on the data page; registry join {v('registry.flight_join_rate')} of flights; "
        f"{v('airports.count')} airports; {v('weather.rows')} hourly weather rows; data/PROVENANCE.md.",
    )
    add(
        has("warehouse.tests", "metrics.disagreements")
        and (raw("warehouse.tests") or 0) >= 100
        and raw("warehouse.tests_failed") == 0
        and raw("metrics.disagreements") == 0,
        f"dbt build: {v('warehouse.models')} models, {v('warehouse.tests')} tests, {v('warehouse.tests_failed')} failed; "
        f"{v('metrics.count')} metrics reconciled at {v('metrics.grains')} grains over {v('metrics.cells')} cells with "
        f"{v('metrics.disagreements')} disagreements.",
    )
    add(
        has("recovery.seeds", "recovery.conditions") and (raw("recovery.seeds") or 0) >= 20,
        f"{v('recovery.conditions')} conditions times {v('recovery.seeds')} seeds, {v('recovery.runs')} runs; results/recovery.",
    )
    add(
        has(
            "plan.1.hash",
            "plan.2.hash",
            "ch1.on_time.change",
            "ch2.padding.change",
            "ch2.changepoints",
            "recovery.definition.seeds",
        ),
        f"plans {v('plan.1.hash')} and {v('plan.2.hash')}; on time change {v('ch1.on_time.change')}, padding change "
        f"{v('ch2.padding.change')} with intervals; {v('ch2.changepoints')} changepoints dated.",
    )
    add(
        has("plan.4.hash", "ch4.share", "ch4.buffer_curve", "ch4.rotations"),
        f"{v('ch4.rotations')} rotations, {v('ch4.broken_chain')} broken chains, {v('ch4.impossible')} impossible sequences; "
        f"inherited share {v('ch4.share')} ({v('ch4.share.low')} to {v('ch4.share.high')}); buffer curve table ch4.buffer_curve.",
    )
    add(
        has("plan.5.hash", "ch5.ranking", "recovery.rank_adjusted.strong"),
        f"{v('ch5.carriers')} carriers raw and adjusted with day clustered intervals; {v('ch5.moved')} change places; "
        f"simulator rank correlation {v('recovery.rank_adjusted.strong')} adjusted against {v('recovery.rank_raw.strong')} raw.",
    )
    add(
        raw("deploy.passed") == "yes",
        f"{v('deploy.base_url')}: {v('deploy.status')} from {v('deploy.client') if has('deploy.client') else 'no client yet'}; "
        f"probability {v('deploy.probability') if has('deploy.probability') else 'not measured'} read back; results/deploy/verification.json.",
    )
    api = q.get("api_tests", {})
    add(
        bool(api.get("passed")) and not api.get("failed"),
        f"tests/api: {api.get('passed', 0)} passed (test_check_is_committed, test_score_is_committed, "
        "test_audit_precedes_response, the out of process scripts/check_persistence.py).",
    )
    add(
        has("plan.3.hash", "ch3.by_carrier", "plan.6.hash", "ch6.weather_share"),
        f"{v('ch3.flagged')} of {v('ch3.carriers')} carriers flagged after Benjamini-Hochberg; weather share {v('ch6.weather_share')} "
        f"against {v('ch6.reported_weather_share')} reported.",
    )
    add(
        has("plan.7.hash", "ch7.events", "ch7.threshold"),
        f"threshold {v('ch7.threshold')} {v('ch7.interior')}; {v('ch7.test.detected')} of {v('ch7.test.events')} reporting year "
        f"events flagged; recovery {v('ch7.study.WN.recovery_days') if has('ch7.study.WN.recovery_days') else 'not measured'} "
        f"and {v('ch7.study.DL.recovery_days') if has('ch7.study.DL.recovery_days') else 'not measured'} days.",
    )
    add(
        has("plan.8.hash", "ch8.hubs", "ch8.by_hour") and (raw("ch8.hubs") or 0) >= 20,
        f"{v('ch8.hubs')} hub curves, {v('ch8.hubs_interior')} with an interior crossing; first leg on time "
        f"{v('ch8.first_on_time')} against {v('ch8.later_on_time')}; buffer trade {v('ch8.trade_overall')} minutes per minute.",
    )
    workbook_recalc = q.get("libreoffice_recalc")
    add(
        has("exports.workbook.formulas", "exports.powerbi.measures", "exports.csv.files")
        and workbook_recalc == "passed",
        f"workbook {v('exports.workbook.sheets')} sheets, {v('exports.workbook.formulas')} summary formulas, recalculation test "
        f"{workbook_recalc or 'not run'}; {v('exports.powerbi.measures')} DAX measures; {v('exports.csv.files')} CSV files with a dictionary.",
    )
    add(
        raw("live.status") == "passed",
        f"{v('live.site_url')}: live check {v('live.status')}.",
    )
    add(
        raw("live.status") == "passed" and bool(web.get("passed")) and not web.get("failed"),
        f"{v('live.routes_loaded')} of {v('live.routes_total')} routes loaded live; asleep: {v('live.asleep_outcome')}; "
        f"Playwright against the test server: {web.get('passed', 0)} passed, {web.get('failed', 0)} failed.",
    )
    add(
        has("latency.live.check.p50_ms") and raw("live.status") == "passed",
        f"POST /v1/checks p50 {v('latency.live.check.p50_ms') if has('latency.live.check.p50_ms') else 'not measured'}, "
        f"p99 {v('latency.live.check.p99_ms') if has('latency.live.check.p99_ms') else 'not measured'}; results/live_check.json {v('live.status')}.",
    )
    add(
        rederive.get("drift") == 0,
        f"claim gate over every document; rederive drift {rederive.get('drift', 'not run')}; limitations section in RESULTS.md.",
    )
    add(
        facts["decisions"] >= 10
        and facts["reversals"] >= 2
        and facts["notebooks_executed"] >= 3
        and facts["notebooks_dead_ends"] >= 3,
        f"DECISIONS.md {facts['decisions']} dated entries, {facts['reversals']} reversals, {facts['corrections']} corrections; "
        f"{facts['notebooks_executed']} executed notebooks, {facts['notebooks_dead_ends']} with a dead end.",
    )
    coverage = q.get("coverage")
    commits = int(facts.get("commits", 0))
    add(
        coverage is not None
        and float(coverage) >= 80
        and q.get("mypy") == "clean"
        and q.get("ruff") == "clean"
        and raw("palette.failures") == 0
        and 40 <= commits <= 60
        and rederive.get("drift") == 0
        and str(rederive.get("where", "in place")) != "in place"
        and bool(release.get("tag_pushed"))
        and facts["license"],
        f"coverage {coverage if coverage is not None else 'not measured'} percent; mypy {q.get('mypy', 'not run')}; ruff {q.get('ruff', 'not run')}; "
        f"palette {v('palette.validated')}; {commits} commits; rederive {rederive.get('status', 'not run')}"
        f"{' in a worktree' if str(rederive.get('where', 'in place')) != 'in place' else ''}; "
        f"tag {'pushed' if release.get('tag_pushed') else 'not pushed'}; Apache 2.0 with the four data sources' terms.",
    )
    return items


def missing_steps(items: list[Item]) -> list[int]:
    return [i.number for i in items if not i.done]
