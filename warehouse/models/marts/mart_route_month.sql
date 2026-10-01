-- Route, carrier and month: the explorer's main table.
select
    route,
    origin,
    dest,
    carrier,
    year,
    month,
    count(*) as scheduled,
    count(*) filter (where cancelled) as cancelled,
    count(*) filter (where not cancelled and not diverted) as flown,
    count(*) filter (where not cancelled and not diverted and {{ on_time('arr_delay') }}) as on_time,
    sum(arr_delay) filter (where not cancelled and not diverted) as arr_delay_sum,
    sum(crs_elapsed) filter (where not cancelled and not diverted) as crs_elapsed_sum,
    sum(actual_elapsed) filter (where not cancelled and not diverted) as actual_elapsed_sum,
    sum(padding) filter (where padding is not null) as padding_sum,
    count(padding) as padding_flights
from {{ ref('fct_flights') }}
group by all
