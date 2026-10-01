-- Every flown leg with a usable tail and both delays is in int_legs, and nothing else is; that no leg
-- is there twice is the unique test on int_legs.flight_id. A count(distinct) here would hold every
-- flight id in one hash table, which the full window does not fit in memory.
with eligible as (
    select count(*) as n from {{ ref('fct_flights') }}
    where not cancelled and not diverted and tail_number is not null and dep_delay is not null and arr_delay is not null
      and sched_dep_utc is not null
),
legs as (select count(*) as n from {{ ref('int_legs') }})
select * from eligible, legs where eligible.n <> legs.n
