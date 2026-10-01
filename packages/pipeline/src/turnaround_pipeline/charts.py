"""Chart specifications: what the site draws, written by the stage that computed the numbers.

Each chart is one JSON file under results/charts, named by its id, carrying its one message (the title),
its conventional subtitle, the provenance label, the SQL behind it, the panels with their series and
annotations, the states the story advances through as the reader scrolls, and the table the table
toggle shows. The message is the manifest's figure title for chart.<id>, so the site and the documents
print the same sentence.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Roles map to the palette in web/src/theme/palette.json: ink is the actual, delay is vermilion
# (slot one), early is blue (slot two), adjusted is slot three, control is the control gray, and cat4
# to cat8 are the remaining categorical slots in their committed order.
ROLES = ("ink", "delay", "early", "adjusted", "control", "cat4", "cat5", "cat6", "cat7", "cat8")


def _clean(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(f"{value:.6g}")
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_clean(v) for v in value]
    return value


@dataclass
class Series:
    name: str
    role: str
    points: list[tuple[Any, float | None]]
    low: Sequence[float | None] | None = None
    high: Sequence[float | None] | None = None
    dashed: bool = False
    label: str | None = None

    def __post_init__(self) -> None:
        if self.role not in ROLES:
            raise ValueError(f"unknown role {self.role!r}")


@dataclass
class Annotation:
    x: Any
    y: float | None
    text: str
    state: str | None = None


@dataclass
class Panel:
    title: str
    series: list[Series]
    annotations: list[Annotation] = field(default_factory=list)
    rules: list[dict[str, Any]] = field(default_factory=list)
    bands: list[dict[str, Any]] = field(default_factory=list)
    y_label: str | None = None
    y_format: str | None = None


@dataclass
class State:
    id: str
    caption: str
    highlight: list[str] = field(default_factory=list)
    show: list[str] = field(default_factory=list)


@dataclass
class Chart:
    id: str
    kind: str
    message: str
    subtitle: str
    source: str
    sql: str
    x_label: str
    x_format: str
    y_label: str
    y_format: str
    panels: list[Panel]
    states: list[State]
    table_columns: list[str]
    table_rows: list[list[Any]]
    notes: list[str] = field(default_factory=list)

    def write(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.id}.json"
        payload = _clean(asdict(self))
        path.write_text(
            json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return path


def rows(frame_rows: Sequence[dict[str, Any]], columns: Sequence[str]) -> list[list[Any]]:
    return [[r[c] for c in columns] for r in frame_rows]
