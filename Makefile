# The pipeline in the order it runs. docs/runbook.md describes each target;
# tests/core/test_make_order.py fails if the Makefile's order disagrees with the stage order.

PY := uv run python
T := uv run turnaround

.PHONY: help setup data warehouse metrics simulate recovery chapters metrics-chapters exports manifest render marts pipeline gates lint types test check rederive web deploy verify-api load-test live-check demo clean

help:
	@grep -E '^[a-z-]+:' Makefile | sed 's/:.*//' | tr '\n' ' '; echo

setup:
	uv sync
	npm --prefix web ci

# The four public sources. This machine may not reach the hosts: run deploy/fetch-data.ps1 on one
# that can and place the files under data/external; the target prints the expected paths and
# verifies what it finds either way.
data:
	$(T) data

# dbt over DuckDB: staging, intermediate and marts, then the metric layer's reconcile step.
warehouse:
	$(T) warehouse

metrics:
	$(T) metrics

simulate:
	$(T) simulate

recovery:
	$(T) recovery

# The eight chapters, the events and the misconnect curves; then the metric layer again with the
# metrics a chapter writes (the inherited share).
chapters:
	$(T) chapters

metrics-chapters:
	$(T) metrics --chapters

exports:
	$(T) exports

manifest:
	$(T) manifest

render:
	$(PY) scripts/check_published_numbers.py --write

marts:
	$(T) marts

pipeline: data warehouse metrics simulate recovery chapters metrics-chapters exports manifest render marts

gates:
	$(PY) scripts/check_no_em_dash.py
	$(PY) scripts/check_vocabulary.py
	$(PY) scripts/check_statement.py
	$(PY) scripts/check_published_numbers.py
	$(PY) scripts/scan_for_planted_identifiers.py
	node scripts/validate_palette.js --config web/src/theme/palette.json

lint:
	uv run ruff check .
	uv run ruff format --check .

types:
	uv run mypy

test:
	uv run pytest --cov --cov-report=term-missing:skip-covered

check: lint types gates test

rederive:
	$(PY) scripts/reset_and_rederive.py

web:
	npm --prefix web run build

# Deploys the API to Fly with the Neon connection string as a secret. Needs flyctl and the
# variables in .env; the machine that built this repository could not reach Fly, so the same
# steps live in deploy/deploy.ps1 for a Windows machine.
deploy:
	sh deploy/deploy.sh

verify-api:
	$(PY) scripts/check_persistence.py --base-url "$${TURNAROUND_API_BASE:-http://127.0.0.1:8080}"

load-test:
	$(PY) scripts/load_test.py --base-url "$${TURNAROUND_API_BASE:-http://127.0.0.1:8080}"

live-check:
	$(PY) scripts/live_check.py

demo:
	$(PY) scripts/build_demo_gif.py

clean:
	rm -rf web/out logs/*.log
