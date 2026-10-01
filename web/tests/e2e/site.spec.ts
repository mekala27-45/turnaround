import { expect, test } from "@playwright/test";

import { BASE, bundle, collectErrors, manifest, open, openAsleep, ready, recorded, ROUTES, story } from "./site";

for (const route of ROUTES) {
  test(`${route} loads with the statement, a pushback paragraph and no console errors`, async ({ page }) => {
    const errors = collectErrors(page);
    await open(page, route);
    await ready(page);
    await expect(page.getByTestId("footer")).toContainText(bundle.statement);
    await expect(page.getByText("What the ops director would push back on").first()).toBeVisible();
    expect(errors).toEqual([]);
  });
}

test("the story's first chapter chart advances through its states as the reader scrolls", async ({ page }) => {
  await open(page, "/");
  await ready(page);
  const first = story.chapters[0];
  if (!first) throw new Error("the story has no chapters");
  const sticky = page.getByTestId(`sticky-${first.id}`);
  await expect(sticky).toHaveAttribute("data-state", first.steps[0]?.state ?? "");
  const last = first.steps[first.steps.length - 1];
  const step = page.getByTestId(`chapter-${first.id}`).locator(`.story-step[data-state="${last?.state}"]`);
  await step.scrollIntoViewIfNeeded();
  await page.mouse.wheel(0, 200);
  await expect(sticky).toHaveAttribute("data-state", last?.state ?? "", { timeout: 15_000 });
  await expect(sticky.getByTestId("chart-message")).toHaveText(manifest.figures[`chart.${first.chart}`]?.title ?? "");
});

test("the method note expands inline with the plan hash, and the SQL toggle shows the SQL", async ({ page }) => {
  await open(page, "/");
  await ready(page);
  const chapter = page.getByTestId(`chapter-${story.chapters[0]?.id}`);
  const note = chapter.getByTestId("method-note");
  await note.locator("summary").click();
  await expect(note).toContainText(String(manifest.values["plan.1.hash"]?.value));
  await chapter.getByTestId("sql-toggle").click();
  await expect(chapter.getByTestId("sql")).toContainText("select");
  await chapter.getByTestId("table-toggle").click();
  await expect(chapter.getByRole("table")).toBeVisible();
});

test("the story prints its reading time and ends with the corrections section", async ({ page }) => {
  await open(page, "/");
  await expect(page.getByTestId("preamble")).toContainText("minutes to read");
  await expect(page.getByTestId("coda")).toContainText("Corrections");
  for (const c of story.chapters) await expect(page.getByTestId(`chapter-${c.id}`).getByTestId("chapter-pushback")).toContainText("push back");
});

test("a selection in the explorer changes every chart", async ({ page }) => {
  await open(page, "/explore/");
  await ready(page);
  const flights = page.getByTestId("selection-flights");
  await expect(flights).toContainText("flights flown");
  const before = await flights.textContent();
  const ontime = page.getByTestId("explore-ontime").getByTestId("chart-message");
  const ontimeBefore = await ontime.textContent();
  const carrier = page.getByTestId("pick-carrier");
  const options = await carrier.locator("option").allTextContents();
  await carrier.selectOption({ label: options[1] ?? "" });
  await expect(flights).not.toHaveText(before ?? "");
  await expect(ontime).not.toHaveText(ontimeBefore ?? "");
  const causes = page.getByTestId("explore-causes").getByTestId("chart-message");
  await expect(causes).toContainText("largest reported cause");
});

test("the SQL box runs a query over the marts in the browser", async ({ page }) => {
  await open(page, "/explore/");
  await ready(page);
  await page.getByTestId("sql-run").click();
  await expect(page.getByTestId("sql-result").getByRole("table")).toBeVisible({ timeout: 30_000 });
});

test("the ranking page draws the slope chart with every carrier named at both ends", async ({ page }) => {
  await open(page, "/rank/");
  const rows = manifest.tables["ch5.ranking"]?.rows ?? [];
  const slope = page.getByTestId("chart-ranking");
  await expect(slope.locator("[data-carrier]")).toHaveCount(rows.length);
  await expect(page.getByTestId("rank-table").getByRole("table")).toBeVisible();
});

test("the rotation timeline draws the aircraft's day and marks the leg that inherited the most", async ({ page }) => {
  await open(page, "/rotations/");
  await ready(page);
  const timeline = page.getByTestId("timeline");
  await expect(timeline.locator("[data-leg]").first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("rotation-timeline").getByTestId("chart-message")).toContainText(/inherited|leg by leg/);
});

test("the planner saves a check through the API once the mock wakes, and shows its id", async ({ page }) => {
  await open(page, "/planner/");
  await expect(page.getByTestId("probability")).toBeVisible({ timeout: 45_000 });
  await page.getByTestId("token").fill("test-token");
  await page.getByTestId("save").click();
  const hub = recorded.connections[0]?.connection ?? "";
  const id = recorded.responses[`check_${hub}`]?.body.check_id ?? "";
  await expect(page.getByTestId("check-id")).toContainText(id);
  await expect(page.getByTestId("check-id")).toContainText("(live)");
});

test("with the API asleep the planner answers from the recorded session and says so", async ({ page }) => {
  await openAsleep(page, "/planner/");
  await expect(page.getByTestId("recorded-label")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByTestId("probability")).toContainText("Recorded session");
  await page.getByTestId("save").click();
  await expect(page.getByTestId("check-id")).toContainText("recorded session");
});

test("the test server refuses HEAD, as the host does", async ({ request }) => {
  const response = await request.fetch(`${BASE}/`, { method: "HEAD" });
  expect(response.status()).toBe(405);
});

test("the data page shows the quarantine report, the reconciliation and the recovery small multiples", async ({ page }) => {
  await open(page, "/data/");
  await ready(page);
  await expect(page.getByTestId("quarantine-table").getByRole("table")).toBeVisible();
  await expect(page.getByTestId("metrics-table").getByRole("table")).toBeVisible();
  await expect(page.getByTestId("recovery-multiples").locator("figure").first()).toBeVisible();
});

test("the briefing has a print button and a section per chapter", async ({ page }) => {
  await open(page, "/report/");
  await expect(page.getByTestId("print")).toBeVisible();
  await expect(page.getByTestId("briefing").locator("section")).toHaveCount(story.chapters.length + 2);
});
