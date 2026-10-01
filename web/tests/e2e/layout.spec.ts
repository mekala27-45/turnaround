import { expect, test } from "@playwright/test";

import { open, ready, ROUTES } from "./site";

// At phone width no page may scroll sideways, and the story stacks each chapter's chart above its text.
for (const route of ROUTES) {
  test(`${route} has no horizontal page scroll at phone width`, async ({ page }) => {
    await open(page, route);
    await ready(page);
    await page.waitForTimeout(500);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}

test("on a phone the story stacks: every chapter shows its whole chart", async ({ page }) => {
  await open(page, "/");
  await ready(page);
  const sticky = page.locator("[data-testid^='sticky-']").first();
  await expect(sticky).toHaveAttribute("data-state", "all");
});
