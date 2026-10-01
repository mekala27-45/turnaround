"""Where everything lives. Resolved once from the repository root."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _find_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        marker = candidate / "pyproject.toml"
        if marker.is_file() and (candidate / "packages" / "core").is_dir():
            return candidate
    raise FileNotFoundError(f"Could not find the turnaround repository root above {start}")


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def external(self) -> Path:
        """Raw public files, fetched on a machine that can reach the hosts, never committed."""
        return self.data / "external"

    @property
    def external_bts(self) -> Path:
        return self.external / "bts"

    @property
    def external_faa(self) -> Path:
        return self.external / "faa"

    @property
    def external_weather(self) -> Path:
        return self.external / "weather"

    @property
    def flights(self) -> Path:
        """Derived flight parquet, one file per month; rebuilt by `make data`, too large to commit."""
        return self.data / "flights"

    @property
    def aircraft(self) -> Path:
        """The registry rows for the tail numbers in the flights; committed."""
        return self.data / "aircraft"

    @property
    def weather(self) -> Path:
        """Hourly weather at the FAA Core 30, committed with attribution."""
        return self.data / "weather"

    @property
    def sim(self) -> Path:
        return self.data / "sim"

    @property
    def warehouse(self) -> Path:
        return self.root / "warehouse"

    @property
    def warehouse_db(self) -> Path:
        """The DuckDB file dbt builds; rebuilt, never committed."""
        return self.root / ".cache" / "warehouse.duckdb"

    @property
    def results(self) -> Path:
        return self.root / "results"

    @property
    def manifest(self) -> Path:
        return self.results / "manifest.json"

    @property
    def marts(self) -> Path:
        """The shipped marts the site, the workbook and the BI extracts read; committed."""
        return self.results / "marts"

    @property
    def report(self) -> Path:
        return self.root / "report"

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    @property
    def story(self) -> Path:
        return self.root / "story"

    @property
    def exports(self) -> Path:
        return self.root / "exports"

    @property
    def web_data(self) -> Path:
        return self.root / "web" / "public" / "data"

    @property
    def scratch(self) -> Path:
        """Checkpoints and spill space; never an input to the rederive."""
        return self.root / ".cache"

    @property
    def logs(self) -> Path:
        return self.root / "logs"


@lru_cache(maxsize=1)
def paths() -> Paths:
    override = os.environ.get("TURNAROUND_ROOT")
    root = Path(override).resolve() if override else _find_root(Path(__file__).resolve())
    return Paths(root=root)
