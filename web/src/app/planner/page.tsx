import type { Metadata } from "next";

import { PageHeader, Pushback, Section } from "@/components/Section";
import { SpecFigure } from "@/components/SpecFigure";
import { chart, manifest } from "@/lib/load";

import { PlannerClient } from "./PlannerClient";

export const metadata: Metadata = { title: "The misconnect calculator" };

export default function PlannerPage() {
  const m = manifest();
  return (
    <>
      <PageHeader kicker="The misconnect calculator" question="How long a connection should you leave?">
        <p>
          Pick a connection at one of the {m.vOr("ch8.hubs", "busiest")} busiest airports: where the first flight starts, where you change, where
          the second flight goes, the month, and the two scheduled hours. The calculator answers with the historical chance of missing the
          connection at every buffer, with an interval and the flights it rests on. A connection is missed when the inbound is cancelled or
          diverted, or lands too late to leave {m.vOr("policy.min_connection", "the minimum connection time")} to change planes.
        </p>
        <p className="text-sm text-ink2">
          The answers come from the live API on Fly. Its machine sleeps when idle; the page asks twice, and if it is still asleep it answers from a
          session recorded against the live API and says so.
        </p>
      </PageHeader>
      <PlannerClient line={m.has("ch8.line") ? m.num("ch8.line") : 0.1} />
      <Section title="The busiest hubs, day by day" id="hubs">
        <SpecFigure spec={chart("decision")} callout={m.figure("chart.decision").callout} testId="hub-curves" />
      </Section>
      <Pushback>
        <p>
          A connection on one ticket is protected: the airline holds the outbound for a late inbound with many connecting passengers and rebooks the
          rest. The curve counts a missed connection the way the schedule would, so it overstates misconnects for well protected connections and
          understates the cost of the ones missed on the last flight of the night. The calculator also works from the hub's cells shifted by each
          route's own average, so a route whose delays have a different shape from its hub's is answered with the hub's shape.
        </p>
      </Pushback>
    </>
  );
}
