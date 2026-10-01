"""What every stage shares: the as of date, the partial manifest location, and a DuckDB connection."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import duckdb
from turnaround_core.config import POLICY
from turnaround_core.manifest import Manifest
from turnaround_core.paths import Paths

DEMONSTRATION_SEED = POLICY.seed


def as_of() -> str:
    return os.environ.get("TURNAROUND_AS_OF", dt.date.today().isoformat())


def partial_path(p: Paths, stage: str) -> Path:
    return p.results / stage / "manifest.json"


def new_partial(stage: str) -> Manifest:
    return Manifest(as_of=as_of(), seed=DEMONSTRATION_SEED)


def save_partial(p: Paths, stage: str, manifest: Manifest) -> Path:
    out = partial_path(p, stage)
    manifest.save(out)
    return out


def connect(
    p: Paths, *, memory_limit: str = "5GB", threads: int = 2, read_only: bool = False
) -> duckdb.DuckDBPyConnection:
    """A connection with the memory limit below physical memory, so DuckDB spills instead of dying."""
    p.scratch.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("set enable_progress_bar = false")
    con.execute(f"set memory_limit = '{memory_limit}'")
    con.execute(f"set threads = {threads}")
    con.execute(f"set temp_directory = '{(p.scratch / 'duckdb_tmp').as_posix()}'")
    con.execute("set preserve_insertion_order = false")
    return con


def flights_glob(p: Paths) -> str:
    return (p.flights / "flights_*.parquet").as_posix()
