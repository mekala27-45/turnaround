"use client";

import { useState } from "react";

import { pointIn, type Tip, Tooltip } from "./Tooltip";
import { useWidth } from "./useWidth";

export interface SlopeLine {
  key: string;
  label: string;
  left: number;
  right: number;
  color: string;
}

/**
 * A slope chart: rank on the left, rank on the right, a line per carrier, named at both ends. Rank 1
 * is at the top. Lines that do not move are drawn in the control gray; risers in blue, fallers in
 * vermilion, so the direction reads without a legend.
 */
export function Slope({
  lines,
  leftLabel,
  rightLabel,
  highlight = [],
  showRight = true,
  testId,
}: {
  lines: SlopeLine[];
  leftLabel: string;
  rightLabel: string;
  highlight?: string[];
  showRight?: boolean;
  testId?: string;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [tip, setTip] = useState<Tip | null>(null);
  const n = Math.max(...lines.map((l) => Math.max(l.left, l.right)), 1);
  const row = 24;
  const height = n * row + 48;
  const labelW = Math.min(170, Math.max(90, width * 0.28));
  const x0 = labelW + 28;
  const x1 = Math.max(width - labelW - 28, x0 + 60);
  const y = (rank: number) => 30 + (rank - 1) * row;
  const focus = new Set(highlight);
  return (
    <div ref={ref} className="relative w-full" data-testid={testId} onMouseLeave={() => setTip(null)}>
      <svg width={width} height={height} role="img" aria-label={`${leftLabel} against ${rightLabel}`}>
        <text x={x0} y={14} textAnchor="middle" className="fill-[var(--ink2)] text-[11px] font-semibold">
          {leftLabel}
        </text>
        <text x={x1} y={14} textAnchor="middle" className="fill-[var(--ink2)] text-[11px] font-semibold">
          {rightLabel}
        </text>
        {lines.map((l) => {
          const dim = focus.size > 0 && !focus.has(l.key);
          const right = showRight ? l.right : l.left;
          return (
            <g
              key={l.key}
              opacity={dim ? 0.28 : 1}
              data-carrier={l.key}
              tabIndex={0}
              onMouseMove={(e) => {
                const at = pointIn(ref.current, e);
                setTip({ x: at.x, y: at.y, lines: [l.label, `${leftLabel}: ${l.left}`, `${rightLabel}: ${l.right}`] });
              }}
              onFocus={(e) => {
                const at = pointIn(ref.current, e);
                setTip({ x: at.x, y: at.y, lines: [l.label, `${leftLabel}: ${l.left}`, `${rightLabel}: ${l.right}`] });
              }}
              onBlur={() => setTip(null)}
            >
              <line x1={x0} x2={x1} y1={y(l.left)} y2={y(right)} stroke={l.color} strokeWidth={focus.has(l.key) ? 3 : 2} />
              <circle cx={x0} cy={y(l.left)} r={4} fill={l.color} />
              <circle cx={x1} cy={y(right)} r={4} fill={l.color} />
              <text x={x0 - 10} y={y(l.left)} dy="0.32em" textAnchor="end" className="text-[11.5px] fill-[var(--ink)]">
                {`${l.left}. ${l.label}`}
              </text>
              {showRight ? (
                <text x={x1 + 10} y={y(right)} dy="0.32em" className="text-[11.5px] fill-[var(--ink)]">
                  {`${l.right}. ${l.label}`}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>
      <Tooltip tip={tip} width={width} />
    </div>
  );
}
