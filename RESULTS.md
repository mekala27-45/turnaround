# Results

Every figure on this page is rendered from `results/manifest.json` (as of 2026-10-01) by the claim gate, which re-renders the page in CI and fails on any difference. The window is January 2015 to July 2026; models choose on 2015 to 2022 and report on 2023 onward.

> Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the public record; no individual traveler appears. The findings are a portfolio analysis, not an official ranking and not travel advice.

## Definition of done

1. **done.** Every monthly file from January 2015 to the latest ingested, the quarantine report published, the registry join rate stated, airports and weather committed with attribution, provenance and licenses recorded. *Evidence:* 139 monthly files from January 2015 to July 2026 (missing: none), 74,201,388 rows; quarantine by rule and by carrier and month on the data page; registry join 90.1% of flights; 397 airports; 3,085,200 hourly weather rows; data/PROVENANCE.md.
2. **done.** Warehouse with dbt tests and exposures; the metric layer reconciled across grains. *Evidence:* dbt build: 18 models, 206 tests, 0 failed; 17 metrics reconciled at 4 grains over 3,501 cells with 0 disagreements.
3. **done.** Simulator with known padding, propagation, carrier effects, planted bunching and a planted meltdown; the recovery study on every condition with at least twenty seeds. *Evidence:* 12 conditions times 20 seeds, 240 runs; results/recovery.
4. **done.** Chapters 1 and 2 with plan hashes, simulator recovery, results on the test years with intervals, the changepoints named. *Evidence:* plans 74cda4464e3380a2 and 13d98f2ebd738a81; on time change -3.7 pts, padding change +3.98 min with intervals; 204 changepoints dated.
5. **done.** Chapter 4: rotations with integrity rules and their counts; the inherited share with its interval; the buffer curve. *Evidence:* 18,151,842 rotations, 369,126 broken chains, 601,945 impossible sequences; inherited share 34.9% (34.8% to 34.9%); buffer curve table ch4.buffer_curve.
6. **done.** Chapter 5: the fair ranking with cluster robust intervals beside the raw ranking, the rank changes named, the simulator recovery. *Evidence:* 15 carriers raw and adjusted with day clustered intervals; 11 change places; simulator rank correlation 0.94 adjusted against -0.07 raw.
7. **not done.** API deployed on Fly with Neon; live URL in the README; verified from a separate client, with the client's response printed. *Evidence:* not yet deployed: not yet deployed from no client yet; probability not measured read back; results/deploy/verification.json.
8. **done.** Checks and scores observed from an independent connection; audit before response; the out of process check. *Evidence:* tests/api: 11 passed (test_check_is_committed, test_score_is_committed, test_audit_precedes_response, the out of process scripts/check_persistence.py).
9. **done.** Chapter 3: the density test with placebos and correction, published either way; chapter 6: causes reported and estimated side by side. *Evidence:* 0 of 15 carriers flagged after Benjamini-Hochberg; weather share 18.8% against 4.2% reported.
10. **done.** Chapter 7: the known events table with citations and detection days; the operating point with its interior test; the two event studies with recovery times. *Evidence:* threshold 29.0 inside the grid; 8 of 8 reporting year events flagged; recovery 9 and 5 days.
11. **done.** Chapter 8: the traveler's tables; the misconnect curves for the twenty hubs with the chosen buffer and its interior test; the airline's buffer trade. *Evidence:* 20 hub curves, 20 with an interior crossing; first leg on time 85.8% against 76.0%; buffer trade 0.46 minutes per minute.
12. **done.** Exports: the workbook with live formulas and its recalculation test, the Tableau extract and specification, the Power BI specification with measures, the CSV bundle with its dictionary. *Evidence:* workbook 23 sheets, 12 summary formulas, recalculation test passed; 18 DAX measures; 19 CSV files with a dictionary.
13. **not done.** The story live on GitHub Pages with sticky charts, method notes, the SQL behind every chart, the corrections section and the print stylesheet. *Evidence:* not yet published: live check not checked.
14. **not done.** Explore, rank, rotations, events, planner, data and report pages live, working from the recorded session when the API is asleep; the test server refuses what the host refuses. *Evidence:* 0 of 0 routes loaded live; asleep: not observed; Playwright against the test server: 29 passed, 0 failed.
15. **not done.** Latency published; the live check in a real browser recorded in results/live_check.json. *Evidence:* POST /v1/checks p50 not measured, p99 not measured; results/live_check.json not checked.
16. **not done.** RESULTS.md with every figure re-derived by the gate and a specific limitations section. *Evidence:* claim gate over every document; rederive drift not run; limitations section in RESULTS.md.
17. **done.** README with the matrix and this checklist; DECISIONS.md with at least ten dated entries, two reversals and the corrections; three executed notebooks with a dead end each; the pushback paragraph on every chapter and page. *Evidence:* DECISIONS.md 22 dated entries, 4 reversals, 4 corrections; 3 executed notebooks, 3 with a dead end.
18. **not done.** Coverage at or above 80 percent, mypy strict clean, ruff clean, zero em dashes, zero banned vocabulary, palette validator green including the dark card run, forty to sixty commits, the rederive run in a worktree before the tag, v0.1.0 pushed after the commits, Apache 2.0 for code with the four data sources' terms declared, repo described, topics set. *Evidence:* coverage 87.0 percent; mypy clean; ruff clean; palette green; 57 commits; rederive not run; tag not pushed; Apache 2.0 with the four data sources' terms.

12 of 18 done; not done: 7, 13, 14, 15, 16, 18.

Stretch items, not counted toward the checklist: the long history before the window, fares from the ticket sample, load factors from the segment data, an aircraft chapter, the Newark page and containers built in CI are not done in this release.

## The eight chapters

| Chapter | Plan hash | The finding | Headline with interval |
|---|---|---|---|
| What on time measures | `74cda4464e3380a2` | The on time rate fell, and flights took longer gate to gate and the schedule grew as much | on time -3.7 pts (-4.9 pts to -2.6 pts), scheduled block +4.6 min (+4.3 min to +5.0 min), actual block +4.4 min (+4.0 min to +4.8 min) |
| Padding in the schedule | `13d98f2ebd738a81` | The schedule grew as fast as the flying slowed, so it absorbed the delay | padding +3.98 min (+3.84 min to +4.13 min); 204 steps |
| The fifteen minute line | `0249fbc74965a7ac` | No carrier's arrivals bunch under the fifteen minute line beyond what the placebos show | 0 of 15 carriers; pooled z -2.40, p 0.992 |
| Inherited delay | `ee4a7aff3c3655b6` | About a third of arrival delay was inherited from the aircraft's previous flight, and a scheduled turn of 75 minutes halves what is passed on | 34.9% (34.8% to 34.9%); rho 1.068 (1.067 to 1.070) |
| The fair ranking | `859c5a40bab6906c` | The ranking changes once you hold constant what each carrier flies: PSA Airlines rises 4 places and Hawaiian Airlines falls 7 | 11 of 15 carriers change places |
| Causes, reported and estimated | `a869209fb6ee8f35` | Weather explains more delay than the weather field records | 18.8% (17.7% to 19.9%) against 4.2% reported |
| Meltdowns and recovery | `c0e2ac3316344144` | Southwest Airlines took 9 days to get back to its peers and Delta Air Lines 5; across every alert episode, how fast a carrier recovers is a trait of the carrier | recall 100% on the reporting years; trait p 0.018 |
| The reader's decision | `3e13c6a0a08d3a8f` | Book the first flight of the aircraft's day, and leave 65 minutes to connect at ATL | first leg +9.8 pts (+9.5 pts to +10.1 pts) more often on time |

## The recovery study

| Condition | Padding error | Changepoint date error | Rho bias | Rho coverage | Inherited share error | Raw rank correlation | Adjusted rank correlation | Bunching false positives | Bunching power | Weather share error | Weather coverage | Detector precision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| confounding moderate, propagation strong, noise high | 1.14 min | 1.7 days | -0.016 | 0% | -1.7 pts | 0.16 | 0.93 | 0.0% | 100% | 0.0 pts | 95% | 44% |
| confounding moderate, propagation strong, noise low | 0.51 min | 1.7 days | -0.011 | 10% | -1.7 pts | 0.10 | 0.95 | 0.0% | 100% | +0.1 pts | 95% | 45% |
| confounding moderate, propagation weak, noise high | 1.14 min | 1.7 days | +0.014 | 5% | -0.7 pts | 0.19 | 0.96 | 0.0% | 100% | -0.2 pts | 95% | 45% |
| confounding moderate, propagation weak, noise low | 0.51 min | 1.7 days | +0.009 | 30% | -1.0 pts | 0.11 | 0.97 | 0.0% | 100% | 0.0 pts | 100% | 48% |
| confounding none, propagation strong, noise high | 1.14 min | 1.7 days | -0.017 | 0% | -1.7 pts | 0.75 | 0.97 | 0.0% | 100% | 0.0 pts | 95% | 43% |
| confounding none, propagation strong, noise low | 0.51 min | 1.7 days | -0.012 | 5% | -1.7 pts | 0.75 | 0.97 | 0.0% | 100% | +0.2 pts | 100% | 45% |
| confounding none, propagation weak, noise high | 1.14 min | 1.7 days | +0.013 | 5% | -0.8 pts | 0.75 | 0.98 | 0.0% | 100% | -0.2 pts | 95% | 44% |
| confounding none, propagation weak, noise low | 0.51 min | 1.7 days | +0.009 | 35% | -1.0 pts | 0.75 | 0.98 | 0.0% | 100% | +0.1 pts | 100% | 47% |
| confounding strong, propagation strong, noise high | 1.13 min | 1.7 days | -0.015 | 0% | -1.6 pts | -0.05 | 0.91 | 0.0% | 100% | 0.0 pts | 95% | 43% |
| confounding strong, propagation strong, noise low | 0.50 min | 1.7 days | -0.010 | 10% | -1.7 pts | -0.10 | 0.94 | 0.0% | 100% | +0.3 pts | 100% | 45% |
| confounding strong, propagation weak, noise high | 1.13 min | 1.7 days | +0.014 | 5% | -0.7 pts | -0.02 | 0.94 | 0.0% | 100% | -0.2 pts | 95% | 44% |
| confounding strong, propagation weak, noise low | 0.50 min | 1.7 days | +0.010 | 25% | -0.9 pts | -0.09 | 0.96 | 0.0% | 100% | +0.1 pts | 100% | 47% |

*Source: the simulated airline network with known truth, the recovery study, every condition and seed, 20 seeds, as of 2026-10-01.*

The padding estimator does worst under confounding none, propagation strong, noise high; the propagation interval covers least under confounding moderate, propagation strong, noise high; the raw ranking is most wrong under confounding strong, propagation strong, noise low, where the adjusted ranking still reaches a rank correlation of 0.94 on average; the weather interval covers least under confounding moderate, propagation strong, noise high. The definition chapter's route panel recovered the scheduled change within 0.01 min over 20 two year simulations.

## The data

| Year | Flights | Carriers |
|---|---:|---:|
| 2015 | 5,819,079 | 14 |
| 2016 | 5,617,658 | 12 |
| 2017 | 5,674,621 | 12 |
| 2018 | 7,206,195 | 18 |
| 2019 | 7,422,037 | 17 |
| 2020 | 4,688,354 | 17 |
| 2021 | 5,995,397 | 17 |
| 2022 | 6,729,125 | 17 |
| 2023 | 6,847,899 | 15 |
| 2024 | 7,079,061 | 15 |
| 2025 | 7,001,619 | 14 |
| 2026 | 4,120,343 | 13 |

*Source: BTS Reporting Carrier On-Time Performance, every row of every monthly file in the window, as of 2026-10-01.*

| Rule | What it catches | Rows | Share | Excluded from |
|---|---|---:|---:|---|
| duplicate key | a second row with the same carrier, date, flight number, origin, destination and scheduled departure | 4 | 0.00% | everything |
| actual without scheduled | an actual departure, arrival or elapsed time with no scheduled time to measure it against | 2 | 0.00% | everything |
| impossible time | a negative taxi time, or an air time or an actual or scheduled elapsed time at or below zero or longer than the longest a domestic flight can take | 31 | 0.00% | everything |
| elapsed mismatch | actual elapsed time that differs from taxi out plus air time plus taxi in by more than the tolerance | 15 | 0.00% | everything |
| status conflict | a row flagged both cancelled and diverted, which cannot both have happened to one flight | 13 | 0.00% | everything |
| missing actual | a flight neither cancelled nor diverted that reports no departure delay, no arrival delay, no actual elapsed time or no air time | 974 | 0.00% | everything |
| cause mismatch | reported delay causes that do not sum to the arrival delay within the tolerance | 119 | 0.00% | the cause shares in chapter 6 |
| tail missing | no tail number on the row | 338,715 | 0.46% | the rotations of chapter 4 |
| tail format | a tail number that is not a valid FAA registration (N, a digit 1 to 9, at most two trailing letters) even after a missing leading N is restored, such as an airline's own fleet number | 1,142,859 | 1.54% | the registry join; the rotations keep the row, since the value still names one aircraft |
| revision | a row that a later download of the same month changed (the later kept, the change counted) | 0 | 0.00% | nothing; the earlier version is the one that is replaced |

*Source: BTS Reporting Carrier On-Time Performance, every row of every monthly file in the window, as of 2026-10-01.* The report by carrier and month is `results/marts/mart_quarantine.parquet`, shown on the data page.

The registry join matched 79.9% of tail numbers and 90.1% of flights; 1,905 tails had no record valid for the dates they flew (foreign registered, retired, reassigned or blanked). Weather: 3,085,200 hourly rows at 30 airports. Weather data by Open-Meteo.com, CC BY 4.0.

## The warehouse and the metric layer

18 models, 206 tests, 0 failed. 17 metrics, each defined over the flights and over the shipped mart, reconciled at 4 grains: 3,501 cells compared, 0 disagreements.

| Metric | Over the flights | Over the mart |
|---|---|---|
| scheduled flights | count(*) | sum(scheduled) |
| cancellation rate | avg(cancelled::int) | sum(cancelled) / sum(scheduled) |
| completion factor | 1 - avg(cancelled::int) | 1 - sum(cancelled) / sum(scheduled) |
| diversion rate | avg(diverted::int) | sum(diverted) / sum(scheduled) |
| on time rate | avg((arr_delay < 15)::int) filter (where not cancelled and not diverted) | sum(on_time) / sum(flown) |
| mean arrival delay | avg(arr_delay) filter (where not cancelled and not diverted) | sum(arr_delay_sum) / sum(flown) |
| median arrival delay | quantile_disc(least(greatest(arr_delay, -60), 300), 0.5) filter (where not cancelled and not diverted and arr_delay is not null) | median_from_histogram |
| mean scheduled block | avg(crs_elapsed) filter (where not cancelled and not diverted) | sum(crs_elapsed_sum) / sum(flown) |
| mean actual block | avg(actual_elapsed) filter (where not cancelled and not diverted) | sum(actual_elapsed_sum) / sum(flown) |
| mean padding | avg(padding) | sum(padding_sum) / sum(padding_flights) |
| padding share | sum(padding) / sum(crs_elapsed) filter (where padding is not null) | sum(padding_sum) / sum(padding_block_sum) |
| reported late aircraft share | sum(cause_late_aircraft) filter (where cause_ok) / sum(cause_late_aircraft + cause_carrier + cause_nas + cause_weather + cause_security) filter (where cause_ok) | sum(cause_late_aircraft_sum) / (sum(cause_late_aircraft_sum) + sum(cause_carrier_sum) + sum(cause_nas_sum) + sum(cause_weather_sum) + sum(cause_security_sum)) |
| reported carrier share | sum(cause_carrier) filter (where cause_ok) / sum(cause_late_aircraft + cause_carrier + cause_nas + cause_weather + cause_security) filter (where cause_ok) | sum(cause_carrier_sum) / (sum(cause_late_aircraft_sum) + sum(cause_carrier_sum) + sum(cause_nas_sum) + sum(cause_weather_sum) + sum(cause_security_sum)) |
| reported nas share | sum(cause_nas) filter (where cause_ok) / sum(cause_late_aircraft + cause_carrier + cause_nas + cause_weather + cause_security) filter (where cause_ok) | sum(cause_nas_sum) / (sum(cause_late_aircraft_sum) + sum(cause_carrier_sum) + sum(cause_nas_sum) + sum(cause_weather_sum) + sum(cause_security_sum)) |
| reported weather share | sum(cause_weather) filter (where cause_ok) / sum(cause_late_aircraft + cause_carrier + cause_nas + cause_weather + cause_security) filter (where cause_ok) | sum(cause_weather_sum) / (sum(cause_late_aircraft_sum) + sum(cause_carrier_sum) + sum(cause_nas_sum) + sum(cause_weather_sum) + sum(cause_security_sum)) |
| reported security share | sum(cause_security) filter (where cause_ok) / sum(cause_late_aircraft + cause_carrier + cause_nas + cause_weather + cause_security) filter (where cause_ok) | sum(cause_security_sum) / (sum(cause_late_aircraft_sum) + sum(cause_carrier_sum) + sum(cause_nas_sum) + sum(cause_weather_sum) + sum(cause_security_sum)) |
| inherited share | sum(inherited_minutes) / sum(arr_delay_pos) | sum(inherited_minutes_sum) / sum(arr_delay_pos_sum) |

## Chapter tables

### What on time measures

| Year | Flights flown | On time | Scheduled block, route panel | Actual block, route panel |
|---|---:|---:|---:|---:|
| 2015 | 5,714,008 | 81.4% | 143.9 min | 138.9 min |
| 2016 | 5,538,145 | 82.6% | 144.4 min | 139.1 min |
| 2017 | 5,579,409 | 81.5% | 145.3 min | 140.0 min |
| 2018 | 7,070,844 | 80.9% | 145.6 min | 140.6 min |
| 2019 | 7,268,231 | 80.9% | 146.4 min | 140.8 min |
| 2020 | 4,399,574 | 90.2% | 145.5 min | 137.9 min |
| 2021 | 5,878,210 | 82.8% | 145.8 min | 139.0 min |
| 2022 | 6,532,008 | 78.9% | 145.8 min | 140.0 min |
| 2023 | 6,743,402 | 79.4% | 146.7 min | 140.9 min |
| 2024 | 6,965,240 | 79.2% | 147.5 min | 141.9 min |
| 2025 | 6,879,483 | 77.7% | 148.5 min | 143.3 min |
| 2026 | 4,014,657 | 76.9% | not applicable | not applicable |

### Padding in the schedule

| Carrier | Month | Padding before | Padding after | Step |
|---|---|---:|---:|---:|
| Endeavor Air | 2020-04 | 20.9 min | 13.7 min | -7.2 min |
| Endeavor Air | 2020-08 | 13.7 min | 17.0 min | +3.4 min |
| Endeavor Air | 2021-02 | 17.0 min | 20.2 min | +3.2 min |
| Endeavor Air | 2021-08 | 20.2 min | 17.4 min | -2.8 min |
| Endeavor Air | 2022-06 | 17.4 min | 19.6 min | +2.2 min |
| Endeavor Air | 2023-04 | 19.6 min | 22.3 min | +2.7 min |
| Endeavor Air | 2024-01 | 22.3 min | 20.3 min | -2.0 min |
| American Airlines | 2015-04 | 15.8 min | 19.7 min | +3.9 min |
| American Airlines | 2015-12 | 19.7 min | 18.1 min | -1.6 min |
| American Airlines | 2016-09 | 18.1 min | 19.4 min | +1.3 min |
| American Airlines | 2017-11 | 19.4 min | 21.0 min | +1.6 min |
| American Airlines | 2018-09 | 21.0 min | 19.7 min | -1.3 min |
| American Airlines | 2019-06 | 19.7 min | 20.8 min | +1.1 min |
| American Airlines | 2020-06 | 20.8 min | 17.5 min | -3.3 min |
| American Airlines | 2020-11 | 17.5 min | 21.2 min | +3.7 min |
| American Airlines | 2021-02 | 21.2 min | 23.5 min | +2.3 min |
| American Airlines | 2021-05 | 23.5 min | 21.4 min | -2.2 min |
| American Airlines | 2022-02 | 21.4 min | 18.2 min | -3.2 min |
| American Airlines | 2023-05 | 18.2 min | 20.7 min | +2.5 min |
| American Airlines | 2024-09 | 20.7 min | 22.2 min | +1.5 min |
| American Airlines | 2025-03 | 22.2 min | 20.6 min | -1.5 min |
| American Airlines | 2025-09 | 20.6 min | 22.3 min | +1.7 min |
| American Airlines | 2026-02 | 22.3 min | 24.4 min | +2.1 min |
| Alaska Airlines | 2015-11 | 15.6 min | 17.3 min | +1.6 min |
| Alaska Airlines | 2016-03 | 17.3 min | 15.9 min | -1.3 min |
| Alaska Airlines | 2017-06 | 15.9 min | 18.2 min | +2.3 min |
| Alaska Airlines | 2017-12 | 18.2 min | 19.5 min | +1.3 min |
| Alaska Airlines | 2018-07 | 19.5 min | 20.7 min | +1.2 min |
| Alaska Airlines | 2019-06 | 20.7 min | 22.4 min | +1.8 min |
| Alaska Airlines | 2020-06 | 22.4 min | 15.3 min | -7.1 min |
| Alaska Airlines | 2020-10 | 15.3 min | 17.3 min | +2.0 min |
| Alaska Airlines | 2021-03 | 17.3 min | 19.0 min | +1.7 min |
| Alaska Airlines | 2021-06 | 19.0 min | 20.3 min | +1.3 min |
| Alaska Airlines | 2023-07 | 20.3 min | 21.8 min | +1.4 min |
| Alaska Airlines | 2025-01 | 20.8 min | 22.9 min | +2.1 min |
| Alaska Airlines | 2025-08 | 22.9 min | 24.1 min | +1.2 min |
| JetBlue Airways | 2016-09 | 18.4 min | 19.7 min | +1.3 min |
| JetBlue Airways | 2019-04 | 20.6 min | 22.9 min | +2.3 min |
| JetBlue Airways | 2019-10 | 22.9 min | 21.5 min | -1.4 min |
| JetBlue Airways | 2020-05 | 21.5 min | 12.2 min | -9.3 min |
| JetBlue Airways | 2020-09 | 12.2 min | 14.2 min | +1.9 min |
| JetBlue Airways | 2020-12 | 14.2 min | 12.2 min | -2.0 min |
| JetBlue Airways | 2021-03 | 12.2 min | 18.9 min | +6.7 min |
| JetBlue Airways | 2021-07 | 18.9 min | 20.9 min | +2.0 min |
| JetBlue Airways | 2023-01 | 20.9 min | 22.8 min | +1.9 min |
| JetBlue Airways | 2024-09 | 22.8 min | 24.4 min | +1.6 min |
| JetBlue Airways | 2025-11 | 24.4 min | 23.0 min | -1.4 min |
| Delta Air Lines | 2015-04 | 19.0 min | 20.2 min | +1.2 min |
| Delta Air Lines | 2016-04 | 20.2 min | 21.5 min | +1.4 min |
| Delta Air Lines | 2018-03 | 22.4 min | 19.7 min | -2.8 min |
| Delta Air Lines | 2018-06 | 19.7 min | 20.8 min | +1.1 min |
| Delta Air Lines | 2019-06 | 20.8 min | 19.4 min | -1.4 min |
| Delta Air Lines | 2020-04 | 19.4 min | 11.3 min | -8.1 min |
| Delta Air Lines | 2020-08 | 11.3 min | 12.8 min | +1.5 min |
| Delta Air Lines | 2021-01 | 12.8 min | 16.0 min | +3.2 min |
| Delta Air Lines | 2021-04 | 16.0 min | 19.4 min | +3.4 min |
| Delta Air Lines | 2021-09 | 19.4 min | 17.8 min | -1.6 min |
| Delta Air Lines | 2022-04 | 17.8 min | 19.1 min | +1.3 min |
| Delta Air Lines | 2023-03 | 19.1 min | 20.7 min | +1.6 min |
| Delta Air Lines | 2026-05 | 20.7 min | 21.9 min | +1.2 min |
| ExpressJet Airlines | 2015-06 | 12.8 min | 15.1 min | +2.3 min |
| ExpressJet Airlines | 2015-09 | 15.1 min | 13.6 min | -1.5 min |
| ExpressJet Airlines | 2016-01 | 13.6 min | 14.8 min | +1.2 min |
| ExpressJet Airlines | 2016-06 | 14.8 min | 17.5 min | +2.7 min |
| ExpressJet Airlines | 2016-09 | 17.5 min | 16.2 min | -1.3 min |
| ExpressJet Airlines | 2017-06 | 16.2 min | 17.9 min | +1.7 min |
| ExpressJet Airlines | 2017-09 | 17.9 min | 16.3 min | -1.7 min |
| ExpressJet Airlines | 2017-12 | 16.3 min | 17.6 min | +1.3 min |
| ExpressJet Airlines | 2018-09 | 17.6 min | 16.1 min | -1.5 min |
| ExpressJet Airlines | 2019-01 | 16.1 min | 17.8 min | +1.6 min |
| ExpressJet Airlines | 2019-09 | 17.8 min | 19.5 min | +1.7 min |
| ExpressJet Airlines | 2020-06 | 19.5 min | 14.1 min | -5.3 min |
| Frontier Airlines | 2015-09 | 14.3 min | 18.2 min | +3.9 min |
| Frontier Airlines | 2016-01 | 18.2 min | 23.1 min | +4.9 min |
| Frontier Airlines | 2016-06 | 23.1 min | 19.8 min | -3.3 min |
| Frontier Airlines | 2016-10 | 19.8 min | 22.4 min | +2.5 min |
| Frontier Airlines | 2019-02 | 22.4 min | 24.2 min | +1.9 min |
| Frontier Airlines | 2020-04 | 24.2 min | 22.3 min | -1.9 min |
| Frontier Airlines | 2020-07 | 22.3 min | 20.1 min | -2.3 min |
| Frontier Airlines | 2021-05 | 20.1 min | 23.4 min | +3.3 min |
| Frontier Airlines | 2022-02 | 23.4 min | 21.1 min | -2.3 min |
| Frontier Airlines | 2022-06 | 21.1 min | 23.6 min | +2.5 min |
| Frontier Airlines | 2023-10 | 23.6 min | 25.4 min | +1.7 min |
| Frontier Airlines | 2024-06 | 25.4 min | 23.8 min | -1.5 min |
| Frontier Airlines | 2025-02 | 23.8 min | 26.1 min | +2.2 min |
| Frontier Airlines | 2026-03 | 26.1 min | 27.9 min | +1.9 min |
| Allegiant Air | 2018-12 | 13.6 min | 11.6 min | -2.0 min |
| Allegiant Air | 2019-03 | 11.6 min | 13.3 min | +1.7 min |
| Allegiant Air | 2019-12 | 13.3 min | 10.9 min | -2.4 min |
| Allegiant Air | 2020-06 | 10.9 min | 12.7 min | +1.9 min |
| Allegiant Air | 2020-11 | 12.7 min | 11.2 min | -1.5 min |
| Allegiant Air | 2022-06 | 11.2 min | 13.3 min | +2.1 min |
| Allegiant Air | 2023-01 | 13.3 min | 14.8 min | +1.6 min |
| Allegiant Air | 2023-11 | 14.8 min | 18.4 min | +3.6 min |
| Allegiant Air | 2024-06 | 18.4 min | 17.0 min | -1.5 min |
| Allegiant Air | 2024-12 | 17.0 min | 18.7 min | +1.7 min |
| Allegiant Air | 2025-04 | 18.7 min | 16.1 min | -2.6 min |
| Allegiant Air | 2026-01 | 16.1 min | 17.4 min | +1.3 min |
| Hawaiian Airlines | 2015-07 | 5.5 min | 7.1 min | +1.6 min |
| Hawaiian Airlines | 2015-11 | 7.1 min | 8.3 min | +1.3 min |
| Hawaiian Airlines | 2016-11 | 9.0 min | 7.8 min | -1.3 min |
| Hawaiian Airlines | 2017-06 | 7.8 min | 9.5 min | +1.8 min |
| Hawaiian Airlines | 2020-06 | 11.0 min | 8.7 min | -2.2 min |
| Hawaiian Airlines | 2021-01 | 8.7 min | 11.1 min | +2.3 min |
| Hawaiian Airlines | 2024-06 | 11.3 min | 10.1 min | -1.2 min |
| Hawaiian Airlines | 2025-02 | 11.0 min | 9.8 min | -1.2 min |
| Hawaiian Airlines | 2025-10 | 9.8 min | 10.9 min | +1.1 min |
| Envoy Air | 2015-04 | 11.3 min | 15.6 min | +4.4 min |
| Envoy Air | 2019-06 | 15.6 min | 16.7 min | +1.1 min |
| Envoy Air | 2020-06 | 16.7 min | 12.9 min | -3.8 min |
| Envoy Air | 2020-10 | 12.9 min | 15.7 min | +2.8 min |
| Envoy Air | 2021-01 | 15.7 min | 20.5 min | +4.8 min |
| Envoy Air | 2021-05 | 20.5 min | 18.0 min | -2.5 min |
| Envoy Air | 2022-04 | 18.0 min | 16.1 min | -1.9 min |
| Envoy Air | 2023-08 | 16.1 min | 18.5 min | +2.4 min |
| Envoy Air | 2024-01 | 18.5 min | 17.2 min | -1.3 min |
| Envoy Air | 2024-09 | 17.2 min | 18.5 min | +1.3 min |
| Envoy Air | 2025-02 | 18.5 min | 17.2 min | -1.3 min |
| Envoy Air | 2025-07 | 17.2 min | 19.3 min | +2.1 min |
| Envoy Air | 2026-01 | 19.3 min | 21.0 min | +1.7 min |
| Envoy Air | 2026-04 | 21.0 min | 23.1 min | +2.1 min |
| Spirit Airlines | 2016-05 | 15.4 min | 17.0 min | +1.6 min |
| Spirit Airlines | 2017-09 | 17.0 min | 19.3 min | +2.3 min |
| Spirit Airlines | 2018-06 | 19.3 min | 17.7 min | -1.6 min |
| Spirit Airlines | 2018-10 | 17.7 min | 20.4 min | +2.7 min |
| Spirit Airlines | 2020-06 | 20.4 min | 18.4 min | -1.9 min |
| Spirit Airlines | 2020-09 | 18.4 min | 14.5 min | -3.9 min |
| Spirit Airlines | 2021-05 | 14.5 min | 19.3 min | +4.8 min |
| Spirit Airlines | 2022-01 | 19.3 min | 16.6 min | -2.7 min |
| Spirit Airlines | 2022-06 | 16.6 min | 21.6 min | +4.9 min |
| Spirit Airlines | 2022-09 | 21.6 min | 19.5 min | -2.1 min |
| Spirit Airlines | 2023-09 | 19.5 min | 21.6 min | +2.1 min |
| Spirit Airlines | 2025-05 | 21.6 min | 20.6 min | -1.0 min |
| Spirit Airlines | 2026-03 | 20.6 min | 18.3 min | -2.3 min |
| PSA Airlines | 2018-06 | 14.9 min | 16.9 min | +2.0 min |
| PSA Airlines | 2019-08 | 16.9 min | 18.1 min | +1.3 min |
| PSA Airlines | 2020-06 | 18.1 min | 15.1 min | -3.0 min |
| PSA Airlines | 2020-11 | 15.1 min | 17.8 min | +2.7 min |
| PSA Airlines | 2021-02 | 17.8 min | 21.9 min | +4.0 min |
| PSA Airlines | 2021-05 | 21.9 min | 18.8 min | -3.0 min |
| PSA Airlines | 2022-02 | 18.8 min | 17.7 min | -1.1 min |
| PSA Airlines | 2022-12 | 17.7 min | 19.1 min | +1.4 min |
| PSA Airlines | 2023-08 | 19.1 min | 20.5 min | +1.3 min |
| PSA Airlines | 2024-03 | 20.5 min | 19.0 min | -1.5 min |
| PSA Airlines | 2024-06 | 19.0 min | 21.2 min | +2.2 min |
| PSA Airlines | 2025-02 | 21.2 min | 19.3 min | -1.9 min |
| PSA Airlines | 2025-07 | 19.3 min | 21.4 min | +2.1 min |
| PSA Airlines | 2026-01 | 21.4 min | 22.8 min | +1.5 min |
| PSA Airlines | 2026-05 | 22.8 min | 24.4 min | +1.6 min |
| SkyWest Airlines | 2015-04 | 13.4 min | 15.4 min | +2.1 min |
| SkyWest Airlines | 2016-04 | 14.6 min | 16.8 min | +2.2 min |
| SkyWest Airlines | 2017-08 | 17.7 min | 18.8 min | +1.2 min |
| SkyWest Airlines | 2018-12 | 18.8 min | 20.1 min | +1.2 min |
| SkyWest Airlines | 2019-12 | 20.1 min | 21.4 min | +1.3 min |
| SkyWest Airlines | 2020-04 | 21.4 min | 16.4 min | -5.0 min |
| SkyWest Airlines | 2021-01 | 16.4 min | 18.6 min | +2.3 min |
| SkyWest Airlines | 2021-06 | 18.6 min | 17.5 min | -1.1 min |
| SkyWest Airlines | 2021-11 | 17.5 min | 18.7 min | +1.2 min |
| SkyWest Airlines | 2023-05 | 18.7 min | 19.8 min | +1.1 min |
| SkyWest Airlines | 2024-12 | 20.7 min | 22.0 min | +1.2 min |
| SkyWest Airlines | 2025-08 | 22.0 min | 23.2 min | +1.2 min |
| SkyWest Airlines | 2026-01 | 23.2 min | 24.2 min | +1.0 min |
| SkyWest Airlines | 2026-04 | 24.2 min | 25.6 min | +1.4 min |
| United Airlines | 2015-07 | 20.8 min | 22.6 min | +1.7 min |
| United Airlines | 2016-09 | 22.6 min | 21.0 min | -1.5 min |
| United Airlines | 2018-04 | 21.8 min | 18.9 min | -2.9 min |
| United Airlines | 2018-09 | 18.9 min | 17.8 min | -1.1 min |
| United Airlines | 2019-01 | 17.8 min | 19.5 min | +1.7 min |
| United Airlines | 2019-06 | 19.5 min | 20.9 min | +1.4 min |
| United Airlines | 2020-01 | 20.9 min | 21.9 min | +1.0 min |
| United Airlines | 2020-06 | 21.9 min | 20.4 min | -1.4 min |
| United Airlines | 2020-11 | 20.4 min | 18.2 min | -2.2 min |
| United Airlines | 2021-06 | 18.2 min | 16.5 min | -1.7 min |
| United Airlines | 2021-09 | 16.5 min | 21.6 min | +5.0 min |
| United Airlines | 2023-08 | 21.6 min | 23.3 min | +1.8 min |
| United Airlines | 2024-11 | 23.3 min | 25.0 min | +1.7 min |
| United Airlines | 2025-12 | 25.0 min | 26.2 min | +1.2 min |
| United Airlines | 2026-04 | 26.2 min | 27.4 min | +1.3 min |
| Virgin America | 2016-10 | 18.1 min | 16.6 min | -1.5 min |
| Virgin America | 2017-05 | 16.6 min | 20.2 min | +3.6 min |
| Virgin America | 2018-01 | 20.2 min | 23.3 min | +3.1 min |
| Southwest Airlines | 2016-03 | 15.1 min | 14.0 min | -1.1 min |
| Southwest Airlines | 2017-01 | 14.7 min | 13.6 min | -1.1 min |
| Southwest Airlines | 2017-05 | 13.6 min | 15.2 min | +1.6 min |
| Southwest Airlines | 2019-01 | 15.5 min | 16.8 min | +1.3 min |
| Southwest Airlines | 2026-01 | 18.2 min | 19.3 min | +1.1 min |
| Mesa Airlines | 2018-09 | 16.2 min | 14.6 min | -1.6 min |
| Mesa Airlines | 2019-06 | 14.6 min | 16.5 min | +1.9 min |
| Mesa Airlines | 2020-06 | 16.5 min | 13.6 min | -2.9 min |
| Mesa Airlines | 2020-09 | 13.6 min | 16.8 min | +3.2 min |
| Mesa Airlines | 2021-01 | 16.8 min | 18.8 min | +2.1 min |
| Mesa Airlines | 2021-05 | 18.8 min | 17.4 min | -1.4 min |
| Mesa Airlines | 2022-06 | 17.4 min | 18.8 min | +1.3 min |
| Mesa Airlines | 2022-09 | 18.8 min | 17.3 min | -1.5 min |
| Republic Airways | 2020-05 | 22.3 min | 19.6 min | -2.7 min |
| Republic Airways | 2021-01 | 19.6 min | 21.6 min | +2.0 min |
| Republic Airways | 2021-06 | 21.6 min | 18.7 min | -2.9 min |
| Republic Airways | 2021-09 | 18.7 min | 20.0 min | +1.3 min |
| Republic Airways | 2022-02 | 20.0 min | 21.0 min | +1.0 min |
| Republic Airways | 2022-08 | 21.0 min | 22.5 min | +1.4 min |
| Republic Airways | 2023-05 | 22.5 min | 23.7 min | +1.2 min |
| Republic Airways | 2024-01 | 23.7 min | 22.4 min | -1.3 min |
| Republic Airways | 2025-07 | 22.4 min | 24.2 min | +1.8 min |
| Republic Airways | 2026-04 | 24.2 min | 26.4 min | +2.2 min |

| Carrier | Padding 2015 | Padding 2025 |
|---|---:|---:|
| American Airlines | 19.3 min | 21.0 min |
| Alaska Airlines | 14.4 min | 23.9 min |
| JetBlue Airways | 17.9 min | 24.8 min |
| Delta Air Lines | 19.4 min | 21.0 min |
| ExpressJet Airlines | 13.6 min | not applicable |
| Frontier Airlines | 14.9 min | 26.5 min |
| Allegiant Air | not applicable | 17.0 min |
| Hawaiian Airlines | 5.4 min | 11.2 min |
| Envoy Air | 14.3 min | 18.6 min |
| Spirit Airlines | 14.3 min | 21.3 min |
| PSA Airlines | not applicable | 21.1 min |
| SkyWest Airlines | 14.4 min | 22.5 min |
| United Airlines | 22.5 min | 24.7 min |
| US Airways | 17.0 min | not applicable |
| Virgin America | 17.4 min | not applicable |
| Southwest Airlines | 15.4 min | 18.6 min |
| Republic Airways | not applicable | 23.8 min |

### The fifteen minute line

| Carrier | Flights | Excess below the line | z against placebos | p | q (BH) | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Endeavor Air | 387,398 | -3.43% | -0.62 | 0.731 | 0.901 | no evidence |
| American Airlines | 3,332,776 | -3.17% | -1.01 | 0.844 | 0.901 | no evidence |
| Alaska Airlines | 911,872 | -4.47% | -0.86 | 0.805 | 0.901 | no evidence |
| JetBlue Airways | 844,465 | -2.07% | 0.52 | 0.300 | 0.901 | no evidence |
| Delta Air Lines | 3,523,945 | -3.65% | -1.29 | 0.901 | 0.901 | no evidence |
| Frontier Airlines | 678,896 | -1.87% | 1.23 | 0.109 | 0.901 | no evidence |
| Allegiant Air | 425,967 | -2.46% | 0.37 | 0.357 | 0.901 | no evidence |
| Hawaiian Airlines | 235,487 | -16.66% | -0.81 | 0.790 | 0.901 | no evidence |
| Envoy Air | 964,863 | -4.21% | -1.13 | 0.871 | 0.901 | no evidence |
| Spirit Airlines | 735,456 | -3.20% | -0.06 | 0.523 | 0.901 | no evidence |
| PSA Airlines | 766,415 | -1.91% | -0.66 | 0.746 | 0.901 | no evidence |
| SkyWest Airlines | 2,665,217 | -6.34% | -0.65 | 0.742 | 0.901 | no evidence |
| United Airlines | 2,685,323 | -3.81% | -1.06 | 0.856 | 0.901 | no evidence |
| Southwest Airlines | 4,966,276 | -3.31% | -1.24 | 0.893 | 0.901 | no evidence |
| Republic Airways | 1,106,683 | -2.69% | 0.32 | 0.374 | 0.901 | no evidence |

### Inherited delay

72,583,211 legs, 54,431,369 linked (75.0%), 10,019 first legs, 17,170,752 gaps, 369,126 broken chains, 601,945 impossible sequences; 18,151,842 rotations on 10,019 tails. Minimum turn 45 min, profiled on 2022; halving buffer 30 min.

| Scheduled turn | Legs | Minutes passed on per late minute | Low | High |
|---|---:|---:|---:|---:|
| 0 to 30 min | 223,551 | 1.50 | 1.48 | 1.53 |
| 30 to 40 min | 1,747,421 | 1.09 | 1.09 | 1.10 |
| 40 to 50 min | 3,901,417 | 1.04 | 1.04 | 1.05 |
| 50 to 60 min | 3,970,697 | 1.04 | 1.04 | 1.04 |
| 60 to 75 min | 4,338,922 | 0.96 | 0.95 | 0.96 |
| 75 to 90 min | 1,573,575 | 0.81 | 0.81 | 0.82 |
| 90 to 120 min | 1,111,771 | 0.65 | 0.65 | 0.66 |
| 120 to 180 min | 712,102 | 0.43 | 0.43 | 0.44 |
| 180 to 300 min | 428,630 | 0.26 | 0.25 | 0.26 |

### The fair ranking

| Carrier | Flights | Raw rank | Raw effect | Adjusted rank | Adjusted effect | Interval | Moved |
|---|---:|---:|---:|---:|---:|---|---|
| Endeavor Air | 391,977 | 1 | -7.39 min | 1 | -13.14 min | -14.14 to -12.14 min | same |
| Republic Airways | 1,119,192 | 2 | -6.26 min | 2 | -8.70 min | -9.36 to -8.03 min | same |
| Envoy Air | 975,162 | 5 | -2.36 min | 3 | -6.10 min | -6.78 to -5.42 min | up 2 |
| Delta Air Lines | 3,572,228 | 4 | -3.63 min | 4 | -2.92 min | -3.26 to -2.58 min | same |
| United Airlines | 2,729,655 | 7 | -1.18 min | 5 | -2.55 min | -2.90 to -2.21 min | up 2 |
| SkyWest Airlines | 2,713,958 | 9 | +0.16 min | 6 | -2.38 min | -3.00 to -1.76 min | up 3 |
| PSA Airlines | 784,660 | 11 | +4.19 min | 7 | -1.58 min | -2.44 to -0.71 min | up 4 |
| Southwest Airlines | 5,003,261 | 6 | -1.63 min | 8 | +1.71 min | +1.40 to +2.02 min | down 2 |
| Alaska Airlines | 918,478 | 3 | -3.98 min | 9 | +2.78 min | +2.39 to +3.16 min | down 6 |
| Spirit Airlines | 749,263 | 10 | +3.14 min | 10 | +3.09 min | +2.52 to +3.66 min | same |
| JetBlue Airways | 866,026 | 13 | +5.99 min | 11 | +3.76 min | +3.17 to +4.35 min | up 2 |
| American Airlines | 3,411,235 | 14 | +6.18 min | 12 | +5.17 min | +4.83 to +5.50 min | up 2 |
| Allegiant Air | 435,740 | 12 | +5.56 min | 13 | +6.86 min | +5.71 to +8.01 min | down 1 |
| Frontier Airlines | 695,137 | 15 | +8.03 min | 14 | +8.54 min | +7.99 to +9.10 min | up 1 |
| Hawaiian Airlines | 236,810 | 8 | -0.66 min | 15 | +11.42 min | +10.61 to +12.24 min | down 7 |

Raw top three: Endeavor Air, Republic Airways, Alaska Airlines; raw bottom three: JetBlue Airways, American Airlines, Frontier Airlines. Adjusted top three: Endeavor Air, Republic Airways, Envoy Air; adjusted bottom three: Allegiant Air, Frontier Airlines, Hawaiian Airlines.

### Causes, reported and estimated

| Year | Late aircraft | Carrier | Air traffic system | Weather | Security |
|---|---:|---:|---:|---:|---:|
| 2015 | 0.0% | 0.0% | 0.0% | 0.0% | 0.00% |
| 2016 | 0.0% | 0.0% | 0.0% | 0.0% | 0.00% |
| 2017 | 0.0% | 0.0% | 0.0% | 0.0% | 0.00% |
| 2018 | 0.0% | 0.0% | 0.0% | 0.0% | 0.00% |
| 2019 | 0.0% | 0.0% | 0.0% | 0.0% | 0.00% |
| 2020 | 0.0% | 0.0% | 0.0% | 0.0% | 0.00% |
| 2021 | 0.0% | 0.0% | 0.0% | 0.0% | 0.00% |
| 2022 | 0.0% | 0.0% | 0.0% | 0.0% | 0.00% |
| 2023 | 0.0% | 0.0% | 0.0% | 0.0% | 0.00% |
| 2024 | 0.0% | 0.0% | 0.0% | 0.0% | 0.00% |
| 2025 | 0.0% | 0.0% | 0.0% | 0.0% | 0.00% |
| 2026 | 0.0% | 0.0% | 0.0% | 0.0% | 0.00% |

| Airport | Flights | Air traffic system share of cause minutes | Air traffic minutes per flight |
|---|---:|---:|---:|
| EWR | 443,734 | 42.3% | 8.01 min |
| SFO | 495,273 | 37.4% | 6.87 min |
| LGA | 520,330 | 33.6% | 5.76 min |
| BOS | 500,000 | 27.9% | 5.20 min |
| FLL | 317,257 | 27.5% | 5.24 min |
| DEN | 1,084,241 | 26.1% | 3.97 min |
| LAS | 655,655 | 25.9% | 3.77 min |
| JFK | 407,827 | 25.6% | 4.82 min |
| MCO | 568,263 | 25.5% | 4.73 min |
| ORD | 1,054,904 | 25.3% | 4.84 min |

| Weather term | Minutes | Standard error |
|---|---:|---:|
| origin precip | +3.95 min | 0.15 |
| origin snow | +50.33 min | 4.83 |
| origin gust | +0.35 min | 0.03 |
| origin low cloud | +3.28 min | 0.22 |
| dest precip | +3.66 min | 0.14 |
| dest snow | +16.60 min | 2.79 |
| dest gust | +0.45 min | 0.03 |
| dest low cloud | +4.54 min | 0.22 |

### Meltdowns and recovery

| Event | Onset | Window | Units | Flagged | First alert | Days after onset |
|---|---|---|---|---|---|---:|
| Boeing 737 MAX grounding | 2019-03-13 | fitting | WN;AA;UA | yes | 2019-03-13 | 0 |
| COVID-19 collapse in air travel | 2020-03-15 | fitting | all | yes | 2020-03-17 | 2 |
| Winter Storm Uri in Texas | 2021-02-14 | fitting | DFW;DAL;IAH;HOU;AUS;SAT | yes | 2021-02-14 | 0 |
| Southwest scheduling crisis | 2022-12-21 | fitting | WN | yes | 2022-12-22 | 1 |
| Winter Storm Elliott | 2022-12-21 | fitting | all | yes | 2022-12-22 | 1 |
| FAA NOTAM system outage | 2023-01-11 | reporting | all | yes | 2023-01-11 | 0 |
| Alaska 1282 and the 737-9 grounding | 2024-01-06 | reporting | AS;UA | yes | 2024-01-06 | 0 |
| CrowdStrike outage and Delta's recovery | 2024-07-19 | reporting | DL | yes | 2024-07-19 | 0 |
| Hurricane Milton | 2024-10-08 | reporting | TPA;MCO;SRQ;RSW;PIE;SFB | yes | 2024-10-08 | 0 |
| Newark radar outages and flight caps | 2025-04-28 | reporting | EWR | yes | 2025-05-01 | 3 |
| Alaska Airlines IT outage and ground stop | 2025-10-23 | reporting | AS | yes | 2025-10-23 | 0 |
| FAA flight reductions during the federal shutdown | 2025-11-07 | reporting | all | yes | 2025-11-08 | 1 |
| January 2026 winter storm | 2026-01-24 | reporting | all | yes | 2026-01-24 | 0 |

Threshold 29.0, chosen from 3.0 to 30.0 with a false alarm costed at 1.0 and a miss at 50.0, inside the grid. Fitting years: 5 of 5 events flagged, 609 false alarm episodes. Reporting years: 8 of 8, 297 false alarm episodes over 57,980 unit days.

| Carrier | Alert episodes | Median days | Mean days | Longest |
|---|---:|---:|---:|---:|
| US Airways | 1 | 1.0 days | 1.0 days | 1 |
| Virgin America | 4 | 1.0 days | 1.2 days | 2 |
| Endeavor Air | 34 | 1.0 days | 1.7 days | 10 |
| Republic Airways | 42 | 1.0 days | 1.9 days | 11 |
| Envoy Air | 25 | 1.0 days | 2.0 days | 10 |
| Alaska Airlines | 9 | 1.0 days | 2.4 days | 10 |
| ExpressJet Airlines | 10 | 1.0 days | 2.5 days | 11 |
| American Airlines | 14 | 1.5 days | 2.6 days | 9 |
| JetBlue Airways | 34 | 2.0 days | 2.0 days | 6 |
| PSA Airlines | 23 | 2.0 days | 2.4 days | 11 |
| Delta Air Lines | 20 | 2.0 days | 2.5 days | 12 |
| United Airlines | 20 | 2.0 days | 2.7 days | 13 |
| Frontier Airlines | 13 | 2.0 days | 2.8 days | 14 |
| Southwest Airlines | 9 | 2.0 days | 2.9 days | 8 |
| Allegiant Air | 13 | 2.0 days | 3.2 days | 14 |
| SkyWest Airlines | 4 | 2.0 days | 3.8 days | 10 |
| Spirit Airlines | 16 | 2.5 days | 2.8 days | 7 |
| Horizon Air | 2 | 3.0 days | 3.0 days | 3 |
| Mesa Airlines | 4 | 4.0 days | 5.2 days | 12 |
| Hawaiian Airlines | 6 | 5.0 days | 6.5 days | 14 |

### The reader's decision

| Leg of the aircraft's day | Flights | On time | Mean arrival delay |
|---|---:|---:|---:|
| first | 6,125,514 | 85.8% | +1.6 min |
| 2 | 5,652,823 | 80.7% | +5.1 min |
| 3 | 4,813,482 | 77.2% | +8.5 min |
| 4 | 3,809,323 | 73.4% | +11.9 min |
| 5 | 2,289,445 | 71.1% | +14.3 min |
| sixth or later | 1,912,195 | 70.5% | +15.5 min |

| Scheduled departure hour | Flights | On time | Mean arrival delay |
|---|---:|---:|---:|
| 00:00 | 39,810 | 81.0% | +3.9 min |
| 01:00 | 13,241 | 78.9% | +7.2 min |
| 02:00 | 5,206 | 78.7% | +4.7 min |
| 03:00 | 2,823 | 79.0% | +5.6 min |
| 04:00 | 1,338 | 81.0% | +5.6 min |
| 05:00 | 697,963 | 91.2% | -2.5 min |
| 06:00 | 1,723,394 | 90.1% | -2.0 min |
| 07:00 | 1,746,305 | 87.5% | -0.5 min |
| 08:00 | 1,678,437 | 85.8% | +0.2 min |
| 09:00 | 1,386,438 | 84.4% | +1.5 min |
| 10:00 | 1,539,031 | 83.1% | +2.7 min |
| 11:00 | 1,530,312 | 81.5% | +4.3 min |
| 12:00 | 1,463,645 | 79.8% | +6.2 min |
| 13:00 | 1,469,118 | 77.8% | +8.1 min |
| 14:00 | 1,404,527 | 75.5% | +10.6 min |
| 15:00 | 1,412,408 | 73.8% | +11.9 min |
| 16:00 | 1,409,368 | 71.8% | +13.9 min |
| 17:00 | 1,531,812 | 70.8% | +15.1 min |
| 18:00 | 1,481,515 | 69.8% | +15.8 min |
| 19:00 | 1,339,271 | 69.1% | +16.3 min |
| 20:00 | 1,101,173 | 68.8% | +16.2 min |
| 21:00 | 830,489 | 71.1% | +14.5 min |
| 22:00 | 584,916 | 71.9% | +14.0 min |
| 23:00 | 210,242 | 78.4% | +6.8 min |

| Day | Flights | On time | Mean arrival delay |
|---|---:|---:|---:|
| Monday | 3,671,692 | 77.9% | +8.5 min |
| Tuesday | 3,366,061 | 81.8% | +4.1 min |
| Wednesday | 3,414,732 | 80.7% | +5.1 min |
| Thursday | 3,665,969 | 77.5% | +8.4 min |
| Friday | 3,687,043 | 76.7% | +9.4 min |
| Saturday | 3,175,920 | 79.3% | +6.7 min |
| Sunday | 3,621,365 | 75.8% | +10.6 min |

| Month | Flights | On time | Mean arrival delay |
|---|---:|---:|---:|
| January | 2,092,057 | 78.6% | +7.1 min |
| February | 2,006,887 | 81.2% | +3.7 min |
| March | 2,341,501 | 77.9% | +7.9 min |
| April | 2,296,099 | 79.6% | +6.2 min |
| May | 2,376,574 | 77.6% | +8.6 min |
| June | 2,358,739 | 73.5% | +13.4 min |
| July | 2,423,845 | 71.1% | +16.9 min |
| August | 1,790,178 | 77.4% | +9.4 min |
| September | 1,697,477 | 83.1% | +2.9 min |
| October | 1,806,087 | 83.6% | +1.8 min |
| November | 1,689,641 | 83.8% | +1.6 min |
| December | 1,723,697 | 78.8% | +6.9 min |

| Hub | Days | Inbound flights | Buffer for under the line | Interval | Interior |
|---|---:|---:|---:|---|---|
| ATL | 1,308 | 1,157,986 | 65 min | 60 to 65 min | yes |
| DEN | 1,308 | 1,084,241 | 70 min | 65 to 70 min | yes |
| DFW | 1,308 | 1,065,628 | 90 min | 85 to 95 min | yes |
| ORD | 1,308 | 1,054,904 | 85 min | 80 to 90 min | yes |
| CLT | 1,308 | 699,850 | 70 min | 70 to 75 min | yes |
| LAX | 1,308 | 682,774 | 65 min | 65 to 65 min | yes |
| PHX | 1,308 | 679,013 | 65 min | 65 to 65 min | yes |
| LAS | 1,308 | 655,655 | 70 min | 70 to 70 min | yes |
| SEA | 1,308 | 580,344 | 60 min | 60 to 60 min | yes |
| MCO | 1,306 | 568,235 | 85 min | 80 to 85 min | yes |
| LGA | 1,307 | 520,330 | 95 min | 90 to 100 min | yes |
| BOS | 1,307 | 499,992 | 90 min | 85 to 95 min | yes |
| DCA | 1,307 | 489,825 | 90 min | 85 to 95 min | yes |
| SFO | 1,308 | 495,273 | 85 min | 80 to 85 min | yes |
| EWR | 1,307 | 443,733 | 100 min | 90 to 105 min | yes |
| DTW | 1,308 | 443,573 | 70 min | 70 to 75 min | yes |
| MSP | 1,308 | 423,542 | 65 min | 60 to 65 min | yes |
| JFK | 1,307 | 407,822 | 90 min | 85 to 95 min | yes |
| IAH | 1,307 | 406,830 | 70 min | 70 to 75 min | yes |
| SLC | 1,308 | 405,229 | 55 min | 55 to 60 min | yes |

| Airport | Turns | Turns reached by a late inbound | Arrival minutes saved per buffer minute | Pays |
|---|---:|---:|---:|---|
| LAS | 533,550 | 27.4% | 0.51 | no |
| DCA | 387,349 | 26.9% | 0.49 | no |
| SFO | 370,543 | 22.7% | 0.42 | no |
| PHX | 539,049 | 22.7% | 0.41 | no |
| MCO | 408,264 | 23.5% | 0.41 | no |
| LGA | 396,699 | 23.7% | 0.39 | no |
| BOS | 353,516 | 22.2% | 0.38 | no |
| DEN | 902,923 | 20.5% | 0.36 | no |
| DFW | 828,718 | 19.4% | 0.34 | no |
| CLT | 575,566 | 18.4% | 0.33 | no |
| ORD | 832,811 | 19.3% | 0.33 | no |
| LAX | 504,858 | 16.9% | 0.31 | no |
| SEA | 454,435 | 15.7% | 0.29 | no |
| JFK | 265,301 | 16.7% | 0.28 | no |
| SLC | 328,749 | 15.0% | 0.28 | no |
| DTW | 341,320 | 14.9% | 0.27 | no |
| EWR | 297,671 | 16.8% | 0.27 | no |
| IAH | 265,610 | 16.4% | 0.27 | no |
| ATL | 937,385 | 14.2% | 0.26 | no |
| MSP | 330,168 | 14.2% | 0.26 | no |

| Route | Turns | Turns reached by a late inbound | Arrival minutes saved per buffer minute | Pays |
|---|---:|---:|---:|---|
| KOA-LIH | 1,278 | 82.6% | 2.16 | yes |
| OGG-ITO | 1,431 | 91.4% | 1.80 | yes |
| OGG-KOA | 5,236 | 75.8% | 1.78 | yes |
| OGG-LIH | 5,197 | 74.3% | 1.73 | yes |
| LIH-OGG | 4,672 | 70.8% | 1.72 | yes |
| LIH-HNL | 25,488 | 75.0% | 1.64 | yes |
| KOA-OGG | 4,596 | 66.3% | 1.64 | yes |
| HHH-CLT | 3,537 | 76.2% | 1.60 | yes |
| ABI-DFW | 3,481 | 78.3% | 1.59 | yes |
| ITO-HNL | 19,872 | 71.1% | 1.51 | yes |

## Latency

The live load test has not run yet.
## Limitations

- **The weather covers thirty airports.** The weather estimate uses flights between two of the FAA's Core 30 airports, which carry most of the traffic and most of the weather delay but not the regional airports where a storm can close the only runway. It is also airport weather at the scheduled hours, not weather along the route, so it is a floor on weather's share.
- **Inherited delay rests on tail numbers.** An aircraft swap at the same airport inside one turn is invisible, and the chain rules split only the swaps that break the airport sequence. The simulator plants swaps; the real swap rate is unknown.
- **The propagation interval is narrower than the uncertainty.** On the simulator rho was biased by +0.012 at weak propagation and its interval covered the truth in 18% of runs; the published interval carries sampling error only.
- **The fair ranking holds constant what the data records.** Spare aircraft, reserve crews and turn standards are the carrier's own choices and are charged to the carrier; they are not in the data.
- **The density test sees arrivals, not schedules.** Managing to the line by lengthening the schedule shows up in the padding chapter, not in the test at the line.
- **The detector is graded against a short table.** 8 reporting year events with citations; disruptions not in the table count as false alarms, which overstates the false alarm rate.
- **Missed connections ignore protection.** The curve treats every inbound and outbound pair the same; airlines hold flights for connecting passengers and rebook the rest, and the minimum connection time is one number for every hub.
- **Reported causes are reported.** The cause fields are filled by the carriers under rules that keep the weather field for extreme weather; the chapter compares them with an estimate, it does not correct them.
