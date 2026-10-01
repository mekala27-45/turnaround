select tz, local_date, cast(local_hour as integer) as local_hour, cast(offset_minutes as integer) as offset_minutes
from {{ source('reference', 'tz_offsets') }}
