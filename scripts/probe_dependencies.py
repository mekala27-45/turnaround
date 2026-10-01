"""Which of the pipeline's dependencies this machine has, probed rather than assumed.

Prints one line per dependency. With --require, exits non zero when any named one is missing; CI
runs it inside the pipeline container so a missing LibreOffice or dbt fails the build instead of
turning into a skipped test.

    uv run python scripts/probe_dependencies.py
    uv run python scripts/probe_dependencies.py --require duckdb,dbt,libreoffice,postgres
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = "postgresql://postgres:postgres@127.0.0.1:5432/turnaround_test"


def _postgres() -> tuple[bool, str]:
    url = os.environ.get("TURNAROUND_TEST_DATABASE_URL", DEFAULT_DB).replace(
        "postgresql+psycopg://", "postgresql://"
    )
    try:
        import psycopg

        with psycopg.connect(url, connect_timeout=3) as conn:
            version = conn.execute("show server_version").fetchone()
        return True, f"server {version[0] if version else 'unknown'}"
    except Exception as exc:  # the reason is the answer
        return False, type(exc).__name__


def _command(*names: str, version: str = "--version") -> Callable[[], tuple[bool, str]]:
    def probe() -> tuple[bool, str]:
        for name in names:
            path = shutil.which(name)
            if path:
                out = subprocess.run([path, version], capture_output=True, text=True, timeout=60)
                lines = (out.stdout or out.stderr).strip().splitlines()
                # The first line that carries a version number; dbt opens with a bare "Core:".
                return True, next((ln.strip(" -") for ln in lines if any(c.isdigit() for c in ln)), path)
        return False, f"none of {', '.join(names)} on PATH"

    return probe


def _module(name: str) -> Callable[[], tuple[bool, str]]:
    def probe() -> tuple[bool, str]:
        found = importlib.util.find_spec(name) is not None
        return found, "importable" if found else "not installed"

    return probe


def _files(pattern: str, what: str) -> Callable[[], tuple[bool, str]]:
    def probe() -> tuple[bool, str]:
        found = sorted(ROOT.glob(pattern))
        return bool(found), f"{len(found)} {what}"

    return probe


def _weather() -> tuple[bool, str]:
    folder = ROOT / "data" / "weather"
    ok = (folder / "hourly.parquet").exists() and (folder / "ATTRIBUTION.md").exists()
    return ok, "hourly.parquet with its attribution" if ok else "missing or written without its attribution"


PROBES: dict[str, Callable[[], tuple[bool, str]]] = {
    "postgres": _postgres,
    "libreoffice": _command("soffice", "libreoffice"),
    "dbt": _command("dbt"),
    "node": _command("node"),
    "duckdb": _module("duckdb"),
    "external": _files("data/external/bts/*.zip", "monthly files"),
    "derived": _files("data/flights/flights_*.parquet", "derived months"),
    "weather": _weather,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require", default="", help="comma separated names that must be present")
    args = parser.parse_args()
    required = [r for r in args.require.split(",") if r]
    unknown = [r for r in required if r not in PROBES]
    if unknown:
        parser.error(f"unknown dependencies {unknown}; choose from {sorted(PROBES)}")
    missing = []
    for name, probe in PROBES.items():
        ok, detail = probe()
        mark = "present" if ok else "missing"
        print(f"{name:12} {mark:8} {detail}")
        if not ok and name in required:
            missing.append(name)
    if missing:
        print(f"required but missing: {', '.join(missing)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
