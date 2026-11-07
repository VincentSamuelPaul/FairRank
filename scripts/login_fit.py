"""login-fit spec: the login page must fit every viewport (docs/DESIGN.md 10.1).

For each size, loads /login and asserts: no horizontal scroll (all sizes); and, for desktop and tablet sizes, that the card, the submit button,
the demo segmented control and the in-card note are fully inside the viewport (no vertical scroll needed either). The landscape phone
(844x390) and phones may scroll vertically. Saves a screenshot per size to docs/screens/round5/login/.

    scripts/login-fit.sh
"""
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("FAIRRANK_URL", "http://localhost:5173")
OUT = pathlib.Path(os.environ.get("OUT", "docs/screens/round5/login"))
# (w, h, must_fit_vertically)
SIZES = [
    (1920, 1080, True), (1536, 864, True), (1440, 900, True), (1366, 768, True), (1280, 720, True), (1024, 768, True),
    (820, 1180, True), (768, 1024, True), (844, 390, False), (430, 932, False), (390, 844, False), (375, 667, False), (360, 640, False),
]
BOX_JS = """() => {
  const q = (s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, left: r.left, right: r.right}; };
  const submit = [...document.querySelectorAll('form button[type=submit]')][0]?.getBoundingClientRect();
  const note = [...document.querySelectorAll('form p')].find(p => p.textContent.includes('Every CV view is logged'))?.getBoundingClientRect();
  const seg = document.querySelector('[aria-labelledby=demo-label]')?.getBoundingClientRect();
  const box = (r) => r && {top: r.top, bottom: r.bottom, left: r.left, right: r.right};
  return {card: q('.login-card'), submit: box(submit), seg: box(seg), note: box(note), sw: document.documentElement.scrollWidth, sh: document.documentElement.scrollHeight};
}"""


def inside(b, w, h):
    return b is not None and b["top"] >= -0.5 and b["left"] >= -0.5 and b["bottom"] <= h + 0.5 and b["right"] <= w + 0.5


def main() -> int:
    fails = 0
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h, fit in SIZES:
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, reduced_motion="reduce", is_mobile=w < 500, has_touch=w < 500)
            page = ctx.new_page()
            page.goto(f"{BASE}/login")
            page.wait_for_load_state("networkidle")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(500)
            m = page.evaluate(BOX_JS)
            problems = []
            if m["sw"] > w:
                problems.append(f"horizontal scroll (scrollWidth {m['sw']} > {w})")
            if fit:
                for name in ("card", "submit", "seg", "note"):
                    if not inside(m[name], w, h):
                        problems.append(f"{name} not inside the viewport: {m[name]}")
                if m["sh"] > h:
                    problems.append(f"page scrolls vertically (scrollHeight {m['sh']} > {h})")
            page.screenshot(path=str(OUT / f"login-{w}x{h}.png"))
            print(("FAIL" if problems else "PASS"), f"{w}x{h}", "; ".join(problems))
            fails += bool(problems)
            ctx.close()
        browser.close()
    print(f"\n{len(SIZES) - fails} passed, {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
