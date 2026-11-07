"""Screenshot the app at desktop and phone sizes into docs/screens/ (for design review against docs/DESIGN.md).

Run against the dev server (docker compose up). Uses the official Playwright image so nothing is installed on the host:

    scripts/screenshots.sh components

Screens: login, components, ranked, candidate, portal, portal-candidate (default: login). Pass `all` for everything.
Demo accounts are synthetic (see deployment.md); the password can be overridden with FAIRRANK_DEMO_PASSWORD.
"""
import os
import pathlib
import sys

from playwright.sync_api import Page, sync_playwright

BASE = os.environ.get("FAIRRANK_URL", "http://localhost:5173")
PASSWORD = os.environ.get("FAIRRANK_DEMO_PASSWORD", "FairRank-demo-1")
OUT = pathlib.Path(os.environ.get("OUT", "docs/screens"))
# CLIP="x,y,w,h" (CSS px) crops a full-page capture, for reviewing details. Writes <screen>-<view>-clip.png.
CLIP = os.environ.get("CLIP")
VIEWS = {"desktop": {"width": 1440, "height": 900}, "phone": {"width": 375, "height": 812}}
RECRUITER, CLIENT = "recruiter1@companya.example", "manager@northwind.example"


def settle(page: Page) -> None:
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(400)


def sign_in(page: Page, email: str) -> None:
    page.goto(f"{BASE}/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.wait_for_url(lambda u: "/login" not in u)
    settle(page)


def open_ranked(page: Page) -> None:
    page.get_by_role("link", name="Senior Java Developer").first.click()
    page.wait_for_selector("ul > li")
    settle(page)


def run(name: str, view: str, page: Page) -> None:
    if name == "login":
        page.goto(f"{BASE}/login")
    elif name == "components":
        page.goto(f"{BASE}/dev/components")
    elif name == "ranked":
        sign_in(page, RECRUITER)
        open_ranked(page)
    elif name == "candidate":
        sign_in(page, RECRUITER)
        open_ranked(page)
        page.locator("ul > li a[href^='/candidates/']").first.click()
        page.wait_for_selector("pre", state="attached")
    elif name == "portal":
        sign_in(page, CLIENT)
    elif name == "portal-candidate":
        sign_in(page, CLIENT)
        page.locator("a[href^='/portal/candidates/']").first.click()
        page.wait_for_selector("pre", state="attached")
    else:
        raise SystemExit(f"unknown screen: {name}")
    settle(page)
    full = name != "login" or view == "phone"
    dims = page.evaluate("[document.documentElement.scrollWidth, innerWidth, document.documentElement.scrollHeight, innerHeight]")
    print(f"{name}-{view}: scrollW={dims[0]} viewW={dims[1]} scrollH={dims[2]} viewH={dims[3]}" + ("  HORIZONTAL SCROLL" if dims[0] > dims[1] else ""))
    if dims[0] > dims[1]:
        wide = page.evaluate("""[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 0.5).slice(0, 6).map(e => e.tagName + '.' + String(e.className).slice(0, 80))""")
        print("  overflowing:", wide)
    OUT.mkdir(parents=True, exist_ok=True)
    if CLIP:
        x, y, w, h = (float(v) for v in CLIP.split(","))
        path = OUT / f"{name}-{view}-clip.png"
        page.screenshot(path=str(path), full_page=True, clip={"x": x, "y": y, "width": w, "height": h})
    else:
        path = OUT / f"{name}-{view}.png"
        page.screenshot(path=str(path), full_page=full)
    print("wrote", path)


def login_animation(browser) -> None:
    """Normal-motion frames of the login demo choreography (the other captures use reduced motion, i.e. the final state)."""
    for view, size in VIEWS.items():
        ctx = browser.new_context(viewport=size, device_scale_factor=2, is_mobile=view == "phone", has_touch=view == "phone")
        page = ctx.new_page()
        page.goto(f"{BASE}/login")
        for ms, label in ((450, "t0450"), (1500, "t1500"), (2700, "t2700"), (7600, "t7600")):
            page.wait_for_timeout(ms - (0 if label == "t0450" else {"t1500": 450, "t2700": 1500, "t7600": 2700}[label]))
            OUT.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(OUT / f"login-anim-{view}-{label}.png"))
            print("wrote", OUT / f"login-anim-{view}-{label}.png")
        ctx.close()


def main(names: list[str]) -> None:
    if names == ["all"]:
        names = ["login", "components", "ranked", "candidate", "portal", "portal-candidate"]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        if names == ["login-anim"]:
            login_animation(browser)
            browser.close()
            return
        for name in names or ["login"]:
            for view, size in VIEWS.items():
                ctx = browser.new_context(
                    viewport=size, device_scale_factor=2, reduced_motion="reduce",
                    is_mobile=view == "phone", has_touch=view == "phone",
                )
                page = ctx.new_page()
                page.on("pageerror", lambda e: print("PAGE ERROR:", str(e)[:300]))
                page.on("console", lambda m: print("console.error:", m.text[:300]) if m.type == "error" else None)
                run(name, view, page)
                ctx.close()
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
