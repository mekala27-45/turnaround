"""Stage: the data the site reads, under web/public/data.

The site is static. Everything it draws comes from files written here from the results the earlier
stages produced: the merged manifest, the story parsed into story.json, every chart specification,
the marts the explorer queries with DuckDB in the browser, the hub curves, and bundle.json (the file
list with byte sizes, so the browser never needs a HEAD request, which the host and the test server
both refuse). No row about a traveler exists to copy, and the identifier scan reads this folder.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from turnaround_core.manifest import Manifest
from turnaround_core.paths import Paths
from turnaround_core.statements import STATEMENT
from turnaround_render.story import write_story_json

EXPLORER_MARTS = (
    "mart_route_month",
    "mart_carrier_month",
    "mart_delay_histogram",
    "mart_hour_profile",
    "mart_leg_position",
    "mart_quarantine",
    "mart_carrier_day",
    "mart_airport_day",
    "mart_inherited_month",
    "rotation_samples",
    "rotation_worst_days",
)


def briefing_sections(text: str) -> dict[str, object]:
    """The rendered briefing split into its sections for the report page: the title, the opening, and
    each section's heading, HTML and the chart it carries (a <!-- chart: id --> marker)."""
    import re

    from markdown_it import MarkdownIt

    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    lines = text.splitlines()
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("# ") else ""
    sections: list[dict[str, object]] = []
    intro: list[str] = []
    current: dict[str, object] | None = None
    body: list[str] = []

    def close() -> None:
        if current is not None:
            raw = "\n".join(body)
            found = re.search(r"<!-- chart: ([a-z_]+) -->", raw)
            current["chart"] = found.group(1) if found else None
            current["html"] = str(md.render(re.sub(r"<!--.*?-->", "", raw).strip()))
            sections.append(current)

    for line in lines[1:]:
        if line.startswith("## "):
            close()
            heading = line[3:].strip()
            current = {"id": re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-"), "title": heading}
            body = []
        elif current is None:
            intro.append(line)
        else:
            body.append(line)
    close()
    return {"title": title, "intro_html": str(md.render("\n".join(intro).strip())), "sections": sections}


def run(p: Paths) -> dict[str, int]:
    out = p.root / "web" / "public" / "data"
    if out.exists():
        for child in out.iterdir():
            if child.name == "recorded_session.json":
                continue  # written by scripts/record_session.py against a running API
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    out.mkdir(parents=True, exist_ok=True)
    manifest = Manifest.load(p.manifest)
    shutil.copy(p.manifest, out / "manifest.json")
    story_md = p.root / "story" / "story.md"
    if story_md.exists():
        write_story_json(story_md, out / "story.json")
    briefing_md = p.root / "report" / "briefing.md"
    if briefing_md.exists():
        payload = briefing_sections(briefing_md.read_text(encoding="utf-8"))
        (out / "briefing.json").write_text(
            json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    charts = sorted((p.results / "charts").glob("*.json"))
    (out / "charts").mkdir(exist_ok=True)
    for chart in charts:
        shutil.copy(chart, out / "charts" / chart.name)
    (out / "marts").mkdir(exist_ok=True)
    files: dict[str, int] = {}
    for name in EXPLORER_MARTS:
        src = p.marts / f"{name}.parquet"
        if src.exists():
            dst = out / "marts" / f"{name}.parquet"
            shutil.copy(src, dst)
            files[f"marts/{name}.parquet"] = dst.stat().st_size
    for extra in ("hub_curves.json",):
        src = p.results / "chapters" / extra
        if src.exists():
            shutil.copy(src, out / extra)
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.suffix in {".json", ".parquet"}:
            files.setdefault(path.relative_to(out).as_posix(), path.stat().st_size)
    bundle = {
        "statement": STATEMENT,
        "as_of": manifest.as_of,
        "written_at": datetime.now(UTC).date().isoformat(),
        "charts": [c.stem for c in charts],
        "files": dict(sorted(files.items())),
        "api": str(manifest.values["deploy.base_url"].value) if "deploy.base_url" in manifest.values else "",
    }
    (out / "bundle.json").write_text(json.dumps(bundle, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {"files": len(files), "charts": len(charts)}


def written(root: Path) -> list[Path]:
    return sorted((root / "web" / "public" / "data").rglob("*"))
