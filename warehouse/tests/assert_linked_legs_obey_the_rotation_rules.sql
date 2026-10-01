-- Every linked leg departs where the previous one arrived, after it arrived, within the gap.
select flight_id
from {{ ref('int_legs') }}
where link_status = 'linked'
  and (prev_dest <> origin
       or sched_dep_utc < prev_sched_arr_utc
       or actual_dep_utc < prev_actual_arr_utc
       or date_diff('minute', prev_sched_arr_utc, sched_dep_utc) > {{ var('rotation_gap_hours') }} * 60)
