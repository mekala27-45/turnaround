select
    code,
    name,
    municipality,
    region,
    cast(latitude as double) as latitude,
    cast(longitude as double) as longitude,
    elevation_ft,
    kind,
    tz
from {{ source('reference', 'airports') }}
