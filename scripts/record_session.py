"""Record an API session for the site's fallback.

Starts the API in a child process against a local Postgres (or drives a running server with
--base-url), walks the flow the planner performs (health, the hubs, the curve for one connection at
every hub, a check saved at every hub, the scoring pass) and writes every response, labelled recorded,
to web/public/data/recorded_session.json. When the live API is asleep the planner serves these
responses and says so on the page. Every check the recording makes carries the note the reset step
deletes by.

    TURNAROUND_TEST_DATABASE_URL=postgresql+psycopg://... python scripts/record_session.py --start-server
    python scripts/record_session.py --base-url https://turnaround-flights-api.fly.dev --token ...
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "data" / "recorded_session.json"
NOTE = "recorded session"


def wait_for(base: str, seconds: float = 120.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            if httpx.get(f"{base}/v1/health", timeout=8.0).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1.0)
    raise SystemExit(f"the API at {base} did not answer within {seconds:.0f} seconds")


def record(base: str, token: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    responses: dict[str, Any] = {}

    def get(name: str, path: str) -> dict[str, Any]:
        r = httpx.get(f"{base}{path}", timeout=120.0)
        responses[name] = {"method": "GET", "path": path, "status": r.status_code, "body": r.json()}
        return dict(r.json())

    health = get("health", "/v1/health")
    hubs = get("hubs", "/v1/hubs")["hubs"]
    month = str(health["outcome_month"])
    connections: list[dict[str, Any]] = []
    for h in hubs:
        origin = h["origins"][0] if h["origins"] else None
        # A connection goes somewhere else: never back to the airport it started from.
        onward = [d for d in h["destinations"] if d != origin]
        if origin is None or not onward:
            continue
        c = {
            "origin": origin,
            "connection": h["hub"],
            "destination": onward[0],
            "travel_month": month,
            "inbound_hour": 12,
            "outbound_hour": 13,
        }
        query = urlencode({k: str(v) for k, v in c.items()})
        name = f"curve_{c['origin']}_{c['connection']}_{c['destination']}_{month}_12_13"
        curve = httpx.get(f"{base}/v1/curve?{query}", timeout=120.0)
        if curve.status_code != 200:
            continue
        responses[name] = {"method": "GET", "path": f"/v1/curve?{query}", "status": 200, "body": curve.json()}
        saved = httpx.post(
            f"{base}/v1/checks",
            json={**c, "buffer_minutes": 60, "note": NOTE},
            headers=headers,
            timeout=120.0,
        )
        saved.raise_for_status()
        responses[f"check_{c['connection']}"] = {
            "method": "POST",
            "path": "/v1/checks",
            "status": saved.status_code,
            "body": saved.json(),
        }
        connections.append(c)
    score = httpx.post(f"{base}/v1/score", json={"note": NOTE}, headers=headers, timeout=180.0)
    responses["score"] = {
        "method": "POST",
        "path": "/v1/score",
        "status": score.status_code,
        "body": score.json(),
    }
    return {
        "recorded": True,
        "recorded_at": datetime.now(UTC).isoformat(),
        "base_url": base,
        "note": NOTE,
        "connections": connections,
        "responses": responses,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--start-server", action="store_true")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--token", default=os.environ.get("TURNAROUND_WRITE_TOKEN", "record-token"))
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()
    server: subprocess.Popen[bytes] | None = None
    base = args.base_url
    try:
        if args.start_server:
            url = os.environ.get("TURNAROUND_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
            if not url:
                raise SystemExit("set TURNAROUND_TEST_DATABASE_URL or DATABASE_URL to start a server")
            env = {
                **os.environ,
                "DATABASE_URL": url,
                "TURNAROUND_WRITE_TOKEN": args.token,
                "TURNAROUND_ENV": "recording",
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
        wait_for(base)
        session = record(base, args.token)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(session, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(
            f"recorded {len(session['responses'])} responses for {len(session['connections'])} connections to {out}"
        )
        return 0
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=20)


if __name__ == "__main__":
    sys.exit(main())
