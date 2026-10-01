"""Each chart's one message is chosen by rule from the result, so it can say the opposite of what was
hoped. These pin the rules on hand built results, one branch at a time."""

from __future__ import annotations

from types import SimpleNamespace as NS

from turnaround_chapters import ch04_inherited, ch05_ranking, ch07_meltdowns, ch08_decision

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
