-- One row per reconstructed rotation: the aircraft's day as the tail number tells it.
select
    rotation_id,
    any_value(tail_number) as tail_number,
    any_value(carrier) as carrier,
    min(flight_date) as first_date,
    count(*) as legs,
    min(sched_dep_utc) as first_departure_utc,
    max(sched_arr_utc) as last_arrival_utc,
    sum(greatest(arr_delay, 0)) as arr_delay_pos_sum,
    max(arr_delay) as worst_arrival_delay,
    count(*) filter (where link_status = 'linked') as linked_legs,
    arg_min(link_status, leg_index) as opened_by
from {{ ref('int_legs') }}
group by rotation_id
