// What the tests share: the routes, the published data the pages are checked against, and a way to
// open a page as a reader would. The build under test points the API at the test server's mock, which
// refuses HEAD, answers its first request with a 503 and then serves the recorded session.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import type { Page } from "@playwright/test";

export const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "/turnaround";

const data = (name: string) => JSON.parse(readFileSync(fileURLToPath(new URL(`../../public/data/${name}`, import.meta.url)), "utf8"));

export interface ManifestFile {
  values: Record<string, { value: number | string | null; fmt: string }>;
  tables: Record<string, { columns: string[]; rows: (number | string | null)[][] }>;
  figures: Record<string, { title: string }>;
}
export const manifest: ManifestFile = data("manifest.json");
export const bundle: { statement: string; charts: string[] } = data("bundle.json");
export const story: { chapters: { id: string; chart: string; steps: { state: string }[] }[] } = data("story.json");
export const recorded: {
  connections: { origin: string; connection: string; destination: string }[];
  responses: Record<string, { body: { check_id?: string } }>;
} = data("recorded_session.json");

export const ROUTES = ["/", "/explore/", "/rank/", "/rotations/", "/events/", "/planner/", "/data/", "/report/"];

/** Open a route; the mock API is the only API the build can reach. */
export async function open(page: Page, route: string): Promise<void> {
  await page.route(
    (url) => url.hostname !== "127.0.0.1" && url.hostname !== "localhost",
    () => {
      // Never answered: no test can reach a live API by accident.
    },
  );
  await page.goto(`${BASE}${route}`);
}

/** Open a route with the mock API hanging too, the way a stopped machine behaves. */
export async function openAsleep(page: Page, route: string): Promise<void> {
  await page.route(
    (url) => url.hostname !== "127.0.0.1" && url.hostname !== "localhost",
    () => {},
  );
  await page.route(
    (url) => url.pathname.startsWith("/mock-api/"),
    () => {
      // Never answered either: the six second probe gives up twice.
    },
  );
  await page.goto(`${BASE}${route}`);
}

/** The page sets data-ready on <html> once its first query has answered, or at once on a page with none. */
export async function ready(page: Page): Promise<void> {
  await page.waitForFunction(() => document.documentElement.getAttribute("data-ready") === "true", null, { timeout: 60_000 });
}

/** The first probe's 503 is the API waking up; the site probes again, so it is the one console error accepted. */
function isWakeUpProbe(text: string, url: string): boolean {
  return text.includes("status of 503") && /\/v1\/health$/.test(url);
}

export function collectErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    if (isWakeUpProbe(msg.text(), msg.location().url)) return;
    errors.push(`${msg.text()} (${msg.location().url})`);
  });
  page.on("pageerror", (err) => errors.push(err.message));
  return errors;
}
