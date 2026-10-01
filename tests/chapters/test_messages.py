"""Each chart's one message is chosen by rule from the result, so it can say the opposite of what was
hoped. These pin the rules on hand built results, one branch at a time."""

from __future__ import annotations

from types import SimpleNamespace as NS

from turnaround_chapters import (
    ch01_definition,
    ch02_padding,
    ch04_inherited,
    ch05_ranking,
    ch07_meltdowns,
    ch08_decision,
)

NAMES = {"WN": "Southwest Airlines", "DL": "Delta Air Lines", "AA": "American Airlines"}


def test_the_meltdown_message_names_the_slower_recovery_and_the_trait_verdict() -> None:
    studies = [NS(carrier="WN", recovery_days=9), NS(carrier="DL", recovery_days=5)]
    text = ch07_meltdowns.message(NS(trait_p_value=0.01, studies=studies), NAMES)  # type: ignore[arg-type]
    assert text.startswith("Southwest Airlines took 9 days to get back to its peers and Delta Air Lines 5")
    assert text.endswith("how fast a carrier recovers is a trait of the carrier")
    null = ch07_meltdowns.message(NS(trait_p_value=0.4, studies=studies), NAMES)  # type: ignore[arg-type]
    assert null.endswith("recovery speed does not separate the carriers")


def test_the_meltdown_message_never_claims_a_detection_or_a_trait_it_did_not_measure() -> None:
    untested = ch07_meltdowns.message(NS(trait_p_value=float("nan"), studies=[]))  # type: ignore[arg-type]
    assert "too few carriers" in untested and "first day" not in untested
    stuck = [NS(carrier="WN", recovery_days=None), NS(carrier="DL", recovery_days=5)]
    text = ch07_meltdowns.message(NS(trait_p_value=float("nan"), studies=stuck), NAMES)  # type: ignore[arg-type]
    assert text.startswith("Southwest Airlines was not back to its peers within the study window")


def test_the_inherited_message_follows_the_share_and_names_the_halving_turn() -> None:
    def result(share: float, halving: float) -> NS:
        return NS(share=share, halving_buffer=halving, estimate=NS(min_turn=35))

    assert ch04_inherited.message(result(0.55, 20)).startswith("Most arrival delay")  # type: ignore[arg-type]
    assert ch04_inherited.message(result(0.45, 20)).startswith("Close to half")  # type: ignore[arg-type]
    assert ch04_inherited.message(result(0.25, 20)).startswith("About a quarter")  # type: ignore[arg-type]
    assert ch04_inherited.message(result(0.25, 20)).endswith(
        "a scheduled turn of 55 minutes halves what is passed on"
    )  # type: ignore[arg-type]
    assert (
        ch04_inherited.message(result(0.1, 0))
        == "A small share of arrival delay was inherited from the aircraft's previous flight"
    )  # type: ignore[arg-type]


def test_the_ranking_message_names_the_biggest_movers_or_says_nothing_moved() -> None:
    rows = [
        NS(carrier="WN", change=2),
        NS(carrier="DL", change=0),
        NS(carrier="AA", change=-2),
    ]
    text = ch05_ranking.message(NS(rows=rows), NAMES)  # type: ignore[arg-type]
    assert text.endswith("Southwest Airlines rises 2 places and American Airlines falls 2")
    still = ch05_ranking.message(NS(rows=[NS(carrier="WN", change=0)]))  # type: ignore[arg-type]
    assert still == "Holding constant what each carrier flies leaves the ranking unchanged"


def test_the_decision_message_gives_the_buffer_and_only_backs_the_first_flight_when_it_is_safer() -> None:
    hub = NS(hub="ATL", crossing=45)
    safer = ch08_decision.message(NS(hubs=[hub], first_advantage=NS(low=0.02)))  # type: ignore[arg-type]
    assert safer == "Book the first flight of the aircraft's day, and leave 45 minutes to connect at ATL"
    unsure = ch08_decision.message(NS(hubs=[hub], first_advantage=NS(low=-0.01)))  # type: ignore[arg-type]
    assert unsure.startswith("Leave 45 minutes to connect at ATL; the first flight")
    never = ch08_decision.message(NS(hubs=[NS(hub="ATL", crossing=None)], first_advantage=NS(low=0.02)))  # type: ignore[arg-type]
    assert never.startswith("No buffer on the grid")


def _iv(estimate: float, low: float, high: float) -> NS:
    return NS(estimate=estimate, low=low, high=high)


def test_the_definition_message_compares_the_schedule_and_the_flying_on_their_difference() -> None:
    def r(
        rate: tuple[float, float, float],
        sched: tuple[float, float, float],
        actual: tuple[float, float, float],
        gap: tuple[float, float, float],
    ) -> NS:
        return NS(
            on_time_change=_iv(*rate),
            sched_block_change=_iv(*sched),
            actual_block_change=_iv(*actual),
            gap_change=_iv(*gap),
        )

    fell = (-0.037, -0.049, -0.026)
    up = (4.6, 4.3, 5.0)
    # Two changes whose intervals overlap and whose difference's interval holds zero grew as much.
    assert ch01_definition.message(r(fell, up, (4.4, 4.0, 4.8), (0.2, -0.1, 0.5))) == (
        "The on time rate fell, and flights took longer gate to gate and the schedule grew as much"
    )
    assert "grew faster still" in ch01_definition.message(r(fell, up, (4.4, 4.0, 4.8), (0.2, 0.1, 0.3)))
    assert "than the schedule grew to allow" in ch01_definition.message(
        r(fell, up, (4.9, 4.5, 5.3), (-0.3, -0.5, -0.1))
    )
    assert ch01_definition.message(
        r((0.004, -0.01, 0.02), (0.1, -0.2, 0.4), (0.1, -0.3, 0.5), (0.0, -0.2, 0.2))
    ) == (
        "The on time rate did not move beyond its interval, and neither the schedule nor the flying moved beyond its interval"
    )
    assert ch01_definition.message(r((0.02, 0.01, 0.03), up, (0.1, -0.3, 0.5), (4.5, 4.1, 4.9))).startswith(
        "The on time rate rose, and the schedule grew while the flying did not"
    )


def test_the_padding_message_never_says_padding_stood_still_when_its_interval_excludes_zero() -> None:
    def r(pad: tuple[float, float, float], gap: tuple[float, float, float]) -> NS:
        return NS(padding_change=_iv(*pad), gap_change=_iv(*gap))

    grew = (3.98, 3.84, 4.13)
    assert ch02_padding.message(r(grew, (-0.18, -0.5, 0.2))) == (
        "The schedule grew as fast as the flying slowed, so it absorbed the delay"
    )
    assert ch02_padding.message(r(grew, (1.0, 0.6, 1.4))).endswith("absorbed the delay and more")
    assert (
        ch02_padding.message(r(grew, (-1.0, -1.4, -0.6)))
        == "The schedule grew, but more slowly than the flying slowed"
    )
    assert ch02_padding.message(r((-2.0, -2.5, -1.5), (0.0, -0.3, 0.3))).startswith("Schedules lost padding")
    assert ch02_padding.message(r((0.1, -0.2, 0.4), (0.0, -0.3, 0.3))).startswith("Padding did not move")
