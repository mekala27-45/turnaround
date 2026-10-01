"""The fair ranking: carriers compared on what they fly, not on where they fly it.

Arrival delay is regressed on carrier with fixed effects for route, month, scheduled departure hour
and aircraft type, fit on cells of carrier, route, month, hour and type with the flight counts as
weights (exact for the linear model; see turnaround_stats.fe). Carrier effects are stated relative
to the flight weighted average carrier. Intervals are clustered by day: a cell spans a month, so the
day level scores are summed over the flights themselves in DuckDB and passed to the sandwich.

The raw ranking is each carrier's mean arrival delay minus the overall mean, beside it.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
import polars as pl
from turnaround_stats.fe import contrasts_to_mean, dummies, fit, vcov_from_scores

CELL_KEYS = ("carrier", "route", "period", "dep_hour", "type_code")


@dataclass(frozen=True)
class Ranking:
    carriers: list[str]
    flights: list[int]
    raw: list[float]
    adjusted: list[float]
    adjusted_se: list[float] | None
    cells: int
    days: int | None
    converged: bool
    iterations: int

    def order(self, which: str) -> list[str]:
        values = self.raw if which == "raw" else self.adjusted
        pairs = sorted(zip(values, self.carriers, strict=True), key=lambda p: (p[0], p[1]))
        return [c for _, c in pairs]


def cells_sql(source: str, where: str, period: str) -> str:
    return f"""
    select carrier, route, {period} as period, dep_hour, coalesce(type_code, 'unknown') as type_code,
           count(*) as flights, avg(arr_delay) as arr_delay
    from {source}
    where not cancelled and not diverted and arr_delay is not null and ({where})
    group by all
    """


def estimate(
    con: duckdb.DuckDBPyConnection,
    source: str,
    *,
    where: str = "true",
    period: str = "year * 100 + month",
    cluster_by_day: bool = False,
) -> Ranking:
    cells = con.execute(
        cells_sql(source, where, period) + " order by carrier, route, period, dep_hour, type_code"
    ).pl()
    carriers = sorted(cells["carrier"].unique().to_list())
    code = {c: i for i, c in enumerate(carriers)}
    carrier_idx = np.array([code[c] for c in cells["carrier"].to_list()], dtype=np.int64)
    weights = cells["flights"].to_numpy().astype(np.float64)
    y = cells["arr_delay"].to_numpy().astype(np.float64)
    groups = [cells[k].to_numpy() for k in ("route", "period", "dep_hour", "type_code")]
    x = dummies(carrier_idx, len(carriers))
    result = fit(y, x, weights, groups, carriers[1:])
    flights = np.bincount(carrier_idx, weights=weights, minlength=len(carriers))
    totals = np.bincount(carrier_idx, weights=weights * y, minlength=len(carriers))
    overall = float((weights * y).sum() / weights.sum())
    raw = (totals / flights) - overall
    vcov = None
    days = None
    if cluster_by_day:
        # After the sweep converges the demeaned residual is the full model's residual, so the cell's
        # fitted value is its mean less that residual.
        vcov, days = _day_clustered(
            con, source, where, period, cells, result.x_tilde, y - result.resid, result.bread_inverse
        )
    effects, effects_vcov = contrasts_to_mean(result.coef, vcov, flights)
    se = (
        [float(s) for s in np.sqrt(np.clip(np.diag(effects_vcov), 0, None))]
        if effects_vcov is not None
        else None
    )
    return Ranking(
        carriers=carriers,
        flights=[int(f) for f in flights],
        raw=[float(v) for v in raw],
        adjusted=[float(v) for v in effects],
        adjusted_se=se,
        cells=cells.height,
        days=days,
        converged=result.converged,
        iterations=result.iterations,
    )


def _day_clustered(
    con: duckdb.DuckDBPyConnection,
    source: str,
    where: str,
    period: str,
    cells: pl.DataFrame,
    x_tilde: np.ndarray,
    fitted: np.ndarray,
    bread_inverse: np.ndarray,
) -> tuple[np.ndarray, int]:
    """Day level scores summed over the flights themselves: for each day, the sum over its flights of
    x_tilde(cell) * (arrival delay - fitted(cell)). Exact for the flight level regression, because the
    regressors and every fixed effect are constant within a cell."""
    k = x_tilde.shape[1]
    frame = cells.select(list(CELL_KEYS)).with_columns(
        pl.Series("fitted", fitted), *[pl.Series(f"x{j}", x_tilde[:, j]) for j in range(k)]
    )
    con.register("_cell_fit", frame.to_arrow())
    sums = ", ".join(f"sum(c.x{j} * (f.arr_delay - c.fitted)) as s{j}" for j in range(k))
    scores = con.execute(
        f"""
        with f as (
            select flight_date, carrier, route, {period} as period, dep_hour,
                   coalesce(type_code, 'unknown') as type_code, arr_delay
            from {source}
            where not cancelled and not diverted and arr_delay is not null and ({where})
        )
        select f.flight_date, {sums}
        from f join _cell_fit c using (carrier, route, period, dep_hour, type_code)
        group by f.flight_date order by f.flight_date
        """
    ).fetchnumpy()
    con.unregister("_cell_fit")
    matrix = np.column_stack([np.asarray(scores[f"s{j}"], dtype=np.float64) for j in range(k)])
    return vcov_from_scores(bread_inverse, matrix), int(matrix.shape[0])


def spearman(a: list[str], b: list[str]) -> float:
    """Rank correlation of two orderings of the same carriers."""
    if sorted(a) != sorted(b):
        raise ValueError("the two rankings list different carriers")
    pos_a = {c: i for i, c in enumerate(a)}
    pos_b = {c: i for i, c in enumerate(b)}
    ra = np.array([pos_a[c] for c in sorted(a)], dtype=np.float64)
    rb = np.array([pos_b[c] for c in sorted(a)], dtype=np.float64)
    return float(np.corrcoef(ra, rb)[0, 1])
