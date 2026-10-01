"""The story's structure: chapters, the chart each one keeps on screen, and the steps it advances through.

``story/story.md`` is rendered from ``story/templates/story.md.j2`` by the claim gate, so every
number in it came from the manifest. It reads as an ordinary long Markdown document on GitHub;
the structure the site needs rides in HTML comments, which GitHub does not display:

    <!-- chapter: padding | 2 | ch2_padding -->     opens chapter 2, whose sticky chart is ch2_padding
    <!-- claim -->                                  the chapter's claim in one sentence
    <!-- step: base -->                             a paragraph; reaching it puts the chart in state "base"
    <!-- method -->                                 the method note, expanded inline
    <!-- pushback -->                               what the ops director would push back on
    <!-- /chapter -->

This module parses that file into ``story.json`` for the site, computes the reading time, and
reads the ``correction`` entries out of DECISIONS.md for the corrections log.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

WORDS_PER_MINUTE = 230
READING_PLACEHOLDER = "@@READING_MINUTES@@"

_CHAPTER_OPEN = re.compile(
    r"^<!-- chapter: (?P<id>[a-z0-9_-]+) \| (?P<number>\d+) \| (?P<chart>[a-z0-9_]+) -->$"
)
_BLOCK = re.compile(r"^<!-- (?P<kind>claim|method|pushback|step: (?P<state>[a-z0-9_-]+)) -->$")
_CHAPTER_CLOSE = "<!-- /chapter -->"
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'.,%-]*")


class StoryFormatError(ValueError):
    pass


@dataclass
class Step:
    state: str
    markdown: str
    html: str = ""


@dataclass
class Chapter:
    id: str
    number: int
    chart: str
    title: str = ""
    claim: str = ""
    claim_html: str = ""
    steps: list[Step] = field(default_factory=list)
    method_html: str = ""
    pushback_html: str = ""


@dataclass
class Story:
    title: str
    reading_minutes: int
    preamble_html: str
    chapters: list[Chapter]
    coda_html: str


def _html(markdown: str) -> str:
    from markdown_it import MarkdownIt

    return str(MarkdownIt("commonmark", {"html": False}).enable("table").render(markdown.strip()))


def reading_minutes(text: str) -> int:
    """Minutes to read the visible prose at a stated pace, rounded up; comments and markup excluded."""
    visible = _COMMENT.sub(" ", text)
    visible = re.sub(r"`[^`]*`", " ", visible)
    words = len(_WORD.findall(visible))
    if words == 0:
        raise StoryFormatError("the story has no words to time")
    return max(1, math.ceil(words / WORDS_PER_MINUTE))


def parse(text: str) -> Story:
    lines = text.splitlines()
    title = ""
    preamble: list[str] = []
    coda: list[str] = []
    chapters: list[Chapter] = []
    current: Chapter | None = None
    block_kind: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if current is None or block_kind is None:
            buffer = []
            return
        body = "\n".join(buffer).strip()
        if block_kind == "claim":
            current.claim = body.strip("*").strip()
            current.claim_html = _html(body)
        elif block_kind == "method":
            current.method_html = _html(body)
        elif block_kind == "pushback":
            current.pushback_html = _html(body)
        elif block_kind.startswith("step:"):
            state = block_kind.split(":", 1)[1].strip()
            current.steps.append(Step(state=state, markdown=body, html=_html(body)))
        elif block_kind == "heading":
            current.title = body.lstrip("#").strip()
        buffer = []

    for raw in lines:
        line = raw.rstrip()
        opened = _CHAPTER_OPEN.match(line)
        if opened:
            if current is not None:
                raise StoryFormatError(f"chapter {opened['id']} opens inside chapter {current.id}")
            current = Chapter(id=opened["id"], number=int(opened["number"]), chart=opened["chart"])
            block_kind = "heading"
            buffer = []
            continue
        if line == _CHAPTER_CLOSE:
            if current is None:
                raise StoryFormatError("a chapter closes that was never opened")
            flush()
            chapters.append(current)
            current = None
            block_kind = None
            continue
        block = _BLOCK.match(line)
        if block:
            if current is None:
                raise StoryFormatError(f"{line} sits outside a chapter")
            flush()
            block_kind = "step:" + block["state"] if block["state"] else block["kind"]
            continue
        if current is None:
            if not title and line.startswith("# "):
                title = line[2:].strip()
            elif chapters:
                coda.append(raw)
            else:
                preamble.append(raw)
            continue
        buffer.append(raw)
    if current is not None:
        raise StoryFormatError(f"chapter {current.id} is never closed")
    if not chapters:
        raise StoryFormatError("the story has no chapters")
    for chapter in chapters:
        if not chapter.claim:
            raise StoryFormatError(f"chapter {chapter.id} has no claim")
        if not chapter.steps:
            raise StoryFormatError(f"chapter {chapter.id} has no steps")
        if not chapter.method_html:
            raise StoryFormatError(f"chapter {chapter.id} has no method note")
        if not chapter.pushback_html:
            raise StoryFormatError(f"chapter {chapter.id} has no pushback paragraph")
    numbers = [c.number for c in chapters]
    if numbers != sorted(numbers) or len(set(numbers)) != len(numbers):
        raise StoryFormatError(f"chapter numbers are out of order: {numbers}")
    return Story(
        title=title,
        reading_minutes=reading_minutes(text),
        preamble_html=_html("\n".join(preamble)),
        chapters=chapters,
        coda_html=_html("\n".join(coda)),
    )


def to_json(story: Story) -> str:
    payload = asdict(story)
    for chapter in payload["chapters"]:
        for step in chapter["steps"]:
            step.pop("markdown")
    return json.dumps(payload, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def chart_ids(story: Story) -> list[str]:
    return [c.chart for c in story.chapters]


@dataclass(frozen=True)
class Correction:
    date: str
    title: str
    body: str


_DECISION_HEADING = re.compile(r"^## (?P<date>\d{4}-\d{2}-\d{2}): (?P<title>.+?)\s*$")


def corrections(decisions: Path) -> list[Correction]:
    """DECISIONS.md entries whose heading carries the ``correction`` tag, oldest first."""
    if not decisions.exists():
        return []
    found: list[Correction] = []
    heading: re.Match[str] | None = None
    body: list[str] = []
    for line in [*decisions.read_text(encoding="utf-8").splitlines(), "## 9999-12-31: end"]:
        match = _DECISION_HEADING.match(line)
        if match:
            if heading is not None and "correction" in heading["title"].lower().split(":")[0]:
                title = re.sub(r"^correction,?\s*", "", heading["title"], flags=re.I).strip()
                found.append(Correction(heading["date"], title, "\n".join(body).strip()))
            heading = match
            body = []
        elif heading is not None:
            body.append(line)
    return found


def write_story_json(story_md: Path, out: Path) -> Story:
    story = parse(story_md.read_text(encoding="utf-8"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_json(story), encoding="utf-8")
    return story
