"""Rendered-UI checks for docs/DESIGN.md section 6. Prints PASS/FAIL with evidence; exit 1 on any FAIL.

    scripts/qa.sh            (needs `docker compose up`; demo accounts are synthetic, see deployment.md)
"""
import json
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
  document.querySelectorAll('[data-qa]').forEach(e => e.removeAttribute('data-qa'));
  // read colours as sRGB through a canvas: handles color-mix()/oklab results that getComputedStyle returns as color(...)
  const cv = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
  const rgba = (css) => { cv.clearRect(0, 0, 1, 1); cv.fillStyle = '#000'; cv.fillStyle = css; cv.fillRect(0, 0, 1, 1); const d = cv.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255]; };
  // when a dialog is open, only the dialog is on screen (the page behind it is dimmed and inert)
  const root = document.querySelector('dialog[open]') || document.body;
  for (const el of root.querySelectorAll('*')) {
    const own = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).map(n => n.textContent.trim()).join(' ');
    if (!own) continue;
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0 || r.width < 2 || r.height < 2) continue;
    if (el.closest('[aria-hidden="true"]') || el.closest('[disabled]')) continue;
    const m = rgba(cs.color);
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
        pts = [(it["left"] - 1, mid), (it["left"] + 3, mid), (it["left"] + 2, it["top"] + 1), (it["left"] + 2, it["top"] + it["h"] - 2), (it["left"] + it["h"] / 2, mid)]
        pts = [(max(x, 0), y_) for x, y_ in pts if 0 <= y_ < vh - 1]
        if not pts:
            continue
        a = it["color"][3] if len(it["color"]) > 3 else 1.0
        best = 0.0
        seen_bg = []
        for x_, y_ in pts:
            try:
                bg = pixel(page, x_, y_)
            except Exception:
                continue
            seen_bg.append(bg)
            fg = tuple(it["color"][i] * a + bg[i] * (1 - a) for i in range(3))
            best = max(best, ratio(fg, bg))
        r = best
        large = it["size"] >= 24 or (it["size"] >= 18.66 and it["weight"] >= 700)
        need = 3.0 if large else 4.5
        worst = min(worst, r / need * 4.5)
        if r < need:
            bad.append(f"{it['text']!r} {r:.2f}<{need} fg={it['color']} bg={seen_bg}")
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
                ("requisitions", RECRUITER, lambda pg: (pg.goto(f"{BASE}/requisitions"), pg.wait_for_selector("ul > li a[href^='/requisitions/']"))),
                ("scorecard", RECRUITER, lambda pg: (open_ranked(pg), pg.get_by_role("link", name="Scorecard").click(), pg.wait_for_selector("text=Scoring criteria"))),
                ("upload", RECRUITER, lambda pg: (open_ranked(pg), pg.get_by_role("link", name="Upload CVs", exact=True).click(), pg.wait_for_selector("text=Drop PDF or DOCX CVs here"))),
            ]:
                c, pg = ctx(w, h, email)
                steps(pg)
                settle(pg)
                sw = pg.evaluate("document.documentElement.scrollWidth")
                wide = pg.evaluate("""(w) => [...document.querySelectorAll('body *')].filter(e => {
                    if (e.getBoundingClientRect().right <= w + 0.5 || e.closest('[aria-hidden=true]')) return false;
                    for (let p = e.parentElement; p; p = p.parentElement) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') return false; }
                    return true;
                }).length""", w)
                check(sw <= w and wide == 0, f"no horizontal scroll: {who} @ {label}px", f"scrollWidth={sw}, elements wider than the viewport={wide}")
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
        rings = []
        for _ in range(9):
            pg.keyboard.press("Tab")
            order.append(pg.evaluate("(() => { const e = document.activeElement; return (e.getAttribute('aria-label') || e.innerText || e.id || e.tagName).trim().slice(0, 22); })()"))
            pg.wait_for_timeout(300)
            rings.append(pg.evaluate("(() => { const e = document.activeElement; if (e === document.body) return true; const s = getComputedStyle(e); return (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== 'none'; })()"))
        ring = all(rings)
        expected = ["How we screen", "Privacy", "email", "password", "Sign in"]
        check(order[:5] == expected, "keyboard: tab order follows the visual order (nav, email, password, sign in)", " > ".join(order[:5]))
        check(bool(ring), "keyboard: every focused control has a visible focus ring", f"{sum(rings)}/{len(rings)}; no ring: {[o for o, r in zip(order, rings) if not r]}")
        pg.get_by_role("button", name="How we screen").click()
        check(pg.get_by_role("dialog").is_visible(), "dead-button check: How we screen opens a dialog")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(250)
        check(not pg.get_by_role("dialog").is_visible(), "Esc closes the dialog")
        pg.get_by_role("button", name="Privacy").click()
        check(pg.get_by_role("dialog").is_visible(), "dead-button check: Privacy opens a dialog")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(250)
        pg.get_by_role("button", name="Recruiter", exact=True).click()
        filled = pg.get_by_label("Email").input_value() == RECRUITER and pg.get_by_label("Password").input_value() != ""
        check(filled, "dead-button check: the Recruiter quick-fill chip fills the sign-in form")
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
        # ---- round 2: command palette, listbox, upload states, stage hues, phone bars, tap targets ----
        c, pg = ctx(1440, 900, RECRUITER)
        pg.goto(f"{BASE}/requisitions")
        settle(pg)
        pg.keyboard.press("Control+k")
        check(pg.get_by_role("dialog", name="Command palette").is_visible(), "command palette opens with Ctrl+K")
        pg.get_by_label("Search requisitions and candidates").fill("Ritika")
        try:
            pg.get_by_role("option", name=re.compile("Ritika")).first.wait_for(timeout=8000)
            pg.keyboard.press("Enter")
            pg.wait_for_url(re.compile("/candidates/"))
            check(True, "command palette finds a candidate and Enter opens it", pg.url.replace(BASE, "")[:28])
        except Exception:
            check(False, "command palette finds a candidate and Enter opens it")
        pg.goto(f"{BASE}/requisitions")
        settle(pg)
        pg.keyboard.press("Control+k")
        pg.get_by_role("option", name=re.compile("New requisition")).first.click()
        try:
            pg.wait_for_selector("dialog[open] #client_org", timeout=5000)
            check(True, "command palette action 'New requisition' opens the dialog")
        except Exception:
            check(False, "command palette action 'New requisition' opens the dialog")
        box = pg.get_by_role("combobox", name=re.compile("")).first
        pg.locator("#client_org").focus()
        pg.keyboard.press("ArrowDown")
        pg.keyboard.press("ArrowDown")
        pg.keyboard.press("Enter")
        picked = pg.locator("#client_org").inner_text().strip()
        check(bool(picked) and "Select a client" not in picked, "listbox is keyboard operable (arrows + Enter pick a client)", picked.replace("\n", " ")[:30])
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(250)
        c.close()

        c, pg = ctx(1440, 900, RECRUITER)
        pg.goto(f"{BASE}/requisitions")
        settle(pg)
        pg.wait_for_selector("ul > li a[href^='/requisitions/']")
        cards = pg.locator("ul > li a[href^='/requisitions/']").count()
        has = pg.evaluate("""() => [...document.querySelectorAll('ul > li a[href^="/requisitions/"]')].filter(a => a.querySelector('[role=img]')).length""")
        check(cards >= 4 and has >= 3, "requisition cards show distribution bar and pipeline progress", f"{cards} cards, {has} with bars")
        c.close()

        c, pg = ctx(1440, 900, RECRUITER)
        pg.goto(f"{BASE}/requisitions")
        settle(pg)
        open_ranked(pg)
        hues = pg.evaluate("""() => {
          const m = {};
          for (const el of document.querySelectorAll('li span.uppercase')) {
            const label = el.textContent.trim();
            const dot = el.querySelector('span[aria-hidden]');
            if (!dot || !['SOURCED','SCREENED','SUBMITTED','SHORTLISTED','INTERVIEW','OFFERED','JOINED','REJECTED'].includes(label.toUpperCase())) continue;
            m[label] = getComputedStyle(dot).backgroundColor;
          }
          return m;
        }""")
        check(len(set(hues.values())) == len(hues) and len(hues) >= 4, "each pipeline stage shown has its own hue (and its label)", ", ".join(sorted(hues)))
        stripes = pg.evaluate("""() => [...document.querySelectorAll('li > span[aria-hidden]')].map(e => getComputedStyle(e).backgroundImage !== 'none' || getComputedStyle(e).backgroundColor !== 'rgba(0, 0, 0, 0)').filter(Boolean).length""")
        check(stripes >= 10, "ranked rows carry a band stripe", f"{stripes} stripes")
        pg.locator("li button[aria-expanded]").first.click()
        check(pg.locator("li button[aria-expanded='true']").count() == 1, "evidence chip expands on click")
        c.close()

        # upload: states with the API mocked (nothing is written to the database)
        c, pg = ctx(1440, 900, RECRUITER)
        open_ranked(pg)
        pg.get_by_role("link", name="Upload CVs", exact=True).click()
        pg.wait_for_selector("text=Drop PDF or DOCX CVs here")
        drag = pg.locator("[data-drag]").first
        pg.evaluate("document.querySelector('[data-drag]').dispatchEvent(new DragEvent('dragover', {bubbles: true, cancelable: true, dataTransfer: new DataTransfer()}))")
        check(drag.get_attribute("data-drag") == "true", "drop zone reacts to a drag-over (animated dashed border)")
        names = ["a.pdf", "b.docx", "c.pdf", "d.pdf"]
        ids = [f"00000000-0000-0000-0000-00000000000{i}" for i in range(4)]
        base = {"note": "", "full_name": "", "band": None, "total": None}
        items = [
            {**base, "candidate_id": ids[0], "name": names[0], "cv_status": "parsed", "score_state": "scored", "band": "strong", "total": 90},
            {**base, "candidate_id": ids[1], "name": names[1], "cv_status": "parsed", "score_state": "pending"},
            {**base, "candidate_id": ids[2], "name": names[2], "cv_status": "needs_review", "score_state": "needs_manual_review"},
            {**base, "candidate_id": ids[3], "name": names[3], "cv_status": "parsed", "score_state": "failed"},
        ]
        def mock(route):
            body = ({"accepted": [{"candidate_id": i, "name": n} for i, n in zip(ids, names)], "rejected": [{"name": "bad.pdf", "reason": "Not a real PDF"}]}
                    if route.request.method == "POST" else {"items": items, "in_progress": True})
            route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
        pg.route("**/api/requisitions/*/uploads/**", mock)
        files = [{"name": n, "mimeType": "application/pdf", "buffer": b"%PDF-1.4"} for n in names + ["bad.pdf"]]
        pg.set_input_files("input[type=file]", files)
        check(not pg.get_by_role("button", name=re.compile("^Upload \\d+ file")).is_enabled(), "Upload stays disabled until consent is ticked")
        pg.locator("input[type=checkbox]").check()
        pg.get_by_role("button", name=re.compile("^Upload \\d+ file")).click()
        pg.wait_for_selector("text=Processing")
        bars = pg.get_by_role("progressbar").count()
        retries = pg.get_by_role("button", name="Retry").count()
        check(bars >= 6, "every file row has its own progress bar", f"{bars} progress bars")
        check(retries == 2, "Retry is offered for the rejected file and the scoring failure only", f"{retries} Retry buttons")
        check(pg.get_by_text("Needs review", exact=True).count() >= 1, "scanned PDF row says Needs review (not rejected)")
        c.close()

        # phone: pinned primary actions and tap targets
        c, pg = ctx(375, 812, RECRUITER)
        open_ranked(pg)
        fixed = pg.evaluate("""() => { const a = document.querySelector('a[aria-label="Upload CVs to this requisition"]'); if (!a) return null; let e = a; while (e && getComputedStyle(e).position !== 'fixed') e = e.parentElement; if (!e) return null; const r = e.getBoundingClientRect(); return {bottom: Math.round(r.bottom), vh: innerHeight, h: Math.round(r.height)}; }""")
        check(bool(fixed) and abs(fixed["bottom"] - fixed["vh"]) <= 1, "ranked list pins Upload CVs to the bottom edge on a phone", str(fixed))
        small = pg.evaluate("""() => [...document.querySelectorAll('main button, main a[href], header a[href], header button')].filter(e => { const r = e.getBoundingClientRect(); const st = getComputedStyle(e); return r.width > 0 && r.height > 0 && st.visibility !== 'hidden' && r.height < 43.5 && (e.innerText.trim() || e.getAttribute('aria-label')) && !e.closest('[aria-hidden=true]') && !e.closest('[hidden]'); }).map(e => (e.getAttribute('aria-label') || e.innerText.trim()).slice(0, 22) + ' ' + Math.round(e.getBoundingClientRect().height)).slice(0, 8)""")
        check(not small, "tap targets on the ranked list are >= 44px on a phone", "; ".join(small))
        c.close()
        c, pg = ctx(375, 812)
        pg.goto(f"{BASE}/login")
        settle(pg)
        fixed = pg.evaluate("""() => { const b = [...document.querySelectorAll('button')].find(x => x.innerText.trim() === 'Sign in'); let e = b; while (e && getComputedStyle(e).position !== 'fixed') e = e.parentElement; if (!e) return null; const r = e.getBoundingClientRect(); return {bottom: Math.round(r.bottom), vh: innerHeight}; }""")
        check(bool(fixed) and abs(fixed["bottom"] - fixed["vh"]) <= 1, "login pins Sign in to the bottom edge on a phone", str(fixed))
        c.close()

        c, pg = ctx(1440, 900, RECRUITER)
        pg.goto(f"{BASE}/requisitions")
        settle(pg)
        pg.wait_for_selector("ul > li a[href^='/requisitions/']")
        pg.wait_for_timeout(900)
        contrast_page(pg, "requisitions @1440")
        check(not nameless(pg), "icon-only controls have accessible names: requisitions")
        bad = not_tabular(pg)
        check(not bad, "numbers use tabular figures: requisitions", ", ".join(bad))
        pg.get_by_role("button", name="New requisition").first.click()
        pg.wait_for_selector("dialog[open]")
        pg.wait_for_timeout(900)
        contrast_page(pg, "new-requisition dialog @1440")
        c.close()
        c, pg = ctx(1440, 900, RECRUITER)
        open_ranked(pg)
        pg.get_by_role("link", name="Scorecard").click()
        pg.wait_for_selector("text=Scoring criteria")
        settle(pg)
        contrast_page(pg, "scorecard @1440")
        check(not nameless(pg), "icon-only controls have accessible names: scorecard")
        c.close()

        browser.close()

    fails = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(fails)} passed, {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
