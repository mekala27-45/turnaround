"""The demonstration network: one seeded year of the simulator with its truth tables, committed under data/sim."""

from __future__ import annotations

import json

import polars as pl
from turnaround_core.manifest import Manifest, Scribe
from turnaround_core.paths import Paths
from turnaround_sim.network import SimSpec, simulate

from turnaround_pipeline.common import DEMONSTRATION_SEED, new_partial, save_partial


def run(p: Paths) -> Manifest:
    spec = SimSpec(seed=DEMONSTRATION_SEED)
    sim = simulate(spec)
    truth = sim.truth
    p.sim.mkdir(parents=True, exist_ok=True)
    sim.flights.write_parquet(p.sim / "flights.parquet", compression="zstd")
    (p.sim / "spec.json").write_text(json.dumps(spec.model_dump(), indent=1, sort_keys=True) + "\n")
    truth_payload = {
        "carrier_effect": {k: round(v, 6) for k, v in sorted(truth.carrier_effect.items())},
        "carrier_effect_ranking": truth.carrier_effect_ranking,
        "padding_change": truth.padding_change,
        "padding_change_date": truth.padding_change_date,
        "propagation": truth.propagation,
        "min_turn": truth.min_turn,
        "inherited_share": round(truth.inherited_share, 6),
        "bunching_carriers": truth.bunching_carriers,
        "meltdown_carrier": truth.meltdown_carrier,
        "meltdown_dates": truth.meltdown_dates,
        "storm_airport_days": truth.storm_days,
    }
    (p.sim / "truth.json").write_text(json.dumps(truth_payload, indent=1, sort_keys=True) + "\n")
    truth.padding_by_carrier_route_month.write_parquet(p.sim / "truth_padding.parquet", compression="zstd")

    manifest = new_partial("simulate")
    s = Scribe(
        manifest,
        source="simulated",
        population="the demonstration network, one simulated year",
        origin="stages/simulate.py",
        seed=spec.seed,
    )
    flights = sim.flights
    s.put("sim.flights", flights.height, "int")
    s.put("sim.carriers", spec.carriers, "int")
    s.put("sim.airports", int(pl.concat([flights["origin"], flights["dest"]]).n_unique()), "int")
    s.put("sim.routes", int(flights["route"].n_unique()), "int")
    s.put("sim.tails", int(flights["tail_number"].n_unique()), "int")
    s.put("sim.days", spec.days, "int")
    s.put("sim.propagation", spec.propagation, "float2")
    s.put("sim.min_turn", spec.min_turn, "min0")
    s.put("sim.inherited_share", truth.inherited_share, "pct1")
    s.put("sim.meltdown_carrier", truth.meltdown_carrier, "text")
    s.put("sim.meltdown_start", truth.meltdown_dates[0], "text")
    s.put("sim.meltdown_days", len(truth.meltdown_dates), "int")
    s.put("sim.bunching_carriers", ", ".join(truth.bunching_carriers), "text")
    s.put("sim.bunching_share", spec.bunching_share, "pct0")
    s.put("sim.storm_airport_days", truth.storm_days, "int")
    s.put("sim.swap_rate", spec.swap_rate, "pct1")
    s.table(
        "sim.truth_carriers",
        ["Carrier", "True effect on arrival delay", "Padding step", "Step date"],
        ["text", "smin2", "smin1", "text"],
        [
            [
                c,
                truth.carrier_effect[c],
                truth.padding_change[c],
                truth.padding_change_date[c] if truth.padding_change[c] else "no step",
            ]
            for c in sorted(truth.carrier_effect)
        ],
    )
    save_partial(p, "simulate", manifest)
    return manifest
