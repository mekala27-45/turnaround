"""The demo recording: the story's opening, one chapter's sticky chart advancing through its states as
the text scrolls, the slope chart of the fair ranking, an aircraft's day on the rotation timeline,
and a check saved through the planner with its id. About fifteen seconds, tight crop, written to
docs/demo.gif from frames captured with Playwright against the test server, which serves the build
made with `npm run build:e2e`, so the check is saved against the mock API and the recording leaves
no row in the live log.

    npm --prefix web run build:e2e && node web/scripts/serve.mjs &
    uv run python scripts/build_demo_gif.py --base http://127.0.0.1:4173/turnaround
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "demo.gif"
WIDTH, HEIGHT = 1180, 760
READY = "document.documentElement.getAttribute('data-ready') === 'true'"


def story_chapter(name: str | None) -> dict[str, Any]:
    story = json.loads((ROOT / "web" / "public" / "data" / "story.json").read_text(encoding="utf-8"))
    chapters: list[dict[str, Any]] = story["chapters"]
    if name:
        for chapter in chapters:
            if chapter["id"] == name:
                return chapter
    # The chapter with the most chart states shows the scroll mechanics best.
    return max(chapters, key=lambda c: len(c.get("steps", [])))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:4173/turnaround")
    parser.add_argument("--chapter", default=None, help="the story chapter to scroll through")
    parser.add_argument("--chromium", default="/opt/pw-browsers/chromium")
    args = parser.parse_args()
    from PIL import Image
    from playwright.sync_api import sync_playwright

    chapter = story_chapter(args.chapter)
    frames: list[Image.Image] = []
    durations: list[int] = []

    def shot(page: Any, hold_ms: int) -> None:
        png = page.screenshot(clip={"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT})
        frames.append(Image.open(io.BytesIO(png)).convert("RGB").resize((885, 570)))
        durations.append(hold_ms)

    def open_route(page: Any, route: str) -> None:
        page.goto(f"{args.base}{route}")
        page.wait_for_function(READY, timeout=60_000)
        page.wait_for_timeout(500)

    with sync_playwright() as p:
        launch = {"executable_path": args.chromium} if Path(args.chromium).exists() else {}
        browser = p.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": WIDTH, "height": 900}, color_scheme="light")
        open_route(page, "/")
        shot(page, 1600)
        for step in chapter.get("steps", []):
            locator = page.get_by_test_id(f"chapter-{chapter['id']}").locator(
                f'.story-step[data-state="{step["state"]}"]'
            )
            locator.scroll_into_view_if_needed()
            page.mouse.wheel(0, 120)
            page.wait_for_timeout(700)
            shot(page, 1300)
        open_route(page, "/rank/")
        page.get_by_test_id("chart-ranking").scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        shot(page, 1800)
        open_route(page, "/rotations/")
        page.get_by_test_id("timeline").locator("[data-leg]").first.wait_for(timeout=30_000)
        page.get_by_test_id("rotation-timeline").scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        shot(page, 1800)
        open_route(page, "/planner/")
        page.get_by_test_id("probability").wait_for(timeout=45_000)
        page.wait_for_timeout(300)
        shot(page, 1300)
        page.get_by_test_id("token").fill("demo-token")
        page.get_by_test_id("save").click()
        page.get_by_test_id("check-id").wait_for(timeout=45_000)
        page.get_by_test_id("check-id").evaluate("el => el.scrollIntoView({block: 'center'})")
        page.wait_for_timeout(400)
        shot(page, 2000)
        browser.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(frames)} frames, {sum(durations) / 1000:.1f} seconds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
