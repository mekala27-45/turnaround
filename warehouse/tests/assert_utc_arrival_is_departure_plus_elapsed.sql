-- The scheduled arrival in UTC is the scheduled departure plus the scheduled elapsed time, to the minute.
select flight_id
from {{ ref('fct_flights') }}
where crs_elapsed is not null and sched_dep_utc is not null
  and date_diff('minute', sched_dep_utc, sched_arr_utc) <> crs_elapsed
