"use client";

import { useEffect, useMemo, useState } from "react";

import { ChartSkeleton, Figure } from "@/components/charts/Figure";
import { LineChart } from "@/components/charts/LineChart";
import { Status } from "@/components/Status";
import {
  type Answer,
  apiSource,
  type CheckOut,
  type Connection,
  type CurveResponse,
  getCurve,
  type HealthResponse,
  type HubsResponse,
  read,
  recordedSession,
  saveCheck,
  type Source,
} from "@/lib/api";
import { formatValue } from "@/lib/format";
import { markReady } from "@/lib/ready";

const HOURS = Array.from({ length: 24 }, (_, h) => h);

export function PlannerClient({ line }: { line: number }) {
  const [source, setSource] = useState<Source | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [hubs, setHubs] = useState<HubsResponse["hubs"]>([]);
  const [presets, setPresets] = useState<Connection[]>([]);
  const [conn, setConn] = useState<Connection | null>(null);
  const [buffer, setBuffer] = useState(60);
  const [curve, setCurve] = useState<Answer<CurveResponse> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [token, setToken] = useState("");
  const [saved, setSaved] = useState<Answer<CheckOut> | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let live = true;
    (async () => {
      const s = await apiSource();
      const session = await recordedSession().catch(() => null);
      if (!live) return;
      setSource(s);
      setPresets(session?.connections ?? []);
      try {
        const h = await read<HealthResponse>("/v1/health", "health");
        const list = await read<HubsResponse>("/v1/hubs", "hubs");
        if (!live) return;
        setHealth(h.body);
        setHubs(list.body.hubs);
        const first = session?.connections?.[0];
        if (first) setConn(first);
      } catch (err) {
        if (live) setError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (!conn) return;
    let live = true;
    setCurve(null);
    setError(null);
    getCurve(conn).then(
      (answer) => {
        if (live) {
          setCurve(answer);
          markReady();
        }
      },
      (err: unknown) => {
        if (live) setError(err instanceof Error ? err.message : String(err));
      },
    );
    return () => {
      live = false;
    };
  }, [conn]);

  const hub = useMemo(() => hubs.find((h) => h.hub === conn?.connection), [hubs, conn]);
  const point = curve?.body.points.reduce((best, p) => (Math.abs(p.buffer - buffer) < Math.abs(best.buffer - buffer) ? p : best), curve.body.points[0]!);
  const recordedOnly = source === "recorded";
  const update = (patch: Partial<Connection>) => setConn((c) => (c ? { ...c, ...patch } : c));

  const save = async () => {
    if (!conn) return;
    setSaving(true);
    try {
      setSaved(await saveCheck(conn, buffer, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5" data-testid="planner">
      <div className="flex flex-wrap items-center gap-3 text-sm" data-testid="api-status">
        {source === null ? <span className="text-ink2">Asking the API whether it is awake</span> : null}
        {source === "live" ? <span className="font-semibold">Live API{health ? `, model ${health.model_version}` : ""}</span> : null}
        {source === "recorded" ? (
          <Status kind="warning" testId="recorded-label">
            Recorded session: the API is asleep, so these answers were recorded against the live API earlier
          </Status>
        ) : null}
      </div>
      <div className="card p-4 grid grid-cols-2 md:grid-cols-4 gap-3 items-end" data-testid="planner-form">
        {recordedOnly ? (
          <label className="flex flex-col text-xs text-ink2 gap-1 col-span-2 md:col-span-4">
            Recorded connection
            <select
              className="text-sm"
              data-testid="pick-preset"
              value={conn ? `${conn.origin}-${conn.connection}-${conn.destination}` : ""}
              onChange={(e) => setConn(presets.find((p) => `${p.origin}-${p.connection}-${p.destination}` === e.target.value) ?? null)}
            >
              {presets.map((p) => (
                <option key={`${p.origin}-${p.connection}-${p.destination}`} value={`${p.origin}-${p.connection}-${p.destination}`}>
                  {`${p.origin} to ${p.connection} to ${p.destination}, ${p.travel_month}, arriving ${p.inbound_hour}:00, leaving ${p.outbound_hour}:00`}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <>
            <label className="flex flex-col text-xs text-ink2 gap-1">
              Connecting at
              <select
                className="text-sm"
                data-testid="pick-hub"
                value={conn?.connection ?? ""}
                onChange={(e) => {
                  const h = hubs.find((x) => x.hub === e.target.value);
                  if (h) update({ connection: h.hub, origin: h.origins[0] ?? "", destination: h.destinations[0] ?? "" });
                }}
              >
                {hubs.map((h) => (
                  <option key={h.hub} value={h.hub}>
                    {h.hub}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-xs text-ink2 gap-1">
              From
              <select className="text-sm" data-testid="pick-origin" value={conn?.origin ?? ""} onChange={(e) => update({ origin: e.target.value })}>
                {(hub?.origins ?? []).map((o) => (
                  <option key={o}>{o}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-xs text-ink2 gap-1">
              To
              <select className="text-sm" data-testid="pick-destination" value={conn?.destination ?? ""} onChange={(e) => update({ destination: e.target.value })}>
                {(hub?.destinations ?? []).map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-xs text-ink2 gap-1">
              Travel month
              <input
                type="month"
                className="text-sm bg-raised border border-hairline rounded px-1 py-0.5"
                data-testid="pick-month"
                value={conn?.travel_month ?? ""}
                onChange={(e) => update({ travel_month: e.target.value })}
              />
            </label>
            <label className="flex flex-col text-xs text-ink2 gap-1">
              First flight lands at
              <select className="text-sm" value={conn?.inbound_hour ?? 12} onChange={(e) => update({ inbound_hour: Number(e.target.value) })}>
                {HOURS.map((h) => (
                  <option key={h} value={h}>{`${String(h).padStart(2, "0")}:00`}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-xs text-ink2 gap-1">
              Second flight leaves at
              <select className="text-sm" value={conn?.outbound_hour ?? 13} onChange={(e) => update({ outbound_hour: Number(e.target.value) })}>
                {HOURS.map((h) => (
                  <option key={h} value={h}>{`${String(h).padStart(2, "0")}:00`}</option>
                ))}
              </select>
            </label>
          </>
        )}
        <label className="flex flex-col text-xs text-ink2 gap-1 col-span-2">
          Scheduled buffer: {formatValue(buffer, "min0")}
          <input type="range" min={0} max={180} step={5} value={buffer} onChange={(e) => setBuffer(Number(e.target.value))} data-testid="buffer" />
        </label>
      </div>
      {error ? (
        <p className="text-sm" role="alert" data-testid="planner-error">
          {error}
        </p>
      ) : null}
      <Figure
        testId="connection-curve"
        message={
          curve && point
            ? `At ${formatValue(point.buffer, "min0")}, the chance of missing this connection is ${formatValue(point.probability, "pct1")} (${formatValue(point.low, "pct1")} to ${formatValue(point.high, "pct1")})`
            : "The chance of missing the connection, by buffer"
        }
        subtitle={conn ? `${conn.origin} to ${conn.connection} to ${conn.destination}, ${conn.travel_month}, by scheduled buffer` : "Pick a connection"}
        source={`Source: the calculator's cells from the BTS on time files, ${curve?.source === "recorded" ? "recorded session" : "live API"}, model ${curve?.body.model_version ?? ""}.`}
        sql={null}
        table={
          curve
            ? {
                columns: ["Buffer", "Chance of missing", "Low", "High", "Flights"],
                formats: ["min0", "pct1", "pct1", "pct1", "int"],
                rows: curve.body.points.map((p) => [p.buffer, p.probability, p.low, p.high, p.flights]),
              }
            : null
        }
        callout={
          curve && point ? (
            <span data-testid="probability">
              {`Rests on ${formatValue(point.flights, "int")} flights (${point.level}). `}
              {curve.body.crossing !== null
                ? `The chance falls under ${formatValue(line, "pct0")} at a buffer of ${formatValue(curve.body.crossing, "min0")}.`
                : `No buffer up to three hours brings it under ${formatValue(line, "pct0")}.`}
              {curve.source === "recorded" ? " Recorded session." : ""}
            </span>
          ) : undefined
        }
      >
        {curve ? (
          <LineChart
            series={[
              {
                key: "p",
                name: "Chance of missing",
                color: "var(--cat-1)",
                points: curve.body.points.map((p) => ({ x: p.buffer, y: p.probability })),
                band: curve.body.points.map((p) => ({ x: p.buffer, low: p.low, high: p.high })),
              },
            ]}
            xFmt="min0"
            yFmt="pct0"
            xLabel="Scheduled buffer"
            yLabel="Chance of missing the connection"
            hRules={[{ y: line, label: `${formatValue(line, "pct0")} line`, color: "var(--control)" }]}
            vRules={[{ x: buffer, label: "your buffer", color: "var(--cat-2)" }]}
          />
        ) : (
          <ChartSkeleton shape="lines" />
        )}
      </Figure>
      <div className="card p-4 flex flex-wrap gap-3 items-end" data-testid="save-check">
        <label className="flex flex-col text-xs text-ink2 gap-1">
          Write token (the API's writes are token gated; this is a demonstration)
          <input type="password" value={token} onChange={(e) => setToken(e.target.value)} autoComplete="off" data-testid="token" />
        </label>
        <button type="button" onClick={save} disabled={!conn || saving} className="text-sm px-3 py-1.5 rounded bg-ink text-surface disabled:opacity-60" data-testid="save">
          {saving ? "Saving" : "Save this check"}
        </button>
        {saved ? (
          <p className="text-sm" data-testid="check-id">
            {`Check ${saved.body.check_id} stored with ${formatValue(saved.body.probability, "pct1")} at ${formatValue(saved.body.buffer_minutes, "min0")}`}
            {saved.source === "recorded" ? ` (recorded session${saved.reason ? `: ${saved.reason}` : ""})` : " (live)"}
          </p>
        ) : null}
      </div>
    </div>
  );
}
