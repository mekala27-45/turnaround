import type { Metadata } from "next";

import { PageHeader, Pushback, Section } from "@/components/Section";
import { SpecFigure } from "@/components/SpecFigure";
import { chart, manifest } from "@/lib/load";

import { RotationsClient } from "./RotationsClient";

export const metadata: Metadata = { title: "The aircraft's day" };

export default function RotationsPage() {
  const m = manifest();
  return (
    <>
      <PageHeader kicker="The aircraft's day" question="Where was a late flight's delay born?">
        <p>
          Every flown leg with a tail number was put back in order on its aircraft's day. Pick a day, or take the worst day of a month, and an
          aircraft: the timeline shows each leg's arrival delay and how much of its departure delay it inherited from the leg before, using the
          propagation coefficient of {m.vOr("ch4.rho", "chapter 4")} and the minimum turn of {m.vOr("ch4.min_turn", "chapter 4")} estimated in chapter 4.
        </p>
      </PageHeader>
      <RotationsClient rho={m.has("ch4.rho") ? m.num("ch4.rho") : 0} minTurn={m.has("ch4.min_turn") ? m.num("ch4.min_turn") : 0} />
      <Section title="The buffer curve" id="buffer">
        <SpecFigure spec={chart("inherited")} callout={m.figure("chart.inherited").callout} testId="buffer-curve" />
      </Section>
      <Section title="The integrity rules and what they did" id="integrity">
        <div className="prose space-y-3" data-testid="integrity">
          <p>
            A leg is linked to the one before it only when it leaves from the airport that one landed at, after it landed, within{" "}
            {m.vOr("policy.rotation_gap_hours", "the stated gap")}; a longer sit starts a new rotation. Of {m.vOr("ch4.legs", "the")} legs,{" "}
            {m.vOr("ch4.linked", "")} were linked ({m.vOr("ch4.linked_share", "")}), {m.vOr("ch4.first", "")} were the first leg on their tail,{" "}
            {m.vOr("ch4.gap", "")} followed a gap, {m.vOr("ch4.broken_chain", "")} broke the chain and were split rather than joined (most are aircraft
            swaps the tail number does not show), and {m.vOr("ch4.impossible", "")} were impossible sequences, quarantined and counted. That leaves{" "}
            {m.vOr("ch4.rotations", "")} rotations on {m.vOr("ch4.tails", "")} aircraft.
          </p>
        </div>
      </Section>
      <Pushback>
        <p>
          Tail numbers miss aircraft swaps, so some links join two aircraft. The chain rules split a pair whenever the next leg does not leave from
          where the last one landed, which is what most swaps look like; a swap between two aircraft at the same airport inside one turn is invisible
          to any reconstruction from public data. The worst day of each month is chosen by the inherited minutes per linked leg, so the page shows
          the days propagation mattered most, not typical days.
        </p>
      </Pushback>
    </>
  );
}
