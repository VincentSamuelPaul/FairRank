"""Candidate screening page screenshots (viewport shots, deviceScaleFactor 2) into docs/screens/round5/candidate/.

States per size: default, expanded (one criterion open), blind (Blind view on), scanned (needs-manual-review CV), loading (request held open).
On a phone it also captures the CV tab. Run: scripts/candidate-shots.sh
"""
import os
import pathlib
import re

from playwright.sync_api import Page, sync_playwright

BASE = os.environ.get("FAIRRANK_URL", "http://localhost:5173")
PASSWORD = os.environ.get("FAIRRANK_DEMO_PASSWORD", "FairRank-demo-1")
OUT = pathlib.Path(os.environ.get("OUT", "docs/screens/round5/candidate"))
RECRUITER = "recruiter1@companya.example"
SIZES = {"1440x900": (1440, 900), "1280x720": (1280, 720), "768x1024": (768, 1024), "375x812": (375, 812)}


def settle(page: Page, ms: int = 500) -> None:
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(ms)


def open_candidate(page: Page, req: str, scanned: bool = False) -> None:
    page.goto(f"{BASE}/requisitions")
    page.wait_for_selector("ul > li a[href^='/requisitions/']")
    page.get_by_role("link", name=req).first.click()
    page.wait_for_selector("ul > li")
    settle(page)
    if scanned:
        row = page.locator("ul > li", has_text="Needs review").first
        row.locator("a[href^='/candidates/']").first.click()
    else:
        page.locator("ul > li a[href^='/candidates/']").first.click()
    page.wait_for_selector("h1")
    settle(page)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        boot = browser.new_context(viewport={"width": 1440, "height": 900})
        bp = boot.new_page()
        bp.goto(f"{BASE}/login")
        bp.get_by_label("Email").fill(RECRUITER)
        bp.get_by_label("Password", exact=True).fill(PASSWORD)
        bp.get_by_role("button", name="Sign in", exact=True).click()
        bp.wait_for_url(lambda u: "/login" not in u)
        state = boot.storage_state()
        boot.close()
        for label, (w, h) in SIZES.items():
            phone = w < 500
            def ctx():
                c = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, reduced_motion="reduce", is_mobile=phone, has_touch=phone, storage_state=state)
                pg = c.new_page()
                pg.on("pageerror", lambda e: print("PAGE ERROR:", str(e)[:200]))
                return c, pg
            def shot(pg: Page, name: str) -> None:
                pg.screenshot(path=str(OUT / f"candidate-{label}-{name}.png"))
                print("wrote", OUT / f"candidate-{label}-{name}.png", "| page scrolls:", pg.evaluate("document.documentElement.scrollHeight > innerHeight + 1"))
            c, pg = ctx()
            open_candidate(pg, "Senior Java Developer")
            shot(pg, "default")
            first = pg.locator("li[id^=crit-] button").first
            first.click()
            pg.wait_for_timeout(500)
            shot(pg, "expanded")
            if phone:
                pg.get_by_role("tab", name="CV").click()
                pg.wait_for_timeout(400)
                shot(pg, "cv")
                pg.get_by_role("button", name="Blind view").click()
            else:
                pg.get_by_role("button", name="Blind view").click()
            pg.wait_for_timeout(300)
            shot(pg, "blind")
            c.close()
            c, pg = ctx()
            open_candidate(pg, "KYC Analyst", scanned=True)
            if phone:
                pg.get_by_role("tab", name="CV").click()
                pg.wait_for_timeout(300)
            shot(pg, "scanned")
            c.close()
            c, pg = ctx()
            pg.route(re.compile(r".*/api/candidates/[0-9a-f-]{36}/$"), lambda route: None)
            pg.goto(f"{BASE}/requisitions")
            pg.wait_for_selector("ul > li a[href^='/requisitions/']")
            pg.get_by_role("link", name="Senior Java Developer").first.click()
            pg.wait_for_selector("ul > li")
            pg.locator("ul > li a[href^='/candidates/']").first.click()
            pg.wait_for_selector("[aria-busy=true]")
            pg.wait_for_timeout(400)
            shot(pg, "loading")
            c.close()
        browser.close()


if __name__ == "__main__":
    main()
