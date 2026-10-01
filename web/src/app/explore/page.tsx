import type { Metadata } from "next";

import { PageHeader, Pushback } from "@/components/Section";
import { manifest } from "@/lib/load";

import { ExploreClient } from "./ExploreClient";

export const metadata: Metadata = { title: "Explore" };

export default function ExplorePage() {
  const m = manifest();
  return (
    <>
      <PageHeader kicker="The explorer" question="Pick a carrier, a route and a month, and see what the flights did.">
        <p>
          Every chart on this page is a query over the marts the warehouse published, run in your browser with DuckDB. Change a picker and every
          chart reruns; the SQL behind each one is under its button, and the box at the bottom takes your own.
        </p>
        <p className="text-ink2 text-sm">
          The window is {m.vOr("data.first_month", "the first month")} to {m.vOr("data.last_month", "the latest month")}. The delay distribution and
          the hour profile come from marts kept by carrier and by month, so the route pickers narrow the other charts only.
        </p>
      </PageHeader>
      <ExploreClient />
      <Pushback>
        <p>
          A route chart is only as good as the flights behind it, and a thin route in a quiet month swings on a handful of bad days. The table toggle
          under every chart gives the flights behind each point, so a reader can see when a number rests on twenty flights rather than twenty
          thousand. Averages here are raw: they describe what passengers on that selection sat through, not how well the carrier ran it, which is
          what the ranking page adjusts for.
        </p>
      </Pushback>
    </>
  );
}
