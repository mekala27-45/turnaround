"use client";

import { Figure } from "@/components/charts/Figure";
import { LineChart } from "@/components/charts/LineChart";
import { formatValue } from "@/lib/format";

export function OperatingPoint({ grid, costs, threshold, source }: { grid: number[]; costs: number[]; threshold: number; source: string }) {
  const best = costs[grid.indexOf(threshold)] ?? null;
  return (
    <Figure
      testId="operating-point"
      message={`The cost curve bottoms out at a threshold of ${formatValue(threshold, "float1")}`}
      subtitle="Total cost on the fitting years by alert threshold: false alarm episodes plus missed disruptions at their stated costs"
      source={source}
      sql={null}
      table={{ columns: ["Threshold", "Cost"], formats: ["float1", "float1"], rows: grid.map((g, i) => [g, costs[i] ?? null]) }}
    >
      <LineChart
        series={[{ key: "cost", name: "Total cost", color: "var(--ink)", points: grid.map((g, i) => ({ x: g, y: costs[i] ?? null })) }]}
        xFmt="float1"
        yFmt="int"
        xLabel="Alert threshold, robust standard deviations"
        yLabel="Cost"
        marks={best !== null ? [{ x: threshold, y: best, label: "chosen", color: "var(--cat-1)" }] : []}
      />
    </Figure>
  );
}
