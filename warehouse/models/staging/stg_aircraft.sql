-- Aircraft columns only: the registry's registrant name and address are never read (packages/contracts/faa.py).
select
    tail_number,
    registry_file,
    mfr_mdl_code,
    type_code,
    year_built,
    type_aircraft,
    type_engine,
    flights as flights_in_window,
    first_seen,
    last_seen
from {{ source('reference', 'aircraft') }}
