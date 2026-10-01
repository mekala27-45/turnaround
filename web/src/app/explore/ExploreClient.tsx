"use client";

import { useEffect, useMemo, useState } from "react";

import { Bars } from "@/components/charts/Bars";
import { Columns } from "@/components/charts/Columns";
import { ChartSkeleton, DataTable, Figure } from "@/components/charts/Figure";
import { LineChart } from "@/components/charts/LineChart";
import { mart, martNames, query, type Row } from "@/lib/data";
import { formatValue } from "@/lib/format";
import { useMart } from "@/lib/useMart";

interface Pick {
  carrier: string;
  origin: string;
  dest: string;
  year: string;
  month: string;
}

const ANY = "";
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const SOURCE = "Source: BTS Reporting Carrier On-Time Performance (real), through the warehouse's marts, queried in the browser.";

function where(p: Pick, cols: { carrier?: boolean; route?: boolean; year?: boolean; month?: boolean }): string {
  const parts: string[] = [];
  if (cols.carrier && p.carrier) parts.push(`carrier = '${p.carrier}'`);
  if (cols.route && p.origin) parts.push(`origin = '${p.origin}'`);
  if (cols.route && p.dest) parts.push(`dest = '${p.dest}'`);
  if (cols.year && p.year) parts.push(`year = ${Number(p.year)}`);
  if (cols.month && p.month) parts.push(`month = ${Number(p.month)}`);
  return parts.length ? `where ${parts.join(" and ")}` : "";
}

function Picker({ label, value, options, onChange, testId }: { label: string; value: string; options: [string, string][]; onChange: (v: string) => void; testId: string }) {
  return (
    <label className="flex flex-col text-xs text-ink2 gap-1 min-w-[8rem]">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)} data-testid={testId} className="text-sm">
        <option value={ANY}>All</option>
        {options.map(([v, text]) => (
          <option key={v} value={v}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}

export function ExploreClient() {
  const [pick, setPick] = useState<Pick>({ carrier: ANY, origin: ANY, dest: ANY, year: ANY, month: ANY });
  const set = (k: keyof Pick) => (v: string) => setPick((p) => ({ ...p, [k]: v }));
  const rm = mart("route_month");

  const carriers = useMart<{ carrier: string }>(`select distinct carrier from ${rm} order by carrier`);
  const origins = useMart<{ origin: string; n: number }>(
    `select origin, sum(scheduled) as n from ${rm} ${where(pick, { carrier: true })} group by origin order by n desc, origin limit 150`,
  );
  const dests = useMart<{ dest: string; n: number }>(
    `select dest, sum(scheduled) as n from ${rm} ${where({ ...pick, dest: ANY }, { carrier: true, route: true })} group by dest order by n desc, dest limit 150`,
  );
  const years = useMart<{ year: number }>(`select distinct year from ${rm} order by year`);

  const sqlMonthly = `select year, month, sum(scheduled) as scheduled, sum(flown) as flown,\n       sum(on_time) / sum(flown) as on_time_rate,\n       sum(arr_delay_sum) / sum(flown) as mean_delay,\n       sum(padding_sum) / sum(flown) as padding\nfrom ${rm}\n${where(pick, { carrier: true, route: true, year: true, month: true })}\ngroup by year, month order by year, month`;
  const monthly = useMart<{ year: number; month: number; scheduled: number; flown: number; on_time_rate: number; mean_delay: number; padding: number }>(sqlMonthly);

  const sqlByMonth = `select month, sum(flown) as flown, sum(on_time) / sum(flown) as on_time_rate\nfrom ${rm}\n${where(pick, { carrier: true, route: true, year: true })}\ngroup by month order by month`;
  const byMonth = useMart<{ month: number; flown: number; on_time_rate: number }>(sqlByMonth);

  const hist = mart("delay_histogram");
  const sqlHist = `select minute, sum(flights) as flights\nfrom ${hist}\n${where(pick, { carrier: true, year: true, month: true })}\ngroup by minute order by minute`;
  const histogram = useMart<{ minute: number; flights: number }>(sqlHist);

  const hours = mart("hour_profile");
  const sqlHour = `select dep_hour, sum(flown) as flown, sum(on_time) / sum(flown) as on_time_rate\nfrom ${hours}\n${where(pick, { year: true, month: true })}\ngroup by dep_hour order by dep_hour`;
  const byHour = useMart<{ dep_hour: number; flown: number; on_time_rate: number }>(sqlHour);

  const cm = mart("carrier_month");
  const sqlCauses = `select sum(cause_late_aircraft_sum) as late_aircraft, sum(cause_carrier_sum) as carrier,\n       sum(cause_nas_sum) as nas, sum(cause_weather_sum) as weather, sum(cause_security_sum) as security\nfrom ${cm}\n${where(pick, { carrier: true, year: true, month: true })}`;
  const causes = useMart<{ late_aircraft: number; carrier: number; nas: number; weather: number; security: number }>(sqlCauses);

  const monthlyRows = monthly.rows ?? [];
  const t = (r: { year: number; month: number }) => Date.UTC(r.year, r.month - 1, 1);
  const flownTotal = monthlyRows.reduce((a, r) => a + r.flown, 0);

  const causeBars = useMemo(() => {
    const c = causes.rows?.[0];
    if (!c) return [];
    const total = c.late_aircraft + c.carrier + c.nas + c.weather + c.security;
    if (!total) return [];
    return [
      { key: "late_aircraft", label: "Late aircraft", value: c.late_aircraft / total, color: "var(--cat-1)" },
      { key: "carrier", label: "Carrier", value: c.carrier / total, color: "var(--cat-4)" },
      { key: "nas", label: "Air traffic system", value: c.nas / total, color: "var(--cat-5)" },
      { key: "weather", label: "Weather", value: c.weather / total, color: "var(--cat-6)" },
      { key: "security", label: "Security", value: c.security / total, color: "var(--cat-7)" },
    ];
  }, [causes.rows]);

  // Every message is computed from the selection's own rows, so it is true of what the chart shows.
  const histRows = histogram.rows ?? [];
  const histTotal = histRows.reduce((a, r) => a + r.flights, 0);
  const early = histRows.filter((r) => r.minute < 0).reduce((a, r) => a + r.flights, 0);
  const late = histRows.filter((r) => r.minute >= 15).reduce((a, r) => a + r.flights, 0);
  const hourRows = (byHour.rows ?? []).filter((r) => r.flown >= 200);
  const bestHour = [...hourRows].sort((a, b) => b.on_time_rate - a.on_time_rate || a.dep_hour - b.dep_hour)[0];
  const worstHour = [...hourRows].sort((a, b) => a.on_time_rate - b.on_time_rate || a.dep_hour - b.dep_hour)[0];
  const monthRows = byMonth.rows ?? [];
  const bestMonth = [...monthRows].sort((a, b) => b.on_time_rate - a.on_time_rate || a.month - b.month)[0];
  const worstMonth = [...monthRows].sort((a, b) => a.on_time_rate - b.on_time_rate || a.month - b.month)[0];
  const paddingMean = flownTotal ? monthlyRows.reduce((a, r) => a + r.padding * r.flown, 0) / flownTotal : null;
  const topCause = [...causeBars].sort((a, b) => b.value - a.value)[0];
  const hh = (h: number) => `${String(h).padStart(2, "0")}:00`;

  return (
    <div className="space-y-6">
      <div className="card p-4 flex flex-wrap gap-4 items-end" data-testid="pickers">
        <Picker label="Carrier" value={pick.carrier} onChange={set("carrier")} options={(carriers.rows ?? []).map((r) => [r.carrier, r.carrier])} testId="pick-carrier" />
        <Picker label="Origin" value={pick.origin} onChange={set("origin")} options={(origins.rows ?? []).map((r) => [r.origin, r.origin])} testId="pick-origin" />
        <Picker label="Destination" value={pick.dest} onChange={set("dest")} options={(dests.rows ?? []).map((r) => [r.dest, r.dest])} testId="pick-dest" />
        <Picker label="Year" value={pick.year} onChange={set("year")} options={(years.rows ?? []).map((r) => [String(r.year), String(r.year)])} testId="pick-year" />
        <Picker label="Month" value={pick.month} onChange={set("month")} options={MONTHS.map((m, i) => [String(i + 1), m])} testId="pick-month" />
        <p className="text-sm text-ink2 ml-auto" data-testid="selection-flights">
          {monthly.rows ? `${formatValue(flownTotal, "int")} flights flown in the selection` : "Loading the marts"}
        </p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Figure
          testId="explore-ontime"
          message={monthlyRows.length ? `On time ${formatValue(monthlyRows.reduce((a, r) => a + r.on_time_rate * r.flown, 0) / Math.max(flownTotal, 1), "pct1")} of the time in the selection` : "On time rate by month"}
          subtitle="Share of flown flights arriving less than fifteen minutes late, by month"
          source={SOURCE}
          sql={sqlMonthly}
          table={{ columns: ["Year", "Month", "Flown", "On time"], formats: ["year", "int", "int", "pct1"], rows: monthlyRows.map((r) => [r.year, r.month, r.flown, r.on_time_rate]) }}
        >
          {monthly.rows ? (
            <LineChart
              series={[{ key: "ot", name: "On time rate", color: "var(--ink)", points: monthlyRows.map((r) => ({ x: t(r), y: r.on_time_rate })) }]}
              xFmt="month"
              yFmt="pct0"
              xLabel="Month"
              yLabel="On time"
              zero={false}
            />
          ) : (
            <ChartSkeleton shape="lines" />
          )}
        </Figure>
        <Figure
          testId="explore-distribution"
          message={histTotal ? `${formatValue(early / histTotal, "pct0")} of flights arrived early, ${formatValue(late / histTotal, "pct0")} fifteen minutes late or more` : "Flights by minute of arrival delay"}
          subtitle="Flights by whole minute of arrival delay, with the fifteen minute line"
          source={SOURCE}
          sql={sqlHist}
          table={{ columns: ["Minute", "Flights"], formats: ["int", "int"], rows: (histogram.rows ?? []).map((r) => [r.minute, r.flights]) }}
        >
          {histogram.rows ? (
            <Columns
              points={(histogram.rows ?? []).filter((r) => r.minute >= -40 && r.minute <= 90).map((r) => ({ x: r.minute, y: r.flights }))}
              xFmt="int"
              yFmt="int"
              xLabel="Arrival delay, minutes"
              yLabel="Flights"
              rules={[{ x: 15, label: "15 minutes", color: "var(--ink)" }]}
            />
          ) : (
            <ChartSkeleton shape="columns" />
          )}
        </Figure>
        <Figure
          testId="explore-hour"
          message={bestHour && worstHour ? `Departures at ${hh(bestHour.dep_hour)} were on time ${formatValue(bestHour.on_time_rate, "pct0")} of the time, at ${hh(worstHour.dep_hour)} ${formatValue(worstHour.on_time_rate, "pct0")}` : "On time rate by scheduled hour"}
          subtitle="On time rate by scheduled departure hour (all carriers and routes)"
          source={SOURCE}
          sql={sqlHour}
          table={{ columns: ["Hour", "Flown", "On time"], formats: ["int", "int", "pct1"], rows: (byHour.rows ?? []).map((r) => [r.dep_hour, r.flown, r.on_time_rate]) }}
        >
          {byHour.rows ? (
            <Bars
              bars={(byHour.rows ?? []).filter((r) => r.flown > 0).map((r) => ({ key: String(r.dep_hour), label: `${String(r.dep_hour).padStart(2, "0")}:00`, value: r.on_time_rate, color: "var(--ink)" }))}
              fmt="pct0"
              axisLabel="On time"
            />
          ) : (
            <ChartSkeleton shape="bars" />
          )}
        </Figure>
        <Figure
          testId="explore-month"
          message={bestMonth && worstMonth ? `${MONTHS[bestMonth.month - 1]} was the best month at ${formatValue(bestMonth.on_time_rate, "pct0")} on time, ${MONTHS[worstMonth.month - 1]} the worst at ${formatValue(worstMonth.on_time_rate, "pct0")}` : "On time rate by calendar month"}
          subtitle="On time rate by calendar month, every year in the selection pooled"
          source={SOURCE}
          sql={sqlByMonth}
          table={{ columns: ["Month", "Flown", "On time"], formats: ["int", "int", "pct1"], rows: (byMonth.rows ?? []).map((r) => [r.month, r.flown, r.on_time_rate]) }}
        >
          {byMonth.rows ? (
            <Bars
              bars={(byMonth.rows ?? []).map((r) => ({ key: String(r.month), label: MONTHS[r.month - 1] ?? String(r.month), value: r.on_time_rate, color: "var(--ink)" }))}
              fmt="pct0"
              axisLabel="On time"
            />
          ) : (
            <ChartSkeleton shape="bars" />
          )}
        </Figure>
        <Figure
          testId="explore-padding"
          message={paddingMean !== null ? `The schedule allowed ${formatValue(paddingMean, "min1")} beyond the unimpeded trip on the average flight` : "Padding by month"}
          subtitle="Mean padding per flown flight, by month"
          source={SOURCE}
          sql={sqlMonthly}
          table={{ columns: ["Year", "Month", "Padding"], formats: ["year", "int", "min1"], rows: monthlyRows.map((r) => [r.year, r.month, r.padding]) }}
        >
          {monthly.rows ? (
            <LineChart
              series={[{ key: "pad", name: "Padding", color: "var(--cat-1)", points: monthlyRows.map((r) => ({ x: t(r), y: r.padding })) }]}
              xFmt="month"
              yFmt="min0"
              xLabel="Month"
              yLabel="Minutes"
            />
          ) : (
            <ChartSkeleton shape="lines" />
          )}
        </Figure>
        <Figure
          testId="explore-causes"
          message={topCause ? `${topCause.label} was the largest reported cause, at ${formatValue(topCause.value, "pct0")} of cause minutes; reported is not caused` : "Reported delay causes"}
          subtitle="Share of reported delay cause minutes (carrier, year and month pickers)"
          source={SOURCE}
          sql={sqlCauses}
          table={{ columns: ["Cause", "Share"], formats: ["text", "pct1"], rows: causeBars.map((b) => [b.label, b.value]) }}
        >
          {causes.rows ? <Bars bars={causeBars} fmt="pct0" axisLabel="Share of cause minutes" /> : <ChartSkeleton shape="bars" />}
        </Figure>
      </div>
      <SqlBox />
    </div>
  );
}

function SqlBox() {
  const names = martNames();
  const [sql, setSql] = useState(`select carrier, sum(on_time) / sum(flown) as on_time_rate\nfrom mart_carrier_month\ngroup by carrier\norder by on_time_rate desc`);
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  useEffect(() => setRows(null), [sql]);
  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await query(sql);
      setRows(result.slice(0, 500));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  };
  const columns = rows && rows[0] ? Object.keys(rows[0]) : [];
  return (
    <section className="card p-4 sm:p-5" aria-labelledby="sqlbox" data-testid="sql-box">
      <h2 id="sqlbox" className="text-xl mb-1">
        Ask your own question
      </h2>
      <p className="text-sm text-ink2 mb-3">Read only SQL over the published marts: {names.map((n) => `mart_${n}`).join(", ")}.</p>
      <textarea
        value={sql}
        onChange={(e) => setSql(e.target.value)}
        className="sql w-full min-h-[140px]"
        aria-label="SQL"
        spellCheck={false}
        data-testid="sql-input"
      />
      <div className="flex items-center gap-3 mt-2">
        <button type="button" onClick={run} disabled={running} className="text-sm px-3 py-1.5 rounded bg-ink text-surface disabled:opacity-60" data-testid="sql-run">
          {running ? "Running" : "Run the query"}
        </button>
        {error ? (
          <p className="text-sm text-ink" role="alert">
            {error}
          </p>
        ) : null}
      </div>
      {rows ? (
        <div className="mt-3" data-testid="sql-result">
          <DataTable
            table={{
              columns,
              formats: columns.map((c) => (typeof rows[0]?.[c] === "number" ? "float3" : "text")),
              rows: rows.map((r) => columns.map((c) => (r[c] as string | number | null) ?? null)),
            }}
          />
        </div>
      ) : null}
    </section>
  );
}
