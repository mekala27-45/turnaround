# turnaround v0.1.0

Why your flight is late: a data story in 8 chapters over 74,201,388 scheduled US domestic flights from January 2015 to July 2026, with the warehouse, the simulator that proves each estimator, a misconnect calculator on a live API, and the exports a BI team would open.

> Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the public record; no individual traveler appears. The findings are a portfolio analysis, not an official ranking and not travel advice.

## The findings

- **What on time measures.** The on time rate fell, and flights took longer gate to gate and the schedule grew as much.
- **Padding in the schedule.** The schedule grew as fast as the flying slowed, so it absorbed the delay.
- **The fifteen minute line.** No carrier's arrivals bunch under the fifteen minute line beyond what the placebos show.
- **Inherited delay.** About a third of arrival delay was inherited from the aircraft's previous flight, and a scheduled turn of 75 minutes halves what is passed on.
- **The fair ranking.** The ranking changes once you hold constant what each carrier flies: PSA Airlines rises 4 places and Hawaiian Airlines falls 7.
- **Causes, reported and estimated.** Weather explains more delay than the weather field records.
- **Meltdowns and recovery.** Southwest Airlines took 9 days to get back to its peers and Delta Air Lines 5; across every alert episode, how fast a carrier recovers is a trait of the carrier.
- **The reader's decision.** Book the first flight of the aircraft's day, and leave 65 minutes to connect at ATL.

## Where it runs

- The story and its pages: https://mekala27-45.github.io/turnaround/
- The calculator's API: https://turnaround-flights-api.fly.dev (deployed and verified)- The briefing: `report/briefing.md` and `report/briefing.html`

## In this release

- 18 dbt models and 206 tests; 17 metrics reconciled at 4 grains with 0 disagreements.
- The recovery study: 240 simulated runs over 12 conditions.
- Eight registered plans, each hash in `results/plans`.
- The workbook with live formulas, the Tableau and Power BI specifications and the CSV bundle in `exports/`.

## The definition of done

17 of 18 lines done; not done: 18. The README prints every line with its evidence. The last line asks for this tag to be pushed after the commits, so it cannot be done at the commit the tag points to; the commit after the tag records the push.