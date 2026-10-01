select * from {{ ref('mart_carrier_month') }} where on_time + late15 <> flown or flown > scheduled
