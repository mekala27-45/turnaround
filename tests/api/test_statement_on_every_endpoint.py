"""Every route the API serves answers with the statement in its body, on success and on failure.
The routes are read from the application itself, so a route added later without the statement, or
without a case here, fails this test."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from turnaround_api.app import create_app
from turnaround_core.statements import STATEMENT

from tests.api.conftest import a_connection

pytestmark = pytest.mark.postgres


def served_routes() -> set[tuple[str, str]]:
    app = create_app()
    return {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/v1/")
        for method in route.methods
        if method in {"GET", "POST"}
    }


def calls(client: TestClient, auth: dict[str, str]) -> dict[tuple[str, str], list[Any]]:
    """For each route, a request that succeeds and one that fails, as (status, body) pairs."""
    body = a_connection(client)
    query = {k: v for k, v in body.items() if k != "buffer_minutes"}
    created = client.post("/v1/checks", json=body, headers=auth)
    check_id = created.json()["check_id"]
    return {
        ("GET", "/v1/health"): [client.get("/v1/health")],
        ("GET", "/v1/hubs"): [client.get("/v1/hubs")],
        ("GET", "/v1/curve"): [
            client.get("/v1/curve", params=query),
            client.get("/v1/curve", params={**query, "inbound_hour": 99}),
        ],
        ("POST", "/v1/checks"): [created, client.post("/v1/checks", json=body)],
        ("GET", "/v1/checks"): [client.get("/v1/checks")],
        ("GET", "/v1/checks/{check_id}"): [
            client.get(f"/v1/checks/{check_id}"),
            client.get("/v1/checks/no-such-check"),
        ],
        ("POST", "/v1/score"): [
            client.post("/v1/score", json={}, headers=auth),
            client.post("/v1/score", json={}),
        ],
        ("GET", "/v1/scorecard"): [client.get("/v1/scorecard")],
        ("GET", "/v1/audit"): [client.get("/v1/audit")],
    }


def test_every_route_carries_the_statement_on_success_and_failure(
    client: TestClient, auth: dict[str, str]
) -> None:
    made = calls(client, auth)
    assert set(made) == served_routes(), "a route was added or removed: add its case here"
    missing = []
    statuses: set[int] = set()
    for (method, path), responses in made.items():
        for response in responses:
            statuses.add(response.status_code)
            if response.json().get("statement") != STATEMENT:
                missing.append(f"{method} {path} -> {response.status_code}")
    assert missing == []
    # The failures above really failed: a validation error, a missing token and an unknown id.
    assert {401, 404, 422} <= statuses
