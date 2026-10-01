"""The check log, observed from outside the application's session."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from turnaround_core.statements import STATEMENT

from tests.api.conftest import a_connection, rows

pytestmark = pytest.mark.postgres


def test_check_is_committed(client: TestClient, auth: dict[str, str], clean_db: str) -> None:
    body = a_connection(client)
    response = client.post("/v1/checks", json={**body, "note": "test"}, headers=auth)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["statement"] == STATEMENT
    assert 0.0 <= created["low"] <= created["probability"] <= created["high"] <= 1.0
    stored = rows(
        clean_db,
        "select origin, connection, destination, travel_month, buffer_minutes, probability, model_version "
        "from checks where check_id = %s",
        (created["check_id"],),
    )
    assert stored == [
        (
            body["origin"],
            "H0",
            body["destination"],
            "2023-12",
            60,
            pytest.approx(created["probability"]),
            created["model_version"],
        )
    ]


def test_score_is_committed(client: TestClient, auth: dict[str, str], clean_db: str) -> None:
    created = client.post("/v1/checks", json=a_connection(client), headers=auth).json()
    later = client.post(
        "/v1/checks", json={**a_connection(client), "travel_month": "2027-03"}, headers=auth
    ).json()
    scored = client.post("/v1/score", json={"note": "test"}, headers=auth)
    assert scored.status_code == 200, scored.text
    body = scored.json()
    assert body["checks"] == 2 and body["outcome_month"] == "2023-12"
    stored = rows(
        clean_db,
        "select outcome_month, realized_rate, pairs, absolute_error, inside_interval from check_scores where check_id = %s",
        (created["check_id"],),
    )
    assert len(stored) == 1
    month, rate, pairs, error, _ = stored[0]
    assert month == "2023-12" and 0.0 <= rate <= 1.0 and pairs > 0
    assert error == pytest.approx(abs(created["probability"] - rate))
    assert rows(clean_db, "select count(*) from check_scores where check_id = %s", (later["check_id"],)) == [
        (0,)
    ]
    assert body["unscored_share"] == pytest.approx(0.5)
    again = client.post("/v1/score", json={}, headers=auth).json()
    assert again["scored"] == 0, "scoring is idempotent: nothing is scored twice"
    read = client.get(f"/v1/checks/{created['check_id']}").json()
    assert read["score"]["pairs"] == pairs


def test_audit_precedes_response(client: TestClient, auth: dict[str, str], clean_db: str) -> None:
    response = client.post("/v1/checks", json=a_connection(client), headers=auth)
    served_at = datetime.fromisoformat(response.json()["served_at"])
    audit = rows(clean_db, "select at, action, resource_id, actor from audit_log order by at")
    assert len(audit) == 1
    at, action, resource_id, actor = audit[0]
    assert action == "create" and actor == "token"
    assert resource_id == response.json()["check_id"]
    assert at <= served_at, "the audit row was committed before the response was built"


def test_writes_need_the_token(client: TestClient, clean_db: str) -> None:
    response = client.post("/v1/checks", json=a_connection(client))
    assert response.status_code == 401
    assert response.json()["statement"] == STATEMENT
    assert rows(clean_db, "select count(*) from checks") == [(0,)]
    assert rows(clean_db, "select count(*) from audit_log") == [(0,)]
    assert client.post("/v1/score", json={}).status_code == 401


def test_curve_is_monotone_and_names_the_crossing(client: TestClient) -> None:
    body = a_connection(client)
    params = {k: v for k, v in body.items() if k != "buffer_minutes"}
    curve = client.get("/v1/curve", params=params).json()
    probs = [p["probability"] for p in curve["points"]]
    assert len(probs) == 37
    assert all(b <= a + 1e-9 for a, b in zip(probs, probs[1:], strict=False))
    if curve["crossing"] is not None:
        crossing = next(p for p in curve["points"] if p["buffer"] == curve["crossing"])
        assert crossing["probability"] <= curve["line"]


def test_bad_input_is_refused_with_the_statement(client: TestClient, auth: dict[str, str]) -> None:
    body = {**a_connection(client), "travel_month": "2023-13"}
    response = client.post("/v1/checks", json=body, headers=auth)
    assert response.status_code == 422
    assert response.json()["statement"] == STATEMENT
    named = client.post("/v1/checks", json={**a_connection(client), "note": "Jane Doe ABC123"}, headers=auth)
    assert named.status_code == 422, "a note that could carry a name or a booking reference is refused"
    unknown = client.post("/v1/checks", json={**a_connection(client), "connection": "ZZZ"}, headers=auth)
    assert unknown.status_code == 404


def test_health_names_the_model_and_the_outcome_month(client: TestClient) -> None:
    health = client.get("/v1/health").json()
    assert health["database"] == "ok"
    assert health["model_version"].startswith("cells-")
    assert health["outcome_month"] == "2023-12"
    assert health["hubs"] == 4


def test_hubs_name_a_busiest_connection_flown_in_the_outcome_month(
    client: TestClient, auth: dict[str, str]
) -> None:
    # The deploy tools check the connection the server names; one not flown that month would be a 404.
    for entry in client.get("/v1/hubs").json()["hubs"]:
        origin, destination = entry["busiest_origin"], entry["busiest_destination"]
        assert origin in entry["origins"] and destination in entry["destinations"]
        assert origin != destination
        body = {
            "origin": origin,
            "connection": entry["hub"],
            "destination": destination,
            "travel_month": "2023-12",
            "inbound_hour": 12,
            "outbound_hour": 13,
            "buffer_minutes": 60,
        }
        assert (
            client.get(
                "/v1/curve", params={k: v for k, v in body.items() if k != "buffer_minutes"}
            ).status_code
            == 200
        )
