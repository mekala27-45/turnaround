import type { Metadata } from "next";

import { MarkReady } from "@/components/MarkReady";

import { ManifestTable } from "@/components/ManifestTable";
import { PageHeader, Pushback, Section } from "@/components/Section";
import { SpecFigure } from "@/components/SpecFigure";
import { chart, manifest } from "@/lib/load";

export const metadata: Metadata = { title: "The fair ranking" };

export default function RankPage() {
  const m = manifest();
  const spec = chart("ranking");
  return (
    <>
      <MarkReady />
      <PageHeader kicker="The fair ranking" question="Which airline runs on time, once you hold constant what each one flies?">
        <p>
          The raw ranking sorts carriers by their average arrival delay. The adjusted ranking holds constant the route, the month, the scheduled hour
          and the aircraft type, so a carrier that flies into the hardest airports at the busiest hours is compared with other carriers on the same
          routes at the same hours. Both are fit on {m.vOr("window.test_first_year", "the reporting years")} onward, with intervals clustered by day.
        </p>
      </PageHeader>
      <SpecFigure spec={spec} callout={m.figure("chart.ranking").callout} testId="rank-slope" />
      <Section title="Raw beside adjusted" id="rank-table">
        <ManifestTable m={m} tableKey="ch5.ranking" testId="rank-table" />
      </Section>
      <Section title="The model" id="rank-model">
        <div className="prose space-y-3">
          <p>{m.vOr("plan.5.estimator", "")}</p>
          <p>
            Plan <code className="mono">{m.vOr("plan.5.hash", "")}</code>, registered before the fit. {m.vOr("plan.5.interval", "")} The fit used{" "}
            {m.vOr("ch5.cells", "the")} cells over {m.vOr("ch5.days", "the")} days.
          </p>
        </div>
      </Section>
      <Section title="Proven on the simulator first" id="rank-recovery">
        <div className="prose space-y-3">
          <p>
            On a simulated network where the true carrier effects are known and better carriers are steered onto harder routes, the adjusted
            ranking's rank correlation with the truth averaged {m.vOr("recovery.rank_adjusted.strong", "")} under strong confounding, against{" "}
            {m.vOr("recovery.rank_raw.strong", "")} for the raw ranking; with moderate confounding {m.vOr("recovery.rank_adjusted.moderate", "")} against{" "}
            {m.vOr("recovery.rank_raw.moderate", "")}, and with none {m.vOr("recovery.rank_adjusted.none", "")} against {m.vOr("recovery.rank_raw.none", "")}.
          </p>
        </div>
      </Section>
      <Pushback>
        <p>
          My carrier flies the hardest routes. This page is the answer to that objection: the route, month, hour and aircraft are held constant. What
          it does not hold constant is anything the carrier chooses that the data does not record, such as how many spare aircraft and crews it
          keeps and how tightly it schedules its turns. Those are the carrier's own decisions, and the ranking is right to charge them to the
          carrier. A regional carrier flying for several mainline brands is ranked as itself, because that is how it reports.
        </p>
      </Pushback>
    </>
  );
}
