"""Rendered-UI checks for docs/DESIGN.md section 6. Prints PASS/FAIL with evidence; exit 1 on any FAIL.

    scripts/qa.sh            (needs `docker compose up`; demo accounts are synthetic, see deployment.md)
"""
import os
import re
import sys
import zlib

from playwright.sync_api import Page, sync_playwright

BASE = os.environ.get("FAIRRANK_URL", "http://localhost:5173")
PASSWORD = os.environ.get("FAIRRANK_DEMO_PASSWORD", "FairRank-demo-1")
RECRUITER, CLIENT = "recruiter1@companya.example", "manager@northwind.example"
SIZES = {"375": (375, 812), "768": (768, 1024), "1440": (1440, 900)}
results: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, evidence: str = "") -> None:
    results.append((ok, name, evidence))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{evidence}]" if evidence else ""))


def settle(page: Page) -> None:
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(300)


def sign_in(page: Page, email: str) -> None:
    page.goto(f"{BASE}/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.wait_for_url(lambda u: "/login" not in u)
    settle(page)


def open_ranked(page: Page) -> str:
    page.goto(f"{BASE}/requisitions")
    settle(page)
    page.get_by_role("link", name="Senior Java Developer").first.click()
    page.wait_for_selector("ul > li")
    settle(page)
    return page.url


# ---- contrast from real pixels -------------------------------------------------
def pixel(page: Page, x: float, y: float) -> tuple[int, int, int]:
    png = page.screenshot(clip={"x": x, "y": y, "width": 1, "height": 1}, type="png")
    i, idat, ctype = 8, b"", 2
    while i < len(png):
        n = int.from_bytes(png[i : i + 4], "big")
        kind = png[i + 4 : i + 8]
        if kind == b"IHDR":
            ctype = png[i + 8 + 9]
        if kind == b"IDAT":
            idat += png[i + 8 : i + 8 + n]
        i += 12 + n
    raw = zlib.decompress(idat)  # one row, one pixel: the filter byte is irrelevant for the first row
    return raw[1], raw[2], raw[3]


def lum(c) -> float:
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b) -> float:
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


TEXT_JS = """() => {
  const out = [], seen = new Set();
  for (const el of document.querySelectorAll('body *')) {
    const own = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).map(n => n.textContent.trim()).join(' ');
    if (!own) continue;
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0 || r.width < 2 || r.height < 2) continue;
    if (el.closest('[aria-hidden="true"]') || el.closest('[disabled]')) continue;
    const m = cs.color.match(/[\\d.]+/g).map(Number);
    const key = cs.color + cs.fontSize + Math.round(r.top / 40) + el.className;
    if (seen.has(key)) continue; seen.add(key);
    const id = out.length; el.setAttribute('data-qa', id);
    out.push({id, text: own.slice(0, 40), color: m, size: parseFloat(cs.fontSize), weight: +cs.fontWeight, top: r.top, left: r.left, h: r.height});
  }
  return out;
}"""


def contrast_page(page: Page, label: str, limit: int = 70) -> None:
    items = page.evaluate(TEXT_JS)[:limit]
    worst, bad = 99.0, []
    for it in items:
        # scroll this exact element (tagged data-qa) to the middle of the viewport, then read its box again
        box = page.evaluate(
            "(id) => { const e = document.querySelector(`[data-qa='${id}']`); if (!e) return null; e.scrollIntoView({block: 'center'}); const r = e.getBoundingClientRect(); return {top: r.top, left: r.left, h: r.height}; }",
            it["id"],
        )
        if not box:
            continue
        it = {**it, **box}
        # Sample a few points on the element's box and just outside it, and keep the one that is background:
        # glyph ink gives a low ratio and a point outside a pill gives the wrong surface, so the best ratio is the real one.
        vh = page.viewport_size["height"]
        mid = it["top"] + it["h"] / 2
        pts = [(it["left"] - 1, mid), (it["left"] + 3, mid), (it["left"] + 2, it["top"] + 1), (it["left"] + 2, it["top"] + it["h"] - 2)]
        pts = [(max(x, 0), y_) for x, y_ in pts if 0 <= y_ < vh - 1]
        if not pts:
            continue
        a = it["color"][3] if len(it["color"]) > 3 else 1.0
        best = 0.0
        for x_, y_ in pts:
            try:
                bg = pixel(page, x_, y_)
            except Exception:
                continue
            fg = tuple(it["color"][i] * a + bg[i] * (1 - a) for i in range(3))
            best = max(best, ratio(fg, bg))
        r = best
        large = it["size"] >= 24 or (it["size"] >= 18.66 and it["weight"] >= 700)
        need = 3.0 if large else 4.5
        worst = min(worst, r / need * 4.5)
        if r < need:
            bad.append(f"{it['text']!r} {r:.2f}<{need}")
    page.evaluate("window.scrollTo(0, 0)")
    check(not bad, f"contrast >= 4.5 on rendered pixels: {label}", f"{len(items)} text runs" + (f"; {'; '.join(bad[:5])}" if bad else ""))


# ---- helpers for the other checks ------------------------------------------------
def nameless(page: Page) -> list[str]:
    return page.evaluate("""() => [...document.querySelectorAll('button, a[href], [role=button], [role=tab]')].filter(e => {
      const txt = (e.innerText || '').trim();
      return !txt && !e.getAttribute('aria-label') && !e.getAttribute('aria-labelledby') && !e.getAttribute('title');
    }).map(e => e.outerHTML.slice(0, 90))""")


def not_tabular(page: Page) -> list[str]:
    return page.evaluate("""() => [...document.querySelectorAll('body *')].filter(e => {
      const own = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ');
      if (!/^[#+]?\\d[\\d.,%]*$|\\b\\d+(\\.\\d+)? ?(yrs|days|CVs|min)\\b/.test(own)) return false;
      if (e.closest('[aria-hidden="true"]') || e.closest('mark')) return false;
      const v = getComputedStyle(e).fontVariantNumeric;
      return !v.includes('tabular-nums');
    }).map(e => e.tagName + ':' + (e.innerText || '').trim().slice(0, 24)).slice(0, 8)""")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()

        sessions: dict[str, dict] = {}

        def ctx(w: int, h: int, email: str | None = None):
            """New browser context; signed-in contexts reuse one login per role (the API throttles logins to 10/min)."""
            if email and email not in sessions:
                boot = browser.new_context(viewport={"width": 1440, "height": 900})
                sign_in(boot.new_page(), email)
                sessions[email] = boot.storage_state()
                boot.close()
            c = browser.new_context(
                viewport={"width": w, "height": h}, reduced_motion="reduce", is_mobile=w < 500, has_touch=w < 500,
                storage_state=sessions.get(email) if email else None,
            )
            return c, c.new_page()

        # 1. widths at 375 / 768 / 1440, no horizontal scroll, on every screen
        for label, (w, h) in SIZES.items():
            for who, email, steps in [
                ("login", None, lambda pg: pg.goto(f"{BASE}/login")),
                ("ranked", RECRUITER, lambda pg: open_ranked(pg)),
                ("candidate", RECRUITER, lambda pg: (open_ranked(pg), pg.locator("ul > li a[href^='/candidates/']").first.click(), pg.wait_for_selector("pre", state="attached"))),
                ("portal", CLIENT, lambda pg: pg.goto(f"{BASE}/portal")),
            ]:
                c, pg = ctx(w, h, email)
                steps(pg)
                settle(pg)
                sw = pg.evaluate("document.documentElement.scrollWidth")
                check(sw <= w, f"no horizontal scroll: {who} @ {label}px", f"scrollWidth={sw}")
                c.close()

        # 2. states (loading skeleton, empty, error) on the ranked list
        c, pg = ctx(1440, 900, RECRUITER)
        pg.goto(f"{BASE}/requisitions")
        settle(pg)
        url = open_ranked(pg)
        pg.route("**/candidates/?**", lambda r: (pg.wait_for_timeout(2500), r.continue_()))
        pg.route("**/candidates/", lambda r: (pg.wait_for_timeout(2500), r.continue_()))
        pg.goto(url, wait_until="commit")
        try:
            pg.get_by_label("Loading").first.wait_for(timeout=2500)
            check(True, "loading state (skeleton) is shown on the ranked list")
        except Exception:
            check(False, "loading state (skeleton) is shown on the ranked list")
        pg.unroute_all()
        pg.goto(url)
        pg.wait_for_selector("ul > li")
        pg.get_by_label("Search candidates").fill("zzzzqqqq")
        try:
            pg.get_by_text("No CVs match these filters").wait_for(timeout=4000)
            check(True, "empty state is shown (no search match), with a Clear filters action")
        except Exception:
            check(False, "empty state is shown (no search match)")
        pg.route("**/api/requisitions/*/candidates/**", lambda r: r.abort())
        pg.goto(url)
        try:
            pg.get_by_text("We couldn’t load this").wait_for(timeout=8000)
            check(pg.get_by_role("button", name="Try again").is_visible(), "error state is shown with a Try again button")
        except Exception:
            check(False, "error state is shown with a Try again button")
        pg.unroute_all()
        c.close()

        # 3. keyboard, dialogs, aria names, dead buttons: login
        c, pg = ctx(1440, 900)
        pg.goto(f"{BASE}/login")
        settle(pg)
        order = []
        for _ in range(9):
            pg.keyboard.press("Tab")
            order.append(pg.evaluate("(() => { const e = document.activeElement; return (e.getAttribute('aria-label') || e.innerText || e.id || e.tagName).trim().slice(0, 22); })()"))
        ring = pg.evaluate("(() => { const e = document.activeElement; const s = getComputedStyle(e); return s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0; })()")
        expected = ["How we screen", "Privacy", "Demo accounts", "email", "password", "Sign in"]
        check(order[:6] == expected, "keyboard: tab order follows the visual order (nav, demo, email, password, sign in)", " > ".join(order[:6]))
        check(bool(ring), "keyboard: focused control has a visible focus ring")
        pg.get_by_role("button", name="How we screen").click()
        check(pg.get_by_role("dialog").is_visible(), "dead-button check: How we screen opens a dialog")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(250)
        check(not pg.get_by_role("dialog").is_visible(), "Esc closes the dialog")
        pg.get_by_role("button", name="Privacy").click()
        check(pg.get_by_role("dialog").is_visible(), "dead-button check: Privacy opens a dialog")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(250)
        pg.get_by_role("button", name="Demo accounts").click()
        pg.get_by_role("button", name="Recruiter").click()
        filled = pg.get_by_label("Email").input_value() == RECRUITER and pg.get_by_label("Password").input_value() != ""
        check(filled, "dead-button check: Demo accounts fills the sign-in form")
        pg.get_by_role("button", name="Sign in", exact=True).click()
        pg.wait_for_url(lambda u: "/login" not in u)
        check("/requisitions" in pg.url, "dead-button check: Sign in lands the recruiter on Requisitions", pg.url.replace(BASE, ""))
        c.close()

        # 4. ranked: chips, open CV, submit tooltip; candidate; portal sheets
        c, pg = ctx(1440, 900, RECRUITER)
        pg.goto(f"{BASE}/requisitions")
        settle(pg)
        open_ranked(pg)
        pg.get_by_role("button", name=re.compile("^Strong")).click()
        settle(pg)
        check(pg.get_by_role("button", name=re.compile("^Strong")).get_attribute("aria-pressed") == "true", "dead-button check: filter chips apply")
        pg.get_by_role("button", name=re.compile("^All")).click()
        settle(pg)
        dis = pg.get_by_role("button", name="Submit to client", disabled=True)
        check(dis.count() > 0, "Submit to client is disabled for CVs not yet opened", f"{dis.count()} rows")
        if dis.count():
            tip = pg.locator("[role=tooltip]", has_text="Open the CV first").first
            pg.locator("span[tabindex='0']", has=dis.first).first.hover()
            pg.wait_for_timeout(250)
            check(tip.is_visible(), "disabled Submit explains why in a tooltip")
        check(not nameless(pg), "icon-only controls have accessible names: ranked", ", ".join(nameless(pg)[:3]))
        bad = not_tabular(pg)
        check(not bad, "numbers use tabular figures: ranked", ", ".join(bad))
        contrast_page(pg, "ranked @1440")
        c.close()

        for label, (w, h) in (("375", SIZES["375"]), ("1440", SIZES["1440"])):
            c, pg = ctx(w, h, CLIENT)
            pg.goto(f"{BASE}/portal")
            settle(pg)
            pg.get_by_role("button", name="How we screen").first.click()
            check(pg.get_by_role("dialog").is_visible(), f"dead-button check: portal How we screen @ {label}")
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(250)
            pg.get_by_role("button", name="Reject").first.click()
            check(pg.get_by_role("dialog").is_visible(), f"dead-button check: Reject opens the reason sheet @ {label}")
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(250)
            h_ok = pg.evaluate("[...document.querySelectorAll('main li button')].filter(b => b.innerText.trim() && b.getBoundingClientRect().height > 0).every(b => b.getBoundingClientRect().height >= 47)")
            check(bool(h_ok), f"portal action buttons are >= 48px tall @ {label}")
            check(not nameless(pg), f"icon-only controls have accessible names: portal @ {label}")
            contrast_page(pg, f"portal @{label}")
            c.close()

        c, pg = ctx(1440, 900, RECRUITER)
        pg.goto(f"{BASE}/requisitions")
        settle(pg)
        open_ranked(pg)
        pg.locator("ul > li a[href^='/candidates/']").first.click()
        pg.wait_for_selector("pre")
        settle(pg)
        check(not nameless(pg), "icon-only controls have accessible names: candidate")
        contrast_page(pg, "candidate @1440")
        c.close()

        c, pg = ctx(1440, 900)
        pg.goto(f"{BASE}/login")
        settle(pg)
        check(not nameless(pg), "icon-only controls have accessible names: login", ", ".join(nameless(pg)[:3]))
        contrast_page(pg, "login @1440")
        c.close()
        c, pg = ctx(375, 812)
        pg.goto(f"{BASE}/login")
        settle(pg)
        contrast_page(pg, "login @375")
        c.close()
        browser.close()

    fails = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(fails)} passed, {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
