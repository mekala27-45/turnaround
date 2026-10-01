"use client";

import { useMemo, useState } from "react";

import { ChartSkeleton, Figure } from "@/components/charts/Figure";
import { type Leg, Timeline } from "@/components/charts/Timeline";
import { mart } from "@/lib/data";
import { formatValue } from "@/lib/format";
import { useMart } from "@/lib/useMart";

type Day = {
  year: number;
  month: number;
  worst_day: string;
  score: number;
};
type LegRow = {
  flight_date: string;
  tail_number: string;
  carrier: string;
  rotation_id: string;
  leg_index: number;
  origin: string;
  dest: string;
  sched_dep_utc: string;
  sched_arr_utc: string;
  dep_delay: number | null;
  arr_delay: number | null;
  sched_turn: number | null;
  link_status: string;
  prev_arr_delay: number | null;
  rank: number;
};

const toMs = (s: string) => Date.parse(s.includes("T") ? `${s}Z` : `${s.replace(" ", "T")}Z`);

export function RotationsClient({ rho, minTurn }: { rho: number; minTurn: number }) {
  const days = useMart<Day>(`select year, month, worst_day, score from ${mart("rotation_worst_days")} order by score desc, worst_day`);
  const [day, setDay] = useState<string>("");
  const chosenDay = day || days.rows?.[0]?.worst_day || "";
  const sqlLegs = chosenDay
    ? `select * from ${mart("rotation_samples")} where flight_date = '${chosenDay}' order by rank, leg_index`
    : null;
  const legs = useMart<LegRow>(sqlLegs);
  const rotations = useMemo(() => {
    const seen = new Map<string, LegRow>();
    for (const r of legs.rows ?? []) if (!seen.has(r.rotation_id)) seen.set(r.rotation_id, r);
    return [...seen.values()];
  }, [legs.rows]);
  const [rotation, setRotation] = useState<string>("");
  const chosen = rotation && rotations.some((r) => r.rotation_id === rotation) ? rotation : (rotations[0]?.rotation_id ?? "");
  const rows = (legs.rows ?? []).filter((r) => r.rotation_id === chosen);
  const timeline: Leg[] = rows.map((r) => {
    const carried =
      r.link_status === "linked" && r.prev_arr_delay !== null && r.sched_turn !== null ? rho * Math.max(0, r.prev_arr_delay - (r.sched_turn - minTurn)) : 0;
    const inherited = Math.min(carried, Math.max(r.dep_delay ?? 0, 0));
    return {
      key: `${r.rotation_id}-${r.leg_index}`,
      label: `${r.origin} to ${r.dest}`,
      start: toMs(r.sched_dep_utc),
      end: toMs(r.sched_arr_utc),
      delay: r.arr_delay,
      inherited,
      turn: r.link_status === "linked" ? r.sched_turn : null,
    };
  });
  const inheritedTotal = timeline.reduce((a, l) => a + l.inherited, 0);
  const lateTotal = timeline.reduce((a, l) => a + Math.max(l.delay ?? 0, 0), 0);
  const top = [...timeline].sort((a, b) => b.inherited - a.inherited)[0];
  const head = rows[0];
  const message =
    head && lateTotal > 0
      ? `${formatValue(inheritedTotal / lateTotal, "pct0")} of this aircraft's arrival delay minutes on ${chosenDay} were inherited from an earlier leg`
      : "The aircraft's day, leg by leg";
  return (
    <div className="space-y-5">
      <div className="card p-4 flex flex-wrap gap-4 items-end" data-testid="rotation-pickers">
        <label className="flex flex-col text-xs text-ink2 gap-1">
          Worst day of the month
          <select value={chosenDay} onChange={(e) => { setDay(e.target.value); setRotation(""); }} data-testid="pick-day" className="text-sm">
            {(days.rows ?? []).map((d) => (
              <option key={d.worst_day} value={d.worst_day}>
                {d.worst_day}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-xs text-ink2 gap-1">
          Aircraft, most delayed first
          <select value={chosen} onChange={(e) => setRotation(e.target.value)} data-testid="pick-tail" className="text-sm">
            {rotations.map((r) => (
              <option key={r.rotation_id} value={r.rotation_id}>
                {`${r.tail_number} (${r.carrier})`}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Figure
        testId="rotation-timeline"
        message={message}
        subtitle={head ? `Tail ${head.tail_number}, ${head.carrier}: each leg's arrival delay, and the part of its departure delay inherited` : "Pick a day and an aircraft"}
        source="Source: BTS Reporting Carrier On-Time Performance (real); rotations rebuilt from tail numbers in the warehouse's int_legs."
        sql={sqlLegs}
        table={{
          columns: ["Leg", "Route", "Arrival delay", "Inherited", "Scheduled turn"],
          formats: ["int", "text", "min0", "min0", "min0"],
          rows: timeline.map((l, i) => [i + 1, l.label, l.delay, l.inherited, l.turn]),
        }}
        callout={top && top.inherited > 0 ? `The leg ${top.label} inherited ${formatValue(top.inherited, "min0")}, the most of the day.` : undefined}
      >
        {legs.rows ? <Timeline legs={timeline} highlight={top && top.inherited > 0 ? top.key : null} testId="timeline" /> : <ChartSkeleton shape="bars" />}
      </Figure>
    </div>
  );
}
