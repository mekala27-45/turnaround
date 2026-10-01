import type { Metadata } from "next";

import { ManifestTable } from "@/components/ManifestTable";
import { PageHeader, Pushback, Section } from "@/components/Section";
import { bundle, manifest } from "@/lib/load";
import { REPO } from "@/lib/site";

import { QuarantineByMonth, RecoveryMultiples } from "./DataClient";

export const metadata: Metadata = { title: "The warehouse" };

export default function DataPage() {
  const m = manifest();
  const b = bundle();
  const recovery = m.has("recovery.by_condition") ? m.table("recovery.by_condition") : null;
  const exports: [string, string, string][] = [
    ["The workbook with live formulas", "exports/workbook.xlsx", "Change the year on the summary sheet and every figure moves; LibreOffice recalculates it in the tests against the metric layer."],
    ["The Tableau extracts and view specification", "exports/tableau/workbook_spec.md", "The route by month mart as one CSV per year and the carrier by month mart as one CSV, with the views the companion workbook shows."],
    ["The Power BI model specification", "exports/powerbi/model.md", "Tables, relationships and DAX measures generated from the metric layer."],
    ["The CSV bundle and its dictionary", "exports/csv/dictionary.csv", "Every chapter's table as CSV, with every column named."],
  ];
  return (
    <>
      <PageHeader kicker="The warehouse" question="Where every number comes from, and how it was checked.">
        <p>
          Every scheduled flight of the reporting carriers from {m.vOr("data.first_month", "the first month")} to {m.vOr("data.last_month", "the latest")}{" "}
          went through named quarantine rules (flagged and counted, nothing deleted) into a dbt warehouse of {m.vOr("warehouse.models", "")} models and{" "}
          {m.vOr("warehouse.tests", "")} tests. The metric layer defines each metric once over the flights and once over the shipped mart and
          compares them at {m.vOr("metrics.grains", "")} grains.
        </p>
      </PageHeader>
      <Section title="The quarantine report" id="quarantine">
        <ManifestTable m={m} tableKey="quarantine.by_rule" testId="quarantine-table" />
        <div className="mt-5">
          <QuarantineByMonth />
        </div>
      </Section>
      <Section title="The metric layer, reconciled" id="metrics" intro={<p>{m.vOr("metrics.cells", "")} cells compared across {m.vOr("metrics.grains", "")} grains, {m.vOr("metrics.disagreements", "")} disagreements.</p>}>
        <ManifestTable m={m} tableKey="metrics.definitions" testId="metrics-table" />
      </Section>
      <Section title="The recovery study" id="recovery" intro={<p>Every estimator, run on simulated networks where the truth is known, {m.vOr("recovery.conditions", "")} conditions with {m.vOr("recovery.seeds", "")} seeds each, before it touched a real flight.</p>}>
        {recovery ? <RecoveryMultiples columns={recovery.columns} formats={recovery.formats} rows={recovery.rows} source={m.prov("recovery.by_condition")} /> : null}
      </Section>
      <Section title="The data dictionary" id="dictionary">
        <div className="card p-4 overflow-x-auto" data-testid="dictionary">
          <table className="data-table">
            <thead>
              <tr>
                <th>Published file</th>
                <th className="num">Bytes</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(b.files).map(([file, bytes]) => (
                <tr key={file}>
                  <td className="mono">{file}</td>
                  <td className="num">{bytes.toLocaleString("en-US")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-ink2">
            Every column of every exported table is named in <a className="underline" href={`${REPO}/blob/main/exports/csv/dictionary.csv`}>the CSV bundle's dictionary</a>, and every
            definition is in <a className="underline" href={`${REPO}/blob/main/docs/definitions.md`}>docs/definitions.md</a>.
          </p>
        </div>
      </Section>
      <Section title="Exports and the BI companions" id="exports">
        <ul className="space-y-3" data-testid="exports">
          {exports.map(([label, path, note]) => (
            <li key={path} className="card p-4">
              <a className="font-semibold underline" href={`${REPO}/blob/main/${path}`}>
                {label}
              </a>
              <p className="text-sm text-ink2 mt-1">{note}</p>
            </li>
          ))}
        </ul>
      </Section>
      <Pushback>
        <p>
          A warehouse can agree with itself and still be wrong about the world. The reconcile proves that two expressions over two grains give the
          same number; it cannot prove the carriers reported their times correctly. That is why the quarantine rules flag impossible times, causes
          that do not add up and duplicate rows rather than fixing them, and why every flagged row is counted here by carrier and month.
        </p>
      </Pushback>
    </>
  );
}
