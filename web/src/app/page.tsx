import { StoryClient } from "./StoryClient";

import { chart, manifest, story } from "@/lib/load";

export default function StoryPage() {
  const s = story();
  const m = manifest();
  const specs = Object.fromEntries(s.chapters.map((c) => [c.chart, chart(c.chart)]));
  const sources = Object.fromEntries(s.chapters.map((c) => [c.chart, m.figure(`chart.${c.chart}`).callout]));
  return <StoryClient story={s} specs={specs} callouts={sources} />;
}
