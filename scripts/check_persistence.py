"""The out of process check: make a check, score it against the outcome month the server holds, and
read the rows back through a connection this process opens itself.

Two modes. `--start-server` migrates with alembic, starts the API in a child process against the
database URL, drives it over HTTP, then reads the check, its score and the audit row with a fresh
psycopg connection in this process. `--base-url` drives a live server (the Fly deployment) and reads
back through the API's own GET endpoints from this separate client, which is the verification the
README prints. In both modes the audit row must be observed at or before the response's served_at.

    python scripts/check_persistence.py --start-server
    python scripts/check_persistence.py --base-url https://turnaround-api.fly.dev --out results/deploy/verification.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""}:
    sys.path.insert(0, str(ROOT))

from turnaround_core.statements import STATEMENT

NOTE = "persistence check"


def wait_for(base: str, seconds: float = 90.0) -> dict[str, Any]:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            response = httpx.get(f"{base}/v1/health", timeout=8.0)
            if response.status_code == 200:
                body: dict[str, Any] = response.json()
                return body
        except httpx.HTTPError:
            pass
        time.sleep(1.0)
    raise SystemExit(f"the API at {base} did not answer within {seconds:.0f} seconds")


def a_connection(base: str, hub: str | None) -> dict[str, Any]:
    listed = httpx.get(f"{base}/v1/hubs", timeout=60.0)
    listed.raise_for_status()
    hubs = {h["hub"]: h for h in listed.json()["hubs"]}
    if not hubs:
        raise SystemExit("the server covers no hubs")
    entry = hubs[hub] if hub else hubs[sorted(hubs)[0]]
    return {
        "origin": entry["origins"][0],
        "connection": entry["hub"],
        "destination": entry["destinations"][0],
    }


def drive(base: str, token: str, hub: str | None, outcome_month: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        **a_connection(base, hub),
        "travel_month": outcome_month,
        "inbound_hour": 12,
        "outbound_hour": 13,
        "buffer_minutes": 60,
        "note": NOTE,
    }
    created = httpx.post(f"{base}/v1/checks", json=body, headers=headers, timeout=120.0)
    created.raise_for_status()
    check = created.json()
    if check["statement"] != STATEMENT:
        raise SystemExit("the check response is missing the statement")
    scored = httpx.post(f"{base}/v1/score", json={"note": NOTE}, headers=headers, timeout=120.0)
    scored.raise_for_status()
    return {
        "check_id": str(check["check_id"]),
        "connection": f"{body['origin']} {body['connection']} {body['destination']}",
        "travel_month": outcome_month,
        "probability": float(check["probability"]),
        "low": float(check["low"]),
        "high": float(check["high"]),
        "flights": int(check["flights"]),
        "model_version": str(check["model_version"]),
        "served_at": datetime.fromisoformat(str(check["served_at"])),
        "scored_reported": int(scored.json()["scored"]),
        "unscored_share": float(scored.json()["unscored_share"]),
    }


def read_back_via_api(base: str, ids: dict[str, Any]) -> dict[str, Any]:
    check = httpx.get(f"{base}/v1/checks/{ids['check_id']}", timeout=60.0)
    check.raise_for_status()
    audit = httpx.get(f"{base}/v1/audit?limit=50", timeout=60.0)
    audit.raise_for_status()
    c = check.json()
    if c["statement"] != STATEMENT or audit.json()["statement"] != STATEMENT:
        raise SystemExit("a response is missing the statement")
    if abs(float(c["probability"]) - ids["probability"]) > 1e-12:
        raise SystemExit("the check did not come back with the probability it was created with")
    entries = audit.json()["entries"]
    created = [x for x in entries if x["action"] == "create" and x["resource_id"] == ids["check_id"]]
    if not created:
        raise SystemExit("no audit row for the check")
    if datetime.fromisoformat(created[0]["at"]) > ids["served_at"]:
        raise SystemExit("the audit row was written after the response was served")
    return {
        "check": {
            k: c[k]
            for k in ("origin", "connection", "destination", "travel_month", "buffer_minutes", "probability")
        },
        "score": c["score"],
        "audit_entries": len(entries),
        "audit_before_response": True,
    }


def read_back_via_postgres(url: str, ids: dict[str, Any], schema: str) -> dict[str, Any]:
    import psycopg

    plain = url.replace("postgresql+psycopg://", "postgresql://")
    prefix = f'"{schema}".' if schema else ""
    with psycopg.connect(plain) as conn, conn.cursor() as cur:
        cur.execute(
            f"select probability, model_version from {prefix}checks where check_id = %s", (ids["check_id"],)
        )
        check = cur.fetchone()
        cur.execute(
            f"select count(*), max(pairs) from {prefix}check_scores where check_id = %s", (ids["check_id"],)
        )
        scores = cur.fetchone()
        cur.execute(
            f"select at from {prefix}audit_log where action = 'create' and resource_id = %s",
            (ids["check_id"],),
        )
        audit = cur.fetchone()
    if check is None or abs(float(check[0]) - ids["probability"]) > 1e-12 or check[1] != ids["model_version"]:
        raise SystemExit("the check row is missing from a fresh connection")
    if scores is None or int(scores[0]) != ids["scored_reported"]:
        raise SystemExit("the score row is missing or does not match what the server reported")
    if audit is None or audit[0] > ids["served_at"]:
        raise SystemExit("the audit row is missing or later than the response")
    return {"check": True, "scores": int(scores[0]), "pairs": scores[1], "audit_before_response": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--start-server", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--hub", default=None)
    parser.add_argument("--out", default=None, help="write the observation as JSON here as well")
    args = parser.parse_args()
    token = os.environ.get("TURNAROUND_WRITE_TOKEN", "check-token")
    server: subprocess.Popen[bytes] | None = None
    base = args.base_url
    schema = os.environ.get("TURNAROUND_DB_SCHEMA", "").strip()
    try:
        if args.start_server:
            url = os.environ.get("TURNAROUND_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
            if not url:
                raise SystemExit("set TURNAROUND_TEST_DATABASE_URL or DATABASE_URL to start a server")
            env = {
                **os.environ,
                "DATABASE_URL": url,
                "TURNAROUND_WRITE_TOKEN": token,
                "TURNAROUND_ENV": "check",
            }
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    str(ROOT / "packages" / "api" / "alembic.ini"),
                    "upgrade",
                    "head",
                ],
                cwd=ROOT / "packages" / "api",
                env=env,
                check=True,
            )
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "turnaround_api.main:app",
                    "--port",
                    str(args.port),
                    "--log-level",
                    "warning",
                ],
                cwd=ROOT,
                env=env,
            )
            base = f"http://127.0.0.1:{args.port}"
        if not base:
            raise SystemExit("give --base-url or --start-server")
        base = base.rstrip("/")
        health = wait_for(base)
        if not health.get("outcome_month"):
            raise SystemExit("the server holds no outcome month to score against")
        ids = drive(base, token, args.hub, str(health["outcome_month"]))
        if args.start_server:
            url = os.environ.get("TURNAROUND_TEST_DATABASE_URL") or os.environ["DATABASE_URL"]
            observed = read_back_via_postgres(url, ids, schema)
        else:
            observed = read_back_via_api(base, ids)
        report = {
            "base_url": base,
            "health": {
                k: health.get(k) for k in ("status", "database", "model_version", "hubs", "outcome_month")
            },
            "ids": {k: str(v) for k, v in ids.items()},
            "observed": observed,
        }
        print(json.dumps(report, indent=1))
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        print(
            "persistence check: a check, its score and its audit row were read back from outside the server process"
        )
        return 0
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=20)


if __name__ == "__main__":
    sys.exit(main())
