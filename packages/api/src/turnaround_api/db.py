"""What the calculator persists across a request boundary: the checks, their scores and the audit
log. Every table is observed from an independently opened connection in the tests, because a test
that shares the application's session cannot see a missing commit (Day 5 of this series found
exactly that bug). No table has a column for a person: a check is airports, hours, a month and a
buffer, and the planted identifier scan holds the log to that."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import Field, Session, SQLModel, create_engine, select


def now() -> datetime:
    return datetime.now(UTC)


class Check(SQLModel, table=True):
    __tablename__ = "checks"
    id: int | None = Field(default=None, primary_key=True)
    check_id: str = Field(index=True, unique=True)
    origin: str
    connection: str = Field(index=True)
    destination: str
    travel_month: str = Field(index=True)
    inbound_hour: int
    outbound_hour: int
    buffer_minutes: int
    probability: float
    low: float
    high: float
    flights: int
    level: str
    model_version: str
    note: str = ""
    created_at: datetime = Field(default_factory=now)


class CheckScore(SQLModel, table=True):
    __tablename__ = "check_scores"
    id: int | None = Field(default=None, primary_key=True)
    check_id: str = Field(foreign_key="checks.check_id", index=True, unique=True)
    outcome_month: str
    realized_rate: float
    pairs: int
    absolute_error: float
    inside_interval: bool
    scored_at: datetime = Field(default_factory=now)


class AuditEntry(SQLModel, table=True):
    __tablename__ = "audit_log"
    id: int | None = Field(default=None, primary_key=True)
    at: datetime = Field(default_factory=now, index=True)
    actor: str
    action: str
    resource: str
    resource_id: str = ""
    detail: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


def schema_options(schema: str = "") -> dict[str, Any]:
    """With a schema, every table name the engine emits is qualified with it, so the tables live
    there whatever the connection's search path says (the hosted database's proxy drops a search
    path set through the startup options, which Day 13's first deploy found)."""
    if not schema:
        return {}
    return {"schema_translate_map": {None: schema}}


def make_async_engine(url: str, schema: str = "") -> AsyncEngine:
    engine = create_async_engine(url, pool_pre_ping=True)
    return engine.execution_options(**schema_options(schema)) if schema else engine


def make_engine(url: str, schema: str = "") -> Any:
    engine = create_engine(url, pool_pre_ping=True)
    return engine.execution_options(**schema_options(schema)) if schema else engine


def ensure_schema(url: str, schema: str) -> None:
    if not schema:
        return
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(text(f'create schema if not exists "{schema}"'))
    engine.dispose()


def create_all(engine: Any) -> None:
    SQLModel.metadata.create_all(engine)


def reset_notes(engine: Any, notes: tuple[str, ...]) -> dict[str, int]:
    """Delete the checks the demo recording and the persistence checks made, by their stated notes,
    with their scores; the audit log is left alone, so the deletion itself stays on the record."""
    counts = {"checks": 0, "scores": 0}
    with Session(engine) as session:
        checks = session.exec(select(Check).where(Check.note.in_(notes))).all()  # type: ignore[attr-defined]
        for c in checks:
            for score in session.exec(select(CheckScore).where(CheckScore.check_id == c.check_id)).all():
                session.delete(score)
                counts["scores"] += 1
            session.delete(c)
            counts["checks"] += 1
        session.add(
            AuditEntry(
                actor="operator", action="reset", resource="check", detail={"notes": list(notes), **counts}
            )
        )
        session.commit()
    return counts
