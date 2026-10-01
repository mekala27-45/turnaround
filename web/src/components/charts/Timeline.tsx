"use client";

import { scaleLinear } from "d3-scale";
import { useState } from "react";

import { formatValue } from "@/lib/format";

import { pointIn, type Tip, Tooltip } from "./Tooltip";
import { useWidth } from "./useWidth";

export interface Leg {
  key: string;
  label: string;
  start: number;
  end: number;
  delay: number | null;
  inherited: number;
  turn: number | null;
}

// The diverging ramp: early is blue, late is vermilion, through the neutral midpoint.
const RAMP = ["var(--div-1)", "var(--div-2)", "var(--div-3)", "var(--div-4)", "var(--div-5)", "var(--div-6)", "var(--div-7)", "var(--div-8)", "var(--div-9)"];

function colorOf(delay: number | null): string {
  if (delay === null) return "var(--control)";
  const steps = [-30, -15, -5, 5, 15, 30, 60, 120];
  let i = 0;
  while (i < steps.length && delay > (steps[i] ?? 0)) i += 1;
  return RAMP[Math.min(i, RAMP.length - 1)] ?? "var(--control)";
}

/** The aircraft's day: one bar per leg from scheduled departure to scheduled arrival, colored by the
 * leg's arrival delay on the diverging ramp, with the minutes it inherited marked on the bar. */
export function Timeline({ legs, highlight, testId }: { legs: Leg[]; highlight: string | null; testId?: string }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [tip, setTip] = useState<Tip | null>(null);
  if (!legs.length) return <p className="text-sm text-ink2">No legs for this aircraft on this day.</p>;
  const lo = Math.min(...legs.map((l) => l.start));
  const hi = Math.max(...legs.map((l) => l.end));
  const margin = { left: 12, right: 12, top: 26, bottom: 30 };
  const innerW = Math.max(width - margin.left - margin.right, 120);
  const x = scaleLinear().domain([lo, hi]).range([0, innerW]);
  const row = 30;
  const height = legs.length * row + margin.top + margin.bottom;
  const hours: number[] = [];
  for (let t = Math.ceil(lo / 3_600_000) * 3_600_000; t <= hi; t += 3 * 3_600_000) hours.push(t);
  return (
    <div ref={ref} className="relative w-full" data-testid={testId} onMouseLeave={() => setTip(null)}>
      <svg width={width} height={height} role="img" aria-label="The aircraft's day, leg by leg">
        <g transform={`translate(${margin.left},${margin.top})`}>
          {hours.map((t) => (
            <g key={t} transform={`translate(${x(t)},0)`}>
              <line y1={-6} y2={legs.length * row} stroke="var(--hairline)" strokeDasharray="2 3" />
              <text y={-10} textAnchor="middle" className="fill-[var(--ink2)] text-[11px] num">
                {new Date(t).toISOString().slice(11, 16)}
              </text>
            </g>
          ))}
          {legs.map((l, i) => {
            const y = i * row;
            const w = Math.max(x(l.end) - x(l.start), 3);
            const lifted = highlight === l.key;
            return (
              <g
                key={l.key}
                tabIndex={0}
                data-leg={l.key}
                data-highlight={lifted ? "true" : "false"}
                onMouseMove={(e) => {
                  const at = pointIn(ref.current, e);
                  setTip({
                    x: at.x,
                    y: at.y,
                    lines: [
                      l.label,
                      `arrival delay ${formatValue(l.delay, "min0")}`,
                      `inherited ${formatValue(l.inherited, "min0")}`,
                      l.turn !== null ? `scheduled turn before it ${formatValue(l.turn, "min0")}` : "first leg of the rotation",
                    ],
                  });
                }}
                onFocus={(e) => {
                  const at = pointIn(ref.current, e);
                  setTip({ x: at.x, y: at.y, lines: [l.label, `arrival delay ${formatValue(l.delay, "min0")}`, `inherited ${formatValue(l.inherited, "min0")}`] });
                }}
                onBlur={() => setTip(null)}
              >
                <rect x={x(l.start)} y={y + 4} width={w} height={20} rx={4} fill={colorOf(l.delay)} stroke={lifted ? "var(--ink)" : "none"} strokeWidth={2} />
                {l.inherited > 0 ? (
                  <rect x={x(l.start)} y={y + 4} width={Math.min(w, (l.inherited / Math.max(l.end - l.start, 1)) * 60_000 * (innerW / Math.max(hi - lo, 1)))} height={20} rx={4} fill="url(#pat-rule)" />
                ) : null}
                <text x={x(l.start) + w + 6 > innerW - 80 ? x(l.start) - 6 : x(l.start) + w + 6} y={y + 14} dy="0.32em" textAnchor={x(l.start) + w + 6 > innerW - 80 ? "end" : "start"} className="text-[11px] fill-[var(--ink)]">
                  {`${l.label}  ${formatValue(l.delay, "smin1")}`}
                </text>
              </g>
            );
          })}
          <text x={innerW / 2} y={legs.length * row + 22} textAnchor="middle" className="fill-[var(--ink2)] text-[11px]">
            Scheduled time, UTC; the hatch is the share of the leg's departure delay inherited from the leg before
          </text>
        </g>
      </svg>
      <Tooltip tip={tip} width={width} />
    </div>
  );
}
