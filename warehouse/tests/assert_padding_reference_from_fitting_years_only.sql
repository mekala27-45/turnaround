-- The unimpeded reference is fixed on the fitting years: no reference cell exists only because of a later year.
select r.route
from {{ ref('int_unimpeded') }} r
left join (
    select route, count(*) as n from {{ ref('stg_flights') }}
    where not excluded and year between {{ var('fit_first_year') }} and {{ var('fit_last_year') }}
    group by route
) f on f.route = r.route
where f.n is null
