-- Additive components by carrier and month: what the metric layer's mart expressions, the workbook
-- and the BI extracts read. Every column is a count or a sum, so any coarser grain is a sum of rows.
select
    carrier,
    year,
    month,
    count(*) as scheduled,
    count(*) filter (where cancelled) as cancelled,
    count(*) filter (where diverted) as diverted,
    count(*) filter (where not cancelled and not diverted) as flown,
    count(*) filter (where not cancelled and not diverted and {{ on_time('arr_delay') }}) as on_time,
    count(*) filter (where not cancelled and not diverted and arr_delay >= 15) as late15,
    sum(arr_delay) filter (where not cancelled and not diverted) as arr_delay_sum,
    sum(greatest(arr_delay, 0)) filter (where not cancelled and not diverted) as arr_delay_pos_sum,
    sum(dep_delay) filter (where not cancelled and not diverted) as dep_delay_sum,
    sum(crs_elapsed) filter (where not cancelled and not diverted) as crs_elapsed_sum,
    sum(actual_elapsed) filter (where not cancelled and not diverted) as actual_elapsed_sum,
    sum(padding) filter (where padding is not null) as padding_sum,
    count(padding) as padding_flights,
    sum(crs_elapsed) filter (where padding is not null) as padding_block_sum,
    count(*) filter (where cause_ok and cause_late_aircraft is not null) as cause_flights,
    sum(cause_late_aircraft) filter (where cause_ok) as cause_late_aircraft_sum,
    sum(cause_carrier) filter (where cause_ok) as cause_carrier_sum,
    sum(cause_nas) filter (where cause_ok) as cause_nas_sum,
    sum(cause_weather) filter (where cause_ok) as cause_weather_sum,
    sum(cause_security) filter (where cause_ok) as cause_security_sum,
    sum(arr_delay) filter (where cause_ok and cause_late_aircraft is not null) as cause_arr_delay_sum
from {{ ref('fct_flights') }}
group by all
