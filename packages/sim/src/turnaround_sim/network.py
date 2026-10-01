"""A synthetic airline network with known truth, in the schema the warehouse gives the chapters.

Every estimator in the story runs here first, on data where the answer is known: the padding in
every schedule and the date it changed, the share of each late arrival carried into the next
departure, each carrier's own effect on arrival delay on routes of known difficulty, which carriers
bunch their arrivals under the fifteen minute line, and the four days one carrier melted down.

The network. Four hubs and thirty six spokes. Each carrier flies from two hubs (its own and its
neighbour's, so every carrier shares routes with others and the carriers form one connected set),
and serves a stated number of spokes from each. Aircraft fly hub, spoke, hub, spoke from a hub each
morning, three to six legs a day.

The delay process, leg by leg along each aircraft's day:

    scheduled block  = unimpeded(route, hour, season) + padding(carrier, route, date)
    actual block     = unimpeded + congestion       congestion is zero with probability p0, else exponential
    own departure    = route difficulty(route, hour) + weather(origin, day) + noise + meltdown
    inherited        = rho * max(0, previous arrival delay - (scheduled turn - minimum turn))
    departure delay  = own + inherited
    arrival delay    = departure delay + congestion - padding + carrier effect

Truth for the ranking is counterfactual and exact: the same draws are run a second time with every
carrier's effect and padding change set to the cross carrier average, and a carrier's true effect is
the mean difference in arrival delay over its own flights, propagation included.

Confounding is planted by letting better carriers serve harder spokes: at strength k the chance a
carrier serves a spoke rises with k times the product of the carrier's quality and the spoke's
difficulty, so the raw ranking is wrong by design and the adjusted one has to earn its keep.

Weather is a storm day at an airport: it adds a known number of minutes to every departure from the
airport and a stated fraction of that to every arrival into it, and it shows in the observed weather
columns as thunder with heavy rain, gusts and low cloud (calm days get light rain now and then, which
does nothing). The reported cause fields are filled the way a carrier fills them, with a planted
convention: late aircraft first, up to the inherited minutes; then the storm's minutes, of which only
a stated share is coded weather and the rest national airspace system; the remainder carrier. So the
reported weather field understates weather by design, and the weather estimator has to find the
minutes the field does not record. These draws come from their own random stream, so adding them
changed none of the draws above.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import numpy.typing as npt
import polars as pl
from turnaround_core.model import StrictModel

HUBS = 4
SPOKES = 36
HARD_MIN_GROUND = 10.0


class SimSpec(StrictModel):
    seed: int
    carriers: int = 8
    spokes_per_hub: int = 14
    aircraft_per_carrier: int = 16
    days: int = 365
    start: str = "2023-01-01"
    confounding: float = 0.5
    propagation: float = 0.8
    noise: float = 8.0
    congestion_zero_share: float = 0.25
    congestion_scale: float = 9.0
    min_turn: int = 35
    bunching_carriers: int = 2
    bunching_share: float = 0.35
    meltdown_carrier: int = 5
    meltdown_day: int = 300
    meltdown_days: int = 4
    weather_storm_rate: float = 0.03
    weather_storm_minutes: float = 30.0
    weather_dest_fraction: float = 0.4
    weather_reported_share: float = 0.3
    swap_rate: float = 0.002
    tail_share: float = 0.10
    tail_minutes: float = 40.0
    turn_scale: float = 12.0


@dataclass(frozen=True)
class Truth:
    """What the estimators are graded against."""

    carrier_effect: dict[str, float]
    carrier_effect_ranking: list[str]
    padding_by_carrier_route_month: pl.DataFrame
    padding_change: dict[str, float]
    padding_change_date: dict[str, str]
    unimpeded: pl.DataFrame
    propagation: float
    min_turn: int
    inherited_minutes: float
    arrival_delay_minutes: float
    inherited_share: float
    bunching_carriers: list[str]
    meltdown_carrier: str
    meltdown_dates: list[str]
    storm_days: int
    weather_minutes: float
    weather_share: float
    reported_weather_share: float


@dataclass(frozen=True)
class Simulation:
    spec: SimSpec
    flights: pl.DataFrame
    truth: Truth


def _carrier_codes(n: int) -> list[str]:
    return [f"C{i}" for i in range(n)]


def simulate(spec: SimSpec) -> Simulation:
    rng = np.random.default_rng(np.random.SeedSequence([spec.seed, 1407]))
    carriers = _carrier_codes(spec.carriers)
    n_airports = HUBS + SPOKES
    names = [f"H{i}" for i in range(HUBS)] + [f"S{i:02d}" for i in range(SPOKES)]
    start = date.fromisoformat(spec.start)

    # Spoke distances and difficulty. Difficulty is a per spoke delay offset in minutes, larger for busy spokes.
    distance = rng.uniform(250, 1600, size=(HUBS, SPOKES))
    spoke_difficulty = rng.normal(0.0, 6.0, SPOKES)
    hub_difficulty = np.array([4.0, 1.0, -1.0, -3.0])
    hour_difficulty = np.array(
        [-4, -4, -4, -4, -4, -3, -3, -2, -1, 0, 0, 1, 1, 2, 2, 3, 4, 5, 6, 6, 5, 3, 1, -1.0]
    )

    # Carrier quality: evenly spaced minute offsets on arrival delay, assigned in a seeded order.
    quality = np.linspace(-4.0, 4.0, spec.carriers)
    quality = quality[rng.permutation(spec.carriers)]

    # Which spokes each carrier serves from each of its two hubs. Better carriers (negative quality) lean
    # toward harder spokes at the stated confounding strength.
    serve: dict[tuple[int, int], list[int]] = {}
    z_quality = (quality - quality.mean()) / quality.std()
    z_difficulty = (spoke_difficulty - spoke_difficulty.mean()) / spoke_difficulty.std()
    for c in range(spec.carriers):
        for home in (c % HUBS, (c + 1) % HUBS):
            score = -spec.confounding * 2.5 * z_quality[c] * z_difficulty + rng.gumbel(size=SPOKES)
            serve[(c, home)] = sorted(np.argsort(-score)[: spec.spokes_per_hub].tolist())

    # Padding: a base per route plus a carrier step at a known date.
    base_padding = rng.uniform(4.0, 14.0, size=(HUBS, SPOKES))
    padding_change: npt.NDArray[np.float64] = rng.choice(
        np.array([-3.0, 0.0, 4.0, 6.0, 8.0]), size=spec.carriers
    ).astype(np.float64)
    change_day: npt.NDArray[np.int64] = rng.integers(60, spec.days - 60, size=spec.carriers).astype(np.int64)

    # Weather: storm days by airport.
    storms = rng.random((n_airports, spec.days)) < spec.weather_storm_rate

    # Bunching and the meltdown.
    bunchers = sorted(rng.choice(spec.carriers, size=spec.bunching_carriers, replace=False).tolist())
    meltdown_days = set(range(spec.meltdown_day, spec.meltdown_day + spec.meltdown_days))

    rows = _schedule(spec, rng, serve, distance, change_day, padding_change, base_padding)
    n = int(rows["carrier"].shape[0])
    hub = rows["hub"]
    spoke = rows["spoke"]
    outbound = rows["outbound"]
    day = rows["day"]
    hour = rows["dep_hour"]
    carrier = rows["carrier"]

    unimpeded: npt.NDArray[np.float64] = (
        28.0
        + distance[hub, spoke] / 7.8
        + np.where(hour >= 15, 4.0, 0.0)
        + np.where(np.isin(rows["month"], [12, 1, 2]), 3.0, 0.0)
    )
    unimpeded = np.round(unimpeded)
    difficulty = spoke_difficulty[spoke] + hub_difficulty[hub] + hour_difficulty[hour]
    origin_airport = np.where(outbound, hub, HUBS + spoke)
    dest_airport = np.where(outbound, HUBS + spoke, hub)
    weather = np.where(storms[origin_airport, day], spec.weather_storm_minutes, 0.0)
    weather_dest = np.where(
        storms[dest_airport, day], spec.weather_storm_minutes * spec.weather_dest_fraction, 0.0
    )
    noise = rng.gamma(2.0, spec.noise / 2.0, n) - spec.noise + rng.normal(0, spec.noise * 0.5, n)
    # A heavy tail: a stated share of legs carry a long own delay (a mechanical, a crew, a missed slot).
    noise = noise + np.where(rng.random(n) < spec.tail_share, rng.exponential(spec.tail_minutes, n), 0.0)
    congestion = np.where(
        rng.random(n) < spec.congestion_zero_share, 0.0, rng.exponential(spec.congestion_scale, n)
    )
    congestion_clear = congestion
    congestion = congestion + weather_dest
    melt = np.isin(day, list(meltdown_days)) & (carrier == spec.meltdown_carrier)
    melt_after = (
        (carrier == spec.meltdown_carrier)
        & (day >= spec.meltdown_day + spec.meltdown_days)
        & (day < spec.meltdown_day + spec.meltdown_days + 6)
    )
    own = difficulty + weather + noise + np.where(melt, 45.0, 0.0) + np.where(melt_after, 12.0, 0.0)
    cancel_p = 0.012 + np.where(storms[origin_airport, day], 0.05, 0.0) + np.where(melt, 0.38, 0.0)
    cancel_p = cancel_p + np.where(melt_after, 0.05, 0.0)
    cancelled = rng.random(n) < cancel_p

    padding_actual = rows["padding"]
    padding_average = rows["padding_average"]

    def run(
        effect: npt.NDArray[np.float64], padding: npt.NDArray[np.float64]
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """The delay chain along every aircraft's day for one assignment of carrier effects and padding."""
        dep = np.zeros(n)
        arr = np.zeros(n)
        inherited = np.zeros(n)
        leg = rows["leg"]
        prev = rows["prev_index"]
        for position in range(int(leg.max()) + 1):
            at = np.nonzero(leg == position)[0]
            carried = np.zeros(at.shape[0])
            if position > 0:
                has_prev = prev[at] >= 0
                p = prev[at][has_prev]
                slack = rows["sched_turn"][at][has_prev] - spec.min_turn
                carried[has_prev] = spec.propagation * np.maximum(0.0, arr[p] - slack)
            dep[at] = np.maximum(own[at] + effect[at] + carried, -15.0)
            if position > 0:
                # An airframe cannot leave before it has arrived and had the hard minimum on the ground.
                has_prev = prev[at] >= 0
                p = prev[at][has_prev]
                floor = arr[p] - rows["sched_turn"][at][has_prev] + HARD_MIN_GROUND
                bound = dep[at][has_prev]
                lifted = np.maximum(bound, floor)
                carried[has_prev] = carried[has_prev] + (lifted - bound)
                dep[at[has_prev]] = lifted
            inherited[at] = carried
            arr[at] = dep[at] + congestion[at] - padding[at]
        return dep, arr, inherited

    dep, arr, inherited = run(quality[carrier], padding_actual)
    _, arr_cf, _ = run(np.full(n, float(quality.mean())), padding_average)

    # Bunching: reported arrivals moved from just over the line to just under it.
    observed_arr = arr.copy()
    bunched = np.zeros(n, dtype=bool)
    for c in bunchers:
        candidates = np.nonzero((carrier == c) & (observed_arr >= 15) & (observed_arr < 20) & ~cancelled)[0]
        k = int(round(candidates.shape[0] * spec.bunching_share))
        if k:
            moved = rng.choice(candidates, size=k, replace=False)
            observed_arr[moved] = rng.integers(10, 15, size=k)
            bunched[moved] = True

    dep_r = np.round(dep)
    arr_r = np.round(observed_arr)
    sched_block = unimpeded + padding_actual
    actual_block = np.round(sched_block + (arr_r - dep_r))
    flight_date = np.array([start + timedelta(days=int(d)) for d in range(spec.days)], dtype="datetime64[D]")[
        day
    ]
    sched_dep_min = rows["sched_dep"]

    # Aircraft swaps: a stated share of legs flown by another tail of the same carrier, which the
    # rotation rules have to split rather than join.
    tails = rows["tail"].astype(object)
    swaps = rng.random(n) < spec.swap_rate
    tails[swaps] = [f"N{9000 + int(c)}SW" for c in carrier[swaps]]

    flights = pl.DataFrame(
        {
            "flight_id": np.arange(n, dtype=np.int64) + 1,
            "flight_date": flight_date,
            "carrier": np.array(carriers, dtype=object)[carrier],
            "tail_number": tails,
            "flight_number": rows["flight_number"],
            "origin": np.array(names, dtype=object)[origin_airport],
            "dest": np.array(names, dtype=object)[dest_airport],
            "crs_dep_local": sched_dep_min.astype(np.int32),
            "dep_hour": hour.astype(np.int8),
            "crs_elapsed": sched_block.astype(np.int32),
            "actual_elapsed": np.where(cancelled, np.nan, actual_block),
            "dep_delay": np.where(cancelled, np.nan, dep_r),
            "arr_delay": np.where(cancelled, np.nan, arr_r),
            "cancelled": cancelled,
            "diverted": np.zeros(n, dtype=bool),
            "type_code": rows["type_code"],
            "true_inherited": np.where(cancelled, np.nan, inherited),
            "true_effect": arr - arr_cf,
            "true_unimpeded": unimpeded,
            "true_padding": padding_actual,
            "true_storm_origin": storms[origin_airport, day],
            "bunched": bunched,
            "swapped": swaps,
        }
    ).with_columns(
        pl.col("flight_date").cast(pl.Date),
        pl.col("actual_elapsed").cast(pl.Int32, strict=False),
        pl.col("dep_delay").cast(pl.Int32, strict=False),
        pl.col("arr_delay").cast(pl.Int32, strict=False),
    )
    flights = flights.with_columns(
        pl.col("flight_date").dt.year().alias("year"),
        pl.col("flight_date").dt.month().alias("month"),
        pl.col("flight_date").dt.weekday().alias("day_of_week"),
        (pl.col("origin") + "-" + pl.col("dest")).alias("route"),
        (pl.col("flight_date").cast(pl.Datetime("us")) + pl.duration(minutes=pl.col("crs_dep_local"))).alias(
            "sched_dep_utc"
        ),
    ).with_columns(
        (pl.col("sched_dep_utc") + pl.duration(minutes=pl.col("crs_elapsed"))).alias("sched_arr_utc"),
        ((pl.col("crs_dep_local") + pl.col("crs_elapsed")) % 1440).alias("crs_arr_local"),
    )

    flights = flights.with_columns(_observed_weather(spec, storms, origin_airport, dest_airport, day, n))
    causes, weather_direct = _reported_causes(
        spec, arr_r, cancelled, inherited, weather, weather_dest, congestion_clear
    )
    flights = flights.with_columns(*causes, pl.Series("true_weather", weather_direct))

    flown = ~cancelled
    observed_late = float(np.sum(np.maximum(arr_r, 0.0)[flown]))
    weather_minutes = float(np.sum(weather_direct[flown]))
    reported_weather = float(flights.filter(~pl.col("cancelled"))["cause_weather"].fill_null(0).sum())
    effects = {}
    for c, code in enumerate(carriers):
        mask = (carrier == c) & flown
        effects[code] = float(np.mean((arr - arr_cf)[mask]))
    mean_effect = float(np.mean(list(effects.values())))
    effects = {k: v - mean_effect for k, v in effects.items()}
    ranking = sorted(effects, key=lambda k: effects[k])
    late_minutes = float(np.sum(np.maximum(arr, 0.0)[flown]))
    inherited_minutes = float(np.sum(np.minimum(inherited, np.maximum(dep, 0.0))[flown]))
    padding_frame = (
        flights.select("carrier", "route", "month", "true_padding")
        .group_by(["carrier", "route", "month"])
        .agg(pl.col("true_padding").mean().alias("padding"))
        .sort(["carrier", "route", "month"])
    )
    unimpeded_frame = (
        flights.select("route", "dep_hour", "month", "true_unimpeded")
        .unique()
        .sort(["route", "dep_hour", "month"])
    )
    truth = Truth(
        carrier_effect=effects,
        carrier_effect_ranking=ranking,
        padding_by_carrier_route_month=padding_frame,
        padding_change={carriers[c]: float(padding_change[c]) for c in range(spec.carriers)},
        padding_change_date={
            carriers[c]: (start + timedelta(days=int(change_day[c]))).isoformat()
            for c in range(spec.carriers)
        },
        unimpeded=unimpeded_frame,
        propagation=spec.propagation,
        min_turn=spec.min_turn,
        inherited_minutes=inherited_minutes,
        arrival_delay_minutes=late_minutes,
        inherited_share=inherited_minutes / late_minutes if late_minutes else 0.0,
        bunching_carriers=[carriers[c] for c in bunchers],
        meltdown_carrier=carriers[spec.meltdown_carrier],
        meltdown_dates=[(start + timedelta(days=d)).isoformat() for d in sorted(meltdown_days)],
        storm_days=int(storms.sum()),
        weather_minutes=weather_minutes,
        weather_share=weather_minutes / observed_late if observed_late else 0.0,
        reported_weather_share=reported_weather / observed_late if observed_late else 0.0,
    )
    return Simulation(spec=spec, flights=flights, truth=truth)


def _observed_weather(
    spec: SimSpec,
    storms: npt.NDArray[np.bool_],
    origin_airport: npt.NDArray[np.int64],
    dest_airport: npt.NDArray[np.int64],
    day: npt.NDArray[np.int64],
    n: int,
) -> list[pl.Series]:
    """The weather columns the warehouse joins at both ends, drawn on their own stream."""
    wx = np.random.default_rng(np.random.SeedSequence([spec.seed, 1407, 6]))
    out: list[pl.Series] = []
    for end, airport in (("origin", origin_airport), ("dest", dest_airport)):
        storm = storms[airport, day]
        drizzle = (wx.random(n) < 0.12) & ~storm
        precip = np.where(storm, wx.gamma(2.0, 2.0, n), np.where(drizzle, wx.exponential(0.4, n), 0.0))
        gusts = np.clip(np.where(storm, wx.normal(55.0, 10.0, n), wx.normal(25.0, 8.0, n)), 0.0, None)
        low_cloud = np.where(storm, wx.uniform(60.0, 100.0, n), wx.uniform(0.0, 60.0, n))
        out += [
            pl.Series(f"{end}_precipitation", np.round(precip, 1)),
            pl.Series(f"{end}_snowfall", np.zeros(n)),
            pl.Series(f"{end}_wind_gusts", np.round(gusts, 1)),
            pl.Series(f"{end}_low_cloud", np.round(low_cloud)),
            pl.Series(f"{end}_thunder", storm),
            pl.Series(f"{end}_fog", np.zeros(n, dtype=bool)),
            pl.Series(f"{end}_freezing", np.zeros(n, dtype=bool)),
        ]
    out.append(pl.Series("weather_both_ends", np.ones(n, dtype=bool)))
    return out


def _reported_causes(
    spec: SimSpec,
    arr_r: npt.NDArray[np.float64],
    cancelled: npt.NDArray[np.bool_],
    inherited: npt.NDArray[np.float64],
    weather: npt.NDArray[np.float64],
    weather_dest: npt.NDArray[np.float64],
    congestion_clear: npt.NDArray[np.float64],
) -> tuple[list[pl.Series], npt.NDArray[np.float64]]:
    """The five cause fields for flights fifteen or more minutes late, filled by the planted convention."""
    late = (arr_r >= 15) & ~cancelled
    total = np.where(late, arr_r, 0.0)
    late_aircraft = np.minimum(np.round(np.maximum(inherited, 0.0)), total)
    rest = total - late_aircraft
    direct = weather + weather_dest
    storm_minutes = np.minimum(direct, rest)
    coded_weather = np.round(storm_minutes * spec.weather_reported_share)
    rest = rest - storm_minutes
    nas_clear = np.minimum(np.round(np.maximum(congestion_clear, 0.0)), rest)
    nas = storm_minutes - coded_weather + nas_clear
    carrier = rest - nas_clear

    def field(name: str, values: npt.NDArray[np.float64]) -> pl.Series:
        return pl.Series(name, np.where(late, values, np.nan)).cast(pl.Int32, strict=False)

    causes = [
        field("cause_carrier", carrier),
        field("cause_weather", coded_weather),
        field("cause_nas", nas),
        field("cause_security", np.zeros_like(total)),
        field("cause_late_aircraft", late_aircraft),
        pl.Series("cause_ok", np.ones(arr_r.shape[0], dtype=bool)),
    ]
    return causes, np.where(cancelled, 0.0, direct)


def _schedule(
    spec: SimSpec,
    rng: np.random.Generator,
    serve: dict[tuple[int, int], list[int]],
    distance: npt.NDArray[np.float64],
    change_day: npt.NDArray[np.int64],
    padding_change: npt.NDArray[np.float64],
    base_padding: npt.NDArray[np.float64],
) -> dict[str, npt.NDArray[Any]]:
    """Every aircraft's day, hub, spoke, hub, spoke, with scheduled times and turns."""
    cols: dict[str, list[Any]] = {k: [] for k in (
        "carrier", "hub", "spoke", "outbound", "day", "leg", "prev_index", "sched_dep", "dep_hour",
        "sched_turn", "padding", "padding_average", "tail", "flight_number", "month", "type_code",
    )}  # fmt: skip
    average_change = float(np.mean(padding_change))
    start = date.fromisoformat(spec.start)
    months = np.array([(start + timedelta(days=d)).month for d in range(spec.days)])
    index = 0
    for c in range(spec.carriers):
        hubs = (c % HUBS, (c + 1) % HUBS)
        for a in range(spec.aircraft_per_carrier):
            hub = hubs[a % 2]
            spokes = serve[(c, hub)]
            tail = f"N{100 + c * 50 + a}C{c}"
            # Aircraft types are shared across carriers, so type and carrier are not the same thing.
            aircraft_type = f"T{int(rng.integers(0, 4))}"
            legs_today = rng.integers(3, 7, size=spec.days)
            first_dep = rng.integers(330, 480, size=spec.days)
            for d in range(spec.days):
                clock = int(first_dep[d])
                prev = -1
                spoke = spokes[int(rng.integers(0, len(spokes)))]
                block_padding_change = padding_change[c] if d >= change_day[c] else 0.0
                for leg in range(int(legs_today[d])):
                    outbound = leg % 2 == 0
                    if outbound and leg > 0:
                        spoke = spokes[int(rng.integers(0, len(spokes)))]
                    hour = (clock // 60) % 24
                    pad = float(base_padding[hub, spoke] + block_padding_change)
                    pad_avg = float(
                        base_padding[hub, spoke]
                        + (average_change if d >= int(np.median(change_day)) else 0.0)
                    )
                    unimpeded = (
                        28.0
                        + distance[hub, spoke] / 7.8
                        + (4.0 if hour >= 15 else 0.0)
                        + (3.0 if months[d] in (12, 1, 2) else 0.0)
                    )
                    block = round(unimpeded) + pad
                    turn = int(spec.min_turn - 5 + rng.gamma(2.0, spec.turn_scale)) if leg > 0 else 0
                    if leg > 0:
                        clock += turn
                        hour = (clock // 60) % 24
                    cols["carrier"].append(c)
                    cols["hub"].append(hub)
                    cols["spoke"].append(spoke)
                    cols["outbound"].append(outbound)
                    cols["day"].append(d)
                    cols["leg"].append(leg)
                    cols["prev_index"].append(prev)
                    cols["sched_dep"].append(clock)
                    cols["dep_hour"].append(hour)
                    cols["sched_turn"].append(turn)
                    cols["padding"].append(pad)
                    cols["padding_average"].append(pad_avg)
                    cols["tail"].append(tail)
                    cols["flight_number"].append(1000 + (c * 97 + a * 13 + leg) % 8000)
                    cols["month"].append(months[d])
                    cols["type_code"].append(aircraft_type)
                    prev = index
                    index += 1
                    clock += int(round(block))
    out = {k: np.asarray(v) for k, v in cols.items()}
    out["sched_turn"] = out["sched_turn"].astype(np.float64)
    out["padding"] = out["padding"].astype(np.float64)
    out["padding_average"] = out["padding_average"].astype(np.float64)
    return out
