// The story as the pipeline parses it from story/story.md: chapters with their sticky chart, the
// steps that advance it, the claim, the method note and the pushback paragraph, as HTML rendered from
// the manifest's numbers.
export interface StoryStep {
  state: string;
  html: string;
}
export interface StoryChapter {
  id: string;
  number: number;
  chart: string;
  title: string;
  claim: string;
  claim_html: string;
  steps: StoryStep[];
  method_html: string;
  pushback_html: string;
}
export interface Story {
  title: string;
  reading_minutes: number;
  preamble_html: string;
  chapters: StoryChapter[];
  coda_html: string;
}
