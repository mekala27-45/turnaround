# turnaround

**Why your flight is late: a data story in 8 chapters, built on every scheduled domestic flight in the United States from January 2015 to July 2026.**

The window starts in January 2015, the year American Airlines and US Airways moved onto one operating certificate, the last merger among the legacy network carriers, which gives ten complete years after the last major carrier integration; it runs to the latest month the Bureau of Transportation Statistics has published (July 2026). Every row in it is used, 74,201,388 scheduled flights of 20 reporting carriers, with nothing sampled. Two sources are narrower than the flights and say so: hourly weather is pulled at the FAA's Core 30 airports rather than at every airport (the free weather tier cannot carry every airport for the window in a day; the weather estimate uses flights between two of them), and the FAA registry join covers 90.1% of flights. Mandatory steps not yet done: 18 (numbered as in the checklist below); the build is not called complete until that list is empty.

- **The story:** https://mekala27-45.github.io/turnaround/
- **The misconnect calculator's API:** https://turnaround-flights-api.fly.dev (verified from a separate client, AJAY, Windows, PowerShell 5.1.26100.9444, at 2026-10-01T23:19:40.2231995Z: a check for MCO ATL LGA in 2026-07 at a 60 min buffer came back at 12.5% (8.7% to 17.6%) on 26,428 flights and read back with its audit row written before the response)
- **The briefing:** [report/briefing.md](report/briefing.md), rendered from the same manifest as the site

> Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the public record; no individual traveler appears. The findings are a portfolio analysis, not an official ranking and not travel advice.

## The eight findings

| Chapter | The finding | The number |
|---|---|---|
| What on time measures | The on time rate fell, and flights took longer gate to gate and the schedule grew as much | on time rate -3.7 pts (-4.9 pts to -2.6 pts); actual gate to gate +4.4 min on the same routes |
| Padding in the schedule | The schedule grew as fast as the flying slowed, so it absorbed the delay | padding +3.98 min (+3.84 min to +4.13 min) on matched cells, 2015 to 2025 |
| The fifteen minute line | No carrier's arrivals bunch under the fifteen minute line beyond what the placebos show | 0 of 15 carriers after Benjamini-Hochberg; pooled z -2.40 against 49 placebos |
| Inherited delay | About a third of arrival delay was inherited from the aircraft's previous flight, and a scheduled turn of 75 minutes halves what is passed on | 34.9% inherited (34.8% to 34.9%) against 37.4% reported |
| The fair ranking | The ranking changes once you hold constant what each carrier flies: PSA Airlines rises 4 places and Hawaiian Airlines falls 7 | 11 of 15 carriers move; PSA Airlines 11 to 7, Hawaiian Airlines 8 to 15 |
| Causes, reported and estimated | Weather explains more delay than the weather field records | weather explains 18.8% (17.7% to 19.9%); the weather field records 4.2% |
| Meltdowns and recovery | Southwest Airlines took 9 days to get back to its peers and Delta Air Lines 5; across every alert episode, how fast a carrier recovers is a trait of the carrier | 8 of 8 reporting year disruptions flagged at threshold 29.0, inside the grid |
| The reader's decision | Book the first flight of the aircraft's day, and leave 65 minutes to connect at ATL | first leg on time 85.8% against 76.0%; ATL needs 65 min to stay under 10% |

Every chapter is a claim that could have come out the other way: a plan hashed before the estimate touched a real flight, an estimator first proven on a simulated airline where the answer is known, a result with an interval, one chart with one message and the SQL behind it, a method note, and a paragraph on what an operations director would push back on.

## What is in it

- **A modeled warehouse.** dbt over DuckDB: 18 models and 206 tests over the flights, the aircraft, the airports and the weather, with named quarantine rules that flag and count and delete nothing, and a metric layer that defines each of 17 metrics once, two ways, reconciled at 4 grains with 0 disagreements.
- **A simulator with known truth.** A synthetic network of 8 carriers and 40 airports with known padding steps, a known propagation coefficient, known carrier effects on routes of known difficulty, planted bunching, a planted meltdown and storms whose minutes the reported cause field under records by design. The recovery study ran 12 conditions with 20 seeds each.
- **The aircraft's day.** Every rotation rebuilt from tail numbers with integrity rules: 18,151,842 rotations, the inherited share of delay, and the buffer curve.
- **The reader's tools.** A misconnect calculator on a live API with a check log scored against the month it was asked about, an explorer with an SQL box over the marts in the browser, a workbook with live formulas, Tableau and Power BI companions.

## Skills

| Skill | Where it lives |
|---|---|
| SQL | `warehouse/`, `metrics/`, the SQL behind every chart |
| Data modeling, analytics engineering | `warehouse/` (dbt models, tests, exposures) |
| Data quality | the quarantine rules (`packages/contracts`) and the quarantine report on the data page |
| Metric definitions and governance | `metrics/metrics.yml`, `docs/definitions.md` |
| Statistics: inference | `packages/stats` (block bootstrap by day, cluster robust errors) |
| Statistics: multiple comparisons | Benjamini-Hochberg across carriers in The fifteen minute line |
| Regression with fixed effects | Inherited delay, The fair ranking, Causes, reported and estimated (`packages/stats/fe.py`, weighted cells and the direct solve) |
| Changepoint detection | Padding in the schedule (PELT) |
| Density and bunching tests | The fifteen minute line |
| Event studies, quasi experiments | Meltdowns and recovery (`packages/events/study.py`) |
| Simulation and estimator validation | `packages/sim`, the recovery study (`packages/evaluation`) |
| Anomaly detection | `packages/events` |
| Probability for decisions | The reader's decision, the misconnect curves (`packages/misconnect`) |
| Data storytelling | `story/`, the sticky chart layout, the method notes |
| Dashboards and BI | `exports/tableau`, `exports/powerbi`, `/explore` |
| Spreadsheet modeling | `exports/workbook.xlsx` with live formulas |
| APIs and persistence | `packages/api`, `fly.toml`, `scripts/check_persistence.py` |
| Visualization | `web/`, the validated palette, one message per chart |
| Communication | `report/briefing.md`, the pushback paragraphs |
| Reproducibility | the claim gate, the rederive, the corrections log |
| Data licensing and provenance | `data/PROVENANCE.md`, the four declared sources |

## Definition of done

1. **done.** Every monthly file from January 2015 to the latest ingested, the quarantine report published, the registry join rate stated, airports and weather committed with attribution, provenance and licenses recorded. *Evidence:* 139 monthly files from January 2015 to July 2026 (missing: none), 74,201,388 rows; quarantine by rule and by carrier and month on the data page; registry join 90.1% of flights; 397 airports; 3,085,200 hourly weather rows; data/PROVENANCE.md.
2. **done.** Warehouse with dbt tests and exposures; the metric layer reconciled across grains. *Evidence:* dbt build: 18 models, 206 tests, 0 failed; 17 metrics reconciled at 4 grains over 3,501 cells with 0 disagreements.
3. **done.** Simulator with known padding, propagation, carrier effects, planted bunching and a planted meltdown; the recovery study on every condition with at least twenty seeds. *Evidence:* 12 conditions times 20 seeds, 240 runs; results/recovery.
4. **done.** Chapters 1 and 2 with plan hashes, simulator recovery, results on the test years with intervals, the changepoints named. *Evidence:* plans 74cda4464e3380a2 and 13d98f2ebd738a81; on time change -3.7 pts, padding change +3.98 min with intervals; 204 changepoints dated.
5. **done.** Chapter 4: rotations with integrity rules and their counts; the inherited share with its interval; the buffer curve. *Evidence:* 18,151,842 rotations, 369,126 broken chains, 601,945 impossible sequences; inherited share 34.9% (34.8% to 34.9%); buffer curve table ch4.buffer_curve.
6. **done.** Chapter 5: the fair ranking with cluster robust intervals beside the raw ranking, the rank changes named, the simulator recovery. *Evidence:* 15 carriers raw and adjusted with day clustered intervals; 11 change places; simulator rank correlation 0.94 adjusted against -0.07 raw.
7. **done.** API deployed on Fly with Neon; live URL in the README; verified from a separate client, with the client's response printed. *Evidence:* https://turnaround-flights-api.fly.dev: deployed and verified from AJAY, Windows, PowerShell 5.1.26100.9444; probability 12.5% read back; results/deploy/verification.json.
8. **done.** Checks and scores observed from an independent connection; audit before response; the out of process check. *Evidence:* tests/api: 11 passed (test_check_is_committed, test_score_is_committed, test_audit_precedes_response, the out of process scripts/check_persistence.py).
9. **done.** Chapter 3: the density test with placebos and correction, published either way; chapter 6: causes reported and estimated side by side. *Evidence:* 0 of 15 carriers flagged after Benjamini-Hochberg; weather share 18.8% against 4.2% reported.
10. **done.** Chapter 7: the known events table with citations and detection days; the operating point with its interior test; the two event studies with recovery times. *Evidence:* threshold 29.0 inside the grid; 8 of 8 reporting year events flagged; recovery 9 and 5 days.
11. **done.** Chapter 8: the traveler's tables; the misconnect curves for the twenty hubs with the chosen buffer and its interior test; the airline's buffer trade. *Evidence:* 20 hub curves, 20 with an interior crossing; first leg on time 85.8% against 76.0%; buffer trade 0.46 minutes per minute.
12. **done.** Exports: the workbook with live formulas and its recalculation test, the Tableau extract and specification, the Power BI specification with measures, the CSV bundle with its dictionary. *Evidence:* workbook 23 sheets, 12 summary formulas, recalculation test passed; 18 DAX measures; 19 CSV files with a dictionary.
13. **done.** The story live on GitHub Pages with sticky charts, method notes, the SQL behind every chart, the corrections section and the print stylesheet. *Evidence:* https://mekala27-45.github.io/turnaround/: live check passed.
14. **done.** Explore, rank, rotations, events, planner, data and report pages live, working from the recorded session when the API is asleep; the test server refuses what the host refuses. *Evidence:* 8 of 8 routes loaded live; asleep: answered on the second probe; Playwright against the test server: 29 passed, 0 failed.
15. **done.** Latency published; the live check in a real browser recorded in results/live_check.json. *Evidence:* POST /v1/checks p50 61 ms, p99 77 ms; results/live_check.json passed.
16. **done.** RESULTS.md with every figure re-derived by the gate and a specific limitations section. *Evidence:* claim gate over every document; rederive drift 0; limitations section in RESULTS.md.
17. **done.** README with the matrix and this checklist; DECISIONS.md with at least ten dated entries, two reversals and the corrections; three executed notebooks with a dead end each; the pushback paragraph on every chapter and page. *Evidence:* DECISIONS.md 22 dated entries, 4 reversals, 4 corrections; 3 executed notebooks, 3 with a dead end.
18. **not done.** Coverage at or above 80 percent, mypy strict clean, ruff clean, zero em dashes, zero banned vocabulary, palette validator green including the dark card run, forty to sixty commits, the rederive run in a worktree before the tag, v0.1.0 pushed after the commits, Apache 2.0 for code with the four data sources' terms declared, repo described, topics set. *Evidence:* coverage 87.0 percent; mypy clean; ruff clean; palette green; 58 commits; rederive reproduced in a worktree; tag not pushed; Apache 2.0 with the four data sources' terms.

## Run it

```
make setup        # uv sync and the site's packages
make data         # every monthly file into typed, flagged parquet; airports, aircraft, weather
make warehouse    # dbt build and test, then the shipped marts
make metrics      # the metric layer's reconcile
make simulate     # the demonstration network and its truth
make recovery     # every estimator on every condition and seed
make chapters     # plans registered, then the eight chapters
make metrics-chapters exports manifest render marts
make gates        # dash, vocabulary, statement, claim gate, identifier scan, palette
make test         # with the Postgres tests when TURNAROUND_TEST_DATABASE_URL is set
make rederive     # everything again from the raw files in a worktree, and a diff
```

The raw files are fetched on a machine that can reach the hosts (`deploy/fetch-data.ps1`); `docs/runbook.md` has the order, what each step writes and what to do when one stops.

## Data and licenses

Code: Apache 2.0. Data: the Bureau of Transportation Statistics' Reporting Carrier On-Time Performance files and the FAA's releasable aircraft registry are U.S. government works in the public domain; OurAirports is public domain; Open-Meteo's historical weather is CC BY 4.0, attributed in `data/weather/ATTRIBUTION.md` and on every page that shows it. `data/PROVENANCE.md` lists every file with its source and its checksum. This is a portfolio analysis and a demonstration API with a token gate on writes and no other authentication.
