"use client";

import { type ReactNode, useId, useState } from "react";

import { formatValue, type Scalar } from "@/lib/format";

export interface TableData {
  columns: string[];
  formats: string[];
  rows: (Scalar | undefined)[][];
}

/**
 * Every chart: its one message as the title, the conventional title demoted to a subtitle, a table
 * toggle and a "show the SQL" toggle beside it, the chart (or its table, or its SQL), a callout whose
 * figures come from the manifest, and the source and window that produced it.
 */
export function Figure({
  message,
  subtitle,
  source,
  sql,
  table,
  callout,
  children,
  controls,
  testId,
}: {
  message: string;
  subtitle: string;
  source: string;
  sql: string | null;
  table: TableData | null;
  callout?: ReactNode;
  children: ReactNode;
  controls?: ReactNode;
  testId?: string;
}) {
  const [view, setView] = useState<"chart" | "table" | "sql">("chart");
  const id = useId();
  const toggle = (next: "table" | "sql") => setView((v) => (v === next ? "chart" : next));
  return (
    <figure className="card chart p-4 sm:p-5 min-w-0" aria-labelledby={id} data-testid={testId} data-view={view}>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-1">
        <h3 id={id} className="font-sans text-[1.05rem] font-bold text-ink leading-snug max-w-[56ch]" data-testid="chart-message">
          {message}
        </h3>
        <div className="no-print flex gap-2 shrink-0">
          <button
            type="button"
            onClick={() => toggle("table")}
            className="text-xs px-2 py-1 border border-hairline rounded text-ink2 hover:text-ink hover:border-control"
            aria-pressed={view === "table"}
            data-testid="table-toggle"
          >
            {view === "table" ? "Show chart" : "Show table"}
          </button>
          {sql ? (
            <button
              type="button"
              onClick={() => toggle("sql")}
              className="text-xs px-2 py-1 border border-hairline rounded text-ink2 hover:text-ink hover:border-control"
              aria-pressed={view === "sql"}
              data-testid="sql-toggle"
            >
              {view === "sql" ? "Hide the SQL" : "Show the SQL"}
            </button>
          ) : null}
        </div>
      </div>
      <p className="text-sm text-ink2 mb-3">{subtitle}</p>
      {controls ? <div className="mb-3">{controls}</div> : null}
      {view === "table" ? <DataTable table={table} /> : null}
      {view === "sql" && sql ? (
        <pre className="sql" data-testid="sql">
          {sql}
        </pre>
      ) : null}
      <div hidden={view !== "chart"}>{children}</div>
      {callout ? <figcaption className="mt-3 text-sm text-ink leading-relaxed prose">{callout}</figcaption> : null}
      <p className="mt-1.5 text-xs text-ink2 leading-snug" data-testid="source-line">
        {source}
      </p>
    </figure>
  );
}

export function DataTable({ table, max = 400, caption }: { table: TableData | null; max?: number; caption?: string }) {
  if (!table) {
    return <p className="text-sm text-ink2">The data is still loading.</p>;
  }
  const rows = table.rows.slice(0, max);
  return (
    <div className="overflow-x-auto max-h-[440px] overflow-y-auto" role="region" aria-label={caption ?? "Chart data"} tabIndex={0}>
      <table className="data-table dense">
        {caption ? <caption>{caption}</caption> : null}
        <thead>
          <tr>
            {table.columns.map((c, i) => (
              <th key={`${c}-${i}`} scope="col" className={table.formats[i] === "text" ? "" : "num"}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r}>
              {row.map((cell, i) => (
                <td key={i} className={table.formats[i] === "text" ? "" : "num"}>
                  {formatValue(cell, table.formats[i] ?? "text")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {table.rows.length > max ? (
        <p className="text-xs text-ink2 mt-2">
          First {formatValue(max, "int")} of {formatValue(table.rows.length, "int")} rows.
        </p>
      ) : null}
    </div>
  );
}

/** A loading state in the shape of the chart it stands in for. */
export function ChartSkeleton({ shape, height = 260 }: { shape: "lines" | "bars" | "columns" | "table"; height?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading the chart" role="img" style={{ minHeight: height }} data-skeleton={shape}>
      {shape === "lines" ? (
        <div className="relative w-full" style={{ height }}>
          {[0.2, 0.4, 0.6, 0.8].map((t) => (
            <div key={t} className="absolute left-10 right-2 border-t border-hairline" style={{ top: `${t * 100}%` }} />
          ))}
          <div className="skeleton absolute left-10 right-2 bottom-6 top-[45%] h-1.5" />
        </div>
      ) : null}
      {shape === "columns" ? (
        <div className="flex items-end gap-1 h-full pt-6" style={{ height }}>
          {Array.from({ length: 28 }, (_, i) => (
            <div key={i} className="skeleton flex-1" style={{ height: `${20 + ((i * 37) % 70)}%` }} />
          ))}
        </div>
      ) : null}
      {shape === "bars" || shape === "table" ? (
        <div className="space-y-3 pt-1">
          {Array.from({ length: 7 }, (_, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="skeleton h-3 w-24 shrink-0" />
              <div className="skeleton h-3" style={{ width: `${30 + ((i * 17) % 50)}%` }} />
            </div>
          ))}
        </div>
      ) : null}
      <span className="sr-only">Loading the chart</span>
    </div>
  );
}
