-- Flights by whole minute of arrival delay, carrier and month: the median comes from here exactly,
-- and the fifteen minute line's density test reads the same counts. Minutes below -60 and above 300
-- are pooled at the ends, which no median and no test window reaches.
select
    carrier,
    year,
    month,
    cast(least(greatest(arr_delay, -60), 300) as integer) as minute,
    count(*) as flights
from {{ ref('fct_flights') }}
where not cancelled and not diverted and arr_delay is not null
group by all
