-- Punctuality by the leg's position in the aircraft's local day: the first departure is leg one.
select
    carrier,
    year(flight_date) as year,
    least(day_leg_index, 6) as leg_position,
    count(*) as flown,
    count(*) filter (where {{ on_time('arr_delay') }}) as on_time,
    sum(arr_delay) as arr_delay_sum,
    sum(dep_delay) as dep_delay_sum
from {{ ref('int_legs') }}
group by all
