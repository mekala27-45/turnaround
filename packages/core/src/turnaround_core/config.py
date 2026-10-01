"""The analysis policy: every threshold, window and split the chapters share, stated once.

The policy is a frozen model so it can be hashed into each chapter's pre-registered plan;
changing a threshold after registration changes the plan's hash and fails the gate.
"""

from __future__ import annotations

from turnaround_core.model import StrictModel

# The FAA's Core 30: the airports the FAA itself uses for its delay statistics. Weather is
# pulled at these thirty because the free Open-Meteo tier cannot carry every airport for
# eleven years in a day (DECISIONS.md, 2026-09-30).
CORE30: tuple[str, ...] = (
    "ATL", "BOS", "BWI", "CLT", "DCA", "DEN", "DFW", "DTW", "EWR", "FLL",
    "HNL", "IAD", "IAH", "JFK", "LAS", "LAX", "LGA", "MCO", "MDW", "MEM",
    "MIA", "MSP", "ORD", "PHL", "PHX", "SAN", "SEA", "SFO", "SLC", "TPA",
)  # fmt: skip

# The five reported delay cause fields, in the fixed order the charts use.
CAUSES: tuple[str, ...] = ("late_aircraft", "carrier", "nas", "weather", "security")

# Scheduled turnaround bins for the buffer curve, minutes, left closed.
TURN_BINS: tuple[int, ...] = (0, 30, 40, 50, 60, 75, 90, 120, 180, 300)


class Policy(StrictModel):
    window_start: str = "2015-01"
    fit_first_year: int = 2015
    fit_last_year: int = 2022
    test_first_year: int = 2023
    on_time_minutes: int = 15
    late_minutes: int = 15
    unimpeded_percentile: float = 0.10
    padding_min_flights: int = 30
    rotation_gap_hours: float = 6.0
    turn_bins: tuple[int, ...] = TURN_BINS
    elapsed_tolerance_minutes: int = 5
    cause_tolerance_minutes: int = 1
    bootstrap_replicates: int = 400
    bh_q: float = 0.05
    interval_level: float = 0.95
    hub_count: int = 20
    misconnect_line: float = 0.10
    min_connection_minutes: int = 25
    seed: int = 20261001


POLICY = Policy()


def is_fit_year(year: int, policy: Policy = POLICY) -> bool:
    return policy.fit_first_year <= year <= policy.fit_last_year


def is_test_year(year: int, policy: Policy = POLICY) -> bool:
    return year >= policy.test_first_year
