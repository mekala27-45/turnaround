"""Runtime settings, read from the environment once."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    write_token: str
    marts: Path
    environment: str
    cors_origins: tuple[str, ...] = ()
    schema: str = ""
    """A Postgres schema for the tables, so the API shares the one free Neon database with the other
    projects' tables; empty means the default search path."""

    @property
    def token_required(self) -> bool:
        return bool(self.write_token)


def load_settings() -> Settings:
    root = Path(os.environ.get("TURNAROUND_ROOT", Path(__file__).resolve().parents[4]))
    return Settings(
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/turnaround"
        ),
        write_token=os.environ.get("TURNAROUND_WRITE_TOKEN", ""),
        marts=Path(os.environ.get("TURNAROUND_MARTS", root / "results" / "marts")),
        environment=os.environ.get("TURNAROUND_ENV", "development"),
        cors_origins=tuple(
            o.strip() for o in os.environ.get("TURNAROUND_CORS_ORIGINS", "*").split(",") if o.strip()
        ),
        schema=os.environ.get("TURNAROUND_DB_SCHEMA", "").strip(),
    )
