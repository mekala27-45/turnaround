# Decisions

Dated entries, newest last. Entries tagged `correction` render into the corrections log at the end
of the story and on the corrections page. Numbers here are the ones the decision was made on; the
current values are in `RESULTS.md`, rendered from the manifest.

## 2026-09-30: the name is turnaround

The time an aircraft spends at the gate between legs is where its day is won or lost, and the
chapter on inherited delay is about exactly that interval. `blocktime` was the other candidate; it
names the schedule, not the place the delay moves through.

## 2026-09-30: the data comes in through the PC, not the build machine

The machine that built this repository could not reach transtats.bts.gov, registry.faa.gov or
open-meteo.com. `deploy/fetch-data.ps1` downloaded every monthly on time file, the registry and the
weather on a Windows machine that could, and the files were staged into the build. OurAirports is
read from its GitHub mirror, which is the same file the project publishes.

## 2026-09-30: weather at the FAA Core 30, not at every airport

The brief asks for hourly weather at every airport in the data for the whole window. Open-Meteo's
free tier allows 10,000 calls a day, and it counts a request for more than two weeks of one
location as several calls: a year at one airport is about 26 calls, so roughly 380 airports for
eleven and a half years is on the order of 110,000 calls, eleven days of quota. The weather is
pulled at the thirty airports the FAA itself uses for its delay statistics, about 360 requests, and
the weather chapter estimates on flights between two of them. The README's first paragraph says so.

## 2026-09-30: no visibility field

Open-Meteo's historical archive has no visibility variable (the forecast API does, the reanalysis it
archives does not). Low cloud cover and the WMO weather code, whose fog and thunderstorm codes are
the conditions that close runways, stand in for it. Temperature, precipitation, snowfall, wind speed
and gusts are pulled as the brief asks.

## 2026-09-30: three palette slots moved by the validator

The ported validator rejected four adjacent pairs in the brief's palette on lightness and chroma
separation: dark slots one and two (vermilion and blue at the same lightness, 0.654 and 0.655), dark
slots six, seven and eight, and light slots seven and eight. Each was moved by the smallest
lightness step that passes, hue and chroma kept: dark slot two `#5B8DEF` to `#6A9DFF`, dark slot seven
`#2E9DD3` to `#44AEE5`, light slot eight `#95561F` to `#93541D`. The validator now passes both modes
and the dark card; its own figures (worst adjacent colour vision separation 12.5 light and 12.4 dark)
replace the brief's.

## 2026-09-30: the derived flight files are not committed

Seventy million rows of derived parquet would put several gigabytes in the repository. The marts
the story, the site, the workbook and the BI extracts read are committed, with the manifest; the
monthly flight parquet is rebuilt from the raw files by `make data`, and the rederive starts there.

## 2026-09-30: the FAA registry keeps the aircraft, not the owner

The releasable registry carries the registrant's name and street address for every aircraft,
including private owners. Only the tail number, manufacturer, model, type, engine type, seats and
year built survive ingest; the identifier scan fails on any registrant column name or the raw
registry header in a committed file.

## 2026-09-30: reversal, the density test standardizes against its placebos

The first version of chapter 3's test reported where the statistic at fifteen minutes ranked among
the fifty placebo thresholds. A rank among fifty cannot go below one in fifty-one, so after
Benjamini-Hochberg across a dozen carriers no carrier could ever pass, planted or not: the recovery
study showed zero power on carriers with bunching planted at a third of the flights over the line.
The test now standardizes the statistic by the placebos' mean and standard deviation and reads a
normal tail; the rank is still reported beside it. The change was made on the simulator, before the
plan was registered and before any real flight was tested.

## 2026-09-30: reversal, propagation takes carrier by date and hour fixed effects

The first propagation model had carrier and origin by date fixed effects only. On the simulator it
overstated rho, because consecutive legs share the way delay builds through the day and share the
days a whole carrier falls over, and both made a late inbound look like the cause of a late
outbound. Carrier by date replaced carrier, departure hour was added, the simulator gained a
physical floor (no airframe leaves before it lands) and a heavy tail of long own delays, and the
recovery study was run again under a new code version so no cached run from the old model survived.

## 2026-09-30: reversal, padding change on matched cells with fixed weights

Chapter 2 first compared the mean padding of every flight in 2015 with every flight in the latest
year. On the partial window that mixed two things: schedules growing on the same routes, and
carriers moving into long routes, which carry more padding in minutes. The change is now measured on
route, carrier, three hour block and month cells flown in both years, each weighted by its mean
flights across the two, with actual block time on the same cells beside it, and the interval
resamples days within each year so each year keeps its own days.

## 2026-09-30: reversal, the registry join matches by validity, not by the latest record

N-numbers are reassigned when an aircraft is deregistered, so the latest registry record for a tail
number is often a different airframe (a 2019 business jet for a 1998 regional jet). The join now
takes a record only when the airframe could have flown the flights: built between 1975 and the year
it was last seen, a turbine engine type, certified before it was first seen, and either still
registered or cancelled after it was first seen; the current record wins over a deregistered one,
and a tail with no valid record is left unmatched and counted rather than given a guess.

## 2026-09-30: weather measures the direct effect, inherited weather stays in chapter 4

A storm at the hub delays the inbound aircraft and then the outbound one. Regressing arrival delay on
the weather at both ends alone would count the inbound's lateness as weather and again as inherited
delay in chapter 4. The weather model carries the inbound aircraft's carried minutes (chapter 4's
term, at its minimum turn) as a control, so the weather share is what the weather did to the flight
directly; the weather that came in on a late aircraft is part of the inherited share. On the
simulator the storm coefficients come back at the planted thirty and twelve minutes with it.

## 2026-09-30: an alert is an episode, and a miss costs fifty false pages

A three day storm flagged three days running is one call to the duty manager, not three. Alerts
became episodes (open above the threshold, stay open while the score stays above half of it), false
alarms are counted as episodes that touch no listed event, and the episode's length is the unit's
recovery time, which is what chapter 7's carrier trait test compares. A missed disruption is costed
at fifty false episodes: an operations center that learns of a meltdown from the news loses a day of
coordinated response, and a false page costs an analyst an hour. The cost and the grid were fixed in
the plan before the threshold was chosen.

## 2026-09-30: the calculator holds out the latest month

The calculator's cells are built from the reporting years up to the month before the latest
published one, and the latest month's flights at the twenty hubs are kept apart as the outcome the
scorer reads. A check for that month is scored against flights its estimate never saw, which is the
late arriving truth Day 13 graded its forecasts on, and the demo queue is made for that month so the
log has scored checks from the first day.

## 2026-10-01: a chart's message is chosen by rule, and the rules are tested

Every chart's title is one sentence picked by code from the result, never written after reading it.
On the development fixture the meltdowns chapter's rule printed "caught on their first day" whatever
the detector had done, and that fixture's detector had missed its planted meltdown. The rule now
names how long each studied carrier took to get back to its peers and states the trait test's
verdict, or that too few carriers qualified; the inherited delay, ranking and decision rules were
tightened the same day to carry the share band, the movers by name and the buffer at the busiest
hub. `tests/chapters/test_messages.py` pins every branch.

## 2026-10-01: a scale test before the real run

The real reporting years hold about twenty million linked legs on a machine with eight gigabytes.
A simulated warehouse of 4.2 million flights found two problems no fixture could: chapter 8 hung
for half an hour because DuckDB 1.5 stalled streaming an unordered union of day histograms (ordered,
it returns in half a second), and chapter 4's buffer curve would have needed most of the machine.
The curve now sweeps one column at a time in float64 and keeps the swept columns in float32, with
every sum in float64; its slopes agree with the all float64 fit to about one part in a hundred
million, and the link groupings arrive as integer codes ranked in DuckDB instead of strings.

## 2026-10-01: correction, a registration without its N is restored, and a fleet number stays in the rotations

The first full ingest flagged 2,093,332 rows, 2.8 percent of the window, under the tail format
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

## 2026-10-01: correction, a time that cannot be is quarantined, scheduled times included

The warehouse's range tests stopped the first full build on 31 flights. One reported 1,557
minutes in the air between Jacksonville and Newark, 820 miles, with the elapsed time made to match;
the other 30 had a scheduled elapsed time below one minute or over 1,500, several of them a
schedule that lands before it leaves. The negative time rule looked only at flown times, so these
rows reached the analysis grain, where a scheduled arrival before its departure would have entered
the padding and the rotations. The rule is now the impossible time rule: a negative taxi time, or
an air time or an actual or scheduled elapsed time at or below zero or over 1,500 minutes, and it
still excludes the row from everything; it flags exactly those 31 rows. The ledger now records a
digest of the ingest contract, so a rule change ingests every month again instead of leaving old
flags in files whose zips did not change.

## 2026-10-01: the full window is built to fit a machine with eight gigabytes

The first build over every month failed three ways the two year build never showed. The rotation
model sorted every flown leg once per window and spilled more than the disk held, so it is now
built in sixteen buckets of tail numbers, which gives the same table row for row because every
window in it stays inside one tail. A test counting distinct flight ids held all seventy million in
one hash table and the process was killed at six gigabytes, so it counts rows and leaves
uniqueness to the unique test that already ran. And dbt set DuckDB's spill directory again on every
cursor, which DuckDB refuses once a query has spilled, so the directory is now fixed when the
database opens. DuckDB's limit came down from five gigabytes to four to leave room for the overshoot.

## 2026-10-01: correction, two more rules from the first full build

The carrier month mart's own tests failed on the full window in two ways no fixture had shown.
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
