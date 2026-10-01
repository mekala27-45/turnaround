"""The eight analysis plans, as registered. Each claim is phrased so that the data could refute it."""

from __future__ import annotations

from turnaround_core.config import POLICY, TURN_BINS

from turnaround_chapters.plan import Plan

SPLIT = "choose on 2015 to 2022, report on 2023 to the latest month"


def definition() -> Plan:
    return Plan(
        chapter=1,
        slug="definition",
        title="On time is a decision",
        claim=(
            "The on time rate moved over the window by a different amount than the time flights actually "
            "spend gate to gate on the same routes, so the metric and the flying can tell different stories."
        ),
        estimator=(
            "Per year: the share of flown flights arriving less than fifteen minutes late, and the mean actual "
            "and scheduled gate to gate time on a fixed panel of routes flown in every year of the window."
        ),
        test="The change from the first full year to the latest full year in each series, with day bootstrap intervals.",
        split="Descriptive over every year; nothing is fit, so there is nothing to choose on the fitting years.",
        family="None; two series, one comparison.",
        interval=f"Block bootstrap over days, {POLICY.bootstrap_replicates} replicates, percentile {POLICY.interval_level:.0%}.",
        simulator=(
            "A two year simulated network whose padding steps on known dates while the flying does not change: the "
            "panel's scheduled block change against the true padding change, and whether the actual block change's "
            "interval covers zero, over twenty seeds."
        ),
        policy={"on_time_minutes": POLICY.on_time_minutes},
    )


def padding() -> Plan:
    return Plan(
        chapter=2,
        slug="padding",
        title="The schedule absorbed the delay",
        claim=(
            "Scheduled block time grew faster than unimpeded flying time on the same routes, hours and seasons, "
            "and the growth arrived in steps on dates that can be named for each carrier."
        ),
        estimator=(
            "Unimpeded block time is the 10th percentile of actual gate to gate time by route, three hour departure "
            "block and season over the fitting years; padding is scheduled block minus unimpeded; each carrier's "
            "monthly series is adjusted for route mix; PELT with a BIC penalty of two parameters finds the steps, "
            "and steps under one minute are not reported."
        ),
        test="Padding change from the first to the latest full year on cells present in both, with intervals.",
        split=SPLIT + "; the unimpeded reference is fixed on the fitting years and applied to every year.",
        family="One changepoint search per carrier; dates are reported, not tested.",
        interval=f"Block bootstrap over days, {POLICY.bootstrap_replicates} replicates.",
        simulator="Padding error and changepoint date error by condition (recovery study).",
        policy={
            "unimpeded_percentile": POLICY.unimpeded_percentile,
            "min_step_minutes": 1.0,
            "min_segment_months": 3,
        },
    )


def line() -> Plan:
    return Plan(
        chapter=3,
        slug="line",
        title="The fifteen minute line",
        claim="Arrival delays bunch just under fifteen minutes for some carriers, more than at placebo thresholds.",
        estimator=(
            "Per carrier, counts by whole minute of arrival delay; a cubic fit to the log counts within twenty five "
            "minutes of the threshold, excluding five minutes either side; excess mass below plus missing mass above."
        ),
        test=(
            "The statistic at fifteen minutes standardized by its distribution at placebo thresholds from ten to "
            "sixty five minutes; one sided normal p value."
        ),
        split=SPLIT
        + "; the threshold, window, span and placebos are fixed here, and the test is reported on 2023 onward.",
        family=f"Every reporting carrier in the test years, Benjamini-Hochberg at q = {POLICY.bh_q}.",
        interval="Not an interval: a p value against placebos, and the excess mass as a share.",
        simulator="False positive rate on clean carriers and power on planted carriers (recovery study).",
        policy={"threshold": 15, "window": 5, "span": 25, "bh_q": POLICY.bh_q},
    )


def inherited() -> Plan:
    return Plan(
        chapter=4,
        slug="inherited",
        title="Most delay is inherited",
        claim=(
            "A large share of arrival delay minutes was inherited from the aircraft's previous leg rather than "
            "born on the leg, larger than the reported late aircraft field says."
        ),
        estimator=(
            "Rotations from tail numbers with the integrity rules; departure delay on the previous arrival's excess "
            "over the scheduled turn less a minimum turn, with carrier by date, origin by date and departure hour "
            "fixed effects; the buffer curve by scheduled turnaround bin."
        ),
        test="The coefficient and the inherited share with intervals; the halving buffer.",
        split=SPLIT + "; the minimum turn is chosen by profile on the fitting years and held fixed.",
        family="None; one coefficient, one share.",
        interval="Cluster robust by tail number and day for the coefficient.",
        simulator="Coefficient bias and coverage, inherited share error (recovery study).",
        policy={"rotation_gap_hours": POLICY.rotation_gap_hours, "turn_bins": list(TURN_BINS)},
    )


def ranking() -> Plan:
    return Plan(
        chapter=5,
        slug="ranking",
        title="The fair ranking",
        claim=(
            "Holding constant the routes, months, departure hours and aircraft types each carrier flies changes the "
            "carrier ranking on arrival delay."
        ),
        estimator=(
            "Arrival delay on carrier with route, month, departure hour and aircraft type fixed effects, weighted "
            "least squares on cells; effects relative to the flight weighted average carrier."
        ),
        test="Rank changes between the raw and the adjusted ranking; effects with intervals.",
        split=SPLIT
        + "; the specification was settled on the fitting years and the ranking is fit on 2023 onward.",
        family="Pairwise rank changes are described, not tested.",
        interval="Cluster robust by day, scores summed over flights.",
        simulator="Rank correlation with the true ranking, adjusted against raw (recovery study).",
        policy={"fixed_effects": ["route", "month", "dep_hour", "type_code"]},
    )


def causes() -> Plan:
    return Plan(
        chapter=6,
        slug="causes",
        title="Causes, reported and estimated",
        claim=(
            "The share of delay minutes that weather explains, estimated from the weather at both ends, differs from "
            "the share the reported weather field assigns."
        ),
        estimator=(
            "Arrival delay on hourly weather at the origin at departure and the destination at arrival (precipitation, "
            "snowfall, gusts over 40 km/h, low cloud, thunder, fog, freezing precipitation), with origin by hour, "
            "destination by hour and month fixed effects and the inbound aircraft's carried minutes as a control, on "
            "flights between two Core 30 airports; the attributable share is the fitted delay above calm weather."
        ),
        test="Estimated weather share against the reported weather field's share on the same flights, with an interval.",
        split=SPLIT + "; the specification is fixed here and the shares are reported on 2023 onward.",
        family="Airports compared on their national airspace system share are described, not tested.",
        interval="Cluster robust by day on the weather coefficients, carried to the share.",
        simulator=(
            "Weather share error and interval coverage against planted storms whose minutes the reported field "
            "under records by design (recovery study)."
        ),
        policy={"airports": "FAA Core 30", "calm_gust_kmh": 40.0},
    )


def meltdowns() -> Plan:
    return Plan(
        chapter=7,
        slug="meltdowns",
        title="A meltdown is a recovery",
        claim="Carrier meltdowns are visible as anomalies days before they end, and recovery speed differs by carrier.",
        estimator=(
            "Daily cancellation rate and mean arrival delay per carrier and at the thirty busiest airports against the "
            "unit's previous 28 days (median and median absolute deviation, with floors); an alert episode opens above "
            "the threshold and stays open while the score stays above half of it; the threshold is chosen by cost over "
            "a grid; event studies of the two carrier meltdowns against other carriers at the same airports."
        ),
        test=(
            "Recall on the known events of the reporting years and the first alert day against onset; false alarms per "
            "thousand unit days; whether carriers differ in alert episode length (Kruskal-Wallis H, permutation p)."
        ),
        split=SPLIT + "; the alert threshold is chosen on the fitting years and graded on 2023 onward.",
        family="One permutation test across carriers with at least five episodes; events are graded one by one.",
        interval="Recovery time is a count of days; the excess is a sum, reported without a model interval.",
        simulator="Detector precision and recall on the planted meltdown (recovery study).",
        policy={
            "window_days": 28,
            "cost_false_alarm": 1.0,
            "cost_miss": 50.0,
            "grid": "3 to 30 in steps of 1",
            "airports": 30,
            "permutations": 2000,
        },
    )


def decision() -> Plan:
    return Plan(
        chapter=8,
        slug="decision",
        title="The reader's decision",
        claim=(
            "The first departure of the aircraft's day is the most punctual, and the connection buffer needed to keep "
            "the misconnect probability under the stated line differs across the largest hubs."
        ),
        estimator=(
            "On time rate and mean delay by scheduled hour, day of week and month; misconnect probability by buffer "
            "from the joint same day distribution of inbound arrival and outbound departure delays at each hub."
        ),
        test=f"The buffer at which the probability crosses {POLICY.misconnect_line:.0%}, with the interior test.",
        split=SPLIT + "; the curves are computed on 2023 onward.",
        family="Hubs are described, not tested.",
        interval=f"Block bootstrap over days, {POLICY.bootstrap_replicates} replicates.",
        simulator=(
            "The day by day curve equals a brute force count of every same day pair of flights at a simulated hub "
            "(test); the calculator's estimates are scored later against the outcome month."
        ),
        policy={
            "misconnect_line": POLICY.misconnect_line,
            "min_connection_minutes": POLICY.min_connection_minutes,
        },
    )


ALL = (definition, padding, line, inherited, ranking, causes, meltdowns, decision)


def all_plans() -> list[Plan]:
    return [make() for make in ALL]
