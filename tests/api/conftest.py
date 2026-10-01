"""API fixtures: a real Postgres, calculator marts built from a simulated network, and a client.

Every test that checks persistence reads back through a psycopg connection opened for the purpose,
never through the application's session: a shared session cannot see a missing commit, which is the
bug Day 5 of this series found and every day since has tested for.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import psycopg
import pytest
from fastapi.testclient import TestClient
from turnaround_api.app import create_app
from turnaround_api.db import SQLModel, make_engine
from turnaround_api.settings import Settings
from turnaround_misconnect import marts
from turnaround_misconnect.curve import curves
from turnaround_sim.network import SimSpec, simulate

from tests._deps import need

TOKEN = "test-token-not-a-secret"
DEFAULT_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/turnaround_test"
HUBS = ("H0", "H1", "H2", "H3")


def _url() -> str:
    return os.environ.get("TURNAROUND_TEST_DATABASE_URL", DEFAULT_URL)


def plain_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://")


def rows(url: str, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    """Read through a connection this call opens and closes: independent of the app's session."""
    with psycopg.connect(plain_url(url)) as conn, conn.cursor() as cur:
        cur.execute(sql, params)  # type: ignore[arg-type]
        return list(cur.fetchall())


PREDICT = "year * 100 + month < 202312"


def build_sim_marts(out: Path, seed: int = 8) -> None:
    """Calculator marts from two simulated years: cells from everything before December 2023, which
    is the outcome month, the way the real marts hold out the latest published month."""
    sim = simulate(SimSpec(seed=seed, days=730, start="2022-01-01", meltdown_day=600))
    con = duckdb.connect()
    con.register("f", sim.flights.to_arrow())
    found = curves(
        con, "f", hubs=list(HUBS), where=PREDICT, min_connection=25, line=0.10, replicates=60, seed=1
    )
    marts.build(con, "f", hubs=list(HUBS), where=PREDICT, outcome=(2023, 12), curves=found, out_dir=out)
    con.close()


@pytest.fixture(scope="session")
def database_url() -> str:
    url = _url()
    try:
        with psycopg.connect(plain_url(url), connect_timeout=3):
            pass
    except psycopg.OperationalError:
        need("postgres", False, f"no Postgres answers at {url}")
    return url


@pytest.fixture(scope="session")
def sim_marts(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("calculator_marts")
    build_sim_marts(out)
    return out


@pytest.fixture()
def clean_db(database_url: str) -> str:
    engine = make_engine(database_url)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    return database_url


@pytest.fixture()
def settings(clean_db: str, sim_marts: Path) -> Settings:
    return Settings(database_url=clean_db, write_token=TOKEN, marts=sim_marts, environment="test")


@pytest.fixture()
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture()
def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def a_connection(client: TestClient, hub: str = "H0") -> dict[str, Any]:
    """The first origin and destination the hub lists, for the outcome month (December)."""
    listed = {h["hub"]: h for h in client.get("/v1/hubs").json()["hubs"]}
    entry = listed[hub]
    return {
        "origin": entry["origins"][0],
        "connection": hub,
        "destination": entry["destinations"][0],
        "travel_month": "2023-12",
        "inbound_hour": 12,
        "outbound_hour": 13,
        "buffer_minutes": 60,
    }
