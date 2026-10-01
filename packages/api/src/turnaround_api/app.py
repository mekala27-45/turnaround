"""The turnaround API: the misconnect calculator and its check log.

``GET /v1/curve`` answers for one connection at every buffer from 0 to 180 minutes, read only.
``POST /v1/checks`` takes an origin, a connecting airport, a destination, a travel month, a scheduled
inbound arrival hour, a scheduled outbound departure hour and a buffer, computes the historical
misconnect probability with its interval and the flights it rests on, writes the check row, then the
audit row, then returns the id. ``GET /v1/checks/{id}`` returns it with its score if any.
``POST /v1/score`` scores every stored check whose travel month is the outcome month the committed
marts hold, against what happened on that connection that month, and reports the share still
unscored. Writes need the token; this is a demonstration and the README says so. Every response body
carries the statement. Every write goes: the row, then the audit row, then commit, then the response.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any

import polars as pl
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException
from turnaround_core.config import POLICY
from turnaround_core.statements import STATEMENT
from turnaround_misconnect import marts as misconnect_marts
from turnaround_misconnect.model import Cells, Estimate, UnknownConnection, realized

from turnaround_api.db import AuditEntry, Check, CheckScore, make_async_engine
from turnaround_api.settings import Settings, load_settings

log = logging.getLogger("turnaround_api")
# Real airports are three letter IATA codes; the simulator's hubs are two characters, and the tests
# drive the API with them, so the shape check allows two to four.
AIRPORT = re.compile(r"^[A-Z0-9]{2,4}$")
MONTH = re.compile(r"^(20[0-9]{2})-(0[1-9]|1[0-2])$")
CURVE_BUFFERS = tuple(range(0, 185, 5))


def envelope(data: dict[str, Any]) -> dict[str, Any]:
    return {**data, "statement": STATEMENT, "served_at": datetime.now(UTC).isoformat()}


class CheckIn(BaseModel):
    origin: str = Field(min_length=2, max_length=4)
    connection: str = Field(min_length=2, max_length=4)
    destination: str = Field(min_length=2, max_length=4)
    travel_month: str = Field(min_length=7, max_length=7, description="YYYY-MM")
    inbound_hour: int = Field(ge=0, le=23)
    outbound_hour: int = Field(ge=0, le=23)
    buffer_minutes: int = Field(ge=0, le=360)
    note: str = Field(default="", max_length=60)

    @field_validator("origin", "connection", "destination")
    @classmethod
    def airport(cls, value: str) -> str:
        value = value.upper()
        if not AIRPORT.match(value):
            raise ValueError("an airport is a three letter code")
        return value

    @field_validator("travel_month")
    @classmethod
    def month(cls, value: str) -> str:
        if not MONTH.match(value):
            raise ValueError("the travel month is YYYY-MM")
        return value

    @field_validator("note")
    @classmethod
    def plain_note(cls, value: str) -> str:
        # A note labels where a check came from (demo, persistence check); it is not a place for a
        # name or a booking reference, so it is held to a short word list of plain characters.
        if value and not re.fullmatch(r"[a-z ]{1,60}", value):
            raise ValueError("a note is lower case words")
        return value


class ScoreIn(BaseModel):
    note: str = Field(default="", max_length=60)


class Served:
    """The committed marts, loaded once, with a version that is the digest of their bytes."""

    def __init__(self, settings: Settings) -> None:
        self.cells: Cells | None = None
        self.outcomes: pl.DataFrame | None = None
        self.version = "none"
        self.outcome_month: str | None = None
        self.hubs: list[str] = []
        self.routes: pl.DataFrame | None = None
        paths = [settings.marts / f"{name}.parquet" for name in misconnect_marts.FILES]
        if not all(p.exists() for p in paths):
            log.warning("the calculator marts are missing under %s", settings.marts)
            return
        digest = hashlib.sha256()
        for p in paths:
            digest.update(p.read_bytes())
        self.version = f"cells-{digest.hexdigest()[:10]}"
        frames = misconnect_marts.load(settings.marts)
        self.cells = Cells.from_frames(
            frames["misconnect_cells"],
            frames["misconnect_lost"],
            frames["misconnect_routes"],
            frames["misconnect_hubs"],
        )
        self.outcomes = frames["misconnect_outcomes"]
        self.routes = frames["misconnect_routes"]
        self.hubs = self.cells.hubs
        first = self.outcomes["flight_date"].min() if self.outcomes.height else None
        self.outcome_month = first.strftime("%Y-%m") if first is not None else None  # type: ignore[union-attr]


class AppState:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine: AsyncEngine = make_async_engine(settings.database_url, settings.schema)
        self.served = Served(settings)


def state_of(request: Request) -> AppState:
    state: AppState = request.app.state.turnaround
    return state


async def session_of(request: Request) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(state_of(request).engine, expire_on_commit=False) as session:
        yield session


def actor_of(request: Request, authorization: Annotated[str | None, Header()] = None) -> str:
    settings = state_of(request).settings
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if settings.token_required and token == settings.write_token:
            return "token"
    return "anonymous"


SessionDep = Annotated[AsyncSession, Depends(session_of)]
ActorDep = Annotated[str, Depends(actor_of)]


def require_writer(actor: str) -> None:
    if actor != "token":
        raise HTTPException(status_code=401, detail="writes need the token")


def require_cells(state: AppState) -> Cells:
    if state.served.cells is None:
        raise HTTPException(status_code=503, detail="the calculator marts are not on this server")
    return state.served.cells


async def audit(
    session: AsyncSession,
    actor: str,
    action: str,
    resource: str,
    resource_id: str = "",
    detail: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditEntry(
            actor=actor, action=action, resource=resource, resource_id=resource_id, detail=detail or {}
        )
    )
    await session.commit()


def _estimate(cells: Cells, body: CheckIn, buffer: int) -> Estimate:
    try:
        return cells.estimate(
            origin=body.origin,
            hub=body.connection,
            destination=body.destination,
            month=int(body.travel_month[5:7]),
            inbound_hour=body.inbound_hour,
            outbound_hour=body.outbound_hour,
            buffer=buffer,
            min_connection=POLICY.min_connection_minutes,
        )
    except UnknownConnection as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _estimate_payload(e: Estimate) -> dict[str, Any]:
    return {
        "probability": e.probability,
        "low": e.low,
        "high": e.high,
        "flights": e.flights,
        "inbound_flights": e.inbound_flights,
        "outbound_flights": e.outbound_flights,
        "level": e.level,
        "correlation_ratio": e.correlation_ratio,
        "lost_share": e.lost_share,
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.turnaround = AppState(settings)
        yield
        await app.state.turnaround.engine.dispose()

    app = FastAPI(title="turnaround", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins) or ["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=envelope({"error": str(exc.detail)}))

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        problems = [
            {"field": ".".join(str(p) for p in e.get("loc", ())), "message": e.get("msg", "")}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422, content=envelope({"error": "invalid request", "detail": problems})
        )

    @app.get("/v1/health")
    async def health(request: Request, session: SessionDep) -> dict[str, Any]:
        state = state_of(request)
        database = "ok"
        try:
            await session.exec(select(Check.id).limit(1))
        except Exception as exc:  # the reason goes to the server log, never to the client
            log.warning("health: the database is unreachable: %s: %s", type(exc).__name__, exc)
            database = "unreachable"
        return envelope(
            {
                "status": "ok",
                "environment": state.settings.environment,
                "database": database,
                "model_version": state.served.version,
                "hubs": len(state.served.hubs),
                "outcome_month": state.served.outcome_month,
                "min_connection_minutes": POLICY.min_connection_minutes,
                "writes": "token gated",
            }
        )

    @app.get("/v1/hubs")
    async def hubs(request: Request) -> dict[str, Any]:
        state = state_of(request)
        require_cells(state)
        routes = state.served.routes
        assert routes is not None
        out = []
        for hub in state.served.hubs:
            inbound = routes.filter((pl.col("direction") == "in") & (pl.col("dest") == hub))
            outbound = routes.filter((pl.col("direction") == "out") & (pl.col("origin") == hub))
            out.append(
                {
                    "hub": hub,
                    "origins": sorted(inbound["origin"].unique().to_list()),
                    "destinations": sorted(outbound["dest"].unique().to_list()),
                }
            )
        return envelope({"hubs": out, "model_version": state.served.version})

    @app.get("/v1/curve")
    async def curve(
        request: Request,
        origin: Annotated[str, Query(min_length=2, max_length=4)],
        connection: Annotated[str, Query(min_length=2, max_length=4)],
        destination: Annotated[str, Query(min_length=2, max_length=4)],
        travel_month: Annotated[str, Query(min_length=7, max_length=7)],
        inbound_hour: Annotated[int, Query(ge=0, le=23)],
        outbound_hour: Annotated[int, Query(ge=0, le=23)],
    ) -> dict[str, Any]:
        state = state_of(request)
        cells = require_cells(state)
        body = CheckIn(
            origin=origin,
            connection=connection,
            destination=destination,
            travel_month=travel_month,
            inbound_hour=inbound_hour,
            outbound_hour=outbound_hour,
            buffer_minutes=0,
        )
        points = [{"buffer": b, **_estimate_payload(_estimate(cells, body, b))} for b in CURVE_BUFFERS]
        crossing = next((p["buffer"] for p in points if p["probability"] <= POLICY.misconnect_line), None)
        return envelope(
            {
                "origin": body.origin,
                "connection": body.connection,
                "destination": body.destination,
                "travel_month": body.travel_month,
                "inbound_hour": inbound_hour,
                "outbound_hour": outbound_hour,
                "line": POLICY.misconnect_line,
                "crossing": crossing,
                "points": points,
                "model_version": state.served.version,
            }
        )

    @app.post("/v1/checks", status_code=201)
    async def create_check(
        body: CheckIn, request: Request, session: SessionDep, actor: ActorDep
    ) -> dict[str, Any]:
        require_writer(actor)
        state = state_of(request)
        cells = require_cells(state)
        e = _estimate(cells, body, body.buffer_minutes)
        row = Check(
            check_id=str(uuid.uuid4()),
            origin=body.origin,
            connection=body.connection,
            destination=body.destination,
            travel_month=body.travel_month,
            inbound_hour=body.inbound_hour,
            outbound_hour=body.outbound_hour,
            buffer_minutes=body.buffer_minutes,
            probability=e.probability,
            low=e.low,
            high=e.high,
            flights=e.flights,
            level=e.level,
            model_version=state.served.version,
            note=body.note,
        )
        session.add(row)
        await session.flush()
        await audit(
            session,
            actor,
            "create",
            "check",
            row.check_id,
            {
                "connection": row.connection,
                "travel_month": row.travel_month,
                "model_version": row.model_version,
            },
        )
        return envelope({"check_id": row.check_id, **_check_payload(row), **_estimate_payload(e)})

    @app.get("/v1/checks")
    async def list_checks(
        session: SessionDep, connection: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        query = select(Check).order_by(col(Check.created_at).desc()).limit(min(max(limit, 1), 500))
        if connection:
            query = query.where(Check.connection == connection.upper())
        rows = (await session.exec(query)).all()
        return envelope({"checks": [_check_payload(r) for r in rows]})

    @app.get("/v1/checks/{check_id}")
    async def get_check(check_id: str, session: SessionDep) -> dict[str, Any]:
        row = (await session.exec(select(Check).where(Check.check_id == check_id))).first()
        if row is None:
            raise HTTPException(status_code=404, detail="no check with that id")
        score = (await session.exec(select(CheckScore).where(CheckScore.check_id == check_id))).first()
        return envelope({**_check_payload(row), "score": _score_payload(score) if score else None})

    @app.post("/v1/score")
    async def score(body: ScoreIn, request: Request, session: SessionDep, actor: ActorDep) -> dict[str, Any]:
        require_writer(actor)
        state = state_of(request)
        require_cells(state)
        outcomes = state.served.outcomes
        month = state.served.outcome_month
        checks = (await session.exec(select(Check))).all()
        scored_ids = {s.check_id for s in (await session.exec(select(CheckScore))).all()}
        added = 0
        no_pairs = 0
        for c in checks:
            if c.check_id in scored_ids or month is None or outcomes is None or c.travel_month != month:
                continue
            result = realized(
                outcomes,
                origin=c.origin,
                hub=c.connection,
                destination=c.destination,
                inbound_hour=c.inbound_hour,
                outbound_hour=c.outbound_hour,
                buffer=c.buffer_minutes,
                min_connection=POLICY.min_connection_minutes,
            )
            if result is None:
                no_pairs += 1
                continue
            rate, pairs = result
            session.add(
                CheckScore(
                    check_id=c.check_id,
                    outcome_month=month,
                    realized_rate=rate,
                    pairs=pairs,
                    absolute_error=abs(c.probability - rate),
                    inside_interval=c.low <= rate <= c.high,
                )
            )
            added += 1
        await session.flush()
        total = len(checks)
        scored = len(scored_ids) + added
        unscored_share = 1.0 - scored / total if total else 1.0
        await audit(
            session,
            actor,
            "score",
            "check",
            "",
            {"scored": added, "no_pairs": no_pairs, "outcome_month": month, "unscored_share": unscored_share},
        )
        return envelope(
            {
                "scored": added,
                "checks": total,
                "no_pairs": no_pairs,
                "outcome_month": month,
                "unscored_share": unscored_share,
            }
        )

    @app.get("/v1/scorecard")
    async def scorecard(session: SessionDep) -> dict[str, Any]:
        checks = (await session.exec(select(Check))).all()
        scores = (await session.exec(select(CheckScore))).all()
        return envelope(
            {
                "checks": len(checks),
                "scored": len(scores),
                "unscored_share": 1.0 - len(scores) / len(checks) if checks else 1.0,
                "mean_absolute_error": sum(s.absolute_error for s in scores) / len(scores)
                if scores
                else None,
                "interval_coverage": sum(1 for s in scores if s.inside_interval) / len(scores)
                if scores
                else None,
            }
        )

    @app.get("/v1/audit")
    async def audit_log(session: SessionDep, limit: int = 100) -> dict[str, Any]:
        rows = (
            await session.exec(
                select(AuditEntry).order_by(col(AuditEntry.at).desc()).limit(min(max(limit, 1), 500))
            )
        ).all()
        return envelope(
            {
                "entries": [
                    {
                        "at": r.at.isoformat(),
                        "actor": r.actor,
                        "action": r.action,
                        "resource": r.resource,
                        "resource_id": r.resource_id,
                        "detail": r.detail,
                    }
                    for r in rows
                ]
            }
        )

    return app


def _check_payload(row: Check) -> dict[str, Any]:
    return {
        "check_id": row.check_id,
        "origin": row.origin,
        "connection": row.connection,
        "destination": row.destination,
        "travel_month": row.travel_month,
        "inbound_hour": row.inbound_hour,
        "outbound_hour": row.outbound_hour,
        "buffer_minutes": row.buffer_minutes,
        "probability": row.probability,
        "low": row.low,
        "high": row.high,
        "flights": row.flights,
        "level": row.level,
        "model_version": row.model_version,
        "note": row.note,
        "created_at": row.created_at.isoformat(),
    }


def _score_payload(s: CheckScore) -> dict[str, Any]:
    return {
        "outcome_month": s.outcome_month,
        "realized_rate": s.realized_rate,
        "pairs": s.pairs,
        "absolute_error": s.absolute_error,
        "inside_interval": s.inside_interval,
        "scored_at": s.scored_at.isoformat(),
    }
