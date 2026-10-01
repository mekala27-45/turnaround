"use client";

import { scaleLinear } from "d3-scale";
import { useState } from "react";

import { formatValue } from "@/lib/format";

import { hbarPath, wrapLabel } from "./shapes";
import { pointIn, type Tip, Tooltip } from "./Tooltip";
import { fitTicks, useWidth } from "./useWidth";

export interface Bar {
  key: string;
  label: string;
  value: number;
  low?: number | null;
  high?: number | null;
  color: string;
  hatched?: boolean;
}

/** Horizontal bars on one value axis, labelled directly, with an interval whisker where one exists. */
export function Bars({
  bars,
  fmt,
  axisLabel,
  highlight = [],
  testId,
}: {
  bars: Bar[];
  fmt: string;
  axisLabel: string;
  highlight?: string[];
  testId?: string;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [tip, setTip] = useState<Tip | null>(null);
  const labelW = Math.min(200, Math.max(110, width * 0.32));
  const row = 34;
  const height = bars.length * row + 44;
  const hi = Math.max(...bars.map((b) => Math.max(b.value, b.high ?? 0)), 0);
  const x = scaleLinear()
    .domain([0, hi || 1])
    .nice(5)
    .range([0, Math.max(width - labelW - 60, 60)]);
  const ticks = fitTicks(x, x.range()[1] ?? 100, (t) => formatValue(t, fmt), 5);
  const focus = new Set(highlight);
  return (
    <div ref={ref} className="relative w-full" data-testid={testId} onMouseLeave={() => setTip(null)}>
      <svg width={width} height={height} role="img" aria-label={axisLabel}>
        <g transform={`translate(${labelW},8)`}>
          {ticks.map((t) => (
            <g key={t} transform={`translate(${x(t)},0)`}>
              <line y2={bars.length * row} stroke="var(--hairline)" strokeDasharray={t === 0 ? undefined : "2 3"} />
              <text y={bars.length * row + 14} textAnchor="middle" className="fill-[var(--ink2)] text-[11px] num">
                {formatValue(t, fmt)}
              </text>
            </g>
          ))}
          <text x={(x.range()[1] ?? 0) / 2} y={bars.length * row + 30} textAnchor="middle" className="fill-[var(--ink2)] text-[11px]">
            {axisLabel}
          </text>
          {bars.map((b, i) => {
            const dim = focus.size > 0 && !focus.has(b.key);
            const yy = i * row + 6;
            const label = wrapLabel(b.label, Math.floor(labelW / 7));
            return (
              <g
                key={b.key}
                opacity={dim ? 0.35 : 1}
                data-bar={b.key}
                tabIndex={0}
                onMouseMove={(e) => {
                  const at = pointIn(ref.current, e);
                  const range = b.low !== undefined && b.low !== null && b.high !== undefined && b.high !== null ? ` (${formatValue(b.low, fmt)} to ${formatValue(b.high, fmt)})` : "";
                  setTip({ x: at.x, y: at.y, lines: [b.label, `${formatValue(b.value, fmt)}${range}`] });
                }}
                onBlur={() => setTip(null)}
              >
                {label.map((line, j) => (
                  <text key={j} x={-10} y={yy + 10 + (label.length > 1 ? (j - 0.5) * 12 : 0)} dy="0.32em" textAnchor="end" className="text-[11.5px] fill-[var(--ink)]">
                    {line}
                  </text>
                ))}
                <path d={hbarPath(0, x(b.value), yy, 20)} fill={b.color} />
                {b.hatched ? <path d={hbarPath(0, x(b.value), yy, 20)} fill="url(#pat-rule)" /> : null}
                {b.low !== undefined && b.low !== null && b.high !== undefined && b.high !== null ? (
                  <g stroke="var(--ink)" strokeWidth={1.4}>
                    <line x1={x(b.low)} x2={x(b.high)} y1={yy + 10} y2={yy + 10} />
                    <line x1={x(b.low)} x2={x(b.low)} y1={yy + 5} y2={yy + 15} />
                    <line x1={x(b.high)} x2={x(b.high)} y1={yy + 5} y2={yy + 15} />
                  </g>
                ) : null}
                <text x={Math.max(x(b.value), x(b.high ?? 0)) + 6} y={yy + 10} dy="0.32em" className="text-[11.5px] fill-[var(--ink)] num">
                  {formatValue(b.value, fmt)}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
      <Tooltip tip={tip} width={width} />
    </div>
  );
}
