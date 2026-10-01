# The warehouse

dbt over DuckDB, in `warehouse/`. Staging types the raw files and applies the quarantine rules; intermediate joins the aircraft, airports and weather and builds the rotation keys; marts are what every reader of the data reads. 18 models, 206 tests, 0 failed on the last build.

> Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the public record; no individual traveler appears. The findings are a portfolio analysis, not an official ranking and not travel advice.

## Layers

| Layer | Model | Grain |
|---|---|---|
| staging | `stg_flights` | one row per flight in the monthly files, typed, with a flag per quarantine rule |
| staging | `stg_aircraft` | one row per tail number and validity window from the FAA registry |
| staging | `stg_airports`, `stg_tz_offsets` | one row per airport; one row per zone and hour for local to UTC |
| staging | `stg_weather` | one row per airport and UTC hour |
| intermediate | `int_flights_utc` | one row per flight, times in UTC, weather joined at the scheduled hours at both ends |
| intermediate | `int_unimpeded` | one row per route, three hour block and season, fixed on the fitting years |
| intermediate | `int_legs` | one row per flown leg with its tail number, its previous leg and the link status |
| marts | `fct_flights` | one row per flight, with padding and the aircraft |
| marts | `mart_route_month`, `mart_carrier_month` | route by carrier by month; carrier by month |
| marts | `mart_carrier_day`, `mart_airport_day` | the detector's daily units |
| marts | `mart_hour_profile`, `mart_delay_histogram`, `mart_leg_position` | the traveler's tables and the line |
| marts | `mart_rotation_day`, `mart_quarantine` | rotations by tail and day; the quarantine report |

`warehouse/models/exposures.yml` names who reads each mart: the story, the explorer, the workbook, the Tableau and Power BI extracts and the API. A mart nobody reads is deleted rather than kept for later.

## Quarantine

Nothing is deleted. Each rule flags rows and names what they are excluded from; a row that fails the cause breakdown check still counts in the on time rate, it just stays out of the cause shares.

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

The report by carrier and month is `mart_quarantine`, on the data page and in the CSV bundle.

## Tests

Every model is tested on its grain (`unique_combination` from `warehouse/tests/generic`), on its keys (`not_null`), on its codes (`accepted_values`) and on its arithmetic (`non_negative`, `between`, `sums_match`, `not_empty`). The singular tests in `warehouse/tests` check what a column test cannot: every flown leg belongs to exactly one rotation; every linked leg obeys the rotation rules; on time never exceeds flown in any mart; the padding reference reads the fitting years only; every row of the files lands in the quarantine report, flagged or clean; and a UTC arrival equals the UTC departure plus the elapsed time.

## The metric layer

`metrics/metrics.yml` defines each metric the story uses once, with two expressions: one over the flight grain and one over the shipped mart. The reconcile step evaluates both at every grain and fails the build on any difference beyond tolerance, so the explorer, the workbook and the story cannot disagree about the on time rate. On the last build: 17 metrics at 4 grains over 3,501 cells, 0 disagreements.

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

## Running it

    make warehouse    # dbt build, then the reconcile
    make metrics      # the reconcile alone, against the marts in results/marts
