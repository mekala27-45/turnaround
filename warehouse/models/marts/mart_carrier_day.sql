-- Carrier and day: the carrier side of the disruption detector and the event studies.
select
    carrier,
    flight_date,
    count(*) as scheduled,
    count(*) filter (where cancelled) as cancelled,
    count(*) filter (where not cancelled and not diverted) as flown,
    sum(arr_delay) filter (where not cancelled and not diverted) as arr_delay_sum,
    count(*) filter (where not cancelled and not diverted and {{ on_time('arr_delay') }}) as on_time
from {{ ref('fct_flights') }}
group by all
