import { readFileSync } from "node:fs";
import { join } from "node:path";

import type { Metadata } from "next";

import { MarkReady } from "@/components/MarkReady";

import { SpecFigure } from "@/components/SpecFigure";
import { chart, manifest } from "@/lib/load";

import { PrintButton } from "./PrintButton";

export const metadata: Metadata = { title: "The briefing" };

interface Briefing {
  title: string;
  intro_html: string;
  sections: { id: string; title: string; html: string; chart: string | null }[];
}

export default function ReportPage() {
  const b = JSON.parse(readFileSync(join(process.cwd(), "public", "data", "briefing.json"), "utf8")) as Briefing;
  const m = manifest();
  return (
    <article className="memo report-sheet max-w-[46rem] mx-auto" data-testid="briefing">
      <MarkReady />
      <div className="no-print flex justify-end mb-4">
        <PrintButton />
      </div>
      <h1 className="text-[2.1rem] leading-tight mb-3">{b.title}</h1>
      <div dangerouslySetInnerHTML={{ __html: b.intro_html }} />
      {b.sections.map((s) => (
        <section key={s.id} aria-labelledby={s.id} data-testid={`briefing-${s.id}`}>
          <h2 id={s.id}>{s.title}</h2>
          {s.chart ? (
            <div className="my-4">
              <SpecFigure spec={chart(s.chart)} callout={m.figure(`chart.${s.chart}`).callout} />
            </div>
          ) : null}
          <div dangerouslySetInnerHTML={{ __html: s.html }} />
        </section>
      ))}
    </article>
  );
}
