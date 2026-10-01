-- The traveler's table: scheduled departure hour, day of week and month, by year.
select
    year,
    month,
    day_of_week,
    dep_hour,
    count(*) as scheduled,
    count(*) filter (where cancelled) as cancelled,
    count(*) filter (where not cancelled and not diverted) as flown,
    count(*) filter (where not cancelled and not diverted and {{ on_time('arr_delay') }}) as on_time,
    sum(arr_delay) filter (where not cancelled and not diverted) as arr_delay_sum
from {{ ref('fct_flights') }}
group by all
