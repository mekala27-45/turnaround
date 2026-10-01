-- Every rule counted by carrier and month, over every reported row; nothing was deleted to make this.
select
    carrier,
    year,
    month,
    count(*) as rows,
    count(*) filter (where q_duplicate_key) as duplicate_key,
    count(*) filter (where q_actual_without_scheduled) as actual_without_scheduled,
    count(*) filter (where q_impossible_time) as impossible_time,
    count(*) filter (where q_elapsed_mismatch) as elapsed_mismatch,
    count(*) filter (where q_status_conflict) as status_conflict,
    count(*) filter (where q_missing_actual) as missing_actual,
    count(*) filter (where q_cause_mismatch) as cause_mismatch,
    count(*) filter (where q_tail_missing) as tail_missing,
    count(*) filter (where q_tail_format) as tail_format,
    count(*) filter (where q_revision) as revision,
    count(*) filter (where excluded) as excluded
from {{ ref('stg_flights') }}
group by all
