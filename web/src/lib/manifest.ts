// The manifest as the site reads it. Every figure on a page is a value here, a table here, or the
// result of a query over a mart the same pipeline wrote. Nothing in this file touches the file
// system, so types and helpers can be shared with browser code; the reading happens in load.ts.
import { formatValue, type Scalar } from "./format";

export interface Provenance {
  as_of: string;
  condition: string | null;
  model: string;
  origin: string;
  population: string;
  seed: number | null;
  seeds: number | null;
  source: string;
}
export interface ValueEntry {
  value: Scalar;
  fmt: string;
  provenance: Provenance;
}
export interface TableEntry {
  columns: string[];
  formats: string[];
  rows: Scalar[][];
  provenance: Provenance;
}
export interface FigureEntry {
  title: string;
  callout: string;
  data: string | null;
  subtitle: string | null;
  sql: string | null;
  provenance: Provenance;
}
export interface Manifest {
  as_of: string;
  seed: number;
  values: Record<string, ValueEntry>;
  tables: Record<string, TableEntry>;
  figures: Record<string, FigureEntry>;
}

const SOURCES: Record<string, string> = {
  simulated: "simulated airline network with known truth",
  "real:bts": "BTS Reporting Carrier On-Time Performance (real)",
  "real:bts+faa": "BTS on time files joined to the FAA registry (real)",
  "real:bts+open_meteo": "BTS on time files with Open-Meteo weather (real)",
  "real:faa": "FAA releasable aircraft registry (real)",
  "real:ourairports": "OurAirports (real)",
  "real:open_meteo": "Open-Meteo historical weather, CC BY 4.0 (real)",
  recorded: "recorded observation",
  mixed: "several sources",
  static: "stated policy and settings",
  api: "the live API",
};

/** The provenance line printed under a chart: source, model, population, condition, seeds, as of. */
export function provenanceLine(p: Provenance): string {
  const parts = [`Source: ${SOURCES[p.source] ?? p.source}`];
  if (p.model && p.model !== "none") parts.push(`model: ${p.model}`);
  parts.push(`population: ${p.population}`);
  if (p.condition) parts.push(`condition: ${p.condition}`);
  if (p.seeds !== null) parts.push(`seeds: ${formatValue(p.seeds, "int")}`);
  else if (p.seed !== null) parts.push(`seed: ${formatValue(p.seed, "int")}`);
  parts.push(`as of ${p.as_of}`);
  return `${parts.join("; ")}.`;
}

export class ManifestView {
  constructor(private readonly m: Manifest) {}

  has(key: string): boolean {
    return key in this.m.values || key in this.m.tables;
  }
  /** A value printed through its format, or a stated fallback when the key is absent. */
  vOr(key: string, fallback: string): string {
    return key in this.m.values ? this.v(key) : fallback;
  }
  entry(key: string): ValueEntry {
    const entry = this.m.values[key];
    if (!entry) throw new Error(`manifest has no value ${key}`);
    return entry;
  }
  raw(key: string): Scalar {
    return this.entry(key).value;
  }
  num(key: string): number {
    const v = this.raw(key);
    if (typeof v !== "number") throw new Error(`manifest value ${key} is not a number`);
    return v;
  }
  text(key: string): string {
    return String(this.raw(key));
  }
  /** A value printed through its own format, the only way a manifest number reaches a page. */
  v(key: string): string {
    const entry = this.entry(key);
    return formatValue(entry.value, entry.fmt);
  }
  fmt(key: string): string {
    return this.entry(key).fmt;
  }
  table(key: string): TableEntry {
    const entry = this.m.tables[key];
    if (!entry) throw new Error(`manifest has no table ${key}`);
    return entry;
  }
  provenance(key: string): Provenance {
    const entry = this.m.tables[key] ?? this.m.values[key];
    if (!entry) throw new Error(`manifest has no entry ${key}`);
    return entry.provenance;
  }
  /** The printed provenance line of a value or table. */
  prov(key: string): string {
    return provenanceLine(this.provenance(key));
  }
  figure(key: string): FigureEntry {
    const entry = this.m.figures[key];
    if (!entry) throw new Error(`manifest has no figure ${key}`);
    return entry;
  }
  /** A chart's one message: the figure title the pipeline wrote for chart.<id>. */
  message(chartId: string): string {
    return this.figure(`chart.${chartId}`).title;
  }
  hasFigure(key: string): boolean {
    return key in this.m.figures;
  }
  get asOf(): string {
    return this.m.as_of;
  }
  get raw_manifest(): Manifest {
    return this.m;
  }
}
