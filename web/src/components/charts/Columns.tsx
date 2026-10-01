"use client";

import { scaleBand, scaleLinear } from "d3-scale";
import { useState } from "react";

import { formatValue } from "@/lib/format";

import { vbarPath } from "./shapes";
import { pointIn, type Tip, Tooltip } from "./Tooltip";
import { fitTicks, textWidth, useWidth } from "./useWidth";

export interface ColumnRule {
  x: number;
  label?: string;
  color?: string;
  faint?: boolean;
}

/**
 * Counts by whole minute as columns: early in blue, late in vermilion, so late and early read without
 * a legend; rules mark a threshold (the fifteen minute line) and faint rules the placebos.
 */
export function Columns({
  points,
  xFmt,
  yFmt,
  xLabel,
  yLabel,
  rules = [],
  height = 300,
  split = 0,
  testId,
}: {
  points: { x: number; y: number }[];
  xFmt: string;
  yFmt: string;
  xLabel: string;
  yLabel: string;
  rules?: ColumnRule[];
  height?: number;
  split?: number;
  testId?: string;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [tip, setTip] = useState<Tip | null>(null);
  const ys = points.map((p) => p.y);
  const y0 = scaleLinear()
    .domain([0, Math.max(...ys, 1)])
    .nice(5);
  const yTicks = y0.ticks(5);
  const left = Math.max(...yTicks.map((t) => textWidth(formatValue(t, yFmt), 11))) + 14;
  const margin = { top: 22, right: 12, bottom: 40, left };
  const innerW = Math.max(width - margin.left - margin.right, 80);
  const innerH = height - margin.top - margin.bottom;
  const y = y0.range([innerH, 0]);
  const xs = points.map((p) => p.x);
  const band = scaleBand<number>().domain(xs).range([0, innerW]).padding(0.12);
  const xAt = (v: number) => {
    const lo = xs[0] ?? 0;
    const hi = xs[xs.length - 1] ?? 1;
    return ((v - lo) / Math.max(hi - lo, 1)) * (innerW - band.bandwidth()) + band.bandwidth() / 2;
  };
  const tickScale = scaleLinear()
    .domain([xs[0] ?? 0, xs[xs.length - 1] ?? 1])
    .range([0, innerW]);
  const xTicks = fitTicks(tickScale, innerW, (t) => formatValue(t, xFmt), 8);
  return (
    <div ref={ref} className="relative w-full" data-testid={testId} onMouseLeave={() => setTip(null)}>
      <p className="text-[11px] text-ink2 mb-1">{yLabel}</p>
      <svg width={width} height={height} role="img" aria-label={`${yLabel} by ${xLabel}`}>
        <g transform={`translate(${margin.left},${margin.top})`}>
          {yTicks.map((t) => (
            <g key={t} transform={`translate(0,${y(t)})`}>
              <line x2={innerW} stroke="var(--hairline)" strokeDasharray={t === 0 ? undefined : "2 3"} />
              <text x={-8} dy="0.32em" textAnchor="end" className="fill-[var(--ink2)] text-[11px] num">
                {formatValue(t, yFmt)}
              </text>
            </g>
          ))}
          {points.map((p) => (
            <path
              key={p.x}
              d={vbarPath(band(p.x) ?? 0, band.bandwidth(), y(0), y(p.y), 2)}
              fill={p.x < split ? "var(--cat-2)" : "var(--cat-1)"}
              opacity={0.88}
              tabIndex={-1}
              onMouseMove={(e) => {
                const at = pointIn(ref.current, e);
                setTip({ x: at.x, y: at.y, lines: [`${xLabel}: ${formatValue(p.x, xFmt)}`, `${yLabel}: ${formatValue(p.y, yFmt)}`] });
              }}
            />
          ))}
          {rules.map((r, i) => (
            <g key={`${r.x}-${i}`} data-rule={r.label ?? (r.faint ? "placebo" : "rule")}>
              <line
                x1={xAt(r.x)}
                x2={xAt(r.x)}
                y1={-6}
                y2={innerH}
                stroke={r.color ?? "var(--control)"}
                strokeWidth={r.faint ? 1 : 2}
                strokeDasharray={r.faint ? "2 3" : undefined}
                opacity={r.faint ? 0.6 : 1}
              />
              {r.label ? (
                <text x={xAt(r.x) + 5} y={-8} className="fill-[var(--ink)] text-[11px] font-semibold">
                  {r.label}
                </text>
              ) : null}
            </g>
          ))}
          {xTicks.map((t) => (
            <text key={t} x={xAt(t)} y={innerH + 17} textAnchor="middle" className="fill-[var(--ink2)] text-[11px] num">
              {formatValue(t, xFmt)}
            </text>
          ))}
          <text x={innerW / 2} y={innerH + 34} textAnchor="middle" className="fill-[var(--ink2)] text-[11px]">
            {xLabel}
          </text>
        </g>
      </svg>
      <Tooltip tip={tip} width={width} />
    </div>
  );
}
