"""The story parser: every chapter has a claim, steps, a method note and a pushback paragraph."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from turnaround_render.story import StoryFormatError, chart_ids, corrections, parse, reading_minutes, to_json

STORY = """# Why your flight is late

*A 3 minute read.*

The standfirst.

<!-- chapter: definition | 1 | ch1_definition -->
## 1. On time is a decision

<!-- claim -->
**On time is a definition the airline's own schedule sets.**

<!-- step: base -->
The share of flights on time by year.

<!-- step: gap -->
The gap between the two lines.

<!-- method -->
Plan hash `abc123`.

<!-- pushback -->
Schedules are realistic, not gamed.
<!-- /chapter -->

<!-- chapter: padding | 2 | ch2_padding -->
## 2. The schedule absorbed the delay

<!-- claim -->
**Padding grew.**

<!-- step: base -->
Padding by carrier.

<!-- method -->
Plan hash `def456`.

<!-- pushback -->
Congestion is real.
<!-- /chapter -->

## Corrections

None yet.
"""


def test_parse_reads_chapters_steps_and_blocks() -> None:
    story = parse(STORY)
    assert story.title == "Why your flight is late"
    assert [c.id for c in story.chapters] == ["definition", "padding"]
    first = story.chapters[0]
    assert first.title == "1. On time is a decision"
    assert first.claim == "On time is a definition the airline's own schedule sets."
    assert [s.state for s in first.steps] == ["base", "gap"]
    assert "abc123" in first.method_html
    assert "realistic" in first.pushback_html
    assert "Corrections" in story.coda_html
    assert chart_ids(story) == ["ch1_definition", "ch2_padding"]


def test_json_round_trips_without_markdown() -> None:
    payload = json.loads(to_json(parse(STORY)))
    assert payload["chapters"][1]["chart"] == "ch2_padding"
    assert "markdown" not in payload["chapters"][0]["steps"][0]


@pytest.mark.parametrize(
    ("broken", "message"),
    [
        (STORY.replace("<!-- claim -->\n**Padding grew.**\n", ""), "no claim"),
        (STORY.replace("<!-- pushback -->\nCongestion is real.\n", ""), "no pushback"),
        (STORY.replace("<!-- method -->\nPlan hash `def456`.\n", ""), "no method"),
        (STORY.replace("<!-- /chapter -->\n\n## Corrections", "\n## Corrections"), "never closed"),
        ("# Nothing here\n", "no chapters"),
    ],
)
def test_a_chapter_missing_a_part_is_rejected(broken: str, message: str) -> None:
    with pytest.raises(StoryFormatError, match=message):
        parse(broken)


def test_reading_time_ignores_comments_and_refuses_an_empty_story() -> None:
    assert reading_minutes("<!-- " + "hidden " * 1000 + "-->" + " word" * 231) == 2
    with pytest.raises(StoryFormatError):
        reading_minutes("<!-- only a comment -->")


def test_corrections_are_read_from_tagged_decisions(tmp_path: Path) -> None:
    decisions = tmp_path / "DECISIONS.md"
    decisions.write_text(
        "# Decisions\n\n## 2026-09-30: the name\n\nNot a correction.\n\n"
        "## 2026-10-01: correction, the padding chart\n\nIt said 4.1, it says 3.2.\n"
    )
    found = corrections(decisions)
    assert len(found) == 1
    assert found[0].date == "2026-10-01"
    assert found[0].title == "the padding chart"
    assert "says 3.2" in found[0].body
    assert corrections(tmp_path / "absent.md") == []
