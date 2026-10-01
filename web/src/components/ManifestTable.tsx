import { DataTable } from "@/components/charts/Figure";
import type { ManifestView } from "@/lib/manifest";

/** A manifest table with its provenance line under it. */
export function ManifestTable({ m, tableKey, caption, testId }: { m: ManifestView; tableKey: string; caption?: string; testId?: string }) {
  if (!m.has(tableKey)) return <p className="text-sm text-ink2">This table has not been computed yet.</p>;
  const t = m.table(tableKey);
  return (
    <div className="card p-4" data-testid={testId}>
      <DataTable table={{ columns: t.columns, formats: t.formats, rows: t.rows }} caption={caption} />
      <p className="mt-2 text-xs text-ink2">{m.prov(tableKey)}</p>
    </div>
  );
}
