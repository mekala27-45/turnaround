// DuckDB-WASM over the published marts. The engine starts in a worker on the first query, after the
// page has painted from the manifest. Every chart that is not drawn from the manifest is a SQL query
// the engine answers.
//
// Why the parquet files are not opened with read_parquet: the 1.32.0 bundle links only DuckDB's core
// functions, and on first use of read_parquet it downloads the parquet extension from
// extensions.duckdb.org. The site fetches nothing from anywhere but its own origin, so each mart is
// read here instead, over HTTP byte ranges (the footer first, then the column chunks), decoded by
// hyparquet and handed to the engine as an Arrow table named mart_<name>. The SQL is the same SQL.
import type { AsyncDuckDBConnection } from "@duckdb/duckdb-wasm";

import bundleJson from "../../public/data/bundle.json";

import { markReady } from "./ready";
import { BASE } from "./site";

export type Row = Record<string, unknown>;

// The bundle lists every published file with its size in bytes. A mart's file is
// marts/mart_<name>.parquet (the warehouse's marts) or marts/<name>.parquet (the chapters' extracts);
// either way a query reads it as the table mart_<name>.
const FILES: Record<string, number> = (bundleJson as { files: Record<string, number> }).files;
const FILE_OF = new Map<string, string>();
for (const f of Object.keys(FILES)) {
  if (!f.startsWith("marts/") || !f.endsWith(".parquet")) continue;
  const stem = f.replace(/^marts\//, "").replace(/\.parquet$/, "");
  FILE_OF.set(stem.startsWith("mart_") ? stem.slice(5) : stem, f);
}
const MARTS = new Set(FILE_OF.keys());

/** Where a mart is served from. */
export function martPath(name: string): string {
  const file = FILE_OF.get(name);
  if (!file) throw new Error(`no published mart named ${name}`);
  return `${BASE}/data/${file}`;
}

/** The names of the published marts, for the SQL box's list of tables. */
export function martNames(): string[] {
  return [...MARTS].sort();
}

/** The table a query reads a mart through, for use in a FROM clause. */
export function mart(name: string): string {
  if (!MARTS.has(name)) throw new Error(`no published mart named ${name}`);
  return `mart_${name}`;
}

let engine: Promise<AsyncDuckDBConnection> | null = null;
const loaded = new Map<string, Promise<void>>();

async function boot(): Promise<AsyncDuckDBConnection> {
  const duckdb = await import("@duckdb/duckdb-wasm/dist/duckdb-browser.mjs");
  const worker = new Worker(`${BASE}/duckdb/duckdb-browser-eh.worker.js`);
  const db = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), worker);
  await db.instantiate(new URL(`${BASE}/duckdb/duckdb-eh.wasm`, window.location.href).href);
  // BIGINT results (counts) arrive as doubles: every count here is far below 2^53, and charts want numbers.
  await db.open({ query: { castBigIntToDouble: true } });
  return db.connect();
}

// The host refuses HEAD, so a mart's length comes from the bundle the pipeline wrote, and failing
// that from a one byte range request, never from HEAD.
async function byteLengthOf(name: string, url: string): Promise<number> {
  const file = FILE_OF.get(name);
  const known = file ? FILES[file] : undefined;
  if (known) return known;
  const probe = await fetch(url, { headers: { Range: "bytes=0-0" } });
  const range = probe.headers.get("Content-Range");
  const total = range?.split("/")[1];
  if (probe.status === 206 && total && Number.isFinite(Number(total))) return Number(total);
  if (probe.status === 200) return (await probe.arrayBuffer()).byteLength;
  throw new Error(`cannot size ${url}: ${probe.status}`);
}

/** A mart as an Arrow IPC stream, read over byte ranges. Runs while the engine is still starting. */
async function decode(name: string): Promise<Uint8Array> {
  const [{ asyncBufferFromUrl, parquetMetadataAsync, parquetReadObjects }, { decompress }, arrow] = await Promise.all([
    import("hyparquet"),
    import("fzstd"),
    import("apache-arrow"),
  ]);
  const url = new URL(martPath(name), window.location.href).href;
  // hyparquet learns a file's length with a HEAD request unless told; GitHub Pages answers HEAD
  // with a 503, so the length comes from the bundle the pipeline wrote, or from a one byte range.
  const file = await asyncBufferFromUrl({ url, byteLength: await byteLengthOf(name, url) });
  const metadata = await parquetMetadataAsync(file);
  const rows = await parquetReadObjects({
    file,
    metadata,
    compressors: { ZSTD: (input: Uint8Array, length: number) => decompress(input, new Uint8Array(length)) },
  });
  const orNull = <T>(v: unknown, cast: (x: unknown) => T): T | null => (v === null || v === undefined ? null : cast(v));
  const columns: Record<string, InstanceType<typeof arrow.Vector>> = {};
  for (const leaf of metadata.schema.slice(1)) {
    const values = rows.map((r) => r[leaf.name]);
    // A column the pipeline wrote with no values at all (a null type) is left out rather than guessed.
    if (leaf.logical_type?.type === "NULL") continue;
    const logical = leaf.logical_type?.type;
    if (logical === "DATE" || leaf.converted_type === "DATE")
      columns[leaf.name] = arrow.vectorFromArray(
        values.map((v) => orNull(v, (x) => (x instanceof Date ? x.toISOString().slice(0, 10) : String(x)))),
        new arrow.Utf8(),
      );
    else if (logical === "TIMESTAMP" || leaf.converted_type === "TIMESTAMP_MICROS" || leaf.converted_type === "TIMESTAMP_MILLIS")
      columns[leaf.name] = arrow.vectorFromArray(
        values.map((v) => orNull(v, (x) => (x instanceof Date ? x.toISOString().slice(0, 19).replace("T", " ") : String(x)))),
        new arrow.Utf8(),
      );
    else if (leaf.type === "BOOLEAN")
      columns[leaf.name] = arrow.vectorFromArray(
        values.map((v) => orNull(v, Boolean)),
        new arrow.Bool(),
      );
    else if (leaf.type === "INT32")
      columns[leaf.name] = arrow.vectorFromArray(
        values.map((v) => orNull(v, Number)),
        new arrow.Int32(),
      );
    else if (leaf.type === "INT64" || leaf.type === "FLOAT" || leaf.type === "DOUBLE")
      columns[leaf.name] = arrow.vectorFromArray(
        values.map((v) => orNull(v, Number)),
        new arrow.Float64(),
      );
    else if (leaf.type === "BYTE_ARRAY")
      columns[leaf.name] = arrow.vectorFromArray(
        values.map((v) => orNull(v, String)),
        new arrow.Utf8(),
      );
  }
  return arrow.tableToIPC(new arrow.Table(columns), "stream");
}

function ensure(name: string): Promise<void> {
  if (!MARTS.has(name)) return Promise.reject(new Error(`no published mart named ${name}`));
  let pending = loaded.get(name);
  if (!pending) {
    engine ??= boot();
    const ready = engine;
    pending = decode(name).then(async (bytes) => (await ready).insertArrowFromIPCStream(bytes, { name: `mart_${name}`, create: true }));
    loaded.set(name, pending);
  }
  return pending;
}

export async function query<T extends Row = Row>(sql: string): Promise<T[]> {
  engine ??= boot();
  const names = [...new Set([...sql.matchAll(/\bmart_([a-z_]+)\b/g)].map((m) => m[1] ?? ""))];
  const [conn] = await Promise.all([engine, ...names.map(ensure)]);
  const table = await conn.query(sql);
  const fields = table.schema.fields.map((f) => f.name);
  const rows = table.toArray().map((r) => {
    const json = r.toJSON() as Row;
    const out: Row = {};
    for (const f of fields) {
      const value = json[f];
      out[f] = typeof value === "bigint" ? Number(value) : value;
    }
    return out as T;
  });
  markReady();
  return rows;
}
