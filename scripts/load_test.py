"""Latency of the calculator from a stated load: p50 and p99 of POST /v1/checks and of
GET /v1/checks/{id} over N sequential requests plus a burst of concurrent checks, against a running
server. Writes results/latency/<label>.json, which the documents quote.

    python scripts/load_test.py --base-url http://127.0.0.1:8080 --label local --requests 60 --concurrency 8
    python scripts/load_test.py --base-url https://turnaround-api.fly.dev --label live
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
NOTE = "load test"


async def _check(
    client: httpx.AsyncClient, base: str, body: dict[str, Any], headers: dict[str, str]
) -> tuple[float, str]:
    started = time.perf_counter()
    response = await client.post(
        f"{base}/v1/checks", json={**body, "note": NOTE}, headers=headers, timeout=120.0
    )
    response.raise_for_status()
    return (time.perf_counter() - started) * 1000.0, str(response.json()["check_id"])


async def _read(client: httpx.AsyncClient, base: str, check_id: str) -> float:
    started = time.perf_counter()
    response = await client.get(f"{base}/v1/checks/{check_id}", timeout=60.0)
    response.raise_for_status()
    return (time.perf_counter() - started) * 1000.0


def _summary(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)
    n = len(ordered)
    if n == 0:
        return {"p50_ms": float("nan"), "p99_ms": float("nan"), "max_ms": float("nan")}
    p99_index = min(n - 1, max(0, int(round(0.99 * (n - 1)))))
    return {
        "p50_ms": round(statistics.median(ordered), 1),
        "p99_ms": round(ordered[p99_index], 1),
        "max_ms": round(ordered[-1], 1),
        "mean_ms": round(statistics.fmean(ordered), 1),
    }


async def run(base: str, token: str, requests: int, concurrency: int) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        health = (await client.get(f"{base}/v1/health", timeout=60.0)).json()
        hubs = (await client.get(f"{base}/v1/hubs", timeout=60.0)).json()["hubs"]
        if not hubs:
            raise SystemExit("the server covers no hubs")
        bodies = [
            {
                "origin": h["origins"][0],
                "connection": h["hub"],
                "destination": h["destinations"][0],
                "travel_month": health["outcome_month"],
                "inbound_hour": 12,
                "outbound_hour": 13,
                "buffer_minutes": 45 + 15 * (i % 4),
            }
            for i, h in enumerate(hubs)
        ]
        # The first request may wake the machine; it is timed separately and not counted.
        wake_ms, _ = await _check(client, base, bodies[0], headers)
        made: list[float] = []
        ids: list[str] = []
        for i in range(requests):
            ms, check_id = await _check(client, base, bodies[i % len(bodies)], headers)
            made.append(ms)
            ids.append(check_id)
        reads = [await _read(client, base, check_id) for check_id in ids]
        burst = await asyncio.gather(
            *[_check(client, base, bodies[i % len(bodies)], headers) for i in range(concurrency)]
        )
    return {
        "base_url": base,
        "measured_at": datetime.now(UTC).isoformat(),
        "requests": requests,
        "concurrency": concurrency,
        "hubs": len(hubs),
        "first_request_ms": round(wake_ms, 1),
        "check": _summary(made),
        "read": _summary(reads),
        "burst_check_max_ms": round(max(ms for ms, _ in burst), 1),
        "errors": 0,
        "note": "sequential requests after one warming request; the burst is concurrent checks",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--label", default="local", help="file name under results/latency")
    parser.add_argument("--requests", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--token", default=os.environ.get("TURNAROUND_WRITE_TOKEN", "check-token"))
    args = parser.parse_args()
    result = asyncio.run(run(args.base_url.rstrip("/"), args.token, args.requests, args.concurrency))
    out = ROOT / "results" / "latency" / f"{args.label}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
