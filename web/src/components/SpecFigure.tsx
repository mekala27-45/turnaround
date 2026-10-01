"use client";

import { Figure } from "@/components/charts/Figure";
import { SpecChart, specTable } from "@/components/charts/SpecChart";
import type { ChartSpec } from "@/lib/charts";

/** A chapter's chart outside the story: every state shown at once. */
export function SpecFigure({ spec, callout, testId }: { spec: ChartSpec; callout?: string; testId?: string }) {
  return (
    <Figure message={spec.message} subtitle={spec.subtitle} source={spec.source} sql={spec.sql} table={specTable(spec)} callout={callout} testId={testId}>
      <SpecChart spec={spec} />
    </Figure>
  );
}
