# Runbook

How to rebuild everything from an empty checkout, in the order the Makefile runs it, and what to do when a step stops. Every target below is in the `Makefile`; `tests/core/test_make_order.py` fails if the Makefile's pipeline order, the stage order in `packages/pipeline/src/turnaround_pipeline/order.py` and the order of the sections in this file disagree.

## Before the first run

    uv sync                  # Python 3.12 workspace, every package editable
    npm --prefix web ci      # the site

Copy `.env.example` to `.env` on any machine that deploys. Nothing in `.env` is ever printed, logged or committed.

## The pipeline

`make pipeline` runs every target below in this order. Each writes a partial manifest to `results/<stage>/manifest.json`; `make manifest` merges them.

### data

`uv run turnaround data`. Reads the monthly BTS files, the FAA registry, the OurAirports table and the Open-Meteo cache from `data/external`, applies the quarantine rules, and writes the derived parquet by month to `data/flights`, the aircraft to `data/aircraft` and the hourly weather to `data/weather/hourly.parquet` with its attribution. Any month missing between January 2015 and the latest file is named in `data.gaps`, and the checklist's first line stays not done until it is filled.

The hosts that serve the files do not answer every network. `deploy/fetch-data.ps1` downloads them on a Windows machine that can reach them, one file at a time with retries, into a folder you then place under `data/external`; the target prints the expected paths either way. Copy the script's `fetch-status-flights.json` beside the zips as `data/external/bts/fetch-status.json`: it records the first month BTS had not published, which is the evidence that the window ends at the latest month and not at whatever was on disk.

### warehouse

`uv run turnaround warehouse`. `dbt build` over DuckDB: every model and every test. Fails on any failed test. The marts land in `results/marts`.

### metrics

`uv run turnaround metrics`. The metric layer's reconcile: every metric evaluated over the flights and over the shipped marts at every grain. Fails on any difference beyond tolerance and names the metric, the grain and the cell.

### simulate

`uv run turnaround simulate`. The demonstration network with its truth tables in `data/sim`.

### recovery

`uv run turnaround recovery`. The recovery study across every condition and seed, cached by input digest under `.cache/recovery`, so a rerun with unchanged code reads the cache. Delete the cache, or change the code version in `packages/evaluation`, to force a run.

### chapters

`uv run turnaround chapters`. Registers the eight plans in `results/plans` first (commit them before the results), then runs every chapter, the events and the misconnect curves. A plan changed after registration is refused; see "When a step stops".

### metrics-chapters

`uv run turnaround metrics --chapters`. The reconcile again, adding the metrics a chapter writes, such as the inherited share.

### exports

`uv run turnaround exports`. The workbook with live formulas (recalculated with LibreOffice when it is installed, and the summary checked against the manifest), the Tableau and Power BI specifications, and the CSV bundle with its dictionary.

### manifest

`uv run turnaround manifest`. Merges the partials into `results/manifest.json` with the policy, the palette, the deploy and latency results and the checklist.

### render

`uv run python scripts/check_published_numbers.py --write`. Renders every document from the manifest: the story, the briefing, the README, RESULTS, ARCHITECTURE and the documents in `docs`.

### marts

`uv run turnaround marts`. Copies what the site reads into `web/public/data`: the manifest, the story, the charts, the explorer's marts and `bundle.json` with every file's size, because the site never asks the host for a size.

## Checking

    make gates     # em dash, vocabulary, statement, claim gate, identifier scan, palette
    make lint      # ruff
    make types     # mypy strict
    make test      # pytest with coverage

Tests that need something this machine may not have (Postgres, LibreOffice, the data files, the weather cache, a live API) skip with a marker that names the missing dependency; CI installs each one and asserts it is present, so a skip on CI is a failure.

## The site

    make web                                 # next build, static export to web/out
    npm --prefix web run build:e2e           # the same build, pointed at the test server's mock API
    npm --prefix web run test:e2e            # Playwright against scripts/serve.mjs

The test server refuses HEAD requests and answers the first API call with a 503, like the real hosts can, so every run exercises the fallback.

## Deploying the API

From the Windows machine with `.env` beside the repository, in Git GUI's Tools menu or PowerShell: `deploy\deploy.ps1`, then `deploy\verify.ps1` (a check from a separate client, read back), then `deploy\replay.ps1` (the demo queue). `deploy\logs.ps1` shows the machine's recent logs. `make deploy` runs the same steps from a shell that can reach Fly.

## Resetting and rederiving

`make rederive` runs `scripts/reset_and_rederive.py`: it clears the rows the recordings created, deletes every derived file, runs the pipeline from the committed inputs in a fresh worktree, and diffs the new manifest against the committed one. Any difference fails it and is printed.

## When a step stops

- **A month is missing.** `data.gaps` in the manifest names it. Fetch it and run again.
- **The reconcile fails.** The message names the metric, the grain and the cell. Fix the mart or the metric definition, not the tolerance.
- **The claim gate reports drift.** A document was edited by hand, or the manifest changed and the documents were not rendered. Edit the template, run `make render`, commit both.
- **A plan hash does not match.** The plan was edited after registration. Revert the edit, or register the new plan under a dated DECISIONS.md entry tagged `reversal` that says what changed and why; the old hash stays in the history.
- **The API answers 503 on the first request.** The machine was asleep; the second request answers. The site does the same.
- **The API answers 503 with "the calculator marts are not on this server".** The image was built before `make chapters` wrote the misconnect marts. Run the chapters stage and deploy again.
- **A build process is killed, or the disk fills, on a small machine.** The full window is about seventy four million rows; the warehouse file is about eleven gigabytes and DuckDB spills beside it under `.cache/duckdb_tmp`. On a machine that kills a process past six gigabytes, keep `TURNAROUND_DUCKDB_MEMORY` at its default of 4GB (DuckDB runs past its limit by up to a gigabyte on a large distinct or window) and run the chapters with `TURNAROUND_CHAPTERS_DUCKDB_MEMORY=1GB`, since chapter 4 holds about twenty million linked legs and their design in memory beside DuckDB. `int_legs` is built in `leg_buckets` buckets of tail numbers (dbt_project.yml); raise the count if its build still spills too much.
