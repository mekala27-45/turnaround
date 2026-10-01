-- Every flown leg with a usable tail and both delays is in exactly one rotation.
with eligible as (
    select count(*) as n from {{ ref('fct_flights') }}
    where not cancelled and not diverted and tail_number is not null and dep_delay is not null and arr_delay is not null
      and sched_dep_utc is not null
),
legs as (select count(*) as n, count(distinct flight_id) as d from {{ ref('int_legs') }})
select * from eligible, legs where eligible.n <> legs.n or legs.n <> legs.d
