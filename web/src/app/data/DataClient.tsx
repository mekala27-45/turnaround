"use client";

import { Bars } from "@/components/charts/Bars";
import { ChartSkeleton, Figure } from "@/components/charts/Figure";
import { mart } from "@/lib/data";
import { formatValue, type Scalar } from "@/lib/format";
import { useMart } from "@/lib/useMart";

// The rules in the order packages/contracts lists them; the mart has one count column per rule.
const RULES = [
  ["duplicate_key", "Duplicate key"],
  ["actual_without_scheduled", "Actual without scheduled"],
  ["impossible_time", "Impossible time"],
  ["elapsed_mismatch", "Elapsed mismatch"],
  ["cause_mismatch", "Cause mismatch"],
  ["tail_missing", "Tail missing"],
  ["tail_format", "Tail format"],
  ["revision", "Revision"],
] as const;
type RuleName = (typeof RULES)[number][0];
type QuarantineRow = { carrier: string; year: number; month: number; rows: number; excluded: number } & Record<RuleName, number>;

export function QuarantineByMonth() {
  const sql = `select carrier, year, month, rows, ${RULES.map(([r]) => r).join(", ")}, excluded\nfrom ${mart("quarantine")}\norder by year, month, carrier`;
  const q = useMart<QuarantineRow>(sql);
  const rows = q.rows ?? [];
  const total = rows.reduce((a, r) => a + r.rows, 0);
  const excluded = rows.reduce((a, r) => a + r.excluded, 0);
  return (
    <Figure
      testId="quarantine-by-month"
      message={total ? `${formatValue(excluded / total, "pct2")} of rows were excluded from everything by a quarantine rule` : "The quarantine report by carrier and month"}
      subtitle="Rows flagged by each rule, by carrier and month; a row can trip more than one rule"
      source="Source: BTS Reporting Carrier On-Time Performance (real), the warehouse's mart_quarantine."
      sql={sql}
      table={{
        columns: ["Carrier", "Year", "Month", "Rows", ...RULES.map(([, label]) => label), "Excluded"],
        formats: ["text", "year", "int", "int", ...RULES.map(() => "int"), "int"],
        rows: rows.map((r) => [r.carrier, r.year, r.month, r.rows, ...RULES.map(([name]) => r[name]), r.excluded]),
      }}
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
