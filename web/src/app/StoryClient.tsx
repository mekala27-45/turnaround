"use client";

import { useEffect, useRef, useState } from "react";

import { Figure } from "@/components/charts/Figure";
import { SpecChart, specTable } from "@/components/charts/SpecChart";
import type { ChartSpec } from "@/lib/charts";
import { markReady } from "@/lib/ready";
import type { Story, StoryChapter } from "@/lib/story";

/** Whether the reader asked for less motion or is on a narrow screen: then each chapter stacks. */
function useStacked(): boolean {
  const [stacked, setStacked] = useState(false);
  useEffect(() => {
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const narrow = window.matchMedia("(max-width: 1023px)");
    const update = () => setStacked(motion.matches || narrow.matches);
    update();
    motion.addEventListener("change", update);
    narrow.addEventListener("change", update);
    return () => {
      motion.removeEventListener("change", update);
      narrow.removeEventListener("change", update);
    };
  }, []);
  return stacked;
}

function Chapter({ chapter, spec, callout, stacked }: { chapter: StoryChapter; spec: ChartSpec; callout: string; stacked: boolean }) {
  const [active, setActive] = useState<string>(chapter.steps[0]?.state ?? "");
  const refs = useRef<(HTMLDivElement | null)[]>([]);
  useEffect(() => {
    if (stacked) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        const first = visible[0];
        if (first) {
          const state = (first.target as HTMLElement).dataset.state;
          if (state) setActive(state);
        }
      },
      { rootMargin: "-35% 0px -45% 0px", threshold: 0 },
    );
    for (const node of refs.current) if (node) observer.observe(node);
    return () => observer.disconnect();
  }, [stacked]);
  return (
    <section className="mt-20 first:mt-10" id={chapter.id} aria-labelledby={`${chapter.id}-title`} data-testid={`chapter-${chapter.id}`}>
      <p className="kicker">
        Chapter <span className="chapter-number">{chapter.number}</span>
      </p>
      <h2 id={`${chapter.id}-title`} className="text-[1.9rem] sm:text-[2.3rem] leading-[1.1] mt-1 mb-3 max-w-[24ch]">
        {chapter.title.replace(/^\d+\.\s*/, "")}
      </h2>
      <div className="longread text-[1.2rem] mb-6" data-testid="claim" dangerouslySetInnerHTML={{ __html: chapter.claim_html }} />
      <div className="story-grid">
        <div className="longread">
          {chapter.steps.map((step, i) => (
            <div
              key={`${step.state}-${i}`}
              ref={(node) => {
                refs.current[i] = node;
              }}
              className="story-step"
              data-state={step.state}
              data-active={!stacked && active === step.state ? "true" : "false"}
              dangerouslySetInnerHTML={{ __html: step.html }}
            />
          ))}
          <details className="mt-4 border-t border-hairline pt-3" data-testid="method-note">
            <summary className="cursor-pointer font-sans text-sm font-semibold text-ink">Method note: plan hash, estimator, split, interval, recovery</summary>
            <div className="mt-2 text-[0.95rem]" dangerouslySetInnerHTML={{ __html: chapter.method_html }} />
          </details>
          <div className="mt-6 text-[1rem]" data-testid="chapter-pushback" dangerouslySetInnerHTML={{ __html: chapter.pushback_html }} />
        </div>
        <div className="story-sticky" data-testid={`sticky-${chapter.id}`} data-state={stacked ? "all" : active}>
          <Figure message={spec.message} subtitle={spec.subtitle} source={spec.source} sql={spec.sql} table={specTable(spec)} callout={callout}>
            <SpecChart spec={spec} state={stacked ? null : active} />
          </Figure>
          {!stacked ? (
            <p className="mt-2 text-xs text-ink2 font-sans" aria-live="polite">
              {spec.states.find((s) => s.id === active)?.caption ?? ""}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export function StoryClient({ story, specs, callouts }: { story: Story; specs: Record<string, ChartSpec>; callouts: Record<string, string> }) {
  const stacked = useStacked();
  useEffect(() => {
    markReady();
  }, []);
  return (
    <article>
      <header className="mb-8 max-w-[70ch]">
        <p className="kicker mb-2">A data story in {story.chapters.length} chapters</p>
        <h1 className="text-[2.4rem] sm:text-[3.4rem] leading-[1.02] mb-4" data-testid="story-title">
          {story.title}
        </h1>
        <div className="longread" data-testid="preamble" dangerouslySetInnerHTML={{ __html: story.preamble_html }} />
        <nav aria-label="Chapters" className="mt-5 font-sans text-sm">
          <ol className="flex flex-wrap gap-x-4 gap-y-1 list-none">
            {story.chapters.map((c) => (
              <li key={c.id}>
                <a href={`#${c.id}`} className="text-ink2 hover:text-ink underline-offset-4 hover:underline">
                  {c.number}. {c.title.replace(/^\d+\.\s*/, "")}
                </a>
              </li>
            ))}
          </ol>
        </nav>
      </header>
      {story.chapters.map((c) => {
        const spec = specs[c.chart];
        return spec ? <Chapter key={c.id} chapter={c} spec={spec} callout={callouts[c.chart] ?? ""} stacked={stacked} /> : null;
      })}
      <section className="mt-20 longread" data-testid="coda" dangerouslySetInnerHTML={{ __html: story.coda_html }} />
    </article>
  );
}
