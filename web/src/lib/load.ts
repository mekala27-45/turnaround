// Build time readers for the committed bundle in public/data. Server components call these while the
// static export renders; nothing here ships to the browser.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import type { ChartSpec } from "./charts";
import { type Manifest, ManifestView } from "./manifest";
import type { Story } from "./story";

const DATA = join(process.cwd(), "public", "data");

function readJson<T>(name: string): T {
  return JSON.parse(readFileSync(join(DATA, name), "utf8")) as T;
}

let cached: ManifestView | null = null;
export function manifest(): ManifestView {
  if (!cached) cached = new ManifestView(readJson<Manifest>("manifest.json"));
  return cached;
}

export interface Bundle {
  statement: string;
  as_of: string;
  written_at: string;
  charts: string[];
  files: Record<string, number>;
  api: string;
}

let bundleCache: Bundle | null = null;
export function bundle(): Bundle {
  if (!bundleCache) bundleCache = readJson<Bundle>("bundle.json");
  return bundleCache;
}

export function story(): Story {
  return readJson<Story>("story.json");
}

export function chart(id: string): ChartSpec {
  return readJson<ChartSpec>(`charts/${id}.json`);
}

export interface HubCurve {
  hub: string;
  buffers: number[];
  probability: number[];
  low: number[];
  high: number[];
  crossing: number | null;
  crossing_low: number | null;
  crossing_high: number | null;
  interior: boolean;
  days: number;
  inbound: number;
}

export function hubCurves(): HubCurve[] {
  return existsSync(join(DATA, "hub_curves.json")) ? readJson<HubCurve[]>("hub_curves.json") : [];
}

export interface LiveCheck {
  checked_at: string;
  browser: string;
  site_url: string;
  routes_loaded: number;
  routes_total: number;
  passed: boolean;
}

export function liveCheck(): LiveCheck | null {
  return existsSync(join(DATA, "live_check.json")) ? readJson<LiveCheck>("live_check.json") : null;
}
