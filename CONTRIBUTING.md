# Contributing

## Setup

```
uv sync
npm --prefix web ci
```

Python 3.12, managed by uv. Node 22 for the site. DuckDB is the only engine the pipeline needs;
Postgres is needed for the API's persistence tests (set `TURNAROUND_TEST_DATABASE_URL`, or the
tests that need it skip with a named reason).

## The rules this repository holds itself to

- **No number is typed into a document.** Every figure in README.md, RESULTS.md, the story, the
  memo and the docs is rendered from `results/manifest.json` by the claim gate. Edit the template
  under `docs/templates`, `report/templates` or `story/templates`, run `make render`, commit both.
- **Every gate has three tests**: it passes clean input, it fails on the defect it exists for, and
  it refuses to report a pass on nothing.
- **Every estimator is proven on the simulator before it touches real flights.** A new estimator
  arrives with its recovery result in `packages/evaluation`.
- **Every chapter's plan is registered before its estimate runs.** Change a plan and its hash
  changes; the gate notices.
- **No em dashes, no filler vocabulary.** `make gates` checks both.
- **Sort before any seeded sample and break ties with a stable key** before a table is published.

## Checks

```
make check   # lint, types, gates, tests with coverage at or above 80 percent
make rederive   # the full pipeline from the raw files, compared with the committed manifest
```

## Commits

Conventional commits (`feat(chapters): ...`, `fix(web): ...`, `test(api): ...`), one module at a
time. A commit that changes a published number also re-renders the documents it appears in.
