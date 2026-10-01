select
    airport,
    cast(timezone('UTC', hour_utc) as timestamp) as hour_utc,
    temperature_2m,
    precipitation,
    snowfall,
    wind_speed_10m,
    wind_gusts_10m,
    cloud_cover_low,
    weather_code,
    fog,
    thunder,
    freezing
from {{ source('open_meteo', 'hourly') }}
