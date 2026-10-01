-- Flights that pass every rule, with UTC times from each airport's time zone.
-- A scheduled departure is a local clock time at the origin; subtracting the origin's UTC offset at
-- that local hour gives UTC. The scheduled arrival is the departure plus the scheduled elapsed time,
-- which avoids reading the arrival clock across midnight and across zones.
with flights as (
    select * from {{ ref('stg_flights') }} where not excluded
),
airports as (
    select code, tz from {{ ref('stg_airports') }}
)
select
    f.*,
    oa.tz as origin_tz,
    da.tz as dest_tz,
    cast(f.flight_date as timestamp) + to_minutes(cast(f.crs_dep_local - o.offset_minutes as bigint)) as sched_dep_utc,
    cast(f.flight_date as timestamp)
        + to_minutes(cast(f.crs_dep_local - o.offset_minutes + coalesce(f.crs_elapsed, 0) as bigint)) as sched_arr_utc
from flights f
left join airports oa on oa.code = f.origin
left join airports da on da.code = f.dest
left join {{ ref('stg_tz_offsets') }} o
    on o.tz = oa.tz and o.local_date = f.flight_date and o.local_hour = least(f.dep_hour, 23)
