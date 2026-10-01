"""Write the three notebooks from source cells, so they are reviewable as code, and execute them
against the committed results. Each keeps a dead end: the alternative that was tried, run again
here, and the reason it was not used. nbmake runs them again in CI.

    uv run python scripts/build_notebooks.py            # write and execute
    uv run python scripts/build_notebooks.py --no-execute
    uv run pytest --nbmake notebooks
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks"

PRELUDE = """import json
import os
from pathlib import Path

import duckdb
import numpy as np
import polars as pl

pl.Config.set_tbl_rows(30)
pl.Config.set_tbl_hide_dataframe_shape(True)
pl.Config.set_fmt_str_lengths(90)
pl.Config.set_tbl_width_chars(160)
pl.Config.set_float_precision(3)
ROOT = Path(os.environ.get("TURNAROUND_NOTEBOOK_ROOT") or (Path.cwd() if (Path.cwd() / "results").exists() else Path.cwd().parent))
manifest = json.loads((ROOT / "results" / "manifest.json").read_text(encoding="utf-8"))
values, tables = manifest["values"], manifest["tables"]


def v(key):
    return values[key]["value"]


def t(key):
    # A manifest value formatted the way the documents print it.
    from turnaround_core.formats import format_value

    return format_value(values[key]["value"], values[key]["fmt"])


def table(key):
    entry = tables[key]
    return pl.DataFrame(entry["rows"], schema=entry["columns"], orient="row")


MARTS = ROOT / "results" / "marts"
print("manifest as of", manifest["as_of"], "with", len(values), "values;", "window", v("data.first_month"), "to", v("data.last_month"))"""


def nb1() -> list[tuple[str, str]]:
    return [
        (
            "markdown",
            """# 01. Padding and the fifteen minute line

Two questions from the first half of the story. How much of a flight's scheduled time is there to
absorb delay, and has that grown? And do carriers' arrivals pile up just under the fifteen minute
line that decides what counts as on time?

The dead end is kept in the middle: a padding reference recomputed every year. It looks more
careful and it hides the very growth the chapter measures. The simulator shows why, with the truth
known; then the real flights, read from the committed marts and the manifest.""",
        ),
        ("code", PRELUDE),
        (
            "markdown",
            """## The reference that drifted with congestion: a dead end, kept

Padding is scheduled block time minus unimpeded block time, the gate to gate time beaten by only a
tenth of flights on the same route, in the same three hour block and season. The question is which
years the tenth percentile is taken over.

Taking it over each year's own flights is the obvious choice and the wrong one. When congestion
slows every flight, the tenth percentile rises with it, and padding measured against a floor that
rises with the delay cannot show the schedule growing to cover that delay. Below, two simulated
years with known padding; in the second year every flight takes six minutes longer and every
schedule grows by the same six minutes, the way a carrier rebuilds its timetable. The truth is that
the schedule grew by six minutes plus whatever padding the carriers added.""",
        ),
        (
            "code",
            """from turnaround_chapters import padding
from turnaround_sim.network import SimSpec, simulate

CONGESTION = 6.0
sim = simulate(SimSpec(seed=11, days=730, start="2022-01-01", meltdown_day=600))
slower = pl.when(pl.col("year") == 2023).then(CONGESTION).otherwise(0.0)
flights = sim.flights.with_columns(
    (pl.col("actual_elapsed").cast(pl.Float64) + slower).alias("actual_elapsed"),
    (pl.col("crs_elapsed").cast(pl.Float64) + slower).alias("crs_elapsed"),
)
con = duckdb.connect()
con.register("flights", flights.to_arrow())
true_padding = dict(con.execute("select year, avg(true_padding) from flights where not cancelled group by 1").fetchall())
truth = CONGESTION + true_padding[2023] - true_padding[2022]

padding.build_unimpeded(con, "flights", where_fit="year = 2022", percentile=0.10, min_flights=30, target="fixed")
fixed = dict(con.execute(f"select year, avg(padding) from ({padding.padded_flights_sql('flights', 'fixed')}) group by 1").fetchall())
yearly = {}
for year in (2022, 2023):
    padding.build_unimpeded(con, "flights", where_fit=f"year = {year}", percentile=0.10, min_flights=30, target=f"ref_{year}")
    yearly[year] = con.execute(
        f"select avg(padding) from ({padding.padded_flights_sql('flights', f'ref_{year}')}) where year = {year}"
    ).fetchone()[0]
pl.DataFrame(
    {
        "": ["the truth: schedule growth over the first year's unimpeded time", "reference fixed on the first year", "reference recomputed every year"],
        "change in padding, minutes": [truth, fixed[2023] - fixed[2022], yearly[2023] - yearly[2022]],
    }
)""",
        ),
        (
            "markdown",
            """The fixed reference recovers the schedule's growth; the yearly one reports only the padding the
carriers added on top and loses the six minutes the schedule grew to absorb the congestion. That is
the growth chapter 2 is about, so the reference is fixed on the fitting years, 2015 to 2022, and
held there (`packages/chapters/src/turnaround_chapters/padding.py`). The cost is stated in the
chapter's pushback: a fixed reference treats a route that genuinely got slower to fly, a new
approach procedure or a longer taxi, as if the airline had padded it.""",
        ),
        ("markdown", "## Padding on the real flights"),
        (
            "code",
            """route_month = pl.read_parquet(MARTS / "mart_route_month.parquet")
by_year = (
    route_month.group_by("year")
    .agg(
        pl.col("padding_flights").sum().alias("flights with a reference"),
        (pl.col("padding_sum").sum() / pl.col("padding_flights").sum()).alias("mean padding, min"),
        (pl.col("crs_elapsed_sum").sum() / pl.col("flown").sum()).alias("mean scheduled block, min"),
        (pl.col("actual_elapsed_sum").sum() / pl.col("flown").sum()).alias("mean actual block, min"),
    )
    .sort("year")
)
print("padding change on matched cells:", t("ch2.padding.change"), "from", v("ch2.first_year"), "to", v("ch2.last_year"))
by_year""",
        ),
        (
            "code",
            """import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(7, 3.2))
ax.plot(by_year["year"], by_year["mean padding, min"], color="#C8552B", marker="o")
ax.set_ylabel("Mean padding, minutes")
ax.set_title("Scheduled block time over the unimpeded reference, all flights", loc="left", fontsize=10)
ax.spines[["top", "right"]].set_visible(False)
plt.show()""",
        ),
        (
            "markdown",
            """The yearly means above mix routes; the chapter's own estimate holds the route, hour and month
fixed (matched cells), which is the number printed above the table and in the story.

## The fifteen minute line

Every flight under fifteen minutes late counts as on time. If schedules or gate procedures aim at
the line, arrivals pile up just under it and thin out just over it. The density test compares the
bunching at fifteen with the same statistic at placebo thresholds where nothing is at stake.""",
        ),
        (
            "code",
            """from turnaround_stats.density import density_test

histogram = pl.read_parquet(MARTS / "mart_delay_histogram.parquet")
first_test_year = int(v("policy.test_first_year"))
pooled = (
    histogram.filter(pl.col("year") >= first_test_year)
    .group_by("minute").agg(pl.col("flights").sum()).sort("minute")
)
test = density_test(pooled["minute"].to_numpy().astype(np.int64), pooled["flights"].to_numpy().astype(np.float64))
print(f"pooled over carriers, {first_test_year} onward: statistic {test.statistic:.4f}, z against {test.placebos_evaluated} placebos {test.z:.2f}, rank p {test.rank_p_value:.3f}")
pooled.filter(pl.col("minute").is_between(8, 22))""",
        ),
        (
            "markdown",
            """The chapter runs the same test per carrier with Benjamini-Hochberg across carriers; its verdict,
either way, is in the story and in `results/manifest.json` under `ch3`.""",
        ),
        ("code", """table("ch3.by_carrier")"""),
    ]


def nb2() -> list[tuple[str, str]]:
    return [
        (
            "markdown",
            """# 02. Rotations and inherited delay

How much of a flight's delay arrived with the aircraft? The answer needs the aircraft's day rebuilt
from tail numbers, and the propagation coefficient: the minutes of departure delay passed on per
minute the inbound flight was late beyond its scheduled turn less a minimum turn.

The dead end is kept here: keying rotations on the tail number and the date, the way the monthly
files are laid out. It splits every overnight.""",
        ),
        ("code", PRELUDE),
        (
            "markdown",
            """## On the simulator, where the coefficient is known

Two simulated years: the minimum turn is chosen on the first, the coefficient and the inherited
share are reported on the second, and the truth is the simulator's own inherited minutes, capped
at each leg's departure delay as the estimator caps them.""",
        ),
        (
            "code",
            """from turnaround_chapters import ch04_inherited, padding
from turnaround_core.config import POLICY, TURN_BINS
from turnaround_rotations import reconstruct
from turnaround_sim.network import SimSpec, simulate

sim = simulate(SimSpec(seed=11, days=730, start="2022-01-01", meltdown_day=600))
con = duckdb.connect()
con.register("sim", sim.flights.to_arrow())
con.execute("create table raw as select * from sim")
padding.build_unimpeded(con, "raw", where_fit="year = 2022", percentile=0.10, min_flights=20)
con.execute(f"create table fct_flights as {padding.padded_flights_sql('raw')}")
con.execute(f"create table int_legs as {reconstruct.full_sql('fct_flights', POLICY.rotation_gap_hours)}")
counts = reconstruct.counts(con, "int_legs")
r = ch04_inherited.estimate(con, legs="int_legs", flights="fct_flights", fit_year=2022, test_first=2023, test_last=2023, bins=TURN_BINS)
truth_share = con.execute(
    "select sum(least(true_inherited, greatest(dep_delay, 0))) / sum(greatest(arr_delay, 0)) "
    "from fct_flights where year = 2023 and not cancelled and not diverted"
).fetchone()[0]
print(counts)
print(f"rho {r.estimate.rho:.3f} (truth {sim.truth.propagation}), minimum turn {r.estimate.min_turn} (truth {sim.truth.min_turn})")
print(f"inherited share {r.share:.3f} (interval {r.share_low:.3f} to {r.share_high:.3f}); truth {truth_share:.3f}")""",
        ),
        (
            "markdown",
            """## Keying rotations on the date: a dead end, kept

The files give each flight a date, the local date of its scheduled departure, and grouping an
aircraft's legs by tail number and date is the first thing anyone writes. It cuts every chain at
midnight: the red eye that lands at dawn and turns forty minutes later, the island night that is
shorter than a long sit at a hub. Those links are exactly where a late arrival is passed to the
morning. The reconstruction instead orders each tail's legs in UTC and starts a new rotation only
after a sit longer than the stated gap.

Below, the same simulated legs with every link that crosses a local date cut, and what that
changes.""",
        ),
        (
            "code",
            """con.execute(
    "create table legs_by_date as "
    "select l.* replace (case when l.link_status = 'linked' and p.flight_date <> l.flight_date then 'gap' else l.link_status end as link_status) "
    "from int_legs l left join int_legs p on p.flight_id = l.prev_flight_id"
)
by_date = ch04_inherited.estimate(con, legs="legs_by_date", flights="fct_flights", fit_year=2022, test_first=2023, test_last=2023, bins=TURN_BINS)
cut, carried = ch04_inherited.across_dates(con, legs="int_legs", legs_where="year(flight_date) = 2023", rho=r.estimate.rho, min_turn=r.estimate.min_turn)
pl.DataFrame(
    [
        {"rule": "UTC order, new rotation after a long sit", "links in the reporting year": r.test_links,
         "links cut at midnight": 0, "inherited minutes lost": 0.0, "inherited share": r.share},
        {"rule": "tail number and local date", "links in the reporting year": by_date.test_links,
         "links cut at midnight": cut, "inherited minutes lost": carried, "inherited share": by_date.share},
    ]
)""",
        ),
        (
            "markdown",
            """The simulator's nights are long: its last arrivals land late in the evening and its first
departures leave hours later, so the links the date rule cuts carry almost nothing and the share
barely moves. That is the simulator's limit, not a defence of the rule. The real network flies red
eyes into the morning banks and short nights in Hawaii, and the cell below reads what the date rule
would have cut there, counted by the chapters stage on the reporting years.""",
        ),
        (
            "code",
            """print("linked legs whose previous leg is on another local date:", v("ch4.across_dates"))
print("their share of all inherited minutes:", t("ch4.across_dates_share"))
print("rotations", v("ch4.rotations"), "from", v("ch4.legs"), "legs on", v("ch4.tails"), "tails;",
      "broken chains", v("ch4.broken_chain"), "impossible sequences", v("ch4.impossible"))
table("ch4.buffer_curve")""",
        ),
        (
            "markdown",
            """## The first flight of the aircraft's day

The traveler's version of the same mechanism: a first departure has no inbound flight to inherit
from. The leg position mart counts on time arrivals by the leg's place in the aircraft's local day.""",
        ),
        (
            "code",
            """legs = pl.read_parquet(MARTS / "mart_leg_position.parquet")
(
    legs.filter(pl.col("year") >= int(v("policy.test_first_year")))
    .group_by("leg_position")
    .agg(pl.col("flown").sum(), (pl.col("on_time").sum() / pl.col("flown").sum()).alias("on time rate"))
    .sort("leg_position")
    .head(8)
)""",
        ),
    ]


def nb3() -> list[tuple[str, str]]:
    return [
        (
            "markdown",
            """# 03. The fair ranking

A carrier's average delay mixes how well it runs with where and when it flies. The fair ranking
regresses arrival delay on carrier with fixed effects for route, month, scheduled hour and aircraft
type, fit on weighted cells. The simulator plants carrier effects on routes of known difficulty
and makes the hardest routes belong to some carriers more than others, so the raw ranking is
confounded by design and the true ranking is known.

The dead end is kept: a model with fixed effects for the origin airport instead of the route. It
puts each carrier's hub in a fixed effect that the carrier owns, and the hub soaks up the carrier.""",
        ),
        ("code", PRELUDE),
        (
            "code",
            """from turnaround_chapters.ranking import estimate, spearman
from turnaround_sim.network import SimSpec, simulate
from turnaround_stats.fe import contrasts_to_mean, dummies, fit


def ranked(con, keys):
    \"\"\"Carriers ordered by their effect under the fixed effects named in keys.\"\"\"
    cells = con.execute(
        f"select carrier, {', '.join(keys)}, count(*) as flights, avg(arr_delay) as arr_delay from f "
        "where not cancelled and not diverted and arr_delay is not null group by all order by all"
    ).pl()
    carriers = sorted(cells["carrier"].unique().to_list())
    index = {c: i for i, c in enumerate(carriers)}
    idx = np.array([index[c] for c in cells["carrier"].to_list()])
    w = cells["flights"].to_numpy().astype(float)
    result = fit(cells["arr_delay"].to_numpy().astype(float), dummies(idx, len(carriers)), w, [cells[k].to_numpy() for k in keys], carriers[1:])
    effects, _ = contrasts_to_mean(result.coef, None, np.bincount(idx, weights=w))
    return [c for _, c in sorted(zip(effects, carriers))]


rows = []
for seed in (1, 2, 3):
    sim = simulate(SimSpec(seed=seed, days=365, start="2022-01-01", confounding=0.9))
    con = duckdb.connect()
    con.register("sim", sim.flights.to_arrow())
    con.execute("create view f as select *, year * 100 + month as period from sim")
    truth = sim.truth.carrier_effect_ranking
    final = estimate(con, "f")
    rows.append(
        {
            "seed": seed,
            "raw": spearman(final.order("raw"), truth),
            "origin airport fixed effect (dead end)": spearman(ranked(con, ["origin", "period", "dep_hour"]), truth),
            "both airports": spearman(ranked(con, ["origin", "dest", "period", "dep_hour"]), truth),
            "route, month, hour, type (shipped)": spearman(final.order("adjusted"), truth),
        }
    )
print("rank correlation with the true ranking, strong confounding")
pl.DataFrame(rows)""",
        ),
        (
            "markdown",
            """The origin airport model is barely better than the raw ranking. Every carrier in the simulator
has a hub, and nearly every departure from that hub is the carrier's own, so the hub's fixed
effect and the carrier's effect are the same variable on half the carrier's flights: the model
credits the hub with the carrier's punctuality and the carrier with whatever is left. Holding both
ends fixed recovers most of the ranking; the route, which holds the pair and its difficulty,
recovers it best and is what ships. The recovery study runs this across every condition; its
summary is in the manifest.""",
        ),
        (
            "code",
            """print("rank correlation, adjusted against raw, over the recovery study:",
      "strong confounding", t("recovery.rank_adjusted.strong"), "against", t("recovery.rank_raw.strong"), ";",
      "no confounding", t("recovery.rank_adjusted.none"), "against", t("recovery.rank_raw.none"))""",
        ),
        (
            "markdown",
            """## The ranking on the real flights

Raw beside adjusted, with day clustered intervals, from the committed manifest. A carrier that moves
down once adjusted was flying easier routes and hours than its raw rank credited.""",
        ),
        ("code", """table("ch5.ranking")"""),
    ]


NOTEBOOKS = {
    "01_padding_and_the_line.ipynb": nb1,
    "02_rotations_and_inherited_delay.ipynb": nb2,
    "03_the_fair_ranking.ipynb": nb3,
}


def build(name: str, cells: list[tuple[str, str]]) -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata["language_info"] = {"name": "python"}
    nb.cells = [
        nbformat.v4.new_markdown_cell(text) if kind == "markdown" else nbformat.v4.new_code_cell(text)
        for kind, text in cells
    ]
    return nb


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-execute", action="store_true")
    parser.add_argument("--only", default=None, help="one notebook file name")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    for name, cells in NOTEBOOKS.items():
        if args.only and name != args.only:
            continue
        nb = build(name, cells())
        if not args.no_execute:
            from nbclient import NotebookClient

            NotebookClient(
                nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(OUT)}}
            ).execute()
        nbformat.write(nb, OUT / name)
        print(f"wrote notebooks/{name}{'' if args.no_execute else ' (executed)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
