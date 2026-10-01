"""The aircraft's day, reconstructed from the tail number.

Every flown leg with a usable tail number is ordered by scheduled departure in UTC within its tail,
and each leg is linked to the one before it when the pair is a possible sequence for one airframe:

1. the leg departs from the airport the previous leg arrived at;
2. it is scheduled to depart after the previous leg was scheduled to arrive, and it actually
   departed after the previous leg actually arrived;
3. the scheduled gap is at most the stated number of hours (six): a longer sit, usually the night,
   starts a new rotation.

A pair that fails rule 1 is a broken chain, most often an aircraft swap the tail number does not
show: the rotation is split there, not joined. A pair that fails rule 2 is an impossible sequence
(one airframe cannot depart before it has arrived): the leg is quarantined as a link, counted, and
starts a new rotation. Ordering is by UTC with the flight id as the tie break, so the same data
gives the same rotations on every run.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

LINK_STATUSES = ("first", "linked", "gap", "broken_chain", "impossible")


@dataclass(frozen=True)
class RotationCounts:
    legs: int
    linked: int
    first: int
    gap: int
    broken_chain: int
    impossible: int
    rotations: int
    tails: int

    @property
    def starts(self) -> int:
        return self.first + self.gap + self.broken_chain + self.impossible


def reconstruct_sql(source: str, gap_hours: float) -> str:
    """The legs of ``source`` with their link to the previous leg, the link's status and the rotation id."""
    return f"""
    with legs as (
        select
            flight_id, flight_date, carrier, tail_number, origin, dest, dep_hour,
            sched_dep_utc, sched_arr_utc, dep_delay, arr_delay,
            sched_dep_utc + to_minutes(cast(dep_delay as bigint)) as actual_dep_utc,
            sched_arr_utc + to_minutes(cast(arr_delay as bigint)) as actual_arr_utc
        from {source}
        where not cancelled and not diverted and tail_number is not null
          and dep_delay is not null and arr_delay is not null and sched_dep_utc is not null
    ),
    ordered as (
        select
            *,
            lag(flight_id) over w as prev_flight_id,
            lag(dest) over w as prev_dest,
            lag(sched_arr_utc) over w as prev_sched_arr_utc,
            lag(actual_arr_utc) over w as prev_actual_arr_utc,
            lag(arr_delay) over w as prev_arr_delay,
            lag(carrier) over w as prev_carrier
        from legs
        window w as (partition by tail_number order by sched_dep_utc, flight_id)
    ),
    statused as (
        select
            *,
            date_diff('minute', prev_sched_arr_utc, sched_dep_utc) as sched_turn,
            date_diff('minute', prev_actual_arr_utc, actual_dep_utc) as actual_turn,
            case
                when prev_flight_id is null then 'first'
                when date_diff('minute', prev_sched_arr_utc, sched_dep_utc) > {gap_hours * 60} then 'gap'
                when prev_dest <> origin then 'broken_chain'
                when sched_dep_utc < prev_sched_arr_utc or actual_dep_utc < prev_actual_arr_utc then 'impossible'
                else 'linked'
            end as link_status
        from ordered
    )
    select
        *,
        tail_number || ':' || cast(
            sum(case when link_status = 'linked' then 0 else 1 end)
                over (partition by tail_number order by sched_dep_utc, flight_id rows unbounded preceding)
            as varchar
        ) as rotation_id
    from statused
    """


def leg_index_sql(source: str) -> str:
    """Leg number within the rotation, and within the tail's local calendar day.

    A rotation can run for days when the aircraft's overnight sits are shorter than the gap (Hawaii's
    inter island flying, red eye operations), which is right for propagation, since a short night
    passes a late arrival on to the morning. The traveler's question is different: the first
    departure of the aircraft's day is its first scheduled departure on the local date, day_leg_index
    one.
    """
    return f"""
    select
        *,
        row_number() over (partition by rotation_id order by sched_dep_utc, flight_id) as leg_index,
        count(*) over (partition by rotation_id) as rotation_legs,
        row_number() over (partition by tail_number, flight_date order by sched_dep_utc, flight_id) as day_leg_index
    from {source}
    """


def full_sql(source: str, gap_hours: float) -> str:
    """Links, statuses, rotation ids and leg numbers in one statement: the warehouse model int_legs is
    generated from this function (scripts/build_warehouse_sql.py), so the simulator and the real
    flights go through the same SQL."""
    return leg_index_sql(f"({reconstruct_sql(source, gap_hours)})")


def reconstruct(con: duckdb.DuckDBPyConnection, source: str, target: str, gap_hours: float) -> RotationCounts:
    """Write the linked legs of ``source`` to table ``target`` and count what the rules did."""
    con.execute(f"create or replace table {target}_stage as {reconstruct_sql(source, gap_hours)}")
    con.execute(f"create or replace table {target} as {leg_index_sql(target + '_stage')}")
    con.execute(f"drop table {target}_stage")
    return counts(con, target)


def counts(con: duckdb.DuckDBPyConnection, target: str) -> RotationCounts:
    row = con.execute(
        f"""
        select
            count(*),
            count(*) filter (where link_status = 'linked'),
            count(*) filter (where link_status = 'first'),
            count(*) filter (where link_status = 'gap'),
            count(*) filter (where link_status = 'broken_chain'),
            count(*) filter (where link_status = 'impossible'),
            count(distinct rotation_id),
            count(distinct tail_number)
        from {target}
        """
    ).fetchone()
    assert row is not None
    return RotationCounts(*[int(v) for v in row])
