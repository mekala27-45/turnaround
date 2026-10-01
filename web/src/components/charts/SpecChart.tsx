"use client";

import type { ChartSpec, SpecPanel, SpecRule, SpecState } from "@/lib/charts";
import { roleColor, xNumber } from "@/lib/charts";
import { formatValue } from "@/lib/format";

import { Bars } from "./Bars";
import { Columns } from "./Columns";
import { type HRule, LineChart, type LineSeries, type PointMark, type Shade, type VRule } from "./LineChart";
import { Slope } from "./Slope";
import { DASHES } from "./useWidth";

/** Which annotation and rule groups a state shows, and which series it lifts. No state shows all. */
function visibility(spec: ChartSpec, stateId: string | null): { show: (group: string | null | undefined) => boolean; highlight: string[] } {
  if (!stateId) return { show: () => true, highlight: [] };
  const index = spec.states.findIndex((s) => s.id === stateId);
  const state: SpecState | undefined = spec.states[index];
  if (!state) return { show: () => true, highlight: [] };
  // A group is shown once its state has been reached: states build on each other as the reader scrolls.
  const reached = new Set(spec.states.slice(0, index + 1).flatMap((s) => s.show));
  return { show: (group) => !group || reached.has(group), highlight: state.highlight };
}

function lineSeries(panel: SpecPanel, highlight: string[]): LineSeries[] {
  return panel.series.map((s, i) => {
    const lifted = highlight.length === 0 || highlight.includes(s.name);
    const points = s.points.map(([x, y]) => ({ x: xNumber(x), y }));
    const band =
      s.low && s.high
        ? s.points.map(([x], j) => ({ x: xNumber(x), low: s.low?.[j] ?? null, high: s.high?.[j] ?? null }))
        : undefined;
    return {
      key: `${s.name}-${i}`,
      name: s.label ?? s.name,
      points,
      color: roleColor(s.role),
      dash: s.dashed ? DASHES[1] : DASHES[i % DASHES.length],
      width: lifted && highlight.length > 0 ? 3 : 2,
      opacity: lifted ? 1 : 0.28,
      band,
    };
  });
}

function rulesOf(rules: SpecRule[], show: (g: string | null | undefined) => boolean): { v: VRule[]; h: HRule[] } {
  const v: VRule[] = [];
  const h: HRule[] = [];
  for (const r of rules) {
    if (!show(r.state)) continue;
    const color = r.role ? roleColor(r.role) : "var(--control)";
    if (r.x !== undefined) v.push({ x: r.x, label: r.label ?? "", color, dash: r.faint ? "2 3" : undefined });
    if (r.y !== undefined) h.push({ y: r.y, label: r.label ?? "", color, dash: "5 3" });
  }
  return { v, h };
}

export function SpecChart({ spec, state = null, height }: { spec: ChartSpec; state?: string | null; height?: number }) {
  const { show, highlight } = visibility(spec, state);
  if (spec.kind === "histogram") {
    const panel = spec.panels[0];
    if (!panel) return null;
    const series = panel.series[0];
    const points = (series?.points ?? []).map(([x, y]) => ({ x: xNumber(x), y: y ?? 0 }));
    const rules = panel.rules
      .filter((r) => r.x !== undefined && show(r.state))
      .map((r) => ({ x: r.x ?? 0, label: r.faint ? undefined : r.label, color: r.role ? roleColor(r.role) : undefined, faint: r.faint }));
    return (
      <Columns
        points={points}
        xFmt={spec.x_format}
        yFmt={spec.y_format}
        xLabel={spec.x_label}
        yLabel={spec.y_label}
        rules={rules}
        split={0}
        height={height ?? 320}
        testId={`chart-${spec.id}`}
      />
    );
  }
  if (spec.kind === "slope") {
    const panel = spec.panels[0];
    if (!panel) return null;
    const lines = panel.series.map((s) => ({
      key: s.name,
      label: s.label ?? s.name,
      left: Number(s.points[0]?.[1] ?? 0),
      right: Number(s.points[1]?.[1] ?? 0),
      color: roleColor(s.role),
    }));
    return (
      <Slope
        lines={lines}
        leftLabel="Raw average"
        rightLabel="Held constant what it flies"
        highlight={highlight}
        showRight={show("adjusted")}
        testId={`chart-${spec.id}`}
      />
    );
  }
  if (spec.kind === "bars") {
    const panel = spec.panels[0];
    if (!panel) return null;
    const bars = panel.series.map((s) => ({
      key: s.name,
      label: s.label ?? s.name,
      value: Number(s.points[0]?.[1] ?? 0),
      low: s.low?.[0] ?? null,
      high: s.high?.[0] ?? null,
      color: roleColor(s.role),
      hatched: s.role === "control",
    }));
    return <Bars bars={bars} fmt={spec.x_format} axisLabel={spec.x_label} highlight={highlight} testId={`chart-${spec.id}`} />;
  }
  // Lines: one panel or several stacked, each on its own axis.
  return (
    <div className="space-y-5" data-testid={`chart-${spec.id}`}>
      {spec.panels.map((panel, i) => {
        const { v, h } = rulesOf(panel.rules, show);
        const shades: Shade[] = panel.bands.map((b) => ({ from: xNumber(b.from), to: xNumber(b.to), label: b.label }));
        const marks: PointMark[] = [];
        for (const a of panel.annotations) {
          if (!show(a.state)) continue;
          const x = xNumber(a.x);
          if (!Number.isFinite(x)) continue;
          if (a.y !== null && a.y !== undefined) marks.push({ x, y: a.y, label: a.text, color: "var(--ink)" });
          else v.push({ x, label: a.text, color: "var(--ink2)", dash: "3 3" });
        }
        return (
          <div key={`${panel.title}-${i}`}>
            {spec.panels.length > 1 ? <p className="text-sm font-semibold text-ink mb-1">{panel.title}</p> : null}
            <LineChart
              series={lineSeries(panel, highlight)}
              xFmt={spec.x_format}
              yFmt={panel.y_format ?? spec.y_format}
              xLabel={spec.x_label}
              yLabel={panel.y_label ?? spec.y_label}
              vRules={v}
              hRules={h}
              shades={shades}
              marks={marks}
              zero={spec.kind === "curves" || spec.kind === "event"}
              height={height ?? (spec.panels.length > 1 ? 220 : 300)}
              compact={spec.panels.length > 2}
            />
            {marks.length ? (
              <ul className="mt-1 text-xs text-ink2 flex flex-wrap gap-x-4">
                {marks.map((m) => (
                  <li key={m.label}>{m.label}</li>
                ))}
              </ul>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

/** A spec's table toggle data. */
export function specTable(spec: ChartSpec): { columns: string[]; formats: string[]; rows: ChartSpec["table_rows"] } {
  const formats = spec.table_columns.map((_, i) => {
    const sample = spec.table_rows.find((r) => r[i] !== null && r[i] !== undefined)?.[i];
    if (typeof sample === "number") return Number.isInteger(sample) && Math.abs(sample) >= 1000 ? "int" : "float3";
    return "text";
  });
  return { columns: spec.table_columns, formats, rows: spec.table_rows };
}

export function describe(spec: ChartSpec): string {
  return `${spec.message}. ${spec.subtitle}. ${formatValue(spec.panels.length, "int")} panel${spec.panels.length === 1 ? "" : "s"}.`;
}
