"""Chapter 6: causes, reported and estimated.

The on time files carry five cause fields, filled in by the carrier for every flight fifteen or more
minutes late: carrier, weather, national airspace system, security and late aircraft. They are a
record of what was reported, not a measurement. This chapter reads them, then estimates the share of
delay minutes weather explains from the weather itself: arrival delay regressed on the hourly
weather at the origin at departure and at the destination at arrival, with origin by hour, destination
by hour and month fixed effects, on flights between two of the thirty airports with weather. The
minutes the inbound aircraft carried in (chapter 4's propagation term, with its minimum turn) enter
as a control, so the weather terms measure what the weather did to this flight directly and the
weather that reached it through a late inbound aircraft stays in chapter 4's inherited share. Calm
weather (no precipitation, snow, thunder, fog or freezing precipitation, gusts at or under 40 km/h,
no low cloud) is the counterfactual; the attributable minutes are the fitted minutes above it, and
the share's interval comes from the coefficients' day clustered covariance.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
import polars as pl
from turnaround_stats.fe import cluster_scores, demean_exact, vcov_from_scores

GUST_CALM_KMH = 40.0
FEATURES: tuple[tuple[str, str], ...] = (
    ("origin_precip", "least(coalesce(origin_precipitation, 0), 10)"),
    ("origin_snow", "least(coalesce(origin_snowfall, 0), 5)"),
    ("origin_gust", f"greatest(coalesce(origin_wind_gusts, 0) - {GUST_CALM_KMH}, 0)"),
    ("origin_low_cloud", "coalesce(origin_low_cloud, 0) / 100.0"),
    ("origin_thunder", "coalesce(origin_thunder, false)::int"),
    ("origin_fog", "coalesce(origin_fog, false)::int"),
    ("origin_freezing", "coalesce(origin_freezing, false)::int"),
    ("dest_precip", "least(coalesce(dest_precipitation, 0), 10)"),
    ("dest_snow", "least(coalesce(dest_snowfall, 0), 5)"),
    ("dest_gust", f"greatest(coalesce(dest_wind_gusts, 0) - {GUST_CALM_KMH}, 0)"),
    ("dest_low_cloud", "coalesce(dest_low_cloud, 0) / 100.0"),
    ("dest_thunder", "coalesce(dest_thunder, false)::int"),
    ("dest_fog", "coalesce(dest_fog, false)::int"),
    ("dest_freezing", "coalesce(dest_freezing, false)::int"),
)
CAUSE_COLUMNS = ("late_aircraft", "carrier", "nas", "weather", "security")


@dataclass(frozen=True)
class CausesResult:
    by_year: pl.DataFrame
    nas_by_airport: pl.DataFrame
    flights_modelled: int
    coefficients: list[tuple[str, float, float]]
    weather_share: float
    weather_share_low: float
    weather_share_high: float
    reported_weather_share: float
    reported_nas_share: float
    reported_weather_cause_share: float
    carried_coefficient: float
    arrival_minutes: float
    days: int
    sql_model: str
    sql_reported: str


def reported_sql(source: str) -> str:
    sums = ", ".join(f"sum(cause_{c}) filter (where cause_ok) as {c}" for c in CAUSE_COLUMNS)
    return f"""
    select year, {sums}, sum(greatest(arr_delay, 0)) filter (where not cancelled and not diverted) as arrival_minutes
    from {source} group by year order by year
    """


def model_sql(source: str, where: str, legs: str, min_turn: int) -> str:
    features = ",\n           ".join(f"{expr} as {name}" for name, expr in FEATURES)
    return f"""
    select f.flight_date, f.origin || ':' || cast(f.dep_hour as varchar) as origin_hour,
           f.dest || ':' || cast(cast(f.crs_arr_local // 60 as integer) % 24 as varchar) as dest_hour,
           f.year * 100 + f.month as period, f.arr_delay,
           {features},
           coalesce(greatest(0, l.prev_arr_delay - (l.sched_turn - {min_turn})), 0) as carried,
           f.cause_weather, f.cause_nas, f.cause_ok
    from (select * from {source} where {where}) f
    left join {legs} l on l.flight_id = f.flight_id and l.link_status = 'linked'
    where f.weather_both_ends and not f.cancelled and not f.diverted and f.arr_delay is not null
    order by f.flight_id
    """


def _codes(values: np.ndarray) -> np.ndarray:
    return np.unique(values, return_inverse=True)[1].astype(np.int64)


def estimate(
    con: duckdb.DuckDBPyConnection,
    source: str,
    *,
    where: str,
    legs: str,
    min_turn: int,
    top_airports: int = 30,
) -> CausesResult:
    sql_reported = reported_sql(source)
    by_year = con.execute(sql_reported).pl()
    total = pl.sum_horizontal(*[pl.col(c) for c in CAUSE_COLUMNS])
    by_year = by_year.with_columns(*[(pl.col(c) / total).alias(f"{c}_share") for c in CAUSE_COLUMNS])
    nas = con.execute(
        f"""
        with busiest as (
            select dest, count(*) as n from {source} where ({where}) group by dest order by n desc, dest limit {top_airports}
        )
        select f.dest as airport, count(*) as flights,
               sum(cause_nas) filter (where cause_ok) / nullif(sum(cause_late_aircraft + cause_carrier + cause_nas
                   + cause_weather + cause_security) filter (where cause_ok), 0) as nas_share,
               sum(cause_nas) filter (where cause_ok) / nullif(count(*), 0) as nas_minutes_per_flight
        from {source} f join busiest b using (dest)
        where ({where}) and not cancelled and not diverted
        group by f.dest order by nas_share desc, airport
        """
    ).pl()
    sql_model = model_sql(source, where, legs, min_turn)
    frame = con.execute(sql_model).pl()
    names = [n for n, _ in FEATURES]
    x = frame.select([*names, "carried"]).to_numpy().astype(np.float64)
    y = frame["arr_delay"].to_numpy().astype(np.float64)
    groups = [_codes(frame[g].to_numpy()) for g in ("origin_hour", "dest_hour", "period")]
    w = np.ones(y.shape[0])
    stacked = demean_exact(np.column_stack([y, x]), w, groups)
    yt, xt = stacked[:, 0], stacked[:, 1:]
    keep = xt.std(axis=0) > 0
    if not keep[-1]:
        raise ValueError("the inbound aircraft control has no variation; were the legs built?")
    xt = xt[:, keep]
    kept_names = [n for n, k in zip([*names, "carried"], keep, strict=True) if k]
    bread_inverse = np.linalg.inv(xt.T @ xt)
    beta = bread_inverse @ (xt.T @ yt)
    resid = yt - xt @ beta
    days = _codes(frame["flight_date"].to_numpy())
    vcov = vcov_from_scores(bread_inverse, cluster_scores(xt, resid, w, days))
    se = np.sqrt(np.clip(np.diag(vcov), 0, None))
    # The weather terms only: the carried control's minutes are chapter 4's, not weather's.
    weather_kept = np.array([n != "carried" for n in kept_names])
    contribution = np.where(weather_kept, x[:, keep].sum(axis=0), 0.0)
    arrival = float(np.maximum(y, 0).sum())
    attributable = float(contribution @ beta)
    share_se = float(np.sqrt(contribution @ vcov @ contribution)) / arrival
    share = attributable / arrival
    reported_weather = float(frame["cause_weather"].fill_null(0).sum())
    reported_nas = float(frame["cause_nas"].fill_null(0).sum())
    causes_total = con.execute(
        f"""
        select sum(cause_late_aircraft + cause_carrier + cause_nas + cause_weather + cause_security) filter (where cause_ok),
               sum(cause_weather) filter (where cause_ok)
        from {source} where weather_both_ends and not cancelled and not diverted and ({where})
        """
    ).fetchone()
    assert causes_total is not None
    return CausesResult(
        by_year=by_year,
        nas_by_airport=nas,
        flights_modelled=int(y.shape[0]),
        coefficients=[
            (n, float(b), float(s)) for n, b, s in zip(kept_names, beta, se, strict=True) if n != "carried"
        ],
        weather_share=share,
        weather_share_low=share - 1.959963984540054 * share_se,
        weather_share_high=share + 1.959963984540054 * share_se,
        reported_weather_share=reported_weather / arrival,
        reported_nas_share=reported_nas / arrival,
        reported_weather_cause_share=float(causes_total[1] or 0) / float(causes_total[0] or 1),
        carried_coefficient=float(beta[-1]),
        arrival_minutes=arrival,
        days=int(days.max()) + 1,
        sql_model=sql_model.strip(),
        sql_reported=sql_reported.strip(),
    )


def message(r: CausesResult) -> str:
    ratio = r.weather_share / r.reported_weather_share if r.reported_weather_share > 0 else float("inf")
    if ratio >= 1.5:
        return "Weather explains more delay than the weather field records"
    if ratio <= 0.67:
        return "The weather field records more delay than the weather explains"
    return "The weather field and the weather itself roughly agree"
