# Why your flight is late

*A data story in 8 chapters, about 23 minutes to read. Every number below is rendered from the analysis manifest; none was typed.*

**About a third of arrival delay was inherited from the aircraft's previous flight, and a scheduled turn of 75 minutes halves what is passed on: 34.9% of arrival delay minutes in the reporting years were inherited from the aircraft's previous flight, against 37.4% in the field the airlines report.**

> Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the public record; no individual traveler appears. The findings are a portfolio analysis, not an official ranking and not travel advice.

<!-- chapter: definition | 1 | definition -->
## 1. What on time measures

<!-- claim -->
**The on time rate fell, and flights took longer gate to gate and the schedule grew as much.**

<!-- step: rate -->
On time has a definition, and the airline writes half of it. A flight is on time when it arrives less than fifteen minutes after its scheduled arrival, the A14 convention the Bureau of Transportation Statistics has used since 1987, and the scheduled arrival is whatever the carrier chose to publish. From 2015 to 2025, across 72,583,211 flown flights, the share arriving on time went from 81.4% to 77.7%, a change of -3.7 pts (interval -4.9 pts to -2.6 pts).

<!-- step: actual -->
Now the flying. On the same 3,631 routes, flown in every full year of the window and carrying 88.7% of its flights, each route weighted the same in every year, the time a flight actually spent between the gates moved +4.4 min (interval +4.0 min to +4.8 min).

<!-- step: scheduled -->
The time the schedule allowed on those routes moved +4.6 min (interval +4.3 min to +5.0 min). The schedule's change less the flying's is +0.2 min (interval 0.0 min to +0.5 min). The schedule kept pace with the flying and no more, so the timetable did not move the on time rate either way: what moved it is delay the block times do not hold, the late departures that the chapter on inherited delay follows from one leg to the next. The rate is a comparison between what happened and what the airline said would happen, and only one of the two is outside the airline's control.

<!-- method -->
*Method.* Plan `74cda4464e3380a2`, registered as *On time is a decision* before the estimate ran, claimed: The on time rate moved over the window by a different amount than the time flights actually spend gate to gate on the same routes, so the metric and the flying can tell different stories. Per year: the share of flown flights arriving less than fifteen minutes late, and the mean actual and scheduled gate to gate time on a fixed panel of routes flown in every year of the window. The change from the first full year to the latest full year in each series, with day bootstrap intervals. Descriptive over every year; nothing is fit, so there is nothing to choose on the fitting years. Block bootstrap over days, 400 replicates, 95% percentile intervals. On two simulated years whose padding steps on known dates while the flying does not change, the panel's scheduled block change came within 0.01 min of the true padding change on average, and the actual block change's interval covered zero in 100% of 20 seeds. The SQL behind the chart is under the chart.

<!-- pushback -->
**What the ops director would push back on.** Longer schedules are not a trick: congestion at the big hubs made gate to gate times longer and less predictable, and a schedule that ignores that strands crews and passengers downline. That is fair, and it is why this chapter puts the time actually flown beside the time scheduled instead of calling the difference gaming. The claim is narrower: the on time rate grades the airline against its own estimate, and an estimate can be made easier to meet. The next chapter measures how much easier.

<!-- /chapter -->

<!-- chapter: padding | 2 | padding -->
## 2. Padding in the schedule

<!-- claim -->
**The schedule grew as fast as the flying slowed, so it absorbed the delay.**

<!-- step: series -->
Padding is the scheduled block time minus the time the trip takes when nothing is in the way, measured as the gate to gate time that only 10% of flights beat on the same route, in the same three hour departure block and season, over 2015 to 2022. In 2025 the average flight carried 21.2 min of it, 14.4% of its scheduled block, and across the year that came to 2,362,990 h of scheduled time. On the same routes, carriers, hours and months flown in both 2015 and 2025, padding moved +3.98 min (interval +3.84 min to +4.13 min) while the actual block time on those cells moved +4.16 min (interval +3.77 min to +4.58 min). Padding's change less the flying's is -0.18 min (interval -0.60 min to +0.24 min), an interval that holds zero: the schedule grew by what the flying lost, no more and no less.
<!-- step: steps -->
The growth did not arrive evenly. A changepoint search (PELT) over each of the 20 carriers' route adjusted, deseasonalized monthly series looked for moves of a minute or more that stayed, and found 204: 131 up and 73 down. The largest was JetBlue Airways in May 2020, a step of -9.3 min. Each is dated in the table under the chart, which is where a scheduler would look for the timetable change that caused it.

<!-- method -->
*Method.* Plan `13d98f2ebd738a81`, registered as *The schedule absorbed the delay* before the estimate ran, claimed: Scheduled block time grew faster than unimpeded flying time on the same routes, hours and seasons, and the growth arrived in steps on dates that can be named for each carrier. Unimpeded block time is the 10th percentile of actual gate to gate time by route, three hour departure block and season over the fitting years; padding is scheduled block minus unimpeded; each carrier's monthly series is adjusted for route mix; PELT with a BIC penalty of two parameters finds the steps, and steps under one minute are not reported. Padding change from the first to the latest full year on cells present in both, with intervals. choose on 2015 to 2022, report on 2023 to the latest month; the unimpeded reference is fixed on the fitting years and applied to every year. Block bootstrap over days, 400 replicates. On the simulator, across 12 conditions with 20 seeds each, padding by carrier, route and month came back within 0.82 min on average, 100% of planted steps were found 1.7 days from their dates on average, and the search reported 0.00 false steps per run. The padding estimator does worst under confounding none, propagation strong, noise high.

<!-- pushback -->
**What the ops director would push back on.** The unimpeded time is fixed on 2015 to 2022, so a route that got slower for reasons no airline controls shows up here as padding that shrank. That is true, and it is the right direction for the error: with the reference fixed, growth in congestion cannot hide growth in padding. Recomputing the reference every year, the obvious alternative, drifts with congestion and hides exactly the growth this chapter measures; the first notebook keeps that dead end.

<!-- /chapter -->

<!-- chapter: line | 3 | line -->
## 3. The fifteen minute line

<!-- claim -->
**No carrier's arrivals bunch under the fifteen minute line beyond what the placebos show.**

<!-- step: shape -->
If carriers managed to the line, arrival delays would pile up just under fifteen minutes and thin out just over it. The chart counts every flown flight in the reporting years by whole minute of arrival delay, 24,231,039 flights between an hour early and three hours late.

<!-- step: line -->
At the line, the pooled distribution holds -3.84% more flights just under fifteen minutes than a smooth curve fitted around it predicts. That number means nothing on its own: every histogram has bumps.

<!-- step: placebos -->
So the same statistic was computed at 49 placebo thresholds between ten and sixty five minutes, where nobody has a reason to manage, to give its natural spread. The line's statistic sits -2.40 placebo standard deviations from their mean. Carrier by carrier, corrected together by Benjamini-Hochberg at q = 0.05, 0 of 15 carriers show bunching. That is a finding, not a failed test: in the reported arrivals, the line is not visibly gamed.
<!-- method -->
*Method.* Plan `0249fbc74965a7ac`, registered as *The fifteen minute line* before the estimate ran, claimed: Arrival delays bunch just under fifteen minutes for some carriers, more than at placebo thresholds. Per carrier, counts by whole minute of arrival delay; a cubic fit to the log counts within twenty five minutes of the threshold, excluding five minutes either side; excess mass below plus missing mass above. The statistic at fifteen minutes standardized by its distribution at placebo thresholds from ten to sixty five minutes; one sided normal p value. choose on 2015 to 2022, report on 2023 to the latest month; the threshold, window, span and placebos are fixed here, and the test is reported on 2023 onward. Every reporting carrier in the test years, Benjamini-Hochberg at q = 0.05. On the simulator, carriers with bunching planted at 35% of the flights just over the line were flagged at a rate of 100%, and clean carriers at 0.0%, across every condition.

<!-- pushback -->
**What the ops director would push back on.** Nobody games the line on purpose; the gate agent closes the door when the aircraft is ready. The test does not need intent, it looks for the shape intent would leave, and its verdict is the same either way. What it cannot see is gaming that moves the schedule rather than the arrival, which is the previous chapter's subject, or an arrival time recorded a few minutes early across the board, which would shift the whole distribution rather than the stretch next to the line.

<!-- /chapter -->

<!-- chapter: inherited | 4 | inherited -->
## 4. Inherited delay

<!-- claim -->
**About a third of arrival delay was inherited from the aircraft's previous flight, and a scheduled turn of 75 minutes halves what is passed on.**

<!-- step: curve -->
A delay reported on a flight is not a delay caused on that flight. To separate the two, every flown leg with a tail number was put back in order on its aircraft's day: 72,583,211 legs, 18,151,842 rotations, 10,019 aircraft. A leg is linked to the one before it only when it leaves from the airport that one landed at, after it landed, within 6 h. 369,126 pairs broke the chain, most of them aircraft swaps the tail number does not show, and were split rather than joined; 601,945 were impossible sequences, quarantined and counted. On the 18,381,035 linked legs of the reporting years, each minute the inbound aircraft arrived beyond the scheduled turn, less a minimum turn of 45 min, put 1.068 minutes onto the next departure (interval 1.067 to 1.070). That makes 34.9% of all arrival delay minutes inherited from an earlier flight (interval 34.8% to 34.9%), against 37.4% in the late aircraft field the airlines report.

<!-- step: halving -->
The chart shows where a buffer would have stopped it. The longer the scheduled turn, the less of a late arrival reaches the next departure, and beyond the minimum turn 30 min of extra buffer halves the minutes passed on. The aircraft's day explorer on the rotations page shows the worst day of each month leg by leg.

<!-- method -->
*Method.* Plan `ee4a7aff3c3655b6`, registered as *Most delay is inherited* before the estimate ran, claimed: A large share of arrival delay minutes was inherited from the aircraft's previous leg rather than born on the leg, larger than the reported late aircraft field says. Rotations from tail numbers with the integrity rules; departure delay on the previous arrival's excess over the scheduled turn less a minimum turn, with carrier by date, origin by date and departure hour fixed effects; the buffer curve by scheduled turnaround bin. choose on 2015 to 2022, report on 2023 to the latest month; the minimum turn is chosen by profile on the fitting years and held fixed. Cluster robust by tail number and day for the coefficient. On the simulator the minimum turn was found exactly in 100% of runs; rho was off by +0.012 on average when the truth was weak propagation and by -0.013 when it was strong, with interval coverage of 18% and 4%, and the inherited share came within 1.3 pts of the truth. The coverage is below the nominal level: the interval carries the sampling error only, not the model's small bias, so read the bounds as narrower than the uncertainty.
<!-- pushback -->
**What the ops director would push back on.** Tail numbers miss aircraft swaps, so some links join two different aircraft. The chain rules split a pair whenever the next leg does not leave from where the last one landed, which is what most swaps look like, and the simulator plants swaps to check that they are split; a swap between two aircraft at the same airport inside the same turn is invisible to any reconstruction from public data. The second objection is that a late inbound and a late outbound can share a cause, a storm or a ground stop, without one causing the other. The carrier by date and airport by date fixed effects take that shared cause out, which is why the coefficient is lower than the raw correlation between the two delays.

<!-- /chapter -->

<!-- chapter: ranking | 5 | ranking -->
## 5. The fair ranking

<!-- claim -->
**The ranking changes once you hold constant what each carrier flies: PSA Airlines rises 4 places and Hawaiian Airlines falls 7.**

<!-- step: raw -->
The usual airline ranking sorts carriers by average arrival delay. That is a fair measure of what a passenger on each carrier sat through and an unfair measure of the carrier, because carriers do not fly the same routes, hours, months or aircraft. On the raw average in the reporting years, the three least delayed carriers were Endeavor Air, Republic Airways, Alaska Airlines, and the three most delayed were JetBlue Airways, American Airlines, Frontier Airlines.

<!-- step: adjusted -->
Holding constant what each carrier flies (route, month, scheduled departure hour and aircraft type, fit by weighted least squares on 3,025,819 cells, with intervals clustered by day), the three least delayed become Endeavor Air, Republic Airways, Envoy Air, and the three most delayed Allegiant Air, Frontier Airlines, Hawaiian Airlines. 11 of 15 carriers change places.

<!-- step: movers -->
PSA Airlines rises the most, from 11 to 7: its routes, hours and months are harder than the average carrier's, and its raw average charges it for them. Hawaiian Airlines falls the most, from 8 to 15: its flying is easier than most, and its raw average credits it for that.

<!-- method -->
*Method.* Plan `859c5a40bab6906c`, registered as *The fair ranking* before the estimate ran, claimed: Holding constant the routes, months, departure hours and aircraft types each carrier flies changes the carrier ranking on arrival delay. Arrival delay on carrier with route, month, departure hour and aircraft type fixed effects, weighted least squares on cells; effects relative to the flight weighted average carrier. choose on 2015 to 2022, report on 2023 to the latest month; the specification was settled on the fitting years and the ranking is fit on 2023 onward. Cluster robust by day, scores summed over flights. On the simulator, where the true ranking is known and the raw one is confounded by design, the adjusted ranking's rank correlation with the truth averaged 0.94 under strong confounding against -0.07 for the raw ranking, and 0.97 against 0.75 with no confounding at all.

<!-- pushback -->
**What the ops director would push back on.** My carrier flies the hardest routes. This chapter is the answer to that objection: the route, month, hour and aircraft are held constant, so a carrier flying into the hardest airports at the busiest hours is compared with other carriers on the same routes at the same hours. What it does not hold constant is anything the carrier chooses that the data does not record, such as how many spare aircraft and crews it keeps and how tightly it schedules its turns. Those are the carrier's own decisions, and the ranking is right to charge them to the carrier.

<!-- /chapter -->

<!-- chapter: causes | 6 | causes -->
## 6. Causes, reported and estimated

<!-- claim -->
**Weather explains more delay than the weather field records.**

<!-- step: reported -->
Every flight that arrives fifteen or more minutes late carries a breakdown of its delay into five reported causes. Over the window, the carriers put 38.9% of the cause minutes on a late aircraft, 34.2% on the carrier, 21.0% on the national airspace system, 5.7% on weather and 0.18% on security. These fields record what was reported, by the carrier, under rules that keep the weather field for extreme weather; ordinary weather that slows the airspace is coded to the national airspace system.

<!-- step: nas -->
The national airspace system's share is highest at EWR, SFO, LGA, airports where capacity, not the weather and not the airline, sets the pace much of the day.

<!-- step: estimated -->
Measured from the weather itself (precipitation, snow, gusts, low cloud, thunder, fog and freezing precipitation at the origin when the flight leaves and at the destination when it lands, on 8,320,779 flights between two of the FAA's Core 30 airports, with the inbound aircraft's lateness held constant), weather explains 18.8% of arrival delay minutes (interval 17.7% to 19.9%). The weather field on the same flights records 4.2%, and the national airspace system field 22.3%.

<!-- method -->
*Method.* Plan `a869209fb6ee8f35`, registered as *Causes, reported and estimated* before the estimate ran, claimed: The share of delay minutes that weather explains, estimated from the weather at both ends, differs from the share the reported weather field assigns. Arrival delay on hourly weather at the origin at departure and the destination at arrival (precipitation, snowfall, gusts over 40 km/h, low cloud, thunder, fog, freezing precipitation), with origin by hour, destination by hour and month fixed effects and the inbound aircraft's carried minutes as a control, on flights between two Core 30 airports; the attributable share is the fitted delay above calm weather. choose on 2015 to 2022, report on 2023 to the latest month; the specification is fixed here and the shares are reported on 2023 onward. Cluster robust by day on the weather coefficients, carried to the share. On the simulator, where storms add a known number of minutes and the reported weather field records only a planted share of them, the estimate came within 1.0 pts of the true share on average and its interval covered the truth in 97% of runs, while the reported field showed 1.7% against a true 8.9%. Weather data by Open-Meteo.com, CC BY 4.0.

<!-- pushback -->
**What the ops director would push back on.** Airport weather is not en route weather: a line of storms between two cities delays a flight that leaves and lands under clear skies. That is right, and it makes this estimate a floor on weather's share rather than a ceiling; that weather lands in the national airspace system field and in the model's hour and month effects. The other objection is that the model adds weather terms together, when a thunderstorm at a hub at five in the afternoon does more than the sum of its parts. The hour effects absorb when storms usually hit, not how hard, so the worst afternoons are the ones this estimate understates most.

<!-- /chapter -->

<!-- chapter: meltdowns | 7 | meltdowns -->
## 7. Meltdowns and recovery

<!-- claim -->
**Southwest Airlines took 9 days to get back to its peers and Delta Air Lines 5; across every alert episode, how fast a carrier recovers is a trait of the carrier.**

<!-- step: first -->
A meltdown shows in the daily numbers before it shows in the news. The detector scores every carrier's day, and every day at the 30 busiest airports, against that carrier's or airport's own previous four weeks, on the share of flights cancelled and the mean arrival delay. Its alert threshold was chosen on 2015 to 2022 by cost, with a missed disruption costed at 50.0 false alarms, and landed at 29.0 robust standard deviations, inside the grid. On the reporting years it flagged 8 of the 8 disruptions in the known events table, at a cost of 5.12 false alarm episodes per thousand carrier and airport days. The chart opens on Southwest Airlines in 2022-12-21: its cancellation rate against every other carrier at its busiest airports (DEN, LAS, MDW, DAL, BWI, PHX, HOU, BNA, OAK, SAN), with the disruption shaded. The storm hit everyone; the gap is the carrier's own.
<!-- step: second -->
Delta Air Lines in 2024-07-19 is the second panel: an outage of the software that runs its crew and aircraft scheduling, against the same kind of peer control. Over its window it cancelled 2,842 more flights than its peers' rate implies, and its passengers sat through 8,329 h of delay beyond theirs. Southwest Airlines's excess over its window was 5,614 flights and 2,531 h of delay.
<!-- step: recovery -->
Recovery is the number that separates them: Southwest Airlines took 9 days from onset to get back inside its own normal gap to its peers for three days running, and Delta Air Lines took 5. Across every alert episode in the window, carriers differ in how long their episodes last (Kruskal-Wallis H 23.11, permutation p 0.018, 15 carriers): how fast an airline recovers is a property of the airline, not only of the storm.
<!-- method -->
*Method.* Plan `c0e2ac3316344144`, registered as *A meltdown is a recovery* before the estimate ran, claimed: Carrier meltdowns are visible as anomalies days before they end, and recovery speed differs by carrier. Daily cancellation rate and mean arrival delay per carrier and at the thirty busiest airports against the unit's previous 28 days (median and median absolute deviation, with floors); an alert episode opens above the threshold and stays open while the score stays above half of it; the threshold is chosen by cost over a grid; event studies of the two carrier meltdowns against other carriers at the same airports. Recall on the known events of the reporting years and the first alert day against onset; false alarms per thousand unit days; whether carriers differ in alert episode length (Kruskal-Wallis H, permutation p). choose on 2015 to 2022, report on 2023 to the latest month; the alert threshold is chosen on the fitting years and graded on 2023 onward. One permutation test across carriers with at least five episodes; events are graded one by one. On the simulator the detector caught the planted meltdown in 100% of runs, 0.0 days after onset on average, with 45% of its alerts landing on a planted meltdown or storm day. The known events table, with a citation for each row, is on the disruptions page.

<!-- pushback -->
**What the ops director would push back on.** The peer control is not a clean control: the other carriers at the same airports were hit by the same storm, and some of them carried the stranded carrier's passengers. The first is the point, since the storm is differenced out; the second pushes the excess down, so the published excess is a floor. Recovery time also depends on what broke: a crew scheduling system rebuilt by hand takes longer than a fleet grounded for an inspection, and two meltdowns are two stories, which is why the trait claim rests on every alert episode in the window rather than on them.

<!-- /chapter -->

<!-- chapter: decision | 8 | decision -->
## 8. The reader's decision

<!-- claim -->
**Book the first flight of the aircraft's day, and leave 65 minutes to connect at ATL.**

<!-- step: curve -->
For the traveler, the safest flight is the aircraft's first of the day: in the reporting years the first leg of an aircraft's day arrived on time 85.8% of the time, against 76.0% for the legs after it, a difference of +9.8 pts (interval +9.5 pts to +10.1 pts). By the clock, departures scheduled at 05:00 were on time 91.2% of the time and those at 20:00 68.8%; November was the best month to fly and July the worst.

<!-- step: hubs -->
A connection is missed when the inbound flight is cancelled or diverted, or lands too late to leave 25 min to change planes. At ATL, the busiest airport, the chance of missing falls under 10% with a scheduled buffer of 65 min (interval 60 min to 65 min); at DEN it takes 70 min, and at DFW 90 min. Across the 20 busiest airports the buffer runs from 55 min to 100 min, and the planner page answers for any connection at them.

<!-- step: buffers -->
For the airline, a minute added to every turn takes delay off the rest of the aircraft's day only where a late inbound reaches into the turn, which was 25.3% of turns in the reporting years. Counting the minute it saves on the next flight and the share that would have carried further down the day, a buffer minute saves 0.46 arrival minutes on average. It does not pay for itself at any of the busiest airports on this count; the most it saves is 0.51 minutes per minute, at LAS, so a buffer is worth adding only where turns are reached far more often than average.
<!-- method -->
*Method.* Plan `3e13c6a0a08d3a8f`, registered as *The reader's decision* before the estimate ran, claimed: The first departure of the aircraft's day is the most punctual, and the connection buffer needed to keep the misconnect probability under the stated line differs across the largest hubs. On time rate and mean delay by scheduled hour, day of week and month; misconnect probability by buffer from the joint same day distribution of inbound arrival and outbound departure delays at each hub. The buffer at which the probability crosses 10%, with the interior test. choose on 2015 to 2022, report on 2023 to the latest month; the curves are computed on 2023 onward. Block bootstrap over days, 400 replicates. The day by day curve equals a brute force count of every same day pair of flights at a simulated hub (test); the calculator's estimates are scored later against the outcome month.

<!-- pushback -->
**What the ops director would push back on.** A connection on one ticket is protected: the airline holds the outbound for a late inbound with many connecting passengers and rebooks the rest. The curve counts a missed connection the way the schedule would, so it overstates misconnects for well protected connections and understates the cost of the ones missed on the last flight of the night. The minimum connection time is also one number here, and at an airport where the gates are a train ride apart it is not one number.

<!-- /chapter -->

## Corrections

**2026-10-01, a registration without its N is restored, and a fleet number stays in the rotations.** The first full ingest flagged 2,093,332 rows, 2.8 percent of the window, under the tail format
rule, far more than typing errors explain. Two carriers made almost all of it. Allegiant reports its
registrations without the leading N (248NV for N248NV, which the FAA registry lists), so every
Allegiant flight in the files failed the rule and missed the registry join. American reported its
own fleet numbers wrapped in N and AA from 2015 to 2017 (N3DAAA, N4YRAA); those are not
registrations, since a registration carries at most two trailing letters, so they stay out of the
registry join. The rule's text also said its rows were left out of the rotations, which the
rotation model never did: a rotation needs a value that names one aircraft, and the chain rules
catch one that does not. The ingest now restores the N when the result is a valid registration and
keeps the reported value beside it as `tail_reported`, the rule excludes from the registry join
only and says so, and `tests/contracts/test_quarantine.py` pins both cases. After the change
950,473 rows carry a restored N and the rule flags 1,142,859, almost all of them American's
fleet numbers.

**2026-10-01, a time that cannot be is quarantined, scheduled times included.** The warehouse's range tests stopped the first full build on 31 flights. One reported 1,557
minutes in the air between Jacksonville and Newark, 820 miles, with the elapsed time made to match;
the other 30 had a scheduled elapsed time below one minute or over 1,500, several of them a
schedule that lands before it leaves. The negative time rule looked only at flown times, so these
rows reached the analysis grain, where a scheduled arrival before its departure would have entered
the padding and the rotations. The rule is now the impossible time rule: a negative taxi time, or
an air time or an actual or scheduled elapsed time at or below zero or over 1,500 minutes, and it
still excludes the row from everything; it flags exactly those 31 rows. The ledger now records a
digest of the ingest contract, so a rule change ingests every month again instead of leaving old
flags in files whose zips did not change.

**2026-10-01, two more rules from the first full build.** The carrier month mart's own tests failed on the full window in two ways no fixture had shown.
Thirteen flights in 2017, all Frontier and Virgin America, are flagged both cancelled and diverted,
so they were counted twice and the month's parts summed to more than its schedule. And 973 flights
neither cancelled nor diverted report no departure delay or no arrival delay (a block of Endeavor
flights in May 2018 has arrival times with the delay left blank), so they sat in the flown count
without being on time or late, and the metric layer's reconcile disagreed with itself in the sixth
decimal. Once those were out, the reconcile found one more: a Republic flight from LaGuardia to
Dallas in March 2018 with its delays but no elapsed time and no air time. Both rules exclude the
row from everything, status conflict and missing actual (no departure delay, no arrival delay, no
elapsed time or no air time on a flight that flew), each planted and found in
`tests/contracts/test_quarantine.py`. Nothing is recomputed from the clock times: the files leave
the field blank, and a value this build made up would be a value nobody reported.

**2026-10-01, two messages compared estimates, and a heading was a registered claim.** On the full window the padding chapter's rule printed "Padding barely moved" over a padding change
of four minutes whose interval runs well clear of zero, because the rule only knew how to say the
schedule grew faster or slower than the flying, and on the real flights it grew by the same amount;
chapter 1's text said the schedule grew faster than the flying on point estimates two tenths of a
minute apart, with overlapping intervals. Both now decide from the interval of the difference,
computed in the same day bootstrap as the two changes, and the tests pin every branch. Separately,
the story's chapter headings were the plans' registered titles, and chapter 4's title, Most delay
is inherited, is a claim the estimate did not bear out. The plans stay as registered; the headings
now name each chapter's subject, and every method note quotes the registered title and claim, so a
claim that failed is printed where it failed.

## How this was built

Every scheduled domestic flight of the reporting carriers from January 2015 to July 2026, 74.2 million rows, went through named quarantine rules into a dbt warehouse whose metric layer defines each number once and reconciles it at 4 grains. Each chapter's plan was hashed before its estimate touched a real flight, and each estimator was first run on a simulated airline network where the answer is known. The story, the memo, the site and the workbook all render from one manifest, so a number here is the number everywhere.

The method appendix, the definitions, the warehouse and the simulator's recovery study are on the [data page](data/), and every chart's SQL is one click from the chart.
