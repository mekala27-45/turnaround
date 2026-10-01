import type { Metadata } from "next";

import { MarkReady } from "@/components/MarkReady";

import { OperatingPoint } from "./OperatingPoint";

import { ManifestTable } from "@/components/ManifestTable";
import { PageHeader, Pushback, Section } from "@/components/Section";
import { SpecFigure } from "@/components/SpecFigure";
import { chart, manifest } from "@/lib/load";

export const metadata: Metadata = { title: "Disruptions" };

export default function EventsPage() {
  const m = manifest();
  const op = m.has("ch7.operating") ? m.table("ch7.operating") : null;
  return (
    <>
      <MarkReady />
      <PageHeader kicker="Disruptions" question="Did the detector see the meltdowns coming, and how fast did each carrier recover?">
        <p>
          The detector scores every carrier's day, and every day at the {m.vOr("ch7.airports", "busiest")} busiest airports, against its own
          previous four weeks. Its threshold was chosen on {m.vOr("policy.fit_years", "the fitting years")} by the cost of a false alarm against a
          missed disruption, and graded on the reporting years against a table of known disruptions, each with a citation.
        </p>
      </PageHeader>
      <Section title="The known disruptions and when they were flagged" id="known">
        <ManifestTable m={m} tableKey="ch7.events" testId="events-table" />
      </Section>
      <Section
        title="The operating point"
        id="operating"
        intro={
          <p>
            A false alarm costs {m.vOr("ch7.cost_false_alarm", "")} and a missed disruption {m.vOr("ch7.cost_miss", "")}; the threshold with the
            least total cost on the fitting years was {m.vOr("ch7.threshold", "")}, {m.vOr("ch7.interior", "")}. On the reporting years it flagged{" "}
            {m.vOr("ch7.test.detected", "")} of {m.vOr("ch7.test.events", "")} disruptions with {m.vOr("ch7.test.false_alarms", "")} false alarm
            episodes.
          </p>
        }
      >
        {op ? (
          <OperatingPoint
            grid={op.rows.map((r) => Number(r[0]))}
            costs={op.rows.map((r) => Number(r[1]))}
            threshold={m.num("ch7.threshold")}
            source={m.prov("ch7.operating")}
          />
        ) : null}
      </Section>
      <Section title="The two carrier meltdowns" id="studies">
        <SpecFigure spec={chart("meltdowns")} callout={m.figure("chart.meltdowns").callout} testId="event-study" />
      </Section>
      <Section title="The alerts in the reporting years" id="alerts">
        <ManifestTable m={m} tableKey="ch7.top_episodes" testId="alerts-table" />
      </Section>
      <Section title="Recovery by carrier" id="recovery">
        <ManifestTable m={m} tableKey="ch7.recovery_by_carrier" testId="recovery-table" />
      </Section>
      <Pushback>
        <p>
          The known events table is short, so a disruption that is real but not in the table counts as a false alarm, which overstates the false
          alarm rate. The peer control in the event studies is the other carriers at the same airports, who were hit by the same storm and carried
          some of the stranded carrier's passengers; the storm is differenced out, and the published excess is a floor.
        </p>
      </Pushback>
    </>
  );
}
