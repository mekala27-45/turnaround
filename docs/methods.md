# Methods

How each chapter was estimated, in the order the story tells it. Every chapter's plan was written, hashed and registered in `results/plans` before its estimator touched the flights; the hash printed under each chapter is the one the gate recomputes from the committed plan, so a plan edited after the fact fails the build rather than quietly changing the question.

> Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the public record; no individual traveler appears. The findings are a portfolio analysis, not an official ranking and not travel advice.

## Shared rules

**The split.** Anything a chapter chooses (a threshold, a minimum turn, a padding reference) is chosen on 2015 to 2022 and reported on 2023 onward. `report_years` in `packages/chapters/src/turnaround_chapters/plan.py` raises `SplitViolation` on a report that reaches into a fitting year, and `tests/chapters/test_plans.py` proves the refusal.

**Intervals.** A block bootstrap over days with 400 replicates and 95% percentile intervals, seeded with 20261001 (`packages/stats/src/turnaround_stats/bootstrap.py`). Days, not flights, are resampled because a bad day hits every flight on it: a flight level bootstrap would treat one thunderstorm as a thousand independent pieces of evidence. Regression coefficients use cluster robust errors by day, or by tail number and day where the chapter's errors travel with the aircraft.

**Multiple comparisons.** Benjamini-Hochberg at q = 0.05 inside every family a plan names (the carriers in the density test, the carriers searched for changepoints). A finding reported without its family's adjustment is a bug.

**Fixed effects.** Two solvers sit in `packages/stats/src/turnaround_stats/fe.py`: alternating projections for the large cell fits of the inherited delay and ranking chapters, and a direct least squares solve over the stacked indicators for the weather model, which has few enough levels to solve exactly and was too slow to converge by projection. The ranking chapter fits weighted least squares on route by carrier by month by hour cells; that fit is exact for the linear model, and `tests/stats/test_fe.py` checks it against a row level fit to floating tolerance.

**The interior test.** Every chosen operating point (an alert threshold, a buffer where a curve crosses a line) must sit strictly inside the grid it was chosen from. A point on the edge means the grid was too narrow and the choice is not a choice; the chapter reports that instead of a number.

**Proven on the simulator first.** Each estimator ran on `packages/sim` across 12 conditions and 20 seeds per condition before it saw a real flight. The recovery results are in `results/recovery` and on the data page.

## On time is a decision

**Claim.** The on time rate moved over the window by a different amount than the time flights actually spend gate to gate on the same routes, so the metric and the flying can tell different stories.

**Estimator.** Per year: the share of flown flights arriving less than fifteen minutes late, and the mean actual and scheduled gate to gate time on a fixed panel of routes flown in every year of the window.

**Split.** Descriptive over every year; nothing is fit, so there is nothing to choose on the fitting years.

**Family.** None; two series, one comparison.

**Interval.** Block bootstrap over days, 400 replicates, 95% percentile intervals.

**What is reported.** The change from the first full year to the latest full year in each series, with day bootstrap intervals.

**Proven on the simulator.** A two year simulated network whose padding steps on known dates while the flying does not change: the panel's scheduled block change against the true padding change, and whether the actual block change's interval covers zero, over twenty seeds.

Plan hash `74cda4464e3380a2`, registered in `results/plans`.

## The schedule absorbed the delay

**Claim.** Scheduled block time grew faster than unimpeded flying time on the same routes, hours and seasons, and the growth arrived in steps on dates that can be named for each carrier.

**Estimator.** Unimpeded block time is the 10th percentile of actual gate to gate time by route, three hour departure block and season over the fitting years; padding is scheduled block minus unimpeded; each carrier's monthly series is adjusted for route mix; PELT with a BIC penalty of two parameters finds the steps, and steps under one minute are not reported.

**Split.** choose on 2015 to 2022, report on 2023 to the latest month; the unimpeded reference is fixed on the fitting years and applied to every year.

**Family.** One changepoint search per carrier; dates are reported, not tested.

**Interval.** Block bootstrap over days, 400 replicates.

**What is reported.** Padding change from the first to the latest full year on cells present in both, with intervals.

**Proven on the simulator.** Padding error and changepoint date error by condition (recovery study).

Plan hash `13d98f2ebd738a81`, registered in `results/plans`.

## The fifteen minute line

**Claim.** Arrival delays bunch just under fifteen minutes for some carriers, more than at placebo thresholds.

**Estimator.** Per carrier, counts by whole minute of arrival delay; a cubic fit to the log counts within twenty five minutes of the threshold, excluding five minutes either side; excess mass below plus missing mass above.

**Split.** choose on 2015 to 2022, report on 2023 to the latest month; the threshold, window, span and placebos are fixed here, and the test is reported on 2023 onward.

**Family.** Every reporting carrier in the test years, Benjamini-Hochberg at q = 0.05.

**Interval.** Not an interval: a p value against placebos, and the excess mass as a share.

**What is reported.** The statistic at fifteen minutes standardized by its distribution at placebo thresholds from ten to sixty five minutes; one sided normal p value.

**Proven on the simulator.** False positive rate on clean carriers and power on planted carriers (recovery study).

Plan hash `0249fbc74965a7ac`, registered in `results/plans`.

## Most delay is inherited

**Claim.** A large share of arrival delay minutes was inherited from the aircraft's previous leg rather than born on the leg, larger than the reported late aircraft field says.

**Estimator.** Rotations from tail numbers with the integrity rules; departure delay on the previous arrival's excess over the scheduled turn less a minimum turn, with carrier by date, origin by date and departure hour fixed effects; the buffer curve by scheduled turnaround bin.

**Split.** choose on 2015 to 2022, report on 2023 to the latest month; the minimum turn is chosen by profile on the fitting years and held fixed.

**Family.** None; one coefficient, one share.

**Interval.** Cluster robust by tail number and day for the coefficient.

**What is reported.** The coefficient and the inherited share with intervals; the halving buffer.

**Proven on the simulator.** Coefficient bias and coverage, inherited share error (recovery study).

Plan hash `ee4a7aff3c3655b6`, registered in `results/plans`.

## The fair ranking

**Claim.** Holding constant the routes, months, departure hours and aircraft types each carrier flies changes the carrier ranking on arrival delay.

**Estimator.** Arrival delay on carrier with route, month, departure hour and aircraft type fixed effects, weighted least squares on cells; effects relative to the flight weighted average carrier.

**Split.** choose on 2015 to 2022, report on 2023 to the latest month; the specification was settled on the fitting years and the ranking is fit on 2023 onward.

**Family.** Pairwise rank changes are described, not tested.

**Interval.** Cluster robust by day, scores summed over flights.

**What is reported.** Rank changes between the raw and the adjusted ranking; effects with intervals.

**Proven on the simulator.** Rank correlation with the true ranking, adjusted against raw (recovery study).

Plan hash `859c5a40bab6906c`, registered in `results/plans`.

## Causes, reported and estimated

**Claim.** The share of delay minutes that weather explains, estimated from the weather at both ends, differs from the share the reported weather field assigns.

**Estimator.** Arrival delay on hourly weather at the origin at departure and the destination at arrival (precipitation, snowfall, gusts over 40 km/h, low cloud, thunder, fog, freezing precipitation), with origin by hour, destination by hour and month fixed effects and the inbound aircraft's carried minutes as a control, on flights between two Core 30 airports; the attributable share is the fitted delay above calm weather.

**Split.** choose on 2015 to 2022, report on 2023 to the latest month; the specification is fixed here and the shares are reported on 2023 onward.

**Family.** Airports compared on their national airspace system share are described, not tested.

**Interval.** Cluster robust by day on the weather coefficients, carried to the share.

**What is reported.** Estimated weather share against the reported weather field's share on the same flights, with an interval.

**Proven on the simulator.** Weather share error and interval coverage against planted storms whose minutes the reported field under records by design (recovery study).

Plan hash `a869209fb6ee8f35`, registered in `results/plans`.

## A meltdown is a recovery

**Claim.** Carrier meltdowns are visible as anomalies days before they end, and recovery speed differs by carrier.

**Estimator.** Daily cancellation rate and mean arrival delay per carrier and at the thirty busiest airports against the unit's previous 28 days (median and median absolute deviation, with floors); an alert episode opens above the threshold and stays open while the score stays above half of it; the threshold is chosen by cost over a grid; event studies of the two carrier meltdowns against other carriers at the same airports.

**Split.** choose on 2015 to 2022, report on 2023 to the latest month; the alert threshold is chosen on the fitting years and graded on 2023 onward.

**Family.** One permutation test across carriers with at least five episodes; events are graded one by one.

**Interval.** Recovery time is a count of days; the excess is a sum, reported without a model interval.

**What is reported.** Recall on the known events of the reporting years and the first alert day against onset; false alarms per thousand unit days; whether carriers differ in alert episode length (Kruskal-Wallis H, permutation p).

**Proven on the simulator.** Detector precision and recall on the planted meltdown (recovery study).

Plan hash `c0e2ac3316344144`, registered in `results/plans`.

## The reader's decision

**Claim.** The first departure of the aircraft's day is the most punctual, and the connection buffer needed to keep the misconnect probability under the stated line differs across the largest hubs.

**Estimator.** On time rate and mean delay by scheduled hour, day of week and month; misconnect probability by buffer from the joint same day distribution of inbound arrival and outbound departure delays at each hub.

**Split.** choose on 2015 to 2022, report on 2023 to the latest month; the curves are computed on 2023 onward.

**Family.** Hubs are described, not tested.

**Interval.** Block bootstrap over days, 400 replicates.

**What is reported.** The buffer at which the probability crosses 10%, with the interior test.

**Proven on the simulator.** The day by day curve equals a brute force count of every same day pair of flights at a simulated hub (test); the calculator's estimates are scored later against the outcome month.

Plan hash `3e13c6a0a08d3a8f`, registered in `results/plans`.

## What none of this does

No chapter claims that a carrier caused anything. The ranking holds constant what each carrier flies; it does not hold constant how it staffs, maintains or schedules, and those are the differences a ranking is supposed to surface. The weather estimate is airport weather at the scheduled hours, not weather en route. The inherited share depends on tail numbers, and an aircraft swap the data does not record shows up as a broken chain rather than as inheritance; the count of those is published beside the share.
