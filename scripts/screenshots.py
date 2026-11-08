"""Screenshot the app at desktop and phone sizes into docs/screens/ (for design review against docs/DESIGN.md).

Run against the dev server (docker compose up). Uses the official Playwright image so nothing is installed on the host:

    scripts/screenshots.sh components

Screens: login, login-anim, components, requisitions, new-requisition, ranked, scorecard, upload, candidate, portal, portal-candidate (default: login). Pass `all` for everything.
Demo accounts are synthetic (see deployment.md); the password can be overridden with FAIRRANK_DEMO_PASSWORD.
"""
import json
import os
import pathlib
import re
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
    page.get_by_label("Password", exact=True).fill(PASSWORD)
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
    elif name == "login-error":
        page.goto(f"{BASE}/login")
        page.get_by_label("Email").fill(RECRUITER)
        page.get_by_label("Password", exact=True).fill("not-the-password")
        page.get_by_role("button", name="Sign in", exact=True).click()
        page.wait_for_selector("[role=alert]")
        page.wait_for_timeout(500)  # let the one-off shake finish
    elif name == "login-filled":
        page.goto(f"{BASE}/login")
        page.get_by_role("button", name=re.compile("^Recruiter")).click()
        page.wait_for_timeout(300)
    elif name == "login-loading":
        # the login request is held open so the in-flight state can be captured; nothing reaches the backend
        page.route("**/api/auth/login/", lambda route: None)
        page.goto(f"{BASE}/login")
        page.get_by_role("button", name=re.compile("^Recruiter")).click()
        page.get_by_role("button", name="Sign in", exact=True).click()
        page.wait_for_selector("text=Signing in")
        page.wait_for_timeout(300)
    elif name == "components":
        page.goto(f"{BASE}/dev/components")
    elif name == "requisitions":
        sign_in(page, RECRUITER)
        page.wait_for_selector("ul > li a[href^='/requisitions/']")
        page.wait_for_timeout(900)  # staggered entrance + count-ups
    elif name == "new-requisition":
        sign_in(page, RECRUITER)
        page.get_by_role("button", name="New requisition").first.click()
        page.wait_for_selector("dialog[open]")
    elif name == "scorecard":
        sign_in(page, RECRUITER)
        open_ranked(page)
        page.get_by_role("link", name="Scorecard").click()
        page.wait_for_selector("text=Scoring criteria")
    elif name == "upload":
        sign_in(page, RECRUITER)
        open_ranked(page)
        page.get_by_role("link", name="Upload CVs", exact=True).click()
        page.wait_for_selector("text=Drop PDF or DOCX CVs here")
    elif name == "upload-files":
        # The API is mocked here so the per-file states can be shown without writing candidates to the database.
        sign_in(page, RECRUITER)
        open_ranked(page)
        page.get_by_role("link", name="Upload CVs", exact=True).click()
        page.wait_for_selector("text=Drop PDF or DOCX CVs here")
        names = ["ritika_bansal.pdf", "arjun_rawat.docx", "scan_kyc.pdf", "pooja_nair.pdf", "duplicate_cv.pdf"]
        ids = [f"00000000-0000-0000-0000-00000000000{i}" for i in range(5)]
        base = {"note": "", "full_name": "", "band": None, "total": None}
        items = [
            {**base, "candidate_id": ids[0], "name": names[0], "full_name": "Ritika Bansal", "cv_status": "parsed", "score_state": "scored", "band": "strong", "total": 100},
            {**base, "candidate_id": ids[1], "name": names[1], "cv_status": "parsed", "score_state": "pending"},
            {**base, "candidate_id": ids[2], "name": names[2], "cv_status": "needs_review", "score_state": "needs_manual_review"},
            {**base, "candidate_id": ids[3], "name": names[3], "cv_status": "parsed", "score_state": "failed"},
            {**base, "candidate_id": ids[4], "name": names[4], "cv_status": "duplicate", "note": "Possible duplicate of CND-91022", "score_state": "scored", "band": "weak", "total": 34},
        ]

        def mock(route):
            if route.request.method == "POST":
                body = {"accepted": [{"candidate_id": i, "name": n} for i, n in zip(ids, names)], "rejected": [{"name": "corrupt.pdf", "reason": "The file is not a real PDF"}]}
            else:
                body = {"items": items, "in_progress": True}
            route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

        page.route("**/api/requisitions/*/uploads/**", mock)
        files = [{"name": n, "mimeType": "application/pdf", "buffer": b"%PDF-1.4 mock"} for n in names]
        files += [{"name": "corrupt.pdf", "mimeType": "application/pdf", "buffer": b"%PDF-1.4 mock"}, {"name": "notes.txt", "mimeType": "text/plain", "buffer": b"x"}]
        page.set_input_files("input[type=file]", files)
        page.get_by_label("Consent is on record").check() if page.get_by_label("Consent is on record").count() else page.locator("input[type=checkbox]").check()
        page.get_by_role("button", name=re.compile("^Upload \\d+ file")).click()
        page.wait_for_selector("text=Processing")
        page.wait_for_timeout(600)
    elif name == "ranked":
        sign_in(page, RECRUITER)
        open_ranked(page)
    elif name == "candidate":
        sign_in(page, RECRUITER)
        open_ranked(page)
        page.locator("ul > li a[href^='/candidates/']").first.click()
        page.wait_for_selector("h1")
    elif name == "candidate-scrolled":
        sign_in(page, RECRUITER)
        open_ranked(page)
        page.locator("ul > li a[href^='/candidates/']").first.click()
        page.wait_for_selector("h1")
        settle(page)
        page.evaluate("window.scrollTo(0, 600)")
        page.wait_for_timeout(700)
    elif name == "pipeline":
        sign_in(page, RECRUITER)
        open_ranked(page)
        page.get_by_role("link", name="Pipeline", exact=True).click()
        page.wait_for_selector("text=Submitted")
    elif name == "report":
        sign_in(page, "head@companya.example")
        page.get_by_role("link", name=re.compile("AI vs recruiter")).click()
        page.wait_for_selector("text=Time window", state="attached") if page.get_by_text("Time window").count() else page.wait_for_timeout(800)
        page.wait_for_timeout(900)
    elif name == "overview":
        sign_in(page, "head@companya.example")
        page.wait_for_selector("text=Delivery")
        page.wait_for_timeout(900)
    elif name == "portal":
        sign_in(page, CLIENT)
    elif name == "portal-candidate":
        sign_in(page, CLIENT)
        page.locator("a[href^='/portal/candidates/']").first.click()
        page.wait_for_selector("h1")
    elif name in ("candidate-criterion", "candidate-blind"):
        sign_in(page, RECRUITER)
        open_ranked(page)
        page.locator("ul > li a[href^='/candidates/']").first.click()
        page.wait_for_selector("h1")
        settle(page)
        if name == "candidate-criterion":
            page.locator("ul.overflow-hidden li button[aria-expanded=false]").first.click()  # a criterion row, not the user menu
        else:
            if view == "phone":
                page.get_by_text("CV", exact=True).first.click()  # Blind view lives on the CV tab on phones
            page.get_by_role("button", name=re.compile("Blind view")).click()
        page.wait_for_timeout(400)
    elif name in ("portal-reject", "portal-slot", "portal-how"):
        sign_in(page, CLIENT)
        want = {"portal-reject": "Reject", "portal-slot": re.compile("Propose"), "portal-how": "How we screen"}[name]
        links = page.locator("a[href^='/portal/candidates/']")
        for i in range(links.count()):
            page.goto(f"{BASE}/portal")
            settle(page)
            page.locator("a[href^='/portal/candidates/']").nth(i).click()
            page.wait_for_selector("h1")
            settle(page)
            btn = page.get_by_role("button", name=want)
            if btn.count():
                btn.first.click()
                page.wait_for_timeout(500)
                break
    else:
        raise SystemExit(f"unknown screen: {name}")
    if name != "login-loading":
        settle(page)
    fold_only = bool(os.environ.get("FOLD")) or name.startswith("login") or name == "new-requisition" or name.endswith("-scrolled")
    full = not fold_only
    dims = page.evaluate("[document.documentElement.scrollWidth, innerWidth, document.documentElement.scrollHeight, innerHeight]")
    print(f"{name}-{view}: scrollW={dims[0]} viewW={dims[1]} scrollH={dims[2]} viewH={dims[3]}" + ("  HORIZONTAL SCROLL" if dims[0] > dims[1] else ""))
    designed = VIEWS[view]["width"]
    wide = page.evaluate("(w) => [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > w + 0.5 && !e.closest('[aria-hidden=true]')).slice(0, 6).map(e => e.tagName + '.' + String(e.className).slice(0, 90))", designed)
    if wide:
        print(f"  WIDER THAN {designed}px:", wide)
    OUT.mkdir(parents=True, exist_ok=True)
    if False:
        page.screenshot(path=str(OUT / "login-phone-fold.png"))  # what a phone actually shows first (the pinned Sign in bar is fixed)
        print("wrote", OUT / "login-phone-fold.png")
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
        names = ["login", "components", "requisitions", "new-requisition", "ranked", "scorecard", "upload", "upload-files", "candidate", "portal", "portal-candidate"]
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
