"use client";

import { Bars } from "@/components/charts/Bars";
import { ChartSkeleton, Figure } from "@/components/charts/Figure";
import { mart } from "@/lib/data";
import { formatValue, type Scalar } from "@/lib/format";
import { useMart } from "@/lib/useMart";

export function QuarantineByMonth() {
  const sql = `select carrier, year, month, rows, excluded\nfrom ${mart("quarantine")}\norder by year, month, carrier`;
  const q = useMart<{ carrier: string; year: number; month: number; rows: number; excluded: number }>(sql);
  const rows = q.rows ?? [];
  const total = rows.reduce((a, r) => a + r.rows, 0);
  const excluded = rows.reduce((a, r) => a + r.excluded, 0);
  return (
    <Figure
      testId="quarantine-by-month"
      message={total ? `${formatValue(excluded / total, "pct2")} of rows were excluded from everything by a quarantine rule` : "The quarantine report by carrier and month"}
      subtitle="Rows and rows excluded by carrier and month"
      source="Source: BTS Reporting Carrier On-Time Performance (real), the warehouse's mart_quarantine."
      sql={sql}
      table={{ columns: ["Carrier", "Year", "Month", "Rows", "Excluded"], formats: ["text", "year", "int", "int", "int"], rows: rows.map((r) => [r.carrier, r.year, r.month, r.rows, r.excluded]) }}
    >
      {q.rows ? (
        <p className="text-sm text-ink2">
          {formatValue(rows.length, "int")} carrier months, {formatValue(total, "int")} rows. Show the table for every carrier and month.
        </p>
      ) : (
        <ChartSkeleton shape="table" height={60} />
      )}
    </Figure>
  );
}

/** Small multiples: one panel per estimator measure, one bar per condition. */
export function RecoveryMultiples({ columns, formats, rows, source }: { columns: string[]; formats: string[]; rows: Scalar[][]; source: string }) {
  const panels = columns.slice(1).map((column, i) => ({ column, fmt: formats[i + 1] ?? "float2", index: i + 1 }));
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5" data-testid="recovery-multiples">
      {panels.map((p) => {
        const values = rows.map((r) => Number(r[p.index] ?? 0));
        const worst = rows[values.indexOf(Math.max(...values.map((v) => Math.abs(v))))]?.[0];
        return (
          <Figure
            key={p.column}
            message={`${p.column}, by condition`}
            subtitle={worst ? `Largest in magnitude under ${String(worst)}` : "By condition"}
            source={source}
            sql={null}
            table={{ columns: ["Condition", p.column], formats: ["text", p.fmt], rows: rows.map((r) => [r[0] ?? null, r[p.index] ?? null]) }}
          >
            <Bars
              bars={rows.map((r, j) => ({
                key: String(r[0]),
                label: String(r[0]).replace("confounding ", "conf. ").replace("propagation ", "prop. "),
                value: Math.abs(values[j] ?? 0),
                color: String(r[0]).includes("strong, ") ? "var(--cat-1)" : "var(--control)",
              }))}
              fmt={p.fmt.replace(/^s/, "").replace("pts1", "apts1")}
              axisLabel={`${p.column} (absolute)`}
            />
          </Figure>
        );
      })}
    </div>
  );
}
