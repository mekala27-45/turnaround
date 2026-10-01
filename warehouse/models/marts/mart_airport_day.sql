-- Departures by airport and day: the airport side of the disruption detector and the cause maps.
select
    origin as airport,
    flight_date,
    count(*) as scheduled,
    count(*) filter (where cancelled) as cancelled,
    count(*) filter (where not cancelled and not diverted) as flown,
    sum(dep_delay) filter (where not cancelled and not diverted) as dep_delay_sum,
    sum(arr_delay) filter (where not cancelled and not diverted) as arr_delay_sum,
    sum(cause_nas) filter (where cause_ok) as cause_nas_sum,
    sum(cause_weather) filter (where cause_ok) as cause_weather_sum,
    sum(arr_delay) filter (where cause_ok and cause_late_aircraft is not null) as cause_arr_delay_sum
from {{ ref('fct_flights') }}
group by all
