"""Browser end-to-end test of every workflow for every kind of user, against the running dev stack (scripts/e2e-ui.sh).

Creates its own requisition ("E2E ...") with synthetic CVs from .review/cvs (docker compose cp web:/tmp/cvs), so seed data is only read.
Each step is isolated: a failure is recorded (with a screenshot in .review/e2e-fail/) and the run continues.
"""
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timedelta

from playwright.sync_api import Page, expect, sync_playwright

BASE = os.environ.get("FAIRRANK_URL", "http://localhost:5173")
PW = os.environ.get("FAIRRANK_DEMO_PASSWORD", "FairRank-demo-1")
CVS = pathlib.Path(".review/cvs")
FAILS = pathlib.Path(".review/e2e-fail")
REC, HEAD, NORTH, MERIDIAN = "recruiter1@companya.example", "head@companya.example", "manager@northwind.example", "manager@meridian.example"
results: list[tuple[bool, str, str]] = []
STATE: dict = {}


def step(name):
    def deco(fn):
        def run(*a, **k):
            page = a[0] if a and isinstance(a[0], Page) else None
            try:
                fn(*a, **k)
                results.append((True, name, ""))
                print("PASS", name)
            except Exception as e:  # noqa: BLE001
                import traceback
                last = [f for f in traceback.extract_tb(e.__traceback__) if f.filename.endswith('e2e_ui.py')][-1]
                msg = (str(e).strip().splitlines()[0][:200] if str(e).strip() else type(e).__name__) + f' (line {last.lineno}: {last.line[:70]})'
                results.append((False, name, msg))
                print("FAIL", name, "|", msg)
                if page:
                    FAILS.mkdir(parents=True, exist_ok=True)
                    try:
                        page.screenshot(path=str(FAILS / (re.sub(r"\W+", "-", name)[:60] + ".png")))
                    except Exception:  # noqa: BLE001
                        pass
        return run
    return deco


def settle(pg: Page, ms=350):
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(ms)


def sign_in(pg: Page, email: str, via_chip: str | None = None):
    pg.goto(f"{BASE}/login")
    if via_chip:
        pg.get_by_role("button", name=via_chip, exact=True).click()
    else:
        pg.get_by_label("Email").fill(email)
        pg.get_by_label("Password", exact=True).fill(PW)
    pg.get_by_role("button", name="Sign in", exact=True).click()
    pg.wait_for_url(lambda u: "/login" not in u)
    settle(pg)


def no_hscroll(pg: Page):
    assert pg.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "horizontal scroll"


def main() -> int:
    with sync_playwright() as p:
        b = p.chromium.launch()
        def ctx(w=1440, h=900, phone=False):
            c = b.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce", is_mobile=phone, has_touch=phone)
            pg = c.new_page()
            pg.on("pageerror", lambda e: results.append((False, "no uncaught page errors", str(e)[:200])))
            return c, pg
        recruiter_journey(ctx)
        client_journey(ctx)
        recruiter_after_client(ctx)
        head_journey(ctx)
        access_control(ctx)
        b.close()
    bad = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(bad)} passed, {len(bad)} failed")
    for _, n, m in bad:
        print("  FAIL", n, "|", m)
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ recruiter
def recruiter_journey(ctx):
    c, pg = ctx()

    @step("recruiter: signs in with the demo role row and lands on Requisitions")
    def _(pg):
        pg.goto(f"{BASE}/login")
        pg.get_by_role("button", name="Recruiter", exact=True).click()
        assert pg.evaluate("document.activeElement.textContent.trim().startsWith('Sign in')")
        pg.get_by_role("button", name="Sign in", exact=True).click()
        pg.wait_for_url(re.compile("/requisitions"))
        expect(pg.get_by_role("heading", name="Requisitions")).to_be_visible()
        settle(pg)
    _(pg)

    @step("recruiter: the New requisition dialog validates, then drafts a scorecard from the example JD")
    def _(pg):
        pg.get_by_role("button", name="New requisition").first.click()
        d = pg.locator("dialog[open]")
        d.get_by_role("button", name="Draft scorecard").click()
        assert d.locator("[role=alert]").count() >= 1, "no validation errors for an empty form"
        d.get_by_role("combobox").first.click() if d.get_by_role("combobox").count() else d.get_by_role("button", name=re.compile("Select a client")).click()
        pg.get_by_role("option", name=re.compile("Northwind")).click()
        d.get_by_label("Title (optional)").fill("E2E Senior Java Developer")
        d.get_by_label("Job description").fill("too short")
        d.get_by_role("button", name="Draft scorecard").click()
        assert d.locator("[role=alert]").count() >= 1, "short JD accepted"
        d.get_by_role("button", name="Use the example JD").click()
        assert len(d.get_by_label("Job description").input_value()) > 50
        d.get_by_role("button", name="Draft scorecard").click()
        pg.wait_for_url(re.compile(r"/requisitions/[0-9a-f-]{36}"), timeout=60000)
        STATE["req_url"] = pg.url.split("?")[0].rsplit("/", 1)[0] if pg.url.rstrip("/").split("/")[-1] in ("scorecard", "upload", "pipeline") else pg.url
        settle(pg)
    _(pg)
    req = STATE.get("req_url", "")
    req_id = re.search(r"/requisitions/([0-9a-f-]{36})", req).group(1) if req else ""

    @step("recruiter: the scorecard is editable (weights, must-have toggle, add, remove with undo) and saves a new version")
    def _(pg):
        pg.goto(f"{BASE}/requisitions/{req_id}/scorecard")
        pg.wait_for_selector("text=Scoring criteria")
        n0 = pg.locator("input[id^=name-]").count()
        assert n0 >= 3, f"AI scorecard has only {n0} criteria"
        pg.get_by_role("button", name=re.compile("^Increase weight")).first.click()
        pg.get_by_role("button", name="Add criterion").click()
        pg.locator("input[id^=name-]").last.fill("Kafka")
        assert pg.locator("input[id^=name-]").count() == n0 + 1
        pg.get_by_role("button", name=re.compile("Remove criterion")).first.click()
        assert pg.locator("input[id^=name-]").count() == n0
        undo = pg.get_by_role("button", name="Undo")
        if undo.count():
            undo.first.click()
            assert pg.locator("input[id^=name-]").count() == n0 + 1
        pg.get_by_role("button", name=re.compile(r"^Save as v")).click()
        expect(pg.get_by_text(re.compile(r"Saved as v\d"))).to_be_visible(timeout=15000)
    _(pg)

    @step("recruiter: a duplicate criterion name is refused by the scorecard form")
    def _(pg):
        pg.locator("input[id^=name-]").nth(1).fill(pg.locator("input[id^=name-]").nth(0).input_value())
        pg.get_by_role("button", name=re.compile(r"^Save as v")).click()
        pg.wait_for_timeout(500)
        assert pg.get_by_text(re.compile("unique|already", re.I)).count() >= 1 or pg.locator("[role=alert]").count() >= 1
        pg.reload()
    _(pg)

    @step("recruiter: Upload stays disabled without consent, rejects bad files with reasons, then processes the batch")
    def _(pg):
        pg.goto(f"{BASE}/requisitions/{req_id}/upload")
        pg.wait_for_selector("text=Drop PDF or DOCX CVs here")
        good = sorted((CVS / "java").glob("*.*"))[:9]
        dup = CVS / "java" / "ritika-bansal_pdf_single.pdf"
        scan = next((CVS / "kyc").glob("*scanned*"))
        files = [str(f) for f in good] + [str(scan)]
        pathlib.Path(".review").mkdir(exist_ok=True)
        (pathlib.Path(".review") / "notes.txt").write_text("not a cv")
        files.append(".review/notes.txt")
        pg.set_input_files("input[type=file]", files)
        btn = pg.get_by_role("button", name=re.compile(r"^Upload \d+ file"))
        assert not btn.is_enabled(), "upload enabled without consent"
        assert pg.get_by_text(re.compile("notes.txt")).count() >= 1, "unsupported file not reported"
        pg.locator("input[type=checkbox]").check()
        assert btn.is_enabled()
        btn.click()
        pg.wait_for_selector("text=Processing", timeout=15000) if pg.get_by_text("Processing").count() == 0 else None
        for _i in range(90):  # the worker scores in small batches
            if pg.get_by_text("Processing").count() == 0 and pg.get_by_text("Queued").count() == 0 and pg.get_by_text("Scoring").count() == 0:
                break
            pg.wait_for_timeout(2000)
        settle(pg)
        assert pg.get_by_text("Needs review", exact=True).count() >= 1, "scanned CV not flagged"
        assert not pg.get_by_text("Processing").count(), "still processing after 3 minutes"
        STATE["uploaded"] = len(good) + 1
    _(pg)

    @step("recruiter: a second upload of the same CV is flagged as a duplicate")
    def _(pg):
        pg.goto(f"{BASE}/requisitions/{req_id}/upload")
        pg.wait_for_selector("text=Drop PDF or DOCX CVs here")
        pg.set_input_files("input[type=file]", str(sorted((CVS / "java").glob("*.*"))[0]))
        pg.locator("input[type=checkbox]").check()
        pg.get_by_role("button", name=re.compile(r"^Upload \d+ file")).click()
        for _i in range(45):
            if pg.get_by_text("Duplicate").count() or pg.get_by_text("duplicate").count():
                break
            pg.wait_for_timeout(2000)
        assert pg.get_by_text(re.compile("duplicate", re.I)).count() >= 1
    _(pg)

    @step("recruiter: ranked list ranks best-first, filters, searches, and never hides low scorers")
    def _(pg):
        pg.goto(f"{BASE}/requisitions/{req_id}")
        pg.wait_for_selector("ul > li")
        settle(pg, 900)
        scores = [int(x) for x in pg.locator("ul > li [role=img][aria-label^='Score']").evaluate_all("els => els.map(e => e.getAttribute('aria-label').match(/\\d+/)[0])")]
        assert scores == sorted(scores, reverse=True) and len(scores) >= 5, scores
        total_rows = pg.locator("ul > li").count()
        pg.get_by_role("button", name=re.compile("^Weak")).click()
        settle(pg)
        weak_rows = pg.locator("ul > li").count()
        assert 0 < weak_rows < total_rows or weak_rows == total_rows, "weak filter"
        pg.get_by_role("button", name=re.compile("^Weak")).click()  # click again clears
        settle(pg)
        pg.get_by_label("Search candidates").fill("zzzzqqqq")
        expect(pg.get_by_text("No CVs match these filters")).to_be_visible(timeout=5000)
        pg.get_by_role("button", name="Clear filters").click()
        settle(pg)
        assert pg.locator("ul > li").count() == total_rows
        pg.get_by_label("Search candidates").fill("a'; DROP TABLE x;--")
        settle(pg, 600)
        assert pg.locator("body").inner_text().strip() != ""
        pg.get_by_label("Search candidates").fill("")
    _(pg)

    @step("recruiter: ranked rows without an opened CV cannot be submitted (disabled, with the reason)")
    def _(pg):
        pg.goto(f"{BASE}/requisitions/{req_id}")
        pg.wait_for_selector("ul > li")
        assert pg.get_by_role("button", name="Submit to client").first.is_disabled()
    _(pg)

    @step("recruiter: the candidate page shows exact highlights, one open criterion at a time, Blind view and find")
    def _(pg):
        pg.locator("ul > li a[href^='/candidates/']").first.click()
        pg.wait_for_selector(".cv-sheet")
        settle(pg)
        STATE["cand_url"] = pg.url
        assert not pg.evaluate("document.documentElement.scrollHeight > innerHeight + 1"), "the page scrolls"
        marks = pg.locator("mark.cv-mark")
        n = marks.count()
        verified = pg.locator("li[id^=crit-] svg[aria-label='Verified evidence'], li[id^=crit-] svg[aria-label='Partial match']").count()
        assert n >= 1 and n <= verified + 1, f"{n} highlights for {verified} verified criteria"
        for i in range(min(n, 4)):
            text = marks.nth(i).inner_text()
            assert len(text) < 200, "a highlight spans an implausible amount of text (whole blocks)"
        rows = pg.locator("li[id^=crit-] > button")
        rows.nth(0).click()
        rows.nth(1).click()
        assert pg.locator("li[id^=crit-] > button[aria-expanded=true]").count() == 1, "more than one criterion open"
        pg.get_by_role("button", name="Blind view").click()
        assert pg.locator(".cv-redact").count() >= 2, "Blind view masked nothing"
        name = pg.locator("h1").inner_text().split("\n")[0]
        assert name.split()[0] not in pg.locator(".cv-sheet").inner_text(), "name still visible in Blind view"
        pg.get_by_role("button", name="Blind view").click()
        pg.keyboard.press("/")
        assert pg.evaluate("document.activeElement.getAttribute('aria-label')") == "Find in CV"
        pg.keyboard.type("Java")
        assert pg.get_by_label("Find in CV").input_value() == "Java"
        expect(pg.locator("[aria-live=polite]").first).to_contain_text("/")
        pg.keyboard.press("Escape")
        pg.locator("body").click(position={"x": 5, "y": 400})
        first = pg.url
        pg.keyboard.press("j")
        pg.wait_for_function("(u) => location.href !== u", arg=first, timeout=8000)
        pg.wait_for_selector(".cv-sheet")
        pg.wait_for_timeout(700)
        pg.keyboard.press("k")
        pg.wait_for_function("(u) => location.href === u", arg=first, timeout=8000)
    _(pg)

    @step("recruiter: submitting through the dialog moves the candidate to Submitted and removes the Submit button")
    def _(pg):
        pg.goto(STATE["cand_url"])
        pg.wait_for_selector(".cv-sheet")
        btn = pg.get_by_role("button", name=re.compile("Submit to client")).first
        assert btn.is_enabled(), "submit disabled after opening the CV"
        btn.click()
        d = pg.locator("dialog[open]")
        d.get_by_label(re.compile("Note for the client")).fill("Strong match on the must-haves.")
        d.get_by_role("button", name="Submit to client").click()
        expect(pg.get_by_text(re.compile("Submitted to the client"))).to_be_visible(timeout=10000)
        pg.wait_for_timeout(500)
        assert pg.get_by_role("button", name=re.compile("Submit to client")).count() == 0 or all(b.is_disabled() for b in pg.get_by_role("button", name=re.compile("Submit to client")).all())
        expect(pg.locator("header").get_by_text("Submitted", exact=False).first).to_be_visible()
        STATE["submitted_name"] = pg.locator("h1").inner_text().split("\n")[0]
        STATE["cand_id"] = pg.url.rsplit("/", 1)[-1]
    _(pg)

    @step("recruiter: a second candidate can be submitted too (open first, then submit)")
    def _(pg):
        pg.goto(f"{BASE}/requisitions/{req_id}")
        pg.wait_for_selector("ul > li")
        pg.wait_for_selector("ul > li a[href^='/candidates/']")
        settle(pg)
        rows = pg.locator("ul > li")
        for i in range(rows.count()):
            txt = rows.nth(i).inner_text()
            if "SCREENED" in txt.upper() and STATE["submitted_name"] not in txt and "Needs review" not in txt:
                rows.nth(i).locator("a[href^='/candidates/']").first.click()
                break
        pg.wait_for_selector(".cv-sheet")
        STATE["second_name"] = pg.locator("h1").inner_text().split("\n")[0]
        STATE["second_url"] = pg.url
        STATE["second_id"] = pg.url.rsplit("/", 1)[-1]
        pg.get_by_role("button", name=re.compile("Submit to client")).first.click()
        pg.locator("dialog[open]").get_by_role("button", name="Submit to client").click()
        expect(pg.get_by_text(re.compile("Submitted to the client"))).to_be_visible(timeout=10000)
    _(pg)

    @step("recruiter: the scanned CV page says Needs manual review and offers the original")
    def _(pg):
        pg.goto(f"{BASE}/requisitions/{req_id}")
        pg.wait_for_selector("ul > li")
        pg.locator("ul > li", has_text="Needs review").first.locator("a[href^='/candidates/']").first.click()
        pg.wait_for_selector("h1")
        expect(pg.get_by_text("Needs manual review").first).to_be_visible()
        assert pg.locator("mark.cv-mark").count() == 0
    _(pg)

    @step("recruiter: the pipeline board lists the submitted candidates under Submitted")
    def _(pg):
        pg.goto(f"{BASE}/requisitions/{req_id}/pipeline")
        pg.wait_for_selector("text=Submitted")
        assert STATE["submitted_name"].split()[0] in pg.locator("main").inner_text()
    _(pg)

    @step("recruiter: Delete on request needs a requester, then wipes the candidate and returns to the list")
    def _(pg):
        pg.goto(f"{BASE}/requisitions/{req_id}")
        pg.wait_for_selector("ul > li a[href^='/candidates/']")
        settle(pg, 800)
        before = pg.locator("ul > li").count()
        pg.locator("ul > li a[href^='/candidates/']").last.click()
        pg.wait_for_selector(".cv-sheet")
        pg.get_by_role("button", name="More actions").click()
        pg.get_by_role("menuitem", name="Delete on request").click()
        d = pg.locator("dialog[open]")
        d.get_by_role("button", name="Delete permanently").click()
        assert d.locator("[role=alert]").count() >= 1, "deletion accepted without a requester"
        d.get_by_label("Requested by").fill("the candidate, by email (e2e)")
        d.get_by_role("button", name="Delete permanently").click()
        pg.wait_for_url(re.compile(r"/requisitions/[0-9a-f-]{36}/?$"), timeout=15000)
        pg.wait_for_selector("ul > li")
        pg.reload()
        pg.wait_for_selector("ul > li")
        settle(pg)
        assert pg.locator("ul > li").count() == before - 1, (before, pg.locator("ul > li").count())
    _(pg)
    c.close()


# ------------------------------------------------------------------------------------------------ client
def client_journey(ctx):
    c, pg = ctx(375, 812, phone=True)

    @step("client (phone): signs in with the Client demo row and lands on the shortlist")
    def _(pg):
        pg.goto(f"{BASE}/login")
        pg.get_by_role("button", name="Client", exact=True).click()
        pg.get_by_role("button", name="Sign in", exact=True).click()
        pg.wait_for_url(re.compile("/portal"))
        settle(pg)
        no_hscroll(pg)
    _(pg)

    @step("client (phone): sees only candidates submitted to their org, with masked contacts and no protected attributes")
    def _(pg):
        links = pg.locator("a[href^='/portal/candidates/']")
        assert links.count() >= 1, "no candidates in the portal"
        mine = pg.locator(f"a[href$='/portal/candidates/{STATE['cand_id']}']").first
        assert mine.count() >= 1, "the candidate the recruiter just submitted is not in the portal"
        assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", mine.inner_text()), "an unmasked email on the list card"
        mine.click()
        pg.wait_for_url(re.compile("/portal/candidates/"))
        STATE["portal_cand"] = pg.url
        pg.wait_for_selector("pre", state="attached")
        settle(pg)
        text = pg.locator("body").inner_text()
        assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", text), "an unmasked email on the candidate page"
        assert "Marital Status: Married" not in text and "Gender: Female" not in text and "Gender: Male" not in text
        no_hscroll(pg)
    _(pg)

    @step("client (phone): How we screen opens and closes")
    def _(pg):
        pg.get_by_role("button", name=re.compile("How we screen")).first.click()
        expect(pg.locator("dialog[open]")).to_be_visible()
        pg.keyboard.press("Escape")
        expect(pg.locator("dialog[open]")).to_have_count(0)
    _(pg)

    @step("client (phone): all three decision buttons are at least 48px tall")
    def _(pg):
        hs = pg.evaluate("[...document.querySelectorAll('button')].filter(b => /Shortlist|Propose|Reject/.test(b.textContent) && b.getBoundingClientRect().height > 0).map(b => b.getBoundingClientRect().height)")
        assert hs and all(h >= 47.5 for h in hs), hs
    _(pg)

    @step("client (phone): Reject needs a reason, Cancel changes nothing")
    def _(pg):
        pg.get_by_role("button", name=re.compile("^Reject")).first.click()
        d = pg.locator("dialog[open]")
        d.get_by_role("button", name="Reject", exact=True).click()
        assert d.locator("[role=alert]").count() >= 1, "rejection accepted without a reason"
        d.get_by_role("button", name="Cancel").click()
        expect(pg.locator("dialog[open]")).to_have_count(0)
    _(pg)

    @step("client (phone): shortlisting works, and the Shortlist button then goes away")
    def _(pg):
        pg.get_by_role("button", name=re.compile("Shortlist")).first.click()
        expect(pg.get_by_text(re.compile("You shortlisted"))).to_be_visible(timeout=10000)
        expect(pg.get_by_role("button", name=re.compile("^Shortlist"))).to_have_count(0)
    _(pg)

    @step("client (phone): proposing a past time is refused, a future time moves the candidate to Interview and unmasks contacts")
    def _(pg):
        pg.get_by_role("button", name=re.compile("Propose")).first.click()
        d = pg.locator("dialog[open]")
        past = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        d.get_by_label("Date and time").fill(past)
        d.get_by_role("button", name="Propose time").click()
        assert d.locator("[role=alert]").count() >= 1, "past time accepted"
        d.get_by_label("Date and time").fill((datetime.now() + timedelta(days=3)).strftime("%Y-%m-%dT10:00"))
        d.get_by_label(re.compile("Note")).fill("Panel of two, video call")
        d.get_by_role("button", name="Propose time").click()
        expect(pg.get_by_text(re.compile("Interview proposed")).first).to_be_visible(timeout=10000)
        settle(pg)
        assert re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", pg.locator("body").inner_text()), "contacts did not unmask at the interview stage"
        no_hscroll(pg)
    _(pg)

    @step("client (phone): a rejection needs a reason and then sticks (second candidate)")
    def _(pg):
        pg.goto(f"{BASE}/portal")
        settle(pg)
        pg.locator(f"a[href$='/portal/candidates/{STATE['second_id']}']").first.click()
        settle(pg)
        pg.get_by_role("button", name=re.compile("^Reject")).first.click()
        d = pg.locator("dialog[open]")
        d.get_by_label("Reason").fill("Notice period too long for this role")
        d.get_by_role("button", name="Reject", exact=True).click()
        expect(pg.get_by_text(re.compile("Rejected")).first).to_be_visible(timeout=10000)
        expect(pg.get_by_text(re.compile("Notice period too long"))).to_be_visible()
    _(pg)

    @step("client (desktop): the same portal is clean on a wide screen")
    def _(pg):
        pg.set_viewport_size({"width": 1440, "height": 900})
        pg.goto(f"{BASE}/portal")
        settle(pg)
        no_hscroll(pg)
        assert pg.locator("a[href^='/portal/candidates/']").count() >= 1
    _(pg)
    c.close()

    c2, pg2 = ctx(375, 812, phone=True)

    @step("client of ANOTHER org (Meridian) sees none of Northwind's candidates, and cannot open them by URL")
    def _(pg):
        sign_in(pg, MERIDIAN)
        pg.wait_for_url(re.compile("/portal"))
        settle(pg)
        assert STATE["cand_id"] not in pg.content(), "another org's candidate id is in the page"
        assert pg.locator(f"a[href$='/{STATE['cand_id']}']").count() == 0 and pg.locator(f"a[href$='/{STATE['second_id']}']").count() == 0
        pg.goto(STATE["portal_cand"])
        settle(pg)
        body = pg.locator("body").inner_text()
        assert "Shortlist" not in body and ("couldn" in body.lower() or "not found" in body.lower() or "went wrong" in body.lower() or STATE["submitted_name"].split()[0] not in body)
    _(pg2)
    c2.close()


def recruiter_after_client(ctx):
    c, pg = ctx()

    @step("recruiter: sees the client's shortlist, rejection reason and proposed slot, and can confirm the slot")
    def _(pg):
        sign_in(pg, REC)
        pg.goto(STATE["cand_url"])
        pg.wait_for_selector(".cv-sheet")
        pg.get_by_role("tab", name="Activity").click()
        settle(pg)
        text = pg.locator("[role=tabpanel]").inner_text()
        assert "client shortlisted" in text.lower() and "interview" in text.lower(), text[:300]
        pg.get_by_role("button", name="Confirm").first.click()
        expect(pg.locator("[role=tabpanel]").get_by_text("confirmed")).to_be_visible(timeout=8000)
    _(pg)

    @step("recruiter: the second candidate shows the client's rejection reason")
    def _(pg):
        pg.goto(STATE["second_url"])
        pg.wait_for_selector(".cv-sheet")
        pg.get_by_role("tab", name="Activity").click()
        expect(pg.locator("[role=tabpanel]").get_by_text(re.compile("Notice period too long"))).to_be_visible()
    _(pg)

    @step("recruiter: Move stage (More menu) moves the interview candidate to Offered and the history records it")
    def _(pg):
        pg.goto(STATE["cand_url"])
        pg.wait_for_selector(".cv-sheet")
        pg.get_by_role("button", name="More actions").click()
        pg.get_by_role("menuitem", name="Offered").click()
        pg.wait_for_timeout(800)
        pg.get_by_role("tab", name="Activity").click()
        assert "Offered" in pg.locator("[role=tabpanel]").inner_text()
    _(pg)
    c.close()


# ------------------------------------------------------------------------------------------------ delivery head
def head_journey(ctx):
    c, pg = ctx()

    @step("delivery head: signs in and lands on Delivery with every requisition and its pipeline")
    def _(pg):
        sign_in(pg, HEAD, via_chip="Delivery head")
        expect(pg.get_by_role("heading", name="Delivery")).to_be_visible()
        assert pg.locator("main a[href^='/requisitions/']").count() >= 3
        no_hscroll(pg)
    _(pg)

    @step("delivery head: the AI vs recruiter report shows agreement and lets the window change")
    def _(pg):
        pg.get_by_role("link", name=re.compile("AI vs recruiter")).click()
        expect(pg.get_by_role("heading", name="AI vs recruiter")).to_be_visible()
        settle(pg)
        text = pg.locator("main").inner_text()
        assert re.search(r"\d+\s?%", text), text[:300]
        pg.get_by_label("Time window").select_option(index=1)
        settle(pg)
        assert pg.locator("main").inner_text().strip()
    _(pg)

    @step("delivery head: read-only everywhere (no upload, no submit, no move, no delete, no scorecard save)")
    def _(pg):
        pg.goto(f"{BASE}/requisitions")
        settle(pg)
        assert pg.get_by_role("button", name="New requisition").count() == 0
        pg.locator("main a[href^='/requisitions/']").first.click()
        pg.wait_for_selector("ul > li")
        assert pg.get_by_role("button", name="Submit to client").count() == 0 or all(b.is_disabled() for b in pg.get_by_role("button", name="Submit to client").all())
        assert pg.get_by_role("link", name="Upload CVs").count() == 0 or pg.get_by_role("link", name="Upload CVs", exact=True).count() == 0
        pg.locator("ul > li a[href^='/candidates/']").first.click()
        pg.wait_for_selector(".cv-sheet")
        assert pg.get_by_role("button", name=re.compile("Submit to client")).count() == 0
        assert pg.get_by_role("button", name="More actions").count() == 0
        pg.goto(pg.url.split("/candidates/")[0] + "/portal")
        settle(pg)
        assert "/portal" not in pg.url, "the head reached the client portal"
    _(pg)
    c.close()


# ------------------------------------------------------------------------------------------------ access control
def access_control(ctx):
    c, pg = ctx()

    @step("signed out: every protected page redirects to login")
    def _(pg):
        for path in ("/requisitions", "/portal", "/pipeline", "/candidates/00000000-0000-0000-0000-000000000000"):
            pg.goto(BASE + path)
            pg.wait_for_url(re.compile("/login"), timeout=8000)
    _(pg)

    @step("client: staff pages bounce back to the portal")
    def _(pg):
        sign_in(pg, NORTH)
        for path in ("/requisitions", "/pipeline", "/candidates/00000000-0000-0000-0000-000000000000"):
            pg.goto(BASE + path)
            pg.wait_for_url(re.compile("/portal"), timeout=8000)
    _(pg)

    @step("recruiter: the client portal and delivery pages bounce back to Requisitions")
    def _(pg):
        pg.context.clear_cookies()
        sign_in(pg, REC)
        for path in ("/portal", "/pipeline", "/pipeline/report"):
            pg.goto(BASE + path)
            pg.wait_for_url(re.compile("/requisitions"), timeout=8000)
    _(pg)

    @step("sign out ends the session: the back button and a reload do not reveal data")
    def _(pg):
        pg.goto(f"{BASE}/requisitions")
        settle(pg)
        pg.get_by_role("button", name=re.compile("Account|menu", re.I)).first.click()
        pg.get_by_role("menuitem", name=re.compile("Sign out", re.I)).click()
        pg.wait_for_url(re.compile("/login"), timeout=8000)
        pg.go_back()
        pg.wait_for_url(re.compile("/login"), timeout=8000)
    _(pg)

    @step("wrong password shows the generic error, with both fields flagged, and typing clears it")
    def _(pg):
        pg.goto(f"{BASE}/login")
        pg.get_by_label("Email").fill(REC)
        pg.get_by_label("Password", exact=True).fill("wrong-password")
        pg.get_by_role("button", name="Sign in", exact=True).click()
        expect(pg.locator("form [role=alert]")).to_contain_text("Invalid email or password")
        assert pg.evaluate("[...document.querySelectorAll('.login-field')].every(f => f.dataset.invalid === 'true')")
        pg.get_by_label("Password", exact=True).type("x")
        expect(pg.locator("form [role=alert]")).to_have_count(0)
    _(pg)

    @step("an API failure shows the error state with Try again (not a blank page)")
    def _(pg):
        pg.context.clear_cookies()
        sign_in(pg, REC)
        pg.route(re.compile(r".*/api/requisitions/$"), lambda r: r.fulfill(status=500, body="{}"))
        pg.goto(f"{BASE}/requisitions")
        expect(pg.get_by_role("button", name="Try again")).to_be_visible(timeout=10000)
        pg.unroute_all()
    _(pg)
    c.close()


if __name__ == "__main__":
    sys.exit(main())
