# Why flights are late: the operations review

*turnaround, as of 2026-10-01. Every scheduled domestic flight of the reporting carriers from January 2015 to July 2026, 74,201,388 flights. Models choose on 2015 to 2022 and report on 2023 onward. Every figure is rendered from the analysis manifest.*

> Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the public record; no individual traveler appears. The findings are a portfolio analysis, not an official ranking and not travel advice.

## The eight findings

- **The on time rate fell, and flights took longer gate to gate and the schedule grew as much.** The on time rate moved -3.7 pts (-4.9 pts to -2.6 pts) from 2015 to 2025; on the same routes the schedule moved +4.6 min and the flying +4.4 min.
- **The schedule grew as fast as the flying slowed, so it absorbed the delay.** Padding moved +3.98 min (+3.84 min to +4.13 min) on matched cells; 204 carrier steps of a minute or more, each dated.
- **No carrier's arrivals bunch under the fifteen minute line beyond what the placebos show.** 0 of 15 carriers after Benjamini-Hochberg against 49 placebo thresholds.
- **About a third of arrival delay was inherited from the aircraft's previous flight, and a scheduled turn of 75 minutes halves what is passed on.** 34.9% of arrival delay minutes were inherited (34.8% to 34.9%), against 37.4% in the late aircraft field; 30 min of extra turn halves what is passed on.
- **The ranking changes once you hold constant what each carrier flies: PSA Airlines rises 4 places and Hawaiian Airlines falls 7.** 11 of 15 carriers change places; PSA Airlines rises from 11 to 7 and Hawaiian Airlines falls from 8 to 15.
- **Weather explains more delay than the weather field records.** Weather at both ends explains 18.8% of arrival delay minutes (17.7% to 19.9%); the weather field records 4.2%.
- **Southwest Airlines took 9 days to get back to its peers and Delta Air Lines 5; across every alert episode, how fast a carrier recovers is a trait of the carrier.** The detector flagged 8 of 8 reporting year disruptions at a threshold of 29.0, inside the grid.
- **Book the first flight of the aircraft's day, and leave 65 minutes to connect at ATL.** The first leg of the aircraft's day is on time 85.8% of the time against 76.0%; at ATL a 65 min buffer keeps the chance of missing a connection under 10%.

## 1. What on time measures

<!-- chart: definition -->
**The on time rate fell, and flights took longer gate to gate and the schedule grew as much.**

The on time rate moved -3.7 pts (interval -4.9 pts to -2.6 pts) from 2015 to 2025. On 3,631 routes flown every year, the scheduled gate to gate time moved +4.6 min and the actual time +4.4 min.

The rate grades the airline against its own estimate. When the estimate grows faster than the flying, the rate improves without a single flight getting faster.

*Method.* Plan `74cda4464e3380a2`. Per year: the share of flown flights arriving less than fifteen minutes late, and the mean actual and scheduled gate to gate time on a fixed panel of routes flown in every year of the window. Block bootstrap over days, 400 replicates, 95% percentile intervals.

**What the ops director would push back on.** Longer schedules reflect real congestion, not gaming. Agreed, which is why the actual time sits beside the scheduled time; the claim is only that the rate measures the airline against a target it sets.

## 2. Padding in the schedule

<!-- chart: padding -->
**The schedule grew as fast as the flying slowed, so it absorbed the delay.**

In 2025 the average flight carried 21.2 min of padding, 14.4% of its scheduled block and 2,362,990 h of scheduled time across the year. On matched cells padding moved +3.98 min while actual block time moved +4.16 min.

PELT found 204 carrier steps of a minute or more; the largest was JetBlue Airways in May 2020, -9.3 min.

*Method.* Plan `13d98f2ebd738a81`. Unimpeded block time is the 10th percentile of actual gate to gate time by route, three hour departure block and season over the fitting years; padding is scheduled block minus unimpeded; each carrier's monthly series is adjusted for route mix; PELT with a BIC penalty of two parameters finds the steps, and steps under one minute are not reported. Block bootstrap over days, 400 replicates.

**What the ops director would push back on.** The unimpeded reference is fixed on the fitting years, so congestion growth shows as padding that shrank, the conservative direction.

## 3. The fifteen minute line

<!-- chart: line -->
**No carrier's arrivals bunch under the fifteen minute line beyond what the placebos show.**

Pooled, the fifteen minute line's bunching statistic sits -2.40 placebo standard deviations from the placebo mean. Carrier by carrier, 0 of 15 pass Benjamini-Hochberg at q = 0.05.

A null is a finding: managing to the line by lengthening the schedule shows up in padding, not here.

*Method.* Plan `0249fbc74965a7ac`. Per carrier, counts by whole minute of arrival delay; a cubic fit to the log counts within twenty five minutes of the threshold, excluding five minutes either side; excess mass below plus missing mass above. Not an interval: a p value against placebos, and the excess mass as a share.

**What the ops director would push back on.** Nobody manages to the line on purpose. The test needs no intent; it looks for the shape intent would leave.

## 4. Inherited delay

<!-- chart: inherited -->
**About a third of arrival delay was inherited from the aircraft's previous flight, and a scheduled turn of 75 minutes halves what is passed on.**

Rotations rebuilt from tail numbers: 18,151,842 on 10,019 aircraft, 369,126 broken chains split and 601,945 impossible sequences quarantined. Each minute of inbound lateness beyond the turn, less a minimum turn of 45 min, passed 1.068 minutes to the next departure (1.067 to 1.070).

That makes 34.9% of arrival delay minutes inherited, against 37.4% reported as late aircraft; 30 min of extra turn halves what is passed on.

*Method.* Plan `ee4a7aff3c3655b6`. Rotations from tail numbers with the integrity rules; departure delay on the previous arrival's excess over the scheduled turn less a minimum turn, with carrier by date, origin by date and departure hour fixed effects; the buffer curve by scheduled turnaround bin. Cluster robust by tail number and day for the coefficient.

**What the ops director would push back on.** Tail numbers miss some aircraft swaps; the chain rules split the ones that break the airport sequence, and the fixed effects remove storms that delay both legs.

## 5. The fair ranking

<!-- chart: ranking -->
**The ranking changes once you hold constant what each carrier flies: PSA Airlines rises 4 places and Hawaiian Airlines falls 7.**

Raw top three: Endeavor Air, Republic Airways, Alaska Airlines. Adjusted for route, month, hour and aircraft: Endeavor Air, Republic Airways, Envoy Air. Raw bottom three: JetBlue Airways, American Airlines, Frontier Airlines; adjusted: Allegiant Air, Frontier Airlines, Hawaiian Airlines.

PSA Airlines rises from 11 to 7; Hawaiian Airlines falls from 8 to 15.

*Method.* Plan `859c5a40bab6906c`. Arrival delay on carrier with route, month, departure hour and aircraft type fixed effects, weighted least squares on cells; effects relative to the flight weighted average carrier. Cluster robust by day, scores summed over flights.

**What the ops director would push back on.** What the data does not record, such as spare aircraft and turn standards, is the carrier's own choice and is charged to it.

## 6. Causes, reported and estimated

<!-- chart: causes -->
**Weather explains more delay than the weather field records.**

Over the window carriers put 38.9% of cause minutes on a late aircraft, 21.0% on the air traffic system and 5.7% on weather. The air traffic system's share is highest at EWR, SFO, LGA.

Measured from the weather at both ends, weather explains 18.8% of arrival delay minutes (17.7% to 19.9%) against 4.2% in the weather field on the same flights.

*Method.* Plan `a869209fb6ee8f35`. Arrival delay on hourly weather at the origin at departure and the destination at arrival (precipitation, snowfall, gusts over 40 km/h, low cloud, thunder, fog, freezing precipitation), with origin by hour, destination by hour and month fixed effects and the inbound aircraft's carried minutes as a control, on flights between two Core 30 airports; the attributable share is the fitted delay above calm weather. Cluster robust by day on the weather coefficients, carried to the share.

**What the ops director would push back on.** Airport weather is not en route weather, so the estimate is a floor on weather's share.

## 7. Meltdowns and recovery

<!-- chart: meltdowns -->
**Southwest Airlines took 9 days to get back to its peers and Delta Air Lines 5; across every alert episode, how fast a carrier recovers is a trait of the carrier.**

The detector's threshold of 29.0 was chosen on the fitting years by cost (inside the grid) and flagged 8 of 8 reporting year disruptions, at 5.12 false alarm episodes per thousand unit days.

Southwest Airlines in 2022-12-21 cancelled 5,614 more flights than its peers' rate implies. Delta Air Lines in 2024-07-19 cancelled 2,842 more.
*Method.* Plan `c0e2ac3316344144`. Daily cancellation rate and mean arrival delay per carrier and at the thirty busiest airports against the unit's previous 28 days (median and median absolute deviation, with floors); an alert episode opens above the threshold and stays open while the score stays above half of it; the threshold is chosen by cost over a grid; event studies of the two carrier meltdowns against other carriers at the same airports. Recovery time is a count of days; the excess is a sum, reported without a model interval.

**What the ops director would push back on.** The peers were hit by the same storm and carried some stranded passengers, so the excess is a floor.

## 8. The reader's decision

<!-- chart: decision -->
**Book the first flight of the aircraft's day, and leave 65 minutes to connect at ATL.**

The first leg of the aircraft's day is on time 85.8% of the time against 76.0% for later legs (+9.8 pts, interval +9.5 pts to +10.1 pts). 05:00 departures were on time 91.2% of the time, 20:00 departures 68.8%.

To stay under a 10% chance of missing a connection: 65 min at ATL, 70 min at DEN, 90 min at DFW. For the airline, a buffer minute saves 0.46 arrival minutes across the rest of the aircraft's day on average.

*Method.* Plan `3e13c6a0a08d3a8f`. On time rate and mean delay by scheduled hour, day of week and month; misconnect probability by buffer from the joint same day distribution of inbound arrival and outbound departure delays at each hub. Block bootstrap over days, 400 replicates.

**What the ops director would push back on.** Connections on one ticket are protected by the airline; the curve counts misconnects the way the schedule would.

## Limitations

- The weather estimate covers flights between two of the FAA's Core 30 airports and the weather at the airports at the scheduled hours, not along the route; it is a floor on weather's share.
- Inherited delay rests on tail numbers; a swap between two aircraft at the same airport inside one turn is invisible.
- On the simulator the propagation interval covered the truth in 18% of runs at weak propagation: the published interval carries sampling error only.
- The fair ranking holds constant what the data records; spare aircraft, reserve crews and turn standards are the carrier's own choices and are charged to it.
- The detector is graded against a table of 8 reporting year disruptions; real disruptions missing from the table count as false alarms.
- The misconnect curve treats every connection the same; airlines protect connections on one ticket, and the minimum connection time is one number at every hub.
