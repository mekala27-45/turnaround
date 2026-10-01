// The chart specifications the pipeline writes to results/charts and the site copies to
// public/data/charts: one message (the title), a subtitle, the provenance line, the SQL behind the
// chart, the panels with their series, annotations, rules and bands, the states the story advances
// through, and the table the table toggle shows.
import type { Scalar } from "./format";

export type Role = "ink" | "delay" | "early" | "adjusted" | "control" | "cat4" | "cat5" | "cat6" | "cat7" | "cat8";

export interface SpecSeries {
  name: string;
  role: Role;
  points: [Scalar, number | null][];
  low: (number | null)[] | null;
  high: (number | null)[] | null;
  dashed: boolean;
  label: string | null;
}
export interface SpecAnnotation {
  x: Scalar;
  y: number | null;
  text: string;
  state: string | null;
}
export interface SpecRule {
  x?: number;
  y?: number;
  label?: string;
  role?: Role;
  faint?: boolean;
  state?: string;
}
export interface SpecBand {
  from: string;
  to: string;
  label: string;
}
export interface SpecPanel {
  title: string;
  series: SpecSeries[];
  annotations: SpecAnnotation[];
  rules: SpecRule[];
  bands: SpecBand[];
  y_label: string | null;
  y_format: string | null;
}
export interface SpecState {
  id: string;
  caption: string;
  highlight: string[];
  show: string[];
}
export interface ChartSpec {
  id: string;
  kind: "multiples" | "line" | "histogram" | "slope" | "bars" | "event" | "curves";
  message: string;
  subtitle: string;
  source: string;
  sql: string;
  x_label: string;
  x_format: string;
  y_label: string;
  y_format: string;
  panels: SpecPanel[];
  states: SpecState[];
  table_columns: string[];
  table_rows: Scalar[][];
  notes: string[];
}

/** The CSS color of a role, from the palette tokens. */
export function roleColor(role: Role): string {
  switch (role) {
    case "ink":
      return "var(--ink)";
    case "delay":
      return "var(--cat-1)";
    case "early":
      return "var(--cat-2)";
    case "adjusted":
      return "var(--cat-3)";
    case "control":
      return "var(--control)";
    default:
      return `var(--cat-${role.slice(3)})`;
  }
}

/** An x value from a spec as a number: years and minutes pass through, ISO dates become epoch ms. */
export function xNumber(x: Scalar): number {
  if (typeof x === "number") return x;
  if (typeof x === "string") {
    const t = Date.parse(x.length === 10 ? `${x}T00:00:00Z` : x);
    if (!Number.isNaN(t)) return t;
    const n = Number(x);
    if (Number.isFinite(n)) return n;
  }
  return Number.NaN;
}
