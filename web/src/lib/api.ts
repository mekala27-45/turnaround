// The live API and its recorded stand in. The first call on a page probes /v1/health with a six
// second limit, twice, because the API's machine stops when idle and the first request wakes it; if
// it is asleep or unreachable, every API feature on the page answers from recorded_session.json for
// the rest of the visit and says so beside the control it affects.
import { API, dataUrl } from "./site";

export type Source = "live" | "recorded";

export interface Envelope {
  statement: string;
  served_at: string;
}
export interface HealthResponse extends Envelope {
  status: string;
  environment: string;
  database: string;
  model_version: string;
  hubs: number;
  outcome_month: string | null;
  min_connection_minutes: number;
  writes: string;
}
export interface HubEntry {
  hub: string;
  origins: string[];
  destinations: string[];
}
export interface HubsResponse extends Envelope {
  hubs: HubEntry[];
  model_version: string;
}
export interface Estimate {
  probability: number;
  low: number;
  high: number;
  flights: number;
  inbound_flights: number;
  outbound_flights: number;
  level: string;
  correlation_ratio: number;
  lost_share: number;
}
export interface CurvePoint extends Estimate {
  buffer: number;
}
export interface CurveResponse extends Envelope {
  origin: string;
  connection: string;
  destination: string;
  travel_month: string;
  inbound_hour: number;
  outbound_hour: number;
  line: number;
  crossing: number | null;
  points: CurvePoint[];
  model_version: string;
}
export interface Connection {
  origin: string;
  connection: string;
  destination: string;
  travel_month: string;
  inbound_hour: number;
  outbound_hour: number;
}
export interface CheckOut extends Envelope, Partial<Estimate> {
  check_id: string;
  origin: string;
  connection: string;
  destination: string;
  travel_month: string;
  inbound_hour: number;
  outbound_hour: number;
  buffer_minutes: number;
  probability: number;
  low: number;
  high: number;
  flights: number;
  level: string;
  model_version: string;
  note: string;
  created_at: string;
  score?: {
    outcome_month: string;
    realized_rate: number;
    pairs: number;
    absolute_error: number;
    inside_interval: boolean;
    scored_at: string;
  } | null;
}

interface RecordedResponse {
  method: string;
  path: string;
  status: number;
  body: unknown;
}
export interface RecordedSession {
  recorded: boolean;
  recorded_at: string;
  base_url: string;
  connections: Connection[];
  responses: Record<string, RecordedResponse>;
}

export interface Answer<T> {
  source: Source;
  status: number;
  body: T;
  /** Why the answer is the recorded one when the API itself is awake. */
  reason?: string;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

const PROBE_TIMEOUT_MS = 6000;
const PROBE_ATTEMPTS = 2;
const PROBE_PAUSE_MS = 4000;

let probe: Promise<Source> | null = null;
let session: Promise<RecordedSession> | null = null;

async function probeOnce(): Promise<Source> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const response = await fetch(`${API}/v1/health`, { signal: controller.signal, cache: "no-store" });
    if (!response.ok) return "recorded";
    const body = (await response.json()) as Partial<HealthResponse>;
    return body.status === "ok" ? "live" : "recorded";
  } catch {
    return "recorded";
  } finally {
    window.clearTimeout(timer);
  }
}

/** Whether this page visit talks to the live API or to the recording. Probed twice, then fixed. */
export function apiSource(): Promise<Source> {
  probe ??= (async (): Promise<Source> => {
    if (!API) return "recorded";
    for (let attempt = 1; attempt <= PROBE_ATTEMPTS; attempt += 1) {
      if (attempt > 1) await new Promise((resolve) => window.setTimeout(resolve, PROBE_PAUSE_MS));
      if ((await probeOnce()) === "live") return "live";
    }
    return "recorded";
  })();
  return probe;
}

export function recordedSession(): Promise<RecordedSession> {
  session ??= fetch(dataUrl("recorded_session.json")).then((r) => {
    if (!r.ok) throw new Error(`the recorded session did not load (${r.status})`);
    return r.json() as Promise<RecordedSession>;
  });
  return session;
}

async function fromRecording<T>(name: string, reason?: string): Promise<Answer<T>> {
  const s = await recordedSession();
  const hit = s.responses[name];
  if (!hit) throw new Error(`the recorded session has no answer for this connection; pick one of the recorded connections`);
  return { source: "recorded", status: hit.status, body: hit.body as T, reason };
}

async function send<T>(path: string, init: RequestInit = {}): Promise<{ status: number; body: T }> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  const body = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new ApiError(response.status, typeof body.error === "string" ? body.error : `status ${response.status}`);
  return { status: response.status, body };
}

/** A read: the live answer when the API is awake, else the recorded one under the given name. */
export async function read<T>(path: string, recordedName: string): Promise<Answer<T>> {
  if ((await apiSource()) === "live") {
    try {
      const { status, body } = await send<T>(path);
      return { source: "live", status, body };
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) throw err;
      return fromRecording<T>(recordedName, "the live API did not answer this request");
    }
  }
  return fromRecording<T>(recordedName);
}

export function curveName(c: Connection): string {
  return `curve_${c.origin}_${c.connection}_${c.destination}_${c.travel_month}_${c.inbound_hour}_${c.outbound_hour}`;
}

export function curvePath(c: Connection): string {
  const q = new URLSearchParams({
    origin: c.origin,
    connection: c.connection,
    destination: c.destination,
    travel_month: c.travel_month,
    inbound_hour: String(c.inbound_hour),
    outbound_hour: String(c.outbound_hour),
  });
  return `/v1/curve?${q.toString()}`;
}

export function getCurve(c: Connection): Promise<Answer<CurveResponse>> {
  return read<CurveResponse>(curvePath(c), curveName(c));
}

/** Save a check. Writes need the token and a live API; without either, the answer is the check the
 * recording made at that hub, labelled as recorded. */
export async function saveCheck(c: Connection, buffer: number, token: string): Promise<Answer<CheckOut>> {
  const name = `check_${c.connection}`;
  if ((await apiSource()) !== "live") return fromRecording<CheckOut>(name);
  if (!token.trim()) return fromRecording<CheckOut>(name, "no write token was given");
  const { status, body } = await send<CheckOut>("/v1/checks", {
    method: "POST",
    body: JSON.stringify({ ...c, buffer_minutes: buffer, note: "saved from the planner" }),
    headers: { Authorization: `Bearer ${token.trim()}` },
  });
  return { source: "live", status, body };
}
