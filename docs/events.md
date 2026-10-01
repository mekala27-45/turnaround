# Events and the alert operating point

The disruption detector in `packages/events`, which the meltdowns chapter of the story reads. It answers one operational question: on which carrier days and airport days did the operation break, and how fast did it come back.

> Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the public record; no individual traveler appears. The findings are a portfolio analysis, not an official ranking and not travel advice.

## The units and the baseline

Two kinds of unit are scored every day: each carrier, and each of the 30 busiest airports. A unit's baseline is its own previous four weeks: the median of its daily cancellation rate and of its mean arrival delay, with the median absolute deviation as the spread and a floor under the spread so a quiet month does not turn a normal Tuesday into an alarm. The day's score is the larger of the two standardized anomalies. Medians, not means, because one meltdown inside the baseline window would otherwise lift the baseline and hide the next one.

## The persistence rule

An alert episode opens on a day whose score passes the threshold and stays open while the score stays above half of it. One storm is one episode however many days it lasts, so a false alarm is counted once rather than once per day, and the length of the episode is the unit's recovery time.

## The operating point

The threshold is a cost decision, not a statistic. A missed disruption is costed at 50.0 false alarm episodes and each false alarm episode at 1.0: an operations desk will put up with a page every few weeks to avoid missing the one that strands a fleet. The threshold minimizing that cost on 2015 to 2022, over a grid from 3.0 to 30.0, is 29.0, inside the grid.

| Threshold | Cost |
|---:|---:|
| 3.0 | 9,617.0 |
| 4.0 | 7,315.0 |
| 5.0 | 5,817.0 |
| 6.0 | 4,805.0 |
| 7.0 | 4,076.0 |
| 8.0 | 3,522.0 |
| 9.0 | 3,069.0 |
| 10.0 | 2,690.0 |
| 11.0 | 2,403.0 |
| 12.0 | 2,149.0 |
| 13.0 | 1,918.0 |
| 14.0 | 1,732.0 |
| 15.0 | 1,564.0 |
| 16.0 | 1,468.0 |
| 17.0 | 1,350.0 |
| 18.0 | 1,255.0 |
| 19.0 | 1,150.0 |
| 20.0 | 1,050.0 |
| 21.0 | 971.0 |
| 22.0 | 909.0 |
| 23.0 | 851.0 |
| 24.0 | 792.0 |
| 25.0 | 750.0 |
| 26.0 | 716.0 |
| 27.0 | 672.0 |
| 28.0 | 631.0 |
| 29.0 | 609.0 |
| 30.0 | 631.0 |

## Graded on the reporting years

On 2023 onward the detector flagged 8 of the 8 known events in the window (100%), with a median first alert 0.0 days after onset, and opened 297 false alarm episodes, 5.12 per thousand unit days over 57,980 unit days. On the fitting years it had flagged 5 of 5.

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

The known events, with a citation for every row, are committed in `data/known_events.csv`. A row is added only with a public source naming the dates, and an event the detector misses stays in the table.

## The event studies

For each carrier meltdown: the carrier's daily cancellation rate and mean delay against the other carriers at the same airports on the same days, the gap shaded over the disruption window, the excess in flights and minutes summed over the window, and the recovery time as the days from onset until the gap is back inside the carrier's own pre-event band for three days running. The peer control never includes the treated carrier; `tests/events/test_events.py` checks it.

- **Delta Air Lines**, onset 2024-07-19 to 2024-07-25, at ATL, MSP, DTW, SLC, LAX, SEA, JFK, BOS, LGA, MCO: 2,842 excess cancellations, 8,329 h excess delay, peak gap +42.7 pts, recovery 5 days.
- **Southwest Airlines**, onset 2022-12-21 to 2022-12-30, at DEN, LAS, MDW, DAL, BWI, PHX, HOU, BNA, OAK, SAN: 5,614 excess cancellations, 2,531 h excess delay, peak gap +70.6 pts, recovery 9 days.

## Is recovery speed a carrier trait

Over every alert episode in the window, for carriers with enough episodes to compare: Kruskal-Wallis H 23.11 across 15 carriers, permutation p 0.018.
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

## Proven on the simulator

The planted meltdown was caught in 100% of runs, 0.0 days after onset on average, and 45% of the detector's alerts landed on a planted meltdown or storm day. The weakest condition was confounding none, propagation strong, noise high.
