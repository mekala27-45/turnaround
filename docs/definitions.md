# Definitions

This is a policy, not a glossary: each definition is a decision, and the reason for it is written next to it. Every expression below is the one the warehouse and the metric layer run; the numbers in it are the policy's.

> Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the public record; no individual traveler appears. The findings are a portfolio analysis, not an official ranking and not travel advice.

## On time

A flight is on time when its arrival delay is under 15 min: the A14 convention the Bureau of Transportation Statistics has used since 1987. Arrival delay is actual gate arrival minus scheduled gate arrival, and the scheduled arrival is the carrier's own. The rate counts flown flights only (not cancelled, not diverted), so a carrier that cancels a late flight improves its on time rate; the cancellation rate sits beside it for that reason.

    avg((arr_delay < 15)::int) filter (where not cancelled and not diverted)

Code: `on_time_rate` in `metrics/metrics.yml`; the flight grain in `warehouse/models/marts/fct_flights.sql`.

## Departure delay and arrival delay

Minutes after the scheduled gate departure and gate arrival, negative when early, as the carrier reports them. Rows whose actual time has no scheduled time, or whose taxi or air time is negative, are flagged by the quarantine rules and left out of everything they would corrupt.

Code: the typed frame in `packages/contracts/src/turnaround_contracts/bts.py`; the flags in `warehouse/models/staging/stg_flights.sql`.

## Block time, unimpeded block time and padding

Block time is gate to gate: scheduled block time is the carrier's scheduled elapsed time, actual block time the actual elapsed time. **Unimpeded block time** is the time the trip takes when nothing is in the way: the gate to gate time beaten by only 10% of flights on the same route, in the same three hour departure block and season, over 2015 to 2022, with at least 30 flights in the cell. It is fixed on those years on purpose: a reference recomputed every year drifts with congestion and hides the growth the padding chapter measures. **Padding** is scheduled block time minus unimpeded block time.

    avg(padding)

Code: `warehouse/models/intermediate/int_unimpeded.sql` for the reference, `warehouse/models/marts/fct_flights.sql` for padding per flight.

## The rotation, the leg index and turnaround

A **rotation** is a sequence of flown legs by one tail number in which each leg leaves from the airport the previous leg landed at, after it landed, within 6 h of its scheduled arrival. A pair that fails the airport rule is a broken chain (usually an aircraft swap) and starts a new rotation rather than joining two aircraft; a pair whose departure precedes the previous arrival is an impossible sequence, quarantined as a link and counted. The **leg index** is the leg's place in its rotation; the **day leg index** its place in the tail's local calendar day, which is what "the first flight of the aircraft's day" means. **Turnaround** is the scheduled minutes between the previous leg's scheduled arrival and this leg's scheduled departure.

Code: `packages/rotations/src/turnaround_rotations/reconstruct.py` and `warehouse/models/intermediate/int_legs.sql`, which apply the same rules; `warehouse/tests/assert_linked_legs_obey_the_rotation_rules.sql` checks every link.

## Inherited delay

The minutes of a leg's departure delay explained by the previous leg's arrival delay: the propagation coefficient times the inbound's lateness beyond the scheduled turn less a minimum turn, capped at the leg's own departure delay. The **inherited share** is those minutes over all arrival delay minutes of flown legs in the reporting years.

    sum(inherited_minutes) / sum(arr_delay_pos)

Code: `packages/rotations/src/turnaround_rotations/propagation.py` and `packages/chapters/src/turnaround_chapters/ch04_inherited.py`.

## Completion factor, cancellation rate and diversion rate

The completion factor is the share of scheduled flights that were not cancelled; the cancellation rate is its complement; the diversion rate is the share of scheduled flights diverted.

    avg(cancelled::int)

Code: `cancellation_rate`, `completion_factor` and `diversion_rate` in `metrics/metrics.yml`.

## The reported cause fields, and why they are not cause

For every flight at least fifteen minutes late, the carrier reports how many minutes to attribute to five causes: the carrier, extreme weather, the national airspace system, security, and a late arriving aircraft. These are reports, filled in by the carrier under rules that keep the weather field for extreme weather and put ordinary weather that slows the airspace into the national airspace system field. A cause breakdown that does not add up to the arrival delay within 1 min is flagged and left out of the cause shares. The story compares the fields with estimates; it never presents a field as a cause.

    sum(cause_weather) filter (where cause_ok) / sum(cause_late_aircraft + cause_carrier + cause_nas + cause_weather + cause_security) filter (where cause_ok)

Code: `cause_ok` in `warehouse/models/marts/fct_flights.sql`; the estimate the fields are compared with in `packages/chapters/src/turnaround_chapters/ch06_causes.py`.

## A disruption, a baseline and recovery time

A **baseline** is a carrier's (or an airport's) median daily cancellation rate and mean arrival delay over its previous four weeks, with the median absolute deviation as its spread. A day's **score** is the larger of its two standardized anomalies. A **disruption alert** opens on a day whose score passes the threshold the cost chose and stays open while the score stays above half of it; the open run is one episode, and its length is the unit's **recovery time**. In the event studies, recovery time is the days from onset until the carrier's gap to its peers is back inside its own pre-event band for three days running.

Code: `packages/events/src/turnaround_events/detect.py` and `study.py`; the full method in [events.md](events.md).

## A misconnect, and a check

A connection is **missed** when the inbound flight is cancelled or diverted, or when its arrival delay, less the outbound flight's own departure delay, uses up the scheduled buffer less a minimum connection time of 25 min. A **check** is one question put to the calculator: an origin, a connecting airport, a destination, a travel month, the two scheduled hours and a buffer. It stores those and the answer, never a person.

Code: `packages/misconnect/src/turnaround_misconnect/curve.py` and `model.py`; the check log in `packages/api/src/turnaround_api/db.py`.
